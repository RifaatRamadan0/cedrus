# Teardown: Aalvee-Aarham/kiln-watch

Repo: https://github.com/Aalvee-Aarham/kiln-watch · live: https://aalvee-aarham.github.io/kiln-watch/ (GitHub Pages, deployed by `.github/workflows/deploy.yml`, daily cron `0 3 * * *`; last deploy runs succeeded 28–31 Oct 2026).
Read as text via `gh api` (copies in `competitors/scratch/src_kiln/`). Live data files fetched into `competitors/scratch/live_kiln/`. Sanity script: `competitors/scratch/scripts/kiln_check.py`.
Region: **Bangladesh only** (64 districts + upazilas, 560 calendars). Everything is cell-days in a 0.01° grid.

## 1. Harmonization as implemented

- **Grid / unit.** 0.01° grid (`kilnwatch/config.py:22-26`, `grid.py:12-20`). A detection becomes a **fire cell-day** per (cell, local date, sensor, pass) (`grid.py:46-48`); duplicates within a cell collapse. Local date = UTC+6 (`ingest.py:211-213`). Season year starts 1 July (`config.py:30`, `grid.py:33-43`).
- **Rate (the cloud-free denominator — VERIFIED).** `rate = 1000 * fire_cells / clear_cells`, NaN if clear fraction < 0.2 (`harmonize.py:230-245`). Clear fraction = mean over the unit of a 0/1 mask where MOD14A1/MYD14A1/VNP14A1 `FireMask` ∈ {5,7,8,9} (`gee.py:15, 38-59`), reduced at 1 km scale in Earth Engine. Caveats in code: the calibration uses the **division** clear fraction for both "kiln" and "other" cells (`harmonize.py:233-234`); NOAA-20/21 reuse the **S-NPP** clear fraction (`pipeline.py:73-75`) and, after S-NPP ends, the S-NPP day-of-year climatology (`metrics.py:148-161`). The daily xxD14A1 mask is a day composite, so the same denominator is used for day and night passes (`pipeline.py:142` divides by 2 for the two passes).
- **Reference sensor (Aqua anchor — VERIFIED).** Direction is VIIRS → **Aqua-MODIS equivalent** ("MYD-eq"). Chain `A<-N`, `N<-J1`, `J1<-J2` (`harmonize.py:18`). Model M0: β = Σ rate_Aqua / Σ rate_SNPP per stratum (division × month × pass × kiln/other) (`harmonize.py:69-92`) with a 6-rung pooling ladder (month→season bucket→division→national; night strata never pooled with day, `harmonize.py:21-37, 85-86`); a stratum needs ≥100 S-NPP cell-days and ≥10 paired days (`config.py:36-37`). M1 = sklearn Poisson GLM (`harmonize.py:118-124`) only ships if its LOSO MAE is >10% lower; **M0 was selected** (`reports/harmonization_report.md`: MAE M0 0.0037 vs M1 0.0047).
- **Pairing.** Same division, same local date, same pass, both sensors observed (`harmonize.py:52-66`). Not same pixel; same-day aggregate.
- **Training period.** `A<-N` uses `CALIB_SEASONS` 2012-13 … 2020-21 (`config_derived.json`; rule "ending before Aqua's drift", `ingest.py:270`). `N<-J1` is fitted on **all** overlapping seasons with no holdout (`harmonize.py:256`). `J1<-J2` uses NRT from 2026-07-01 only and **all 84 strata fail to calibrate** (rung −1 in `reports/harmonization_report.md`): NOAA-21 is not in the record.
- **Record assembly** (`metrics.py:132-145, 158-161`): Aqua (weight 1) before 2012-07-01; S-NPP × β1 from 2012-07-01 to 2026-11-02; NOAA-20 × β1·β2 after. **Terra is never used** in the harmonized series (shown only as raw). No NOAA-20/S-NPP pooling or dedup: one sensor per era.
- **Orbital drift.** Handled by design: Aqua only anchors to 2012-07, and β is fitted on seasons ending 2020-21. Nothing models drift explicitly. Side finding (live `harmonization.json`): Aqua's own national rate drops to 6.8 and 6.4 in 2021-22/2022-23 while harmonized S-NPP reads 13.3/18.8, then recovers to 13.9/20.2. Cause UNVERIFIED (drift or Aqua data gaps); it is useful evidence that post-2021 Aqua is not a usable reference.
- **Filters.** Confidence nominal+high (MODIS conf ≥30) (`config.py:35`, `pipeline.py:27`, `ingest.py:188-190`). SP supersedes NRT per sensor-day (`ingest.py:235-239`). **No `type` (static-source) filter** in the calendar; `type==2` is only used in kiln gates (`gates.py:172`). They argue kiln heat is 0.15% of detections. **No scan-angle term** (the GLM has an optional `scan` column, `harmonize.py:113-114`, but M0 shipped). Day/night is handled as a stratum.

