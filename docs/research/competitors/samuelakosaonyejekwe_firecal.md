# Teardown: samuelakosaonyejekwe/firecal ("FireCal")

Repo: https://github.com/samuelakosaonyejekwe/firecal  · Live: https://samuelakosaonyejekwe.github.io/firecal/ (works; first load sometimes stalls on "Loading…", see section 4)
Read 31 Oct 2026 as text (gh api). Local copies: `scratch/firecal_src/`. Their published country JSONs: `scratch/firecal_data/`. My check script: `scratch/tools/firecal_check.py`. Screenshots: `shots/samuelakosa_firecal*.png`.

## 1. Harmonization as implemented

- **Unit:** the 0.1° "fire cell-day", meaning a cell with at least one detection on a UTC day. Set by `app/constants.py:12` (CELL=10) and `pipeline/build.py:56-63` (floor(lat*10), floor(lon*10)). Data is stored daily per (cell, sensor) and calibrated monthly.
- **Direction:** MODIS is mapped to VIIRS-equivalent. VIIRS S-NPP is the reference from 20 Jan 2012 (`analysis.py:118-132, 451-452`).
- **Equations** (`analysis.py:404-411`):
  - `k_area = (ΣV + 50·k_world)/(ΣM + 50)`
  - `k_month = (ΣV_m + 20·k_area)/(ΣM_m + 20)` (LAMBDA_AREA=50, LAMBDA=20; `constants.py:26-27`)
  - The harmonized series is VIIRS when it exists, otherwise k_month·MODIS (Terra+Aqua). For Nov 2000 to Jul 2002 a separate Terra-only factor k_terra is fitted on 2012-2021 Terra. Inside lost VIIRS orbit strips the value is VIIRS + k·MODIS (`analysis.py:452`).
- **k_world = 2.653** and **k_terra_world = 6.7234**: pooled ΣV/ΣM over all 208 countries for Feb 2012 to 2024, with outage days excluded (`pipeline/prior.py:155-186`). It is versioned in `app/resources/prior.json` (computed 2026-10-04; VIIRS 62.7M and MODIS 23.6M cell-days).
- **Filters** (`build.py:50-55`): `type = 0` only (drops volcanoes, static sources and offshore). MODIS confidence ≥ 30. VIIRS confidence n or h. There is no day/night split, no scan-angle or pixel-size term and no FRP use in the harmonization.
- **NOAA-20/NOAA-21:** not used at all. Only `modis` and `viirs-snpp` archives are fetched (`pipeline/fetch.py:21`), and the live feed is S-NPP NRT. S-NPP delivery ends 2 Nov 2026 and nothing replaces it.
- **Terra/Aqua drift:** handled only by excluding 2022 onward from the **Terra-only** fit (`constants.py:18-23`, `analysis.py:400-401`). The main Terra+Aqua k is still trained on the drifted 2022-2024 years, and Aqua drift is not modelled.
- **Sensor outages** (the strongest part): `prior.py:115-152` finds four kinds of outage over the whole world, using a rolling 61-day median of shares:
  - VIIRS out worldwide: 45 days.
  - VIIRS out in a 10° longitude strip, i.e. a lost orbit: 18 days.
  - MODIS or Terra out: 70 days.
  - Aqua out: 35 days.
  These days are left out of every fit and test and are filled from the other sensor or from climatology (`analysis.py:430-467`).
- **Overlap and training:** all of Feb 2012 to Dec 2024. The archive ends 2024, so the calendar stops at Dec 2024. The months from 2025 to last week are not filled; the README admits this.

## 2. Validation and leakage

- **Split:** leave-one-year-out on annual totals per area (`analysis.py:413-428`). The metric is the median APE of the annual VIIRS total. The monthly R² is **in-sample** (`analysis.py:470-474`). A VIIRS-independent check compares Terra×k_terra with (T+A)×k over 2003-2011 (`analysis.py:478-482`).
- **Leakage 1 (the requested check): confirmed in code, impact negligible.**
  - `_cv` excludes year y from the area fit (`analysis.py:406-407`), but the shrinkage target `prior` = k_world (`analysis.py:433, 408`) was pooled over all years including y (`prior.py:169-176`).
  - The README admits this.
  - I re-implemented `_fit_k/_cv` on their published daily JSON and matched the published LOYO: Nigeria 1.8 vs 1.9, Argentina 4.8 vs 4.7, Portugal 5.2 vs 5.8, Lebanon 26.9 vs 26.4, Cyprus 13.7 vs 13.9, Germany 28.1 vs 28.1.
  - Moving k_world by ±10% changes LOYO by at most 0.5 pp (Cyprus 13.3 to 14.2) and by 0.0 pp for large countries. Dropping one year out of 13 moves the pooled prior by far less than 10%.
  - Conclusion: the leak is real, but it cannot explain any of their numbers.
