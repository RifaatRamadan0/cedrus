# Bake-off results: shrinkage ratio A vs learned detection response B

_Generated 2026-10-31T19:21:14+00:00 by `python -m pipeline.bakeoff.run`. Rules: [BAKEOFF_PLAN.md](BAKEOFF_PLAN.md), committed before any of this code existed. Do not edit by hand._

Re-run from the repo root:

```bash
python -m pipeline.bakeoff.run
```

**Chosen: A shrinkage ratio.**

Regions included (9): portugal, lebanon, cyprus, jordan, israel, palestine, greece, syria, turkey.
No development region was left out.
Sealed regions (Morocco, Tunisia, central Chile, Western Cape) were not read.

## Decision

Pooled leave-one-year-out (2012…2019), weighted CRPS of B ÷ A = **1.526**; 90% paired block-bootstrap interval 1.433 … 1.598 (2000 resamples, held-out years as blocks, seed 20261031).

| Clause | Needed | Got | |
|---|---|---|---|
| (i) weighted CRPS ratio B ÷ A | ≤ 0.95 | 1.526 | **fail** |
| (ii) upper end of the 90% bootstrap interval | < 1.00 | 1.598 | **fail** |
| (iii) B's 80% coverage | 0.75 … 0.85 | 0.978 | **fail** |

B is chosen only if all three pass. Result: **A shrinkage ratio**.

The winner refit on all of 2012–2019 is in `data/processed/bakeoff/frozen_A.json` (not committed: data/ is ignored).

## Deviations / interpretations

Points where the plan was silent, ambiguous or could not be applied word for word. Each was settled by the most literal reading; none was chosen by looking at scores.

1. **Window starts Feb 2012.** The plan says 2012–2019 with "Suomi NPP from 2012-02"; rows run 2012-02 … 2019-12 (as in TEST_PLAN.md). January 2012 detections are used only as the date − 1 chance control for units on 1 Feb 2012. Nothing from 2020 on is read: for units on 31 Dec 2019 the date + 1 control would be 2020, so c = the date − 1 count alone (12 units).
2. **"Same date" is FIRMS `acq_date` (UTC).** East of about 25°E the Suomi NPP and Aqua night passes fall around midnight UTC, so a fire seen by both can carry two different dates and is then not matched. Night units within 60 min of midnight: portugal 0 of 7,438, lebanon 802 of 1,059, cyprus 463 of 528, jordan 934 of 1,191, israel 1,428 of 1,790, palestine 701 of 939, greece 2,613 of 3,243, syria 14,241 of 22,788, turkey 26,332 of 37,726. For information only (not used anywhere in the models), matching that allows the date to cross midnight would give these mean matched counts per night unit: cyprus 0.011 → 0.017, greece 0.153 → 0.188, israel 0.022 → 0.028, jordan 0.006 → 0.011, lebanon 0.012 → 0.018, palestine 0.011 → 0.015, portugal 0.459 → 0.459, syria 0.046 → 0.055, turkey 0.054 → 0.061.
3. **Pass** = Suomi NPP detections with one date and day/night, chained while consecutive `acq_time` values are ≤ 30 min apart (longest pass found: 3 min).
4. **Matching time window** is checked pixel to pixel: an Aqua pixel can match a Suomi NPP pixel with the same date and day/night and |Δt| ≤ 60 min. Its nearest unit is the unit holding its nearest such pixel; it is matched if that distance is within its own ½·√(scan² + track²) + 0.5 km.
5. **Distances** are chords between points on a 6371 km sphere (in a cKDTree) rather than an equirectangular projection; at 1–3 km the two agree to well under a metre.
6. **A unit's row**: the cell of the unit's pixel nearest its centroid (a unit can straddle a cell edge), with the month and day/night of its pass. Unit FRP ≤ 0 sets the indicator and log FRP to 0; when no training unit has FRP ≤ 0 the indicator's coefficient is 0.
7. **Outage rule**: the two families are MODIS (Terra + Aqua) and Suomi NPP, counted per UTC date over all included regions. Outage days: MODIS 1, Suomi NPP 1; months not scored: 2012-03, 2016-02. These months are left out of every score (inner tuning and outer); fitting uses all months, because the plan restricts scoring only. Days with zero Terra (or zero Aqua) while Suomi NPP had ≥ 50 are not part of the rule; they are listed below for information (Terra 30, Aqua 14).
8. **Inner leave-one-year-out criterion** is the primary score (weighted mean CRPS, weights from the inner training years), pooled over the inner held-out years. A tie would go to the smaller grid value.
9. **A where the prior ratio is undefined.** If a region × month × day/night had no Suomi NPP detection in training, r0 falls back to the region × day/night ratio, then to all regions × day/night (0 scored rows over the eight folds). Where r0 = 0 the posterior rate a/r0 is infinite and the forecast is all mass at 0 (455 scored rows). Where a region × month × day/night had no training row with V = 0, b_A falls back to the region × day/night mean (0 scored rows).
10. **B's region effects** are fitted with one reference region, then centred per day/night (their mean moved into the month terms, which leaves the fit unchanged), so shrinking towards 0 means towards the average region. τ² and the shrinkage are computed per day/night; var(β̂) is the population variance (ddof 0) of the centred effects; se comes from the expected Fisher information. α stays at its maximum-likelihood value.
11. **Coverage** counts y inside [q10, q90], with q the smallest k where F(k) ≥ 0.1 or 0.9, unweighted over scored rows. Most rows have y = 0 and a forecast whose 90th percentile is 0, which counts as covered. Coverage on active rows (Y > 0 or V > 0) is shown for information; the rule uses all rows.
12. **WAPE**: cell-month adds day and night before taking |error| (cell × month, as in TEST_PLAN.md); national-month is region × month. Row-level WAPE (cell × month × day/night) is shown too.
13. **CRPS** sums k = 0 … K with K = max(0.9999 quantile, y + 50).
14. **Bootstrap** interval is the 5th–95th percentile of the resampled ratios.
15. **Border cells**: rows are per region, so a cell on a border has a row in each country file it appears in, each counting only that file's detections.
16. **Frozen refit**: its tuning value is chosen by leave-one-year-out over all eight years.

