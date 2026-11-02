# Teardown: squadronzero/squadron-zero (SHIFT, Team Squadron Zero)

Repo: https://github.com/squadronzero/squadron-zero (82 files). Live: https://squadronzero.github.io/squadron-zero/
Read as text via `gh api` on 31 Oct 2026 (copies in `competitors/src/sz/`). Their published validation files were downloaded from Pages into `competitors/data/sz/v/`. Last commit: 2026-10-17. The site data release is dated 15 Oct (`meta.json` generated 2026-10-15, record end 2026-10-12).

## 1. Harmonization as implemented

- **Measures** (`settings.yaml:110-121`, `harmonise.py:15-19`):
  - "burning cells": 0.05 deg cells with at least one detection per day (L2 grid, `settings.yaml:29-30`);
  - FRP sum.
  - MODIS = the union of Terra and Aqua per cell-day.
- **Direction:** MODIS is put on the **S-NPP VIIRS scale**. From 2012-01-20 the record *is* observed S-NPP (`harmonise.py:5-6`).
- **Equation:** a ratio per place and calendar month, k = Σ S-NPP / Σ MODIS over the fit years (`factors.py:192-223`).
  - It is applied as cells_h = k per MODIS burning cell, and frp_h = FRP x k_frp (`harmonise.py:229-278`).
  - Output is aggregated to 0.25 deg x day L3 (`harmonise.py:280-289`), and to 1 deg daily tiles for the web.
- **Factor grid** (`report_resolution.json`; `resolution.py:1-30`):
  - production uses 2.5 deg "fine_shrunk" factors, pulled towards their 10 deg tile with a pseudo-count prior;
  - fallback chain: own month -> own all-year -> zone/tile -> world.
  - The 10 deg version left regional 2012 steps of Java +83% and Florida -31%.
  - Note: `report_harmonise.json` still names 10 deg factors in its `final_model_D7` text, while `factor_resolution_deg` says 2.5. That is a stale string.
- **Filters:**
  - `type == 0`; NRT rows with no type are kept unless they fall in a static-source cell (mask built from FIRMS type 1/2/3 in at least 2 years, applied in every year; 77,706 cells; `settings.yaml:58-62, 555-564`, `scan.py`, `report_factors.json`);
  - confidence nominal/high only (MODIS >= 30; `settings.yaml:64-72`);
  - FRP between 0 and 50,000 MW;
  - day and night both kept (counted separately);
  - optional local-solar-day basis (`harmonise.py:159-166, 467`).
  - **No scan-angle handling at all:** scan and track are not kept in L2.
- **Low-confidence check:** a pre-registered test of keeping low-confidence detections. The current filter was kept (`report_confidence.json`).
- **Terra/Aqua drift:** handled by **source choice** (D19). Merged MODIS is used to 2019 and Aqua alone from 2020 (`settings.yaml:117-121`). It was chosen by a pre-registered 6-test rule (`selection.py:1-25`; `report_selection.json`: winner MODIS_then_Aqua, score 73.4, global drift 0.10%/yr). Their own data show the late Aqua/Terra drift at up to 8.5%/yr (Africa).
- **Record start:**
  - Terra-only Jan-Jun 2002 is flagged "not comparable", and baselines start in 2003 (`settings.yaml:73-78`).
  - **The record starts in 2002, not 2000:** fetch `first_year: 2002` (`settings.yaml:533-535`). Nov 2000 to Dec 2001 is missing.
- **NOAA-20:**
  - **Not pooled.** It fills S-NPP gap days per 30 deg zone, with a tested factor (`harmonise.py:263-266`, `nodata.py`). 662,252 L3 rows are NOAA-20 fills.
  - It is meant to carry the record after S-NPP ends (`settings.yaml:306`, target S-NPP through 2100 with fills [NOAA-20, D19]).
  - Continuity fit 2019-2023, test 2024-2025 (`report_continuity.json`):
    - k_cells = 0.95-0.99;
    - raw detection ratio 0.99-1.07, which matches the README's "0.97-1.07";
    - test total error ≤ 2.5% for cells; FRP up to -8.3% (Kalimantan).
  - Fill test on simulated outages: NOAA-20 substitution error 1.8% for cells, 2.6% for FRP (`nodata__fill_test_scores.csv`).
  - **NOAA-21 is not used.**
- **Overlap/training period:**
  - `overlap_years` is 2012-2025 for selection, factors and resolution (`settings.yaml:142, 170, 192, 226`);
  - the Aqua piece uses 2020-2025;
  - the legacy v1 split was 2012-2021 / 2022-2025 (`settings.yaml:84-89`).

## 2. Validation and leakage

- **Tests:**
  - LOYO over 2012-2025;
  - backward test: fit 2016-2025, predict 2012-2015 (the use case);
  - a "forward" split only for comparison.
