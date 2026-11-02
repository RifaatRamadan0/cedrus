# Teardown: Kaushik2210/Ember-Line (EMBERLINE)

Repo: https://github.com/Kaushik2210/Ember-Line (186 files). Live: https://emberline-zeta.vercel.app
Read as text via `gh api` on 31 Oct 2026 (copies in `competitors/src/ember/`). Nothing was cloned or run.

## 1. Harmonization as implemented

- **Unit and scale:** one model per analysed region (a bbox or uploaded shape), fitted on **region-total weekly sums**. It is not fitted per cell. `normalize.py:1-18`, `series.py:297-309` (a week counts only if all 7 days were observed), `pipeline.py:238-240`.
- **Direction:** MODIS is mapped to **VIIRS-equivalent** units (VIIRS S-NPP is the reference). In log1p space: u = log1p(MODIS weekly), v = log1p(VIIRS weekly).
- **Candidate models** (`normalize.py:111-176`):
  - Huber log-log line (epsilon 1.35);
  - Theil-Sen log-log line;
  - seasonal quantile mapping (DJF/MAM/JJA/SON, 51 quantiles, at least 20 weeks per season, otherwise pooled);
  - isotonic regression.
  - Baselines `raw` and `scale` (median log shift) are scored but never selected.
- **Harmonized daily series** (`normalize.py:313-356`):
  - Where VIIRS observed, the series is **raw VIIRS** with no band.
  - Elsewhere it is the weekly MODIS value mapped through the model, then split across the days of the week in proportion to MODIS's daily pattern (uniformly if the week is empty).
  - So the output is a spliced series: VIIRS from 2012-06, reconstructed values before that.
- **Metric:** the default is `frp_sum_mw` (summed FRP), not counts (`pipeline.py:172`, `scripts/validation_report.py:32`). `det_count`, `active_1km` (unique 0.01 deg footprints) and `cells_active` are available (`grid.py:99-109`).
- **Grid:** `GridSpec` defaults to 0.25 deg regular, or H3 res 5 (`grid.py:123-127`). It only affects `cells_active`; the model works on region totals.
- **Filters** (`quality.py:19-29`):
  - MODIS confidence >= 30; VIIRS confidence n or h;
  - `type == 0`, with rows that have no type kept;
  - day/night: both by default;
  - persistent-source mask: 0.02 deg cells active on more than 10% of observed days, only applied when the record has at least 365 days.
  - **No scan-angle filter or correction.** Scan bins are used only in the agreement diagnostics (`overpass.py:29`).
- **Satellites:**
  - Only `MODIS_SP` and `VIIRS_SNPP_SP` are used (`pipeline.py:57`).
  - NOAA-20 is opt-in for prefetch and is **not used** in harmonization (`docs/DECISIONS.md:46-47, 86-87`, `punjab-haryana.md:190`). NOAA-21 is absent.
  - So there is **no plan for S-NPP's end on 2 Nov 2026**.
- **Terra/Aqua:**
  - Weeks before 2002-07-04 use a separate Terra-only model, fitted on Terra's overlap with VIIRS (`pipeline.py:358-399`, `normalize.py:359-379`).
  - **Terra drift is not corrected** (README "Limitations"). That Terra-only model is trained on 2012-2026, which includes the drifted Terra years from 2020 on, and is then applied to 2000-2002.
- **Overlap/training period:** every complete overlap week, 2012-06 to 2026-06 (734 weeks for Punjab, `punjab-haryana.md:112`).
- **Diagnostics:** coincident-overpass matching of Aqua-MODIS against S-NPP-VIIRS within 750 m and 30 min, using a KD-tree in 4D (`overpass.py:1-92`). It reports corroboration rates by FRP bin, scan bin and day/night (`punjab-haryana.md:76-108`).

## 2. Validation and leakage