## Overall: pooled leave-one-year-out

454,770 scored rows, 127,939 MODIS detections.

| Model | Weighted CRPS (primary) | CRPS | 80% coverage | Cell-month WAPE | National-month WAPE | Row WAPE (cell x month x day/night) | Coverage on active rows (information only) |
|---|---|---|---|---|---|---|---|
| A shrinkage ratio | 0.261 | 0.135 | 97.2% | 68.3% | 17.3% | 75.5% | 82.1% |
| B learned detection response | 0.398 | 0.165 | 97.8% | 82.4% | 32.1% | 92.6% | 85.9% |

## Forward check: fit 2012–2016, score 2017–2019

a = 30, b = 0.01 (chosen by leave-one-year-out inside 2012–2016). Weighted CRPS ratio B ÷ A = **1.463**. 176,040 scored rows, 43,719 MODIS detections.

| Model | Weighted CRPS (primary) | CRPS | 80% coverage | Cell-month WAPE | National-month WAPE | Row WAPE (cell x month x day/night) | Coverage on active rows (information only) |
|---|---|---|---|---|---|---|---|
| A shrinkage ratio | 0.246 | 0.131 | 97.2% | 75.2% | 21.4% | 83.1% | 81.6% |
| B learned detection response | 0.359 | 0.154 | 97.8% | 93.5% | 40.1% | 103.9% | 85.5% |

By region:

