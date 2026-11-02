# Teardown: stachulemko/firecal

Repo: https://github.com/stachulemko/firecal (27 files). Read as text via `gh api`; copies are in `competitors/scratch/src_stach/`.
**No live URL.** The repo has `homepage: null` and `has_pages: false`, and there is no Dockerfile or deploy config. The app is a FastAPI server you run locally (`firecal serve`). History: 10 commits, all stamped 2026-10-10T11:43:18Z (one bulk upload), so the development chronology can't be checked. Presets: Poland, Portugal, Paraná Delta, Sierras de Córdoba, Corrientes/Iberá, Galicia, Greece (`firecal/pipeline.py:32-47`). Any country, region or drawn box can be analysed on demand.

**Relation to samuelakosaonyejekwe/firecal:** they share only the name. **No shared code found.** samuelakosa's repo is laid out differently (`app/analysis.py`, `pipeline/*.py`, duckdb, no LightGBM; its `requirements.txt` has no lightgbm or scikit-learn). Its `app/main.py` differs and none of stachulemko's identifiers (`TransferFeatures`, `QuantileMap`, `level_factor`, `sensor_availability`) appear in it. samuelakosa's repo was created 2026-10-01 and stachulemko's 2026-10-10. I did no deep read of samuelakosa.

## 1. Harmonization as implemented

- **Reference sensor: MODIS → VIIRS S-NPP** (`config.py:89`, `harmonize.py:1-20`). This is the opposite direction to Kiln Watch and CEDRUS. The unit is S-NPP **detection counts** (pixels, not cell-days) per grid cell per **UTC** `acq_date` (`sources/firms.py:66-70`). There is no local-day shift.
- **Grid:** adaptive, the finest of 0.1/0.25/0.5/1.0° that keeps ≤1600 cells over the AOI bbox (`config.py:92-93`, `geo.py:199-210`). The time unit is daily.
- **Filters:** confidence nominal+high (`qa_filter`, `harmonize.py:85-94`; MODIS ≥30, `config.py:90`). `type` > 0 is dropped (volcano, static, offshore). For NRT data, which has no `type`, a detection is dropped if it falls within about 400 m (with halo) of an archive-flagged static location (`harmonize.py:67-82`). Day/night enters as Terra/Aqua day and night counts in the features. Scan angle enters only through `m_area`, the summed MODIS pixel footprint (`harmonize.py:327-329`).
- **Outage detection** (`harmonize.py:101-176`): a sensor counts as down if it is silent while a same-family sensor (rescaled) implies ≥15 detections (cross-family ≥45), or if it is silent ≥7 days while its own ±15-day climatology implies ≥100. This is good practice: "no data" is not treated as "no fire".
- **Transfer model** (`harmonize.py:268-415, 535-660`): a LightGBM Poisson model at cell-day level, 250 rounds, `max_delta_step` capped. Features (`harmonize.py:268-271`): Terra/Aqua day and night counts, FRP, footprint area, ±1/3/7-day MODIS windows, neighbour sums, a MODIS cell climatology (all years), lat/lon, and day of year. Quiet rows are subsampled at 20% and up-weighted. 15% of rows are trained with Aqua masked so the model also covers the Terra-only era (Nov 2000 – Jul 2002).
  - Then `LevelModel` (`harmonize.py:386-414`) computes AOI calendar-month ratios ΣV/Σ(T+A), shrunk toward the global ratio with k=20. `level_factor` (`harmonize.py:417-430`) rescales the ML daily series to the ratio level over ±15 days ("ML + level").
  - Then `QuantileMap` (`harmonize.py:436-480`): a ±30-day empirical quantile mapping that turns the expected value into a "most likely day" count, with a realistic share of zero days.
- **Training/overlap:** stable years 2012–2020 (`config.py:95-96`; 2020 is included in CV and in production, not held out). The production model is fitted on all stable years (`harmonize.py:611-613`).
- **Assembly** (`harmonize.py:707-764`): observed S-NPP whenever available. In S-NPP gaps, NOAA-20 × r20, else NOAA-21 × r21. r = ΣS-NPP/ΣNOAA over all common days, all cells, one global scalar (`harmonize.py:635-641`). The MODIS transfer is used **only** before 2012 and in all-VIIRS gaps. NOAA-20/21 are never pooled into the record. They are averaged only as forecast predictors (`multi_sensor`, `harmonize.py:667-696`).
- **Orbital drift:** avoided by training on ≤2020. A "drift test" scores the transfer on years >2020 against observed S-NPP (`harmonize.py:620-631`). The score is computed but not printed in the README. Because post-2012 output is raw S-NPP, drift does not affect the published record.

## 2. Validation

- **Transfer:** 3-fold blocked CV over whole interleaved years (`folds = stable[i::3]`, `harmonize.py:550`), e.g. {2012,2015,2018}. The QuantileMap is validated leave-one-year-out (`harmonize.py:588-595`). Metrics (`_agg_metrics`, `harmonize.py:502-532`) are daily/weekly/monthly/yearly r, log-r, bias, MAE-log and extreme-day hit rate. README numbers: Portugal daily r 0.927, monthly log-r 0.972, bias −1.9%; Paraná 0.934/0.916/−5.7%; Poland 0.807/0.889/−0.7%. Reproduction is **not cheap**: there are no published outputs in the repo, and the pipeline would have to be run, which the brief forbids. UNVERIFIED.
- **Leakage hunt (transfer):**
  - No target leakage. Features are MODIS-only. The README and `harmonize.py:272-273` record that a VIIRS-climatology feature was tried and rejected for leakage. That is the full extent of the "leakage-checked" claim: **there is no automated leakage test** (`tests/test_core.py` has 17 unit tests on synthetic data, none for leakage).
  - `clim_m_cm` (MODIS cell climatology) uses all years, including CV test years (`harmonize.py:308-316`). This is transductive on the input only. Acceptable.
  - Hyperparameters (250 rounds, ±15-day level window, k=20, QM ±30) and the "ML+level beats both" choice were apparently judged on the same CV folds that are reported. Selection on the evaluation set is UNVERIFIED (no tuning code in the repo).