- **Split:** leave-one-year-out (LOYO) over the overlap years, on weekly region totals (`normalize.py:254-262`).
- **Metrics:** r2_log, mae_log, mae_raw, bias_rel, Spearman and coverage (`normalize.py:183-193`).
- **Reported results, Punjab & Haryana FRP** (`docs/validation/punjab-haryana.md:114-123`):
  - quantile mapping is chosen: mae_log 0.514, r2_log 0.892, bias +1.4%, coverage 0.899;
  - scale baseline: 0.603; raw MODIS: 0.922;
  - interval half-width 1.144 log units, i.e. about x3.1 (I checked: e^1.144 = 3.14);
  - Terra-only model: mae_log 0.777, about x6.6 (`:131-136`).
  - **This is the only real-data validation report.**

**Leakage and optimism found:**

1. **Model selection uses the same folds that produce the reported score.**
   - `fit_normalizer` computes out-of-fold LOYO predictions for every candidate (`normalize.py:256-262`), then picks the lowest `mae_log` on those same predictions (`:281-284`). The CV table it reports is that same table.
   - There is no nested CV, so the winner's 0.514 is optimistically biased.
   - The bias is small: 4 candidates, and the runner-up isotonic model scores 0.575.
2. **The cross-conformal coverage check is held out, but only loosely.**
   - Good: coverage for year y uses residuals that are out-of-fold for year y, against a threshold from the other years' residuals (`normalize.py:268-277`).
   - But each of those other years' residuals came from a model trained with year y included, so year y's data still leaks into its own threshold. The effect is mild.
   - Coverage is marginal only: pooled over weekly region totals, not split by season or by magnitude.
   - It does not discriminate. `raw` and `scale` also reach about 0.90 (`punjab-haryana.md:120-121`), so it confirms only that the quantile machinery works, not that the model is good.