| Region | Rows | MODIS (Y) | Weighted CRPS A | Weighted CRPS B | B ÷ A | CRPS A | CRPS B | Coverage A | Coverage B | Cell-month WAPE A | Cell-month WAPE B | National-month WAPE A | National-month WAPE B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| portugal | 13,176 | 8,699 | 0.387 | 0.550 | 1.423 | 0.304 | 0.439 | 95.3% | 96.4% | 55.2% | 114.6% | 15.1% | 75.6% |
| lebanon | 2,016 | 143 | 0.064 | 0.064 | 0.989 | 0.057 | 0.056 | 98.2% | 98.3% | 137.2% | 145.0% | 49.4% | 79.9% |
| cyprus | 1,512 | 74 | 0.049 | 0.050 | 1.012 | 0.045 | 0.045 | 98.2% | 98.3% | 178.1% | 190.2% | 95.1% | 103.4% |
| jordan | 4,896 | 132 | 0.034 | 0.033 | 0.991 | 0.028 | 0.027 | 99.0% | 98.9% | 170.6% | 171.1% | 88.4% | 95.7% |
| israel | 3,456 | 331 | 0.086 | 0.084 | 0.977 | 0.077 | 0.074 | 97.4% | 97.5% | 128.5% | 132.9% | 35.8% | 48.1% |
| palestine | 1,584 | 121 | 0.068 | 0.070 | 1.024 | 0.064 | 0.066 | 97.8% | 97.4% | 137.3% | 144.2% | 57.5% | 56.3% |
| greece | 27,720 | 3,117 | 0.085 | 0.100 | 1.179 | 0.061 | 0.070 | 98.4% | 98.5% | 91.2% | 98.0% | 21.1% | 31.0% |
| syria | 20,016 | 7,446 | 0.267 | 0.293 | 1.096 | 0.212 | 0.223 | 96.4% | 98.2% | 71.2% | 87.9% | 25.0% | 53.9% |
| turkey | 101,664 | 23,656 | 0.277 | 0.435 | 1.569 | 0.122 | 0.140 | 97.1% | 97.7% | 79.4% | 85.0% | 21.5% | 22.9% |

## Per region (leave-one-year-out pool)

| Region | Rows | MODIS (Y) | Weighted CRPS A | Weighted CRPS B | B ÷ A | CRPS A | CRPS B | Coverage A | Coverage B | Cell-month WAPE A | Cell-month WAPE B | National-month WAPE A | National-month WAPE B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| portugal | 34,038 | 22,293 | 0.348 | 0.530 | 1.523 | 0.265 | 0.399 | 95.5% | 96.7% | 50.7% | 105.3% | 15.3% | 75.2% |
| lebanon | 5,208 | 512 | 0.077 | 0.079 | 1.021 | 0.070 | 0.072 | 98.0% | 98.2% | 115.5% | 120.7% | 44.5% | 68.0% |
| cyprus | 3,906 | 345 | 0.069 | 0.072 | 1.052 | 0.063 | 0.067 | 97.8% | 97.9% | 121.4% | 137.6% | 62.0% | 77.9% |
| jordan | 12,648 | 307 | 0.027 | 0.029 | 1.067 | 0.024 | 0.024 | 99.1% | 99.0% | 180.0% | 183.7% | 81.6% | 96.3% |
| israel | 8,928 | 945 | 0.093 | 0.095 | 1.024 | 0.083 | 0.084 | 97.4% | 97.6% | 124.4% | 136.5% | 38.0% | 57.3% |
| palestine | 4,092 | 313 | 0.066 | 0.068 | 1.016 | 0.062 | 0.063 | 98.1% | 97.8% | 133.4% | 138.7% | 58.6% | 64.7% |
| greece | 71,610 | 10,776 | 0.104 | 0.132 | 1.277 | 0.075 | 0.090 | 98.1% | 98.3% | 77.8% | 88.2% | 15.1% | 29.7% |
| syria | 51,708 | 15,090 | 0.216 | 0.234 | 1.084 | 0.167 | 0.175 | 96.9% | 98.0% | 74.6% | 83.3% | 23.0% | 40.8% |
| turkey | 262,632 | 77,358 | 0.315 | 0.509 | 1.617 | 0.138 | 0.168 | 97.1% | 97.7% | 68.8% | 73.0% | 16.0% | 17.1% |

## Per held-out year