## 2. Validation

- **Pre-registration: VERIFIED.** `PREREGISTRATION.md` was first committed in `0d755c5` (2026-10-05 21:47Z) together with only docs. The first code and results came in `01ff756` (2026-10-06 05:43Z). The current `docs/PREREGISTRATION.md` is byte-identical to the original (CRLF-normalised diff). `meta.json` pins `prereg_sha: 0d755c5`. That no data were looked at before the commit is UNVERIFIABLE.
- **LOSO (leave-one-season-out) over the 9 calibration seasons** (`harmonize.py:140-178`). β is re-estimated without the held-out season, the interval is β-bootstrap draws × Poisson noise, and the unit is division × ISO week × pass × loc. Pooled 95% coverage is **0.985 [0.982, 0.987], n=13,340: FAIL** against the pre-registered 0.90–0.97 target. They publish it as a failure in `docs/BLOCKERS.md`. Mostly near-zero counts, so it over-covers.
- **Seam test + Chow (VERIFIED and reproduced).** `seam_stat` (`harmonize.py:193-204`) compares the mean of 2012-13/2013-14 with 2009-10/2010-11. `chow_test` (`stats.py:68-87`) is a linear-trend F-test on the national season series, with the break at 2012-13 and 2011-12 dropped. My recomputation from live `harmonization.json`: d_raw 55.12, d_harm 1.59, Chow p raw 5.95e-5, harm 0.286. This matches the README exactly.
  - **Caveat (in-sample, near-tautological):** the "after" seasons 2012-13/2013-14 are **inside the β calibration window**, and β is fitted precisely so that S-NPP×β ≈ Aqua. Over the calibration seasons, national harm/Aqua = **1.000** (my check). The seam test therefore mostly re-tests whether Aqua itself jumped (Aqua's own 2012-14 vs 2009-11 change is −0.33). It is not leakage in the classic sense, but it is not out-of-sample evidence.
- **Overlap agreement (exploratory)** `validate.py:58-87`: VIIRS/Aqua ratio and Lin's CCC on district-months. README claims held-out seasons give 4.8× → 1.04×. I could not reproduce it: the live `harmonization.json` has no `overlap` key. On the published national series, held-out (2021-22…2025-26) harm/Aqua = **1.29** (raw 4.36). That gap is confounded by the Aqua collapse in 2021-23. Their 1.04 is UNVERIFIED.
- **Outlook backtest** (`validate.py:123-170`): LOSO Brier skill 0.075 [0.056, 0.097]. **Leak:** the p90 normal that defines an "unusual day" uses all seasons including the held-out one. The docstring admits this (`validate.py:127`). `outlook.json` returned **404** on the live site (31 Oct). By design it ships only from 1 Nov or when it is estimable (`export.py:254-260`).
- Model selection M0 vs M1 is made on the same LOSO run whose coverage is reported (`harmonize.py:279`). The rule was pre-registered, so the effect is minor.

## 3. Uncertainty and calibration

- **Season-block bootstrap: VERIFIED** (`harmonize.py:95-107`). It resamples whole seasons with replacement, 1000 draws for `A<-N`. With only 9 calibration seasons, the β intervals rest on 9 blocks.
- **Three different interval formulas** are shipped:
  1. National yearly bands: β draws only, **no count noise** (`pipeline.py:135-168`). My check: they contain Aqua's observed value in only 5/9 calibration and 1/5 later seasons. These are parameter bands, not predictive bands.
  2. Per-area weekly bands (`pipeline.py:283-297`): a delta method with `var = Σ(w² + var β)` per cell-day. This treats β error as **independent across cell-days**, but β is shared within a stratum. The β term is understated by about a factor of N (cell-days per week). Coverage of these bands is **never checked**.
  3. LOSO intervals: the only ones checked. Result 0.985, which over-covers.
- Drawn boxes (`web/src/lib/calendar.ts:135-158`, `ExplorerPage.tsx:393-396`) use an **unweighted mean of the division's β across all strata** (fallback 0.25), the district clear fraction, and **no interval**.

## 4. Web app

- Stack: React 19 + Vite 8 + Tailwind 4, ECharts 6, globe.gl/three, Cesium (Space page), PWA (`web/package.json`). Static GitHub Pages. All analysis happens in the browser from a precomputed export.
- Sizes (live): entry JS 255 KB + ui 99 KB + CSS 107 KB (uncompressed), plus lazy chunks. Data: `harmonization.json` 141 KB, `nrt/current_season.json` 36 KB, a per-unit `calendar/<id>.json`, and world geojsons up to 3.4 MB (`data/static/world_states.geojson`).
- Area selection: search (EN/Bangla), tap a district or upazila, geolocation (matched on the device), **draw a box**, or a **keyboard coordinates form** (`ExplorerPage.tsx:159`). Bangladesh only, so any box outside Bangladesh has no data.
- CSV: per-area **daily table** (`calendarToCsv`, `calendar.ts:128-133`): date, harmonized MYD-eq, split by harvest window, raw rate per sensor, activity index. Also a research zip of CSV + Parquet (`kilnwatch/research.py`). **No raw hotspot CSV**: lat/lon are deliberately forbidden in public outputs (`research.py:24`, `config.py:51`). The challenge asks for "downloadable CSV of hotspots", so this misses it.
- Accessibility: day/night themes; the CVD-warning split colour gets a **decal pattern** (`theme.ts:63`, `charts.tsx:62`); a keyboard alternative to drawing; `prefers-reduced-motion` is respected; aria attributes on Explorer. The fire ramp is a 5-step yellow→dark red, which is lightness-monotone.
- Freshness: base calendars are from build `6903ee1`, generated **7 Oct 2026** (footer + `meta.json`). Only the NRT banner and `current_season.json` update daily (updated_at 2026-10-31T09:24Z).
- **First 30 s for a judge** (headless at 1440×900, `shots/kiln-watch_home.png`, `shots/kiln-watch_area.png`): a large headline, "NASA satellites have watched Bangladesh burn for 23 years. We made their records agree.", two CTAs, a red banner "Today is Day 123 of the 2026-27 burning season. 30 districts have had unusual fire activity.", and 11 nav tabs. On my (very slow) connection the hero chart and the Area page stayed as loading skeletons after about 60–110 s. Assets were downloading at a few KB/s here, so I could not judge real load time; UNVERIFIED on a normal connection. The site is not broken, and the HTML and data endpoints return 200.

## 5. Weaknesses a judge would notice

- One country only (Bangladesh). The "world map" just shows where they have no coverage.
- The headline seam result (97% of jump removed, Chow p 0.29) is **in-sample**: β was fitted on those seasons.
- The pre-registered coverage test **failed**. They say so honestly, but it is still a fail.
- No raw hotspot CSV. Terra is unused. NOAA-21 is uncalibrated. NOAA-20's β2 has no holdout.
- Cell-days per 1,000 clear cells (Aqua-equivalent) is a hard unit for lay users.
- Scope sprawl: kilns, night lights, radar, news scraping, a Gemini agent, a 3D globe, 11 tabs. The core harmonization is a small part of the site.
- Per-area 95% bands use a formula that understates β uncertainty, and those bands are never calibration-checked.

## 6. Best idea to borrow

**The cloud-free denominator from the daily fire-mask products** (MOD14A1/MYD14A1/VNP14A1 `FireMask` classes 5/7/8/9, mean over the area per day, `gee.py:38-59`), with "not seen" stored separately from "no fire" (NaN when the clear fraction is below 0.2). Close second: **pre-register thresholds in a commit before the code, then publish the failures**. That is cheap and very credible with judges. Credit Kiln Watch if we use either.

## Scores (1–5)

Scientific validity 4 · uncertainty 3 · calibration evidence 3 (checked, failed conservative, other bands unchecked) · coverage 1 · app UX 4 · CSV 2 · accessibility 4 · storytelling 5.