- **Headline metric:** **category agreement %**. Real and predicted months are both classed low / normal / unusual / critical against the S-NPP log1p monthly climatology (`selection.py:94-132`). They also report total error %, false alarms and drift.
- **Reported numbers:**
  - factors: fire-weighted score 79.1 (FRP) / 78.3 (cells); global backward error 3.1% / 2.7% (`report_factors.json`);
  - fine_shrunk factors: score 71.0 against 65.7 for coarse; fire-weighted median absolute FRP error 4.2% (`report_resolution.json`);
  - **2012 step gap: +0.8% (cells), -0.2% (FRP)**. A naive stitch jumps x2.64. Regional gaps reach ±9%: Florida -9.1, Iberia +9.2, Siberia -8.7 (`l3__step_2012.csv`);
  - anomaly rule: 26.9% false alarms, 83.3% of real unusual months caught (`report_harmonise.json`).
- **Reproduced:** from `l3__yearly_totals.csv` (script `scratch/sz_step.py`), the global step gap is +0.9% (cells) and -0.2% (FRP), and the raw switch is 2.64. This matches their numbers.
- **Global S-NPP/MODIS cell ratio** (`scratch/sz_ratio.py`): 2.67-2.81 in 2013-2023, but 2.53 in 2024 (outages) and 2.87 in 2025.

**Leakage and optimism found:**

1. **The spec's held-out claim is false for production.**
   - `docs/SCIENTIFIC_SPECIFICATION.md:62-63` says calibration is "fitted on 2012-2021 and tested on 2022-2025 and 2026, years the model never sees".
   - In fact the production factors are fitted on all of 2012-2025 (`settings.yaml:226`; `factors.py:410-415` calls `bootstrap(..., years, ...)` over every overlap year).
   - Variant selection also used LOYO over 2012-2025 (`factors.py:255-258, 375-408`).
   - Only Jan-Sep 2026 is untouched (`checks.py:184-254`, run once, locked). **Its result is not published:** `report_checks.json` is absent from `export.py:43-50`, Pages returns 404 for it, and the site data predate the checks commits of 15-17 Oct.
2. **Selection on the same folds that are then reported.**
   - The pre-registered sequences pick the variant with the best LOYO + backward score: mask, size split, borrow, smooth (`factors.py:394-408`); resolution adoption (`resolution.py` rule); D19 (`selection.py:232-251`).
   - The reported scores are the winners' scores on those same folds.
   - Pre-registration (rules committed before the runs, `settings.yaml:154, 177, 196, 234, 311, 362, 427`) limits the number of forking paths. The candidate sets are small, so the bias is small.
3. **The 2012-step GATE is in-sample** (`harmonise.py:542-567`).
   - The gap is [S-NPP(2013-15)/(k·MODIS(2009-11))] / [MODIS(2013-15)/MODIS(2009-11)], which reduces to S-NPP(2013-15) / (k·MODIS(2013-15)).
   - k is fitted on years that include 2013-2015, so this is a fit-consistency check, not a test.
   - An out-of-sample version would fit k without 2012-2015.
4. **The category baseline includes the test year.** `evaluate` builds the S-NPP climatology from all years, including the predicted year (`factors.py:261-262` → `selection.py:94-102`). This is mild and symmetric between real and predicted values.
5. **Coverage check** (`checks.py:258-360`):
   - Design: 95% month bands are calibrated on 2016-2019 LOYO residuals and verified backward on 2012-2015; accepted if coverage is 90-99%. This is good.
   - But the calibration-year fits include the 2012-2015 verify years (mild leakage).
   - **The result is unpublished.** The uncertainty on the live site (`uncertainty.json`, written by `harmonise.uncertainty_table`) is the *factor* bootstrap range, which their own docstring says is "about the factor, not about a single month" (`checks.py:16-17`).
   - Calibration of the published band is therefore UNVERIFIED and likely under-covers single months. This is an inference.

## 3. Uncertainty

- **Factor 95% range:**
  - built from a bootstrap that resamples whole years (200 draws, `factors.py:280-335`);
  - widened for borrowed factors by the measured spread between tile and zone;
  - plus confidence-drift and regional step terms in quadrature (`harmonise.py:347-387`).
- **Sizes:**
  - median ±77% for cells and ±109% for FRP over all factors;
  - fire-weighted ±23.5% for FRP;
  - tested tiles 42%, thin tiles 217% (`report_harmonise.json`, `report_factors.json`).
- The band is shown only for MODIS-era months, in the Trend chart (`App.jsx:89, 185-188`; `Charts.jsx:215-230`). There is no Poisson or sampling term.
- **Anomalies:** an "era-fair" variant widened sigma by the factor error. It was rejected by the pre-registered rule because false alarms fell 26.9→23.3 while caught fell 83.3→73.5. The 27% false-alarm rate is **shown to the user** next to the month grid (`App.jsx:91`).