- **Leakage 2 (mild):** the outage days are detected from the VIIRS/MODIS ratio over all years, held-out years included (`prior.py:119-152`), and are then removed from the test (`analysis.py:443-446`). Days where the target collapses against the predictor are therefore dropped before scoring. The threshold is below 25% of the usual ratio, so only gross outages are affected.
- **Leakage 3 (mild):** the TERRA_DRIFT=2022 cut was chosen by inspecting the full record (`constants.py:18-23`).
- **Real problem: the metric flatters.** Annual country totals hide monthly error. My forward test reused their code (train Feb 2012 to 2019, test 2020-2024, as in CEDRUS's protocol; `firecal_check.py`). Results:

| Country | Their headline (LOYO annual) | Forward monthly WAPE | Forward median annual APE |
|---|---|---|---|
| Nigeria | 1.9% | 7.9% | 3.2% |
| Argentina | 4.7% | 9.8% | 5.8% |
| Portugal | 5.8% | 26.6% | 6.3% |
| Lebanon | 26.4% | 48.5% | 31.5% |
| Cyprus | 13.9% | 93.6% | 27.3% |
| Germany | 28.1% | 36.4% | 22.1% |

  - Portugal 2022 is +29% in the forward test.
  - Approximation: VIIRS-strip outage days were not removed in my version because the JSON does not carry them. My LOYO still matches theirs within 0.6 pp.
- **Not comparable to CEDRUS:** their numbers are country totals, while CEDRUS reports 0.25° cell-month WAPE. At country scale, CEDRUS's Portugal number should be compared with roughly 26.6% monthly.

## 3. Uncertainty and calibration

- There are no intervals on the harmonized values, k, or anomalies. Anomalies are plain z = (x−μ)/σ over all complete years (`analysis.py:562-582`). The "normal range" is the p10-p90 climatology (`analysis.py:591`). The nowcast is a percentile against past years (`analysis.py:821-875`).
- **No interval-coverage check exists anywhere in the code or tests.** The word "calibration" in the UI ("Robust calibration") refers to the MODIS→VIIRS ratio fit, not to uncertainty.
- The "indicative only" flag fires when overlap is under 3,000 VIIRS cell-days, R² < 0.5, or LOYO > 15% (`constants.py:30-32`, `analysis.py:501`). Lebanon, Cyprus and Germany are flagged.

## 4. Web app

- **Stack:**
  - Static GitHub Pages build (`pipeline/static_site.py`), plus an optional FastAPI server (`app/main.py`).
  - Vanilla JS, MapLibre GL 4.7.1 (cdnjs), a custom ECharts bundle, Esri light-gray tiles.
  - PWA with offline mode (`sw.js`).
  - Python and JS engines are kept in parity by `tests/test_engine_parity.py`.
  - GitHub Actions cron watchers rebuild the live layer (`.github/workflows/live.yml`, `guard.yml`).
- **Area selection:** search 208 countries, click a country, click a fire square (about 55 km area), draw a box (up to 20°×20° on the web, merging countries without double-counting), "◎ Me" geolocation, or typed coordinates. Lebanon and Argentina are both available.
- **CSV** (`app.js:1157-1170`): the **daily** series for the area, with columns `date, modis_cell_days, viirs_cell_days, harmonized_cell_days, frp_mw, source`. There are no raw hotspots and no intervals. Per-country JSON is downloadable, and the local server has an API.
- **Performance:**
  - Served JS is about 390 KB compressed (echarts 339 KB) and the country JSON is about 88 KB compressed for Nigeria.
  - In one run the browser fetched NASA's **32.6 MB** global 7-day CSV (`firms2…/SUOMI_VIIRS_C2_Global_7d.csv`), because live.js self-refreshes when the published copy is stale. That is heavy on mobile.
  - Lower charts are lazy-rendered and appeared blank in a full-page capture. This is probably IntersectionObserver lazy rendering (UNVERIFIED).
- **Accessibility:**
  - Many aria attributes: role=search/application/region, aria-pressed, aria-live, aria-busy, progressbar.
  - ECharts `aria.enabled` adds generated chart descriptions (`app.js:703`).
  - Keyboard: "/" focuses search and Esc cancels drawing (`app.js:1445-1448`).
  - Sequential ramp is a single-hue orange with monotone lightness; the anomaly ramp is a blue to red diverging scale (`styles.css:13-14`). Both read as CVD-reasonable, but there is no stated CVD test.
  - Light and dark themes.
- **What a judge sees in the first 30 s:**
  - A welcome modal with 6 numbered steps.
  - For `#country=Nigeria`: an "Early warning: this week" card ("1,444 fire cell-days, highest for these dates since 2001", 6-day bars), KPI tiles ("Typical fire season 10 Dec–14 Mar", "Harmonization skill ±1.9%, Robust calibration").
  - "What this means" briefings for Responders, Land managers and Scientists.
  - A month×year calendar for 2000-2024 with T / T/A / T+A / V era labels per row.
  - Very polished.
  - Two of four headless runs sat on "Loading…" for 30-45 s with no failed requests. This is probably network-dependent (UNVERIFIED).

## 5. Weaknesses a judge would notice

1. S-NPP only, with no NOAA-20/21, even though S-NPP ends 2 Nov 2026. The record stops Dec 2024, and 2025-2026 appear only in the live week.
2. There is no uncertainty at all, and the headline "±1.9%" is an annual country-total LOYO. Monthly error is much larger (table above).
3. The Terra-only era looks inflated. Nigeria's 2001 total is 242k versus 181-193k in 2002-2004, and 3 of its 5 "unusual months" are in 2001 (Jan +3.1σ, Nov +2.3σ, Mar +2.1σ). This is a possible k_terra era artefact (UNVERIFIED). Portugal's unusual months also include Dec and Sep 2001.
4. Drift handling is a single date cut, and only for the Terra-only factor.
5. The prior leak is documented but still present.
6. No day/night split, scan-angle term or FRP in the harmonization.

## 6. Best idea to borrow

**The sensor-outage catalogue**, with credit:
- worldwide VIIRS, MODIS, Terra and Aqua outage days;
- lost-orbit detection in 10° longitude strips;
- fills from the other sensor, versioned in `prior.json` (`pipeline/prior.py`).

Their list includes five worldwide VIIRS outage episodes in 2024. That may explain part of CEDRUS's +45% 2024 outlier and the false-zero months. Runner-up: the "indicative only" flag with a stated reason, and the Python↔JS parity test.

## Scores (1-5)

Scientific validity 3 · Uncertainty 1 · Calibration evidence 1 · Coverage 5 · App UX 5 · CSV 3 · Accessibility 4 · Storytelling 4
