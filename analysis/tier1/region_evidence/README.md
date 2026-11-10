# Per-region forward tests, 10 November 2026

Each product region was tested on its own data with the frozen models: fit February 2012–December 2019,
score every month of January 2020–December 2021 against MODIS. This uses the same protocol, test functions and
five pass rules as the [La Rioja diagnostic](../la_rioja_evidence/REPORT.md). Nothing was tuned. The rules were
fixed before the first run, and the results are reported whatever they show.

Run: `.venv\Scripts\python -u analysis/tier1/region_evidence/run_validation.py cyprus jordan lebanon portugal syria`.
Each region's `REPORT.md` and `results.json` record the checksums, the outage exclusions and the yearly totals.

## What this test is and is not

- Portugal, Lebanon, Syria, Jordan and Cyprus were **development regions**: their 2012–2019 data helped choose
  the model. Their 2020+ MODIS was never used for fitting, tuning or choosing it (the tournament's leakage test,
  `docs/TOURNAMENT_RESULTS.md`). So this is a **forward test in time**, not a test on an unseen region. La Rioja
  was not a development region.
- 2022–2025 cannot be scored against MODIS in any region, because Aqua and Terra drift in orbit from 2022. The
  satellite-agreement row compares two VIIRS satellites. That is a consistency check, not an accuracy check.

## Results, burning days (the app's default unit)

| Region | MODIS burning days, 2020–21 | Region-month error | Simple conversion | Total bias | 80% coverage | Result |
|---|---:|---:|---:|---:|---:|---|
| Portugal | 2,019 | 15.3% | 30.8% | +3.8% | 76.6% | PASS |
| Syria | 2,595 | 19.5% | 27.0% | +7.3% | 84.1% | PASS |
| La Rioja | 3,320 | 11.0% | 19.9% | −4.4% | 81.2% | PASS |
| Lebanon | 245 | 28.3% | 58.0% | −16.0% | 89.5% | FAIL (total) |
| Jordan | 81 | 53.7% | 66.5% | +20.3% | 89.2% | FAIL (total) |
| Cyprus | 139 | 47.8% | 64.3% | −35.8% | 77.0% | FAIL (total) |

## Results, hotspots

| Region | Region-month error | Simple conversion | Total bias | Result |
|---|---:|---:|---:|---|
| Portugal | 15.4% | 20.8% | +4.3% | PASS |
| Syria | 27.5% | 24.4% | +5.7% | FAIL (region-month error more than 1 point worse than the simple conversion) |
| La Rioja | 13.4% | 13.7% | −4.8% | PASS |
| Lebanon | 34.7% | 57.7% | −21.4% | FAIL (total) |
| Jordan | 64.8% | 72.3% | +28.9% | FAIL (total) |
| Cyprus | 54.8% | 59.7% | −40.3% | FAIL (total) |

## Reading the failures

- **Every region beat the simple conversion on region-month error except Syria's hotspots, and on cell-month
  error except La Rioja's hotspots (62.8% against 61.9%, inside the 1-point margin).** The failures are mostly rule (c), which requires the two-year total to be within
  10% of observed MODIS.
- **Lebanon, Jordan and Cyprus have very few fires.** With 81–245 observed burning days over two years, random
  (Poisson) variation alone is 6–11% of the total, comparable to the 10% allowance. One large event moves the total a lot. In Cyprus, July and
  November 2021 account for almost two-thirds of the shortfall. This explains why the rule is hard to pass in
  small regions. It does not turn the failures into passes, and the rule was not changed.
- **Syria 2021 was overestimated in both units** (662 predicted against 490 observed burning days), outside the
  model's annual 80% interval. 2020 was close (2,122 against 2,105).
- Syria excludes August and September 2020 from the accuracy window under the existing outage rule. No other
  region excluded a month.

## Jordan and Cyprus removed from the app

Rule: **a region is shown only if its forward test had enough fires to measure (about 200 MODIS burning days in
2020–2021) and its grid-cell error is under 100%.**

| Region | MODIS burning days, 2020–21 | Grid-cell error (burning days) | Shown |
|---|---:|---:|---|
| Portugal | 2,019 | 79.9% | Yes |
| Syria | 2,595 | 68.9% | Yes |
| La Rioja | 3,320 | 59.9% | Yes |
| Lebanon | 245 | 78.4% | Yes |
| Cyprus | 139 | 100.0% | **No** |
| Jordan | 81 | 163.3% | **No** |

- **This rule was chosen after seeing the results**, on 10 November 2026. It is a product decision, not a
  pre-registered test, and it is recorded here so it can be judged as such.
- It separates Jordan and Cyprus from Lebanon, which failed the same ±10% total rule. Lebanon has enough fires
  to score, and its cell error is under 100%.
- Why the counts differ: per 1,000 km², Lebanon has about 53 Suomi NPP detections a year, Cyprus 24 and Jordan 4
  (2012–2025). Most of Jordan is desert; 62% of its detections are in its northwest corner. Jordan has more
  VIIRS detections than Cyprus but fewer MODIS burning days, which is consistent with small fires that the 375 m
  VIIRS pixels detect and the 1 km MODIS pixels often miss.
- Removed from the app only: both keep the `dev` role in `pipeline/regions.py`, their raw files and audits stay,
  and their reports stay in this folder. `web/data/cyprus/` and `web/data/jordan/` were deleted (recoverable from
  git history).

## Where the results are shown

`pipeline/regions.py` adds one shared note to every region, stating that accuracy is checked against MODIS only
up to 2021. Syria and Lebanon each get their own result note and a border-cell note: 11 of Lebanon's 28 cells
are shared with Syria and hold 23% of Lebanon's estimated values. Notes are refreshed with
`python pipeline/export_v2.py --catalog-only`, which rewrites only `regions.json` and regenerates no region data.
`tools/check_tier1_preservation.py` now compares Portugal's and Lebanon's catalog entries without their `notes`,
and checks the notes against `regions.py` instead. Portugal shows its passing result with its limits: evidence for
regional-level performance in 2020–2021, not for years after 2021 or single cells (78–80% cell error).

Not added: a note that Portugal's border cells extend into Spain. Unlike Lebanon and Syria, there is no second
exported grid to compare with, and no country outlines are available locally, so it is unverified. Natural Earth
country boundaries would settle it; this is lower priority than other work.