- **Forecast** (`forecast.py:440-539`): train = full VIIRS years before the validation year. Validation = 3rd-last full year (used for early stopping and the residual model). Test = last two full years, 2023–2024 (`forecast.py:450-452`). The climatology uses only years before the validation year (`forecast.py:453-454`).
  - **Leak 1 (test-year tuning):** `MIN_COUNT_ROUNDS = 150` was set by looking at the test years. The comment says so outright (`forecast.py:400-403`: "On the unseen test years, 150 trees ranked days better (critical-day AUC 0.72 -> 0.75 …)"). The README also lists alternatives "Rejected … with measurements on the test years" (an area-level second model, 400 trees). So the 2023–24 scores are **not clean holdout**.
  - **Leak 2 (weather oracle):** target-day weather is observed reanalysis (`forecast.py:283`). It is disclosed as an upper bound, and a persistence-weather lower bound is also reported.
  - **Minor:** backtests in the validation year are labelled "out-of-sample" (`pipeline.py:137, 145`), although that year drove early stopping and residual calibration.
- README forecast numbers: cell AUC 0.83–0.86 vs climatology 0.74–0.82; critical-day AUC 0.75–0.99; skill vs climatology +0.28 to +0.44. All UNVERIFIED.

## 3. Uncertainty and calibration

- **Reconstruction bands** (MODIS era): empirical 10/90% log-residual quantiles in 4 magnitude bins, taken from the CV out-of-fold daily AOI residuals (`harmonize.py:576-583`, `_bands` `harmonize.py:699-704`). They are exported as `activity_p10/p90`. **Coverage is never checked out-of-sample**: they are ~80% by construction on the same residuals. The drift years could have served as a test but are not used for that. Bands are daily only; there are no monthly or annual intervals.
- **Forecast bands:** `ResidualModel` (`forecast.py:318-363`) holds empirical residuals by lead group × magnitude tercile, calibrated on the validation year. **Coverage is checked on the test years** (`interval80_coverage`, `forecast.py:511`). README: 0.76–0.77 (Poland, Portugal) and 0.89–0.91 (Paraná) against a nominal 0.80. They say an NB model covered 98%.

## 4. Web app

- FastAPI (`app/main.py`, 13 routes) plus a single-page vanilla JS front end with Leaflet 1.9.4 from a CDN and hand-written SVG/canvas charts (`app/static/app.js` 58 KB, `charts.js` 18 KB, `style.css` 13 KB). The front end is light, but the server does heavy work. The first analysis of a country downloads that country's FIRMS yearly archives (README: about 1 min, 2–3 GB for Brazil or Russia), then trains two LightGBM stacks (1–3 min).
- Area selection: preset dropdown, country/region search (233 countries + 294 states), map click, **draw rectangle** (`app.js:44-85`), or **W/S/E/N number inputs** (`index.html:37-40`).
- CSV: `/api/analyses/{id}/daily.csv` (`main.py:225-242`) gives a daily AOI table: S-NPP-equivalent, most-likely day, p10/p90, source, normal, 7-day percentile, anomaly, raw counts per sensor, FRP. **No raw hotspot CSV.**
- Accessibility: light/dark themes; a sequential heat ramp light→dark (`--heat-1..6`) and a blue–red diverging ramp (CVD-reasonable, but not checked); some aria (`aria-live` messages, tablist roles, labels on inputs). No colour-blind test.
- Live: **not deployed**, so a judge sees nothing unless they run it locally.

## 5. Weaknesses a judge would notice

- No live demo, and a single bulk commit on 10 Oct.
- MODIS→VIIRS direction: post-2012 values are just raw S-NPP. Most of the "harmonization" applies only to 2000–2011, and the S-NPP→NOAA-20 continuity is one global scalar.
- The "leakage-checked" claim is prose only. The forecast test years were used to pick training length and to reject alternatives (`forecast.py:400-403`).
- Reconstruction intervals are not calibration-checked.
- Days are UTC dates, not local, which matters for night passes in the Americas.
- The challenge's hotspot CSV is missing.
- The forecast is the polished part. It goes beyond the brief (FWI, ENSO, Open-Meteo) but adds weather-oracle caveats.

## 6. Best idea to borrow

**Sensor-outage inference** (`harmonize.py:101-176`): mark a sensor-day "down" when the sensor is silent but a same-family sensor, rescaled by the long-term ratio, implies ≥15 detections, or after a ≥7-day silence where its own climatology expects ≥100. It catches the 2001 Terra gap and the S-NPP safe-hold of 27 Jul 2022. Cheap, keyless, and directly protects anomaly maps from fake "no fire" months. Runner-up: the **expected vs most-likely-day quantile map**, which fixes the visible 2012 seam in a daily heat map. Credit stachulemko/firecal if we use either.

## Scores (1–5)

Scientific validity 3 · uncertainty 3 · calibration evidence 2 (forecast only) · coverage 4 (any area, on demand) · app UX 2 (local only) · CSV 3 · accessibility 3 · storytelling 2.