| Year | Rows | MODIS (Y) | Weighted CRPS A | Weighted CRPS B | B ÷ A | CRPS A | CRPS B | Coverage A | Coverage B | Cell-month WAPE A | Cell-month WAPE B | National-month WAPE A | National-month WAPE B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2012 | 48,900 | 11,682 | 0.232 | 0.325 | 1.401 | 0.121 | 0.144 | 97.4% | 98.0% | 74.8% | 91.8% | 21.3% | 39.5% |
| 2013 | 58,680 | 19,700 | 0.287 | 0.476 | 1.660 | 0.146 | 0.190 | 97.1% | 97.8% | 61.0% | 78.1% | 11.6% | 32.0% |
| 2014 | 58,680 | 9,212 | 0.193 | 0.275 | 1.425 | 0.089 | 0.098 | 97.9% | 98.2% | 89.5% | 93.8% | 23.3% | 31.6% |
| 2015 | 58,680 | 22,917 | 0.326 | 0.539 | 1.656 | 0.166 | 0.213 | 96.8% | 97.5% | 57.9% | 62.9% | 12.6% | 15.4% |
| 2016 | 53,790 | 20,709 | 0.340 | 0.536 | 1.575 | 0.168 | 0.215 | 96.8% | 97.5% | 60.1% | 75.8% | 14.6% | 30.8% |
| 2017 | 58,680 | 18,507 | 0.288 | 0.463 | 1.605 | 0.159 | 0.204 | 97.0% | 97.5% | 66.9% | 98.1% | 18.1% | 47.4% |
| 2018 | 58,680 | 9,770 | 0.173 | 0.263 | 1.521 | 0.091 | 0.103 | 97.7% | 98.1% | 86.1% | 95.7% | 27.0% | 34.5% |
| 2019 | 58,680 | 15,442 | 0.252 | 0.313 | 1.240 | 0.139 | 0.154 | 97.0% | 97.8% | 76.7% | 84.2% | 21.2% | 33.3% |

## Tuning inside each fold

| Held out | a (A) | b (B) | Inner weighted CRPS, A by a | Inner weighted CRPS, B by b | α | τ² day | τ² night | NB converged | Seconds |
|---|---|---|---|---|---|---|---|---|---|
| 2012 | 30 | 0.01 | 1: 0.2892, 3: 0.2764, 10: 0.2697, 30: 0.2688 | 0.01: 0.4092, 0.03: 0.4522, 0.1: 0.5716, 0.3: 0.6627 | 1.927 | 0.1278 | 0.3393 | True | 242.2 |
| 2013 | 30 | 0.01 | 1: 0.2755, 3: 0.2626, 10: 0.2560, 30: 0.2553 | 0.01: 0.3820, 0.03: 0.4231, 0.1: 0.5328, 0.3: 0.6132 | 2.031 | 0.1324 | 0.3640 | True | 240.8 |
| 2014 | 30 | 0.01 | 1: 0.2998, 3: 0.2860, 10: 0.2786, 30: 0.2772 | 0.01: 0.4219, 0.03: 0.4616, 0.1: 0.5834, 0.3: 0.6788 | 1.910 | 0.1300 | 0.3797 | True | 247.8 |
| 2015 | 30 | 0.01 | 1: 0.2648, 3: 0.2516, 10: 0.2447, 30: 0.2435 | 0.01: 0.3653, 0.03: 0.4011, 0.1: 0.5022, 0.3: 0.5778 | 2.070 | 0.1392 | 0.3678 | True | 233.0 |
| 2016 | 30 | 0.01 | 1: 0.2656, 3: 0.2520, 10: 0.2450, 30: 0.2440 | 0.01: 0.3708, 0.03: 0.4119, 0.1: 0.5166, 0.3: 0.5929 | 2.051 | 0.1452 | 0.3313 | True | 239.9 |
| 2017 | 30 | 0.01 | 1: 0.2763, 3: 0.2649, 10: 0.2587, 30: 0.2577 | 0.01: 0.3798, 0.03: 0.4228, 0.1: 0.5391, 0.3: 0.6268 | 1.885 | 0.1333 | 0.3313 | True | 243.0 |
| 2018 | 30 | 0.01 | 1: 0.3057, 3: 0.2912, 10: 0.2832, 30: 0.2816 | 0.01: 0.4266, 0.03: 0.4686, 0.1: 0.5932, 0.3: 0.6889 | 1.918 | 0.1418 | 0.3528 | True | 247.3 |
| 2019 | 30 | 0.01 | 1: 0.2903, 3: 0.2770, 10: 0.2698, 30: 0.2685 | 0.01: 0.4267, 0.03: 0.4669, 0.1: 0.5871, 0.3: 0.6782 | 2.075 | 0.1559 | 0.3543 | True | 236.6 |
| forward | 30 | 0.01 | 1: 0.3295, 3: 0.3132, 10: 0.3037, 30: 0.3010 | 0.01: 0.4550, 0.03: 0.5003, 0.1: 0.6397, 0.3: 0.7477 | 1.886 | 0.1641 | 0.3256 | True | 96.3 |

