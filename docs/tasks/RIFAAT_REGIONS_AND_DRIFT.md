# Rifaat: more regions, and putting numbers on MODIS drift

**Why:** rivals beat us on coverage. Their "global" claims are untested or very coarse: SHIFT uses 2.5° squares, about 250 km. Our answer is to cover **every region where our method sat a test, at 1 km detail**, so the app can say: "everywhere you can open here, we showed it works". You built the Tier 1 path (Syria, La Rioja, the forward tests, the accuracy notes), so you're the right person for this.

**Who touches what, so we don't collide:**
- **You:** `pipeline/`, `web/data/` (including `regions.json`), `tools/` scripts for data and analysis, and docs about regions and data.
- **Hussein and Claude:** `web/app.js`, `web/fx.js`, `web/*.css`, `web/index.html`, translations, the submission page.

If you need a change in the front end, write it in Slack or the pull request and we'll make it.

Work in **this repo** (`RifaatRamadan0/cedrus`), not the old `cedrus` repo: accept the GitHub invite first. Use one branch and one pull request per batch.

## Task 1: add the regions, in this order

Follow the same steps you used for Tier 1 (`docs/TIER1_PLAN.md`): source audit, export, forward test on the region's own data, accuracy note in `regions.json`. All boxes are already in `pipeline/regions.py`.

**Batch A, the eight sealed-exam regions (highest value, please first).** The model never saw these before its exams, and it passed there. Say so in each region's note:
- Round 3, burning days (the default unit): `northern_algeria`, `southern_france`, `south_australia`, `n_california`
- Round 2, hotspots: `central_spain`, `southern_italy`, `sw_australia`, `s_california`

**Batch B, development regions:** `greece`, `turkey`, `morocco`, `tunisia`, `central_chile`, `western_cape`, `israel`, `palestine`. Their accuracy note should say these regions were used for development, not as sealed exams.

**Rules:**
- **Same per-region forward test as Tier 1.** If a region fails it badly, leave it out and say why in the docs, as you did with Jordan and Cyprus. Honest beats bigger.
- **Cover 2000-12 to 2026-07, like the others.**
  - Regions defined by a box, not a whole country, need the FIRMS area API, so get your own free key at https://firms.modaps.eosdis.nasa.gov/api/map_key/. Put it in `.env` as `FIRMS_API_KEY` and never commit it.
  - `pipeline/01b_download_area.py` already waits out the transaction limit.
- **Keep the web files small.** Note the size of each region's `monthly_bd.json` and its yearly record folders in the pull request. Say so if one is very large.
- `python tools/probe_site.py` must still pass. It's Portugal-centred, so it mainly guards against breaking things.
- **Push Batch A as soon as it's done, even before Batch B,** so we can show it.

## Task 2: how far the MODIS satellites drifted, in numbers (small, about half a day)

We switch to VIIRS from 2022 because Terra and Aqua drifted from their planned orbits. Two rivals show this with numbers and we don't yet.

For each product region, and for Terra and Aqua separately, compute per year 2003–2026:
- the **median local solar time** of the overpass: `acq_time` (UTC) + longitude ÷ 15 hours, split into day and night passes;
- the **MODIS ÷ VIIRS ratio** of detections or burning days per year. This is the effect on the counts, and we already have it as the drift chart's input.

Write the results to `web/data/overpass.json`, in this shape:

```json
{"regions": {"portugal": {"terra": {"day": {"2003": 10.62}, "night": {}}, "aqua": {"day": {}, "night": {}}}},
 "method": "median local solar time of MODIS detections = acq_time UTC + lon/15; type 0, confidence >= 30",
 "built": "2026-11-14"}
```

Add a short `docs/MODIS_DRIFT.md` in plain words: how many minutes Terra and Aqua moved, from which year, with one chart. We'll draw it in the app.

## When you're stuck

Ask in Slack straight away. A 5-minute question beats a lost hour.

## Task 3 (after Tasks 1–2): NOAA-21, calibrated like NOAA-20

NASA's Suomi NPP notice (2 Nov 2026) tells users to switch to NOAA-20 and NOAA-21, but gives no cross-calibration. NOAA-21 flies in Suomi NPP's orbital plane, about 50 minutes apart, with the same 375 m sensor, and FIRMS carries its archive.

Fit a NOAA-21 → Suomi NPP factor exactly as J-S does for NOAA-20, from the months when both flew. Then use the average of NOAA-20 and NOAA-21 estimates in the estimated era. Before running it, write a short dated plan (`docs/NOAA21_PLAN.md`) saying what counts as a pass: for example, handover agreement of at least 80%, as in our exams.