## 4. Web app

- **Stack:** React + Vite + MapLibre, static on GitHub Pages (`web/`, `.github/workflows/pages.yml`).
- **Data:** a GitHub release `site_data.zip` of 134.5 MB: daily 1 deg values per 10 deg tile (`daily/*.bin.gz`), monthly 0.25 deg map layers, a zones mask, `uncertainty.json`, and `notfire.json` (`export.py:1-25`, `web/src/data.js`). The main JS bundle is 539 KB.
- **Area selection:**
  - a dropdown of preset places;
  - **"Draw an area"**: mouse-drag a box, at most 30 deg per side (`App.jsx:99-105`, `MapView.jsx:72-85`);
  - values are summed on a 1 deg grid, so edges are accurate to about 100 km (`Pages.jsx:158`);
  - no lat/lon entry and no polygon; drawing is mouse-only.
- **Views** (`App.jsx:41, 172-196`):
  - Explore: daily calendar canvas (every day since 2002), month-by-year anomaly-class grid (low/normal/unusual/critical), monthly trend with the 95% band;
  - "The 2012 switch";
  - Validation;
  - Method;
  - a "Show heat that isn't fire" layer (volcanoes, flares, offshore).
  - No-data days are shown as gaps, not zeros.
- **CSV** (`data.js:198-205`): one row per day for the area: `date, burning_cells_snpp_equivalent, fire_power_mw_snpp_equivalent, filled_from_partner, no_data`. **No raw hotspots and no uncertainty columns.**
- **Accessibility:**
  - light and dark themes from prefers-color-scheme;
  - single-hue orange sequential ramp;
  - class colours blue / grey / orange / dark rust (`App.jsx:22-31`);
  - canvas and SVG `role="img"` with aria-labels; `aria-live` story panel; `role="alert"` errors; nav with `aria-current`;
  - no axe or CI accessibility tests.
- **Live status:**
  - HTML, `meta.json` and every validation file return 200.
  - Headless Chrome hung on the WebGL map in 3 attempts, so **the first-30-seconds visual is UNVERIFIED**.
  - From the code, the first screen is the Explore view: header "One fire record from two generations of NASA satellites, 2002 to today", the map of the latest month, and the first preset place's calendar.

## 5. Weaknesses a judge would notice

- The record starts in 2002, while the challenge says 2000s to present.
- The fire-count quantity is "burning 0.05 deg cells", not hotspot counts.
- Boxes are capped at 30 deg and summed on a 1 deg grid: coarse for small areas such as a municipality.
- Per-month uncertainty is wide (median ±77-109%) and its coverage is unpublished. The "untouched 2026 test" exists but its result is not shown.
- The spec wording overstates the held-out design.
- No scan-angle treatment. No NOAA-21.
- The jargon-heavy decision log (D19, D21, D25, ...) leaks into reports.
- The README is out of date: it says "Planned: api/ and web/", but the web is built.

## 6. Best idea to borrow (with credit)

- **The sensor-switch step test as a headline metric.** Compare the harmonised record's step across the switch date (mean of 3 years after / 3 years before) with the step that MODIS alone shows over the same years, globally and per region (`harmonise.py:542-567`, `step_2012.csv`).
- Publish it next to the naive-stitch jump (x2.64).
- We should run it **out-of-sample**, fitting k without 2012-2015, which fixes their leak. We should also apply it at the S-NPP→NOAA-20 handover.
- Runner-up: show the anomaly classifier's measured false-alarm rate beside the calendar (`App.jsx:91`).

## Scores (1-5)

| Criterion | Score | Basis |
|---|---|---|
| Scientific validity | 4 | Global, per 2.5 deg x month ratio, drift handled by switching to Aqua, NOAA-20 continuity tested, pre-registered rules; but in-sample gate and selection on the same folds |
| Uncertainty | 3 | Factor bootstrap plus borrowing spread; not a predictive interval; no count noise |
| Calibration evidence | 2 | A well-designed coverage check exists in code, but no result is published and the site band is the factor range |
| Coverage (regions) | 5 | Whole Earth, 2002-2026, 10 test regions |
| App UX | 3 | Static and fast-loading data, draw box, 4 views; ≤30 deg box, 1 deg resolution, no lat/lon entry; visual UNVERIFIED |
| CSV | 3 | Daily area series with fill and no-data flags; no raw hotspots or bands |
| Accessibility | 3 | aria and themes, CVD-tolerant ramps; no automated audit; mouse-only draw |
| Storytelling | 4 | "The 2012 switch" view, honest false-alarm disclosure, "heat that isn't fire" layer |