## The learned response g(FRP)

Fitted on every unit of 2012–2019. m = Aqua pixels matched to the unit on its own date; c = the same with Aqua from date − 1 and date + 1 (chance). ĝ are the two Poisson fits; g = max(ĝ_match − ĝ_chance, 0.001). Bin values are means over the units in the bin.

**Day** (165,455 units). log ĝ_match = -3.539 + 0.723·log FRP + 0.000·1[FRP ≤ 0]; log ĝ_chance = -4.803 + 0.526·log FRP + 0.000·1[FRP ≤ 0].

| Unit FRP (MW) | Units | Median FRP | Matched m (observed) | Chance c (observed) | ĝ_match | ĝ_chance | g |
|---|---|---|---|---|---|---|---|
| 0-1 | 515 | 0.9 | 0.017 | 0.011 | 0.026 | 0.008 | 0.018 |
| 1-2 | 10,608 | 1.7 | 0.031 | 0.009 | 0.041 | 0.011 | 0.031 |
| 2-5 | 57,233 | 3.3 | 0.058 | 0.015 | 0.070 | 0.015 | 0.054 |
| 5-10 | 41,255 | 6.9 | 0.120 | 0.023 | 0.119 | 0.023 | 0.097 |
| 10-20 | 27,456 | 13.5 | 0.211 | 0.034 | 0.195 | 0.033 | 0.162 |
| 20-50 | 18,126 | 28.8 | 0.376 | 0.051 | 0.343 | 0.049 | 0.294 |
| 50-100 | 5,841 | 66.1 | 0.635 | 0.076 | 0.617 | 0.076 | 0.542 |
| 100-500 | 3,933 | 161.8 | 1.277 | 0.126 | 1.282 | 0.128 | 1.154 |
| > 500 | 488 | 805.2 | 3.842 | 0.278 | 4.587 | 0.318 | 4.269 |

**Night** (76,702 units). log ĝ_match = -4.139 + 0.883·log FRP + 0.000·1[FRP ≤ 0]; log ĝ_chance = -5.023 + 0.718·log FRP + 0.000·1[FRP ≤ 0].

| Unit FRP (MW) | Units | Median FRP | Matched m (observed) | Chance c (observed) | ĝ_match | ĝ_chance | g |
|---|---|---|---|---|---|---|---|
| 0-1 | 27,690 | 0.6 | 0.002 | 0.003 | 0.011 | 0.005 | 0.006 |
| 1-2 | 18,734 | 1.4 | 0.007 | 0.007 | 0.022 | 0.008 | 0.013 |
| 2-5 | 15,703 | 3.0 | 0.023 | 0.014 | 0.044 | 0.015 | 0.029 |
| 5-10 | 6,682 | 6.7 | 0.098 | 0.029 | 0.089 | 0.027 | 0.062 |
| 10-20 | 3,654 | 13.6 | 0.244 | 0.056 | 0.163 | 0.044 | 0.120 |
| 20-50 | 2,416 | 29.0 | 0.528 | 0.101 | 0.327 | 0.077 | 0.250 |
| 50-100 | 960 | 65.2 | 0.981 | 0.189 | 0.664 | 0.136 | 0.528 |
| 100-500 | 686 | 163.8 | 2.058 | 0.259 | 1.713 | 0.292 | 1.421 |
| > 500 | 177 | 935.0 | 7.486 | 0.946 | 10.592 | 1.237 | 9.355 |