3. **The check does not match how the product is used.**
   - LOYO interpolates interior years from 2012-2026. The product extrapolates **backwards** to 2000-2011, and no backward or temporal-block test exists.
   - For weeks above the fitted range, `EXTRAPOLATION_WIDEN = 1.5` is an untested constant (`normalize.py:47, 225`).
   - Coverage of the **daily** values (the weekly band split by MODIS's daily share) and of monthly sums is never checked.
4. **Terra-only model trained on drifted Terra.** It is fitted on 2012-2026 Terra (`pipeline.py:378-384`) and applied to 2000-2002. Terra's equator crossing drifts from 2020 (their own annotation, `punjab-haryana.md:191`).
5. **Data smell in their own report.** For the 2026 half-year, the VIIRS/MODIS det_count ratio is 7.73 against about 4.5 in every other year (`punjab-haryana.md:34`). These weeks are inside the 734 training weeks. Cause UNVERIFIED: it could be season mix in a partial year, or MODIS drift/degradation.

## 3. Uncertainty

- **Method:** a split-conformal-style constant: the 90% quantile of absolute out-of-fold log residuals, the same width for every week (`normalize.py:196-201, 287`), applied as exp(v ± q).
- Observed VIIRS days carry **no band**: no Poisson or detection uncertainty.
- Anomalies (`anomalies.py:23-58`) are robust z-scores against a LOYO day-of-year median and MAD. They **ignore the prediction bands**.
- **Calibration result:** 0.899 at 90% nominal, on held-out weekly totals (see the caveats in section 2).

## 4. Web app

- **Stack:** Next.js 15, React 19, Tailwind v4, ECharts, MapLibre with deck.gl, NASA GIBS imagery, nuqs URL state (`web/package.json`). FastAPI backend, Python 3.12, polars and DuckDB, parquet cache.
- **Area selection:**
  - 8 curated region bboxes (`regions.py:23-97`);
  - draw a box or upload GeoJSON (README; `pipeline.py:188-192` applies point-in-polygon);
  - no lat/lon text entry seen (UNVERIFIED).
- **Calendar:** day-of-year x year canvas, inferno ramp on log1p (`web/lib/calendar.ts:35-41`). It is daily, **not** a month x year grid. Raw MODIS, raw VIIRS or harmonized views. 90% band in the tooltip.
- **Other features:** MODIS/VIIRS compare slider over GIBS imagery, seasonality (STL), anomaly events, agreement tab, quality tab, PNG export, share link.
- **CSV** (`routes.py:193-206`):
  - one row per day with `date, harmonized, lo, hi, reconstructed, modis_raw, viirs_raw`;
  - region totals in the chosen metric (FRP by default);
  - **no raw hotspot CSV.** Hotspot points come only as GeoJSON, at most 7 days and 50k features (`hotspots.py:12-13, 93-95`).
  - GeoJSON summary and a methods JSON are also offered.
- **Accessibility:**
  - axe WCAG 2.1 AA Playwright tests on every page and tab (`web/e2e/a11y.spec.ts`), but canvases are excluded;
  - Okabe-Ito sensor colours (#e69f00, #56b4e9) and the inferno ramp;
  - aria-labels on the calendar canvas and the export menu (`ExportMenu.tsx:35-40`);
  - Escape closes the menu.
- **Performance:** the 13 JS chunks of the landing page total about 595 KB. A live fetch is capped at 300 FIRMS requests (`jobs.py:110`), which covers about 4 years of 5-day chunks. So a new drawn area over 2000-2025 cannot be analysed live unless it was prefetched.
- **Live URL status (checked 31 Oct 2026): the data service is down.**
  - The bundle points the API at a Cloudflare quick tunnel, `https://timeline-dosage-estate-united.trycloudflare.com` (chunk `2d1324fc4570fb75.js`), and that name returns NXDOMAIN.
  - The landing page shows the hero and three empty stat cards (`shots/emberline_home.png`).
  - /atlas shows "The data service is not reachable, so the case studies cannot be shown." (`shots/emberline_atlas.png`).
  - /explore hung the headless renderer (not captured).
  - **What a judge sees in the first 30 seconds:** a polished but empty shell.

## 5. Weaknesses a judge would notice

- The live app has no data: a dead tunnel backend.
- S-NPP only, with no NOAA-20/21 continuity, while S-NPP delivery ends 2 Nov 2026.
- Region-level weekly model: no per-cell harmonization, and each drawn area needs at least 40 overlap weeks and 3 years.
- The default quantity is FRP, while the challenge asks for hotspot counts. They admit FRP changes in 2015.
- Terra drift is not corrected.
- Only one region (Punjab) has a written validation.
- Intervals of about x3.1 on weekly totals are wide. The method page says so honestly.

## 6. Best idea to borrow (with credit)

- **Coincident-overpass matching, Aqua-MODIS vs S-NPP-VIIRS** (`api/emberline/science/overpass.py`): 750 m / 30 min KD-tree, with a co-observation proxy that excludes detections the other sensor could not judge.
- It gives empirical corroboration rates by FRP bin and MODIS pixel size: 21% at FRP < 5 MW rising to 43% at >= 50 MW in Punjab (`punjab-haryana.md:84-91`).
- That is an empirical P_det(FRP, pixel size) curve, which we can use to fit or check our Sofiev-style detection-probability operator.
- Runner-up: showing out-of-fold "before/after" scatters so the after picture is not self-flattering (`DECISIONS.md:102-103`).

## Scores (1-5)

| Criterion | Score | Basis |
|---|---|---|
| Scientific validity | 3 | Honest LOYO out-of-fold predictions, but a region-total weekly model, FRP default, no NOAA-20, Terra drift ignored |
| Uncertainty | 3 | Conformal constant width; no band on observed days; anomalies ignore it |
| Calibration evidence | 3 | Coverage measured on held-out years (0.899), but marginal, non-discriminating, one region, interpolation only |
| Coverage (regions) | 2 | 8 curated boxes; one validated; live API down |
| App UX | 2 | Polished, but judges see empty cards and "not reachable" |
| CSV | 3 | Daily harmonized values with bands and raw; no raw hotspots |
| Accessibility | 4 | axe in CI, Okabe-Ito colours, inferno ramp, aria labels |
| Storytelling | 3 | Atlas stories computed from data, but blank while the API is down |