## Data

| Region | Cells | Rows | MODIS detections (Y) | Suomi NPP detections (V) | Fire units | Suomi NPP passes |
|---|---|---|---|---|---|---|
| portugal | 183 | 34,770 | 23,158 | 62,152 | 19,095 | 3,850 |
| lebanon | 28 | 5,320 | 512 | 3,721 | 2,663 | 1,814 |
| cyprus | 21 | 3,990 | 349 | 1,792 | 1,034 | 626 |
| jordan | 68 | 12,920 | 309 | 2,352 | 1,820 | 1,441 |
| israel | 48 | 9,120 | 952 | 5,409 | 3,374 | 2,040 |
| palestine | 22 | 4,180 | 313 | 2,516 | 1,771 | 1,290 |
| greece | 385 | 73,150 | 10,978 | 37,448 | 21,498 | 4,185 |
| syria | 278 | 52,820 | 15,165 | 76,546 | 43,739 | 6,928 |
| turkey | 1,412 | 268,280 | 78,136 | 243,698 | 147,163 | 8,403 |

Rows: 464,550, of which 454,770 are in scored months. Rows are 2012-02 … 2019-12 × day/night for every cell with a detection.

Outage days, MODIS: 2016-02-19. Suomi NPP: 2012-03-25.

Information only — zero-Terra days: 2012-02-11, 2012-11-08, 2012-12-28, 2013-01-01, 2013-03-09, 2013-10-03, 2013-12-27, 2014-02-09, 2014-02-22, 2014-04-11, 2014-12-21, 2014-12-26, 2015-01-22, 2015-03-06, 2015-04-11, 2015-12-16, 2015-12-26, 2016-02-19, 2016-02-20, 2016-12-07, 2017-01-22, 2017-02-14, 2017-04-12, 2018-05-17, 2018-11-19, 2018-12-23, 2018-12-29, 2019-01-26, 2019-11-01, 2019-12-10; zero-Aqua days: 2012-05-08, 2012-10-23, 2012-12-29, 2013-02-05, 2014-03-25, 2014-04-19, 2015-01-15, 2016-02-19, 2017-10-01, 2018-04-07, 2018-04-08, 2018-04-14, 2018-05-01, 2019-04-27.

## Timings

Laptop run, 8 worker processes for the folds.

| Stage | Seconds |
|---|---|
| data, units and matching | 14 |
| outer folds and forward check (inner tuning included) | 336 |
| scores and bootstrap | 5 |
| response table | 1 |
| frozen refit of the winner | 160 |
| total | 516 |

## Independent test of this bake-off (added 31 Oct 2026, after the run)

A separate tester, who had not seen the builder's reasoning, re-ran and attacked the bake-off. **Verdict: the decision stands; B lost fairly.**
- **No bug sank B.** B's over-prediction (pooled leave-one-year-out +21%, Portugal +68%) is identical in-sample and out-of-sample. It comes from the model form the plan specified: one multiplier scales both the background b and the exposure Ê. The NB2 fit is a verified, unique maximum-likelihood solution.
- **Even with help B can't pass.** With unfair help (totals recalibrated and dispersion chosen on the held-out years), B is still 1.22× worse than A.
- **The rule had a flaw: clause (iii) was an automatic veto.** 85–90% of rows are "no fire, forecast 0", so B's coverage could never fall inside 0.75–0.85. It did not decide this result, because (i) and (ii) failed by a wide margin. Future coverage rules count active rows only (Y > 0 or V > 0).
- **A quirk in A: rows with V = 0 are counted twice.** A's pooled sums include MODIS detections from rows where V = 0, which are also predicted by b_A, giving +9%. This handicaps A, not B. A is frozen as specified.
- **Overstated claim corrected.** "B worse on every region and year" holds in the leave-one-year-out pool. In the forward check, B beats A slightly in Lebanon (0.989), Jordan (0.991) and Israel (0.977).
- **Tuning hit the grid edges.** A picked a = 30 in every fold and B picked b = 0.01. b = 0.01 is B's true optimum. A larger a could only widen A's lead.
