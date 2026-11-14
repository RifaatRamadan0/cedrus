# Do the 80% ranges hold 80%?

_Generated 2026-11-13T12:57:57+00:00 by `python analysis/range_coverage/run_test.py`. Do not edit by hand._

**No.** With 2020–2021 estimated exactly as 2022 onward is, the ranges held the observed MODIS value in 31 of 77 (40%) whole-region months in burning days and 27 of 80 (34%) in hotspots. Single cells, blocks of cells and circles with an estimate of 3 or more held it in 34–74% of area-months. The estimates themselves are not affected.

This test was not pre-registered. It was first run on 13 November 2026, after a review found the ranges too narrow, and is reported whatever it shows. Nothing is tuned; no model, export or published file is changed.

## Method

- The real exporter is run into a scratch folder with one change: the observed era ends at 2019-12 instead of 2021-12, so 2020–2021 is estimated from VIIRS as 2022 onward is. Both models are fitted on 2012–2019 either way. Every other month of the scratch files equals the published files (checked).
- The ranges are built as the website builds them: whole regions and blocks as `regionSeries()` in `web/app.js`, circles as `exactSeries()`.
- The reference is observed MODIS in 2020–2021, taken from the published files.
- Area-months are grouped by the estimate, never by the observed value.

## Whole regions: months with an estimate of 10 or more

| Region | Burning days | Hotspots |
|---|---|---|
| Portugal | 10 of 23 (43%) | 9 of 24 (38%) |
| Lebanon | 6 of 8 (75%) | 5 of 8 (62%) |
| Syria | 2 of 22 (9%) | 1 of 24 (4%) |
| La Rioja | 13 of 24 (54%) | 12 of 24 (50%) |
| **All four** | **31 of 77 (40%)** | **27 of 80 (34%)** |

## By area size, burning days

Share of area-months in which the range held the observed value, by the estimate of the area-month.

| Area | Estimate 0.5-3 | Estimate 3-10 | Estimate 10-30 | Estimate 30+ |
|---|---|---|---|---|
| Circle, 5 km (cells touched, median: 1) | 335 of 934 (36%) | 63 of 150 (42%) | 7 of 18 (39%) | 3 of 3 (100%) |
| Circle, 10 km (cells touched, median: 2) | 686 of 1789 (38%) | 302 of 604 (50%) | 59 of 126 (47%) | 12 of 20 (60%) |
| Circle, 25 km (cells touched, median: 7) | 1402 of 3297 (43%) | 847 of 1477 (57%) | 434 of 699 (62%) | 135 of 238 (57%) |
| Circle, 50 km (cells touched, median: 18) | 1375 of 3942 (35%) | 1587 of 2797 (57%) | 775 of 1362 (57%) | 445 of 763 (58%) |
| Circle, 100 km (cells touched, median: 46) | 842 of 2321 (36%) | 1553 of 3403 (46%) | 1301 of 2707 (48%) | 900 of 1855 (49%) |
| One cell | 1465 of 1646 (89%) | 311 of 421 (74%) | 71 of 115 (62%) | 15 of 31 (48%) |
| Block of 2 × 2 cells | 503 of 1341 (38%) | 200 of 335 (60%) | 79 of 127 (62%) | 29 of 51 (57%) |
| Block of 4 × 4 cells | 220 of 703 (31%) | 156 of 290 (54%) | 72 of 114 (63%) | 38 of 65 (58%) |
| Block of 8 × 8 cells | 105 of 270 (39%) | 70 of 180 (39%) | 56 of 108 (52%) | 38 of 67 (57%) |
| Whole region | 2 of 5 (40%) | 3 of 7 (43%) | 14 of 29 (48%) | 17 of 48 (35%) |

## By area size, hotspots

Share of area-months in which the range held the observed value, by the estimate of the area-month.

| Area | Estimate 0.5-3 | Estimate 3-10 | Estimate 10-30 | Estimate 30+ |
|---|---|---|---|---|
| Circle, 5 km (cells touched, median: 1) | 347 of 895 (39%) | 68 of 142 (48%) | 6 of 17 (35%) | 1 of 3 (33%) |
| Circle, 10 km (cells touched, median: 2) | 636 of 1833 (35%) | 253 of 608 (42%) | 53 of 107 (50%) | 12 of 23 (52%) |
| Circle, 25 km (cells touched, median: 7) | 1301 of 3593 (36%) | 776 of 1518 (51%) | 351 of 657 (53%) | 109 of 208 (52%) |
| Circle, 50 km (cells touched, median: 18) | 1207 of 4183 (29%) | 1622 of 2993 (54%) | 676 of 1371 (49%) | 383 of 795 (48%) |
| Circle, 100 km (cells touched, median: 47) | 733 of 2219 (33%) | 1523 of 3635 (42%) | 1080 of 2648 (41%) | 772 of 1922 (40%) |
| One cell | 1556 of 1744 (89%) | 306 of 457 (67%) | 63 of 118 (53%) | 21 of 35 (60%) |
| Block of 2 × 2 cells | 495 of 1432 (35%) | 205 of 355 (58%) | 73 of 140 (52%) | 27 of 53 (51%) |
| Block of 4 × 4 cells | 217 of 743 (29%) | 142 of 307 (46%) | 63 of 125 (50%) | 29 of 67 (43%) |
| Block of 8 × 8 cells | 96 of 264 (36%) | 68 of 201 (34%) | 49 of 108 (45%) | 32 of 73 (44%) |
| Whole region | 3 of 6 (50%) | 2 of 4 (50%) | 12 of 31 (39%) | 15 of 49 (31%) |

Circles: 120 centres per region and unit, drawn from the positions of 2012–2019 Suomi NPP records (seed 20261113), each used at every radius.
Sums over several cells with an estimate under 3 do badly for a separate reason: adding half-widths in quadrature puts the lower end above zero (for example an estimate of 0.4 with a range of 0.4–0.5).

## Where the shortfall comes from

From the models' own forecast means and variances, 2020–2021.

### Single rows: one cell, one month, day or night, Suomi NPP alone

This is the unit the sealed exams scored. Pooled over active rows the coverage is near 80%, as in the exams; it falls as the forecast grows, because the forecast is close to Poisson for cells with a long history.

| Rows | Burning days | Hotspots |
|---|---|---|
| Active rows (the exams' definition) | 4719 of 5748 (82%) | 4633 of 5748 (81%) |
| Forecast 0.5-3 | 1666 of 1856 (90%) | 1717 of 1968 (87%) |
| Forecast 3-10 | 332 of 480 (69%) | 316 of 497 (64%) |
| Forecast 10-30 | 75 of 112 (67%) | 67 of 116 (58%) |
| Forecast 30+ | 12 of 24 (50%) | 10 of 22 (45%) |

### Squared error ÷ the variance the model states (1.0 = calibrated)

| Level | Burning days | Hotspots |
|---|---|---|
| Row, Suomi NPP alone (active rows) | 2.1 | 3.1 |
| Cell-month, satellites independent (as published) | 3.3 | 5.6 |
| Cell-month, satellites fully dependent | 1.7 | 2.9 |
| Region-month, cells and satellites independent (as published) | 8.2 | 16.6 |
| Region-month, cells independent, satellites fully dependent | 4.3 | 8.7 |

### The two satellites err together

Correlation between the Suomi NPP-based and the NOAA-20-based forecast errors against the same MODIS value. The published variance averages them as if this were 0.

| Region | Burning days: cell-months / region-months | Hotspots: cell-months / region-months |
|---|---|---|
| Portugal | 0.81 / 0.93 | 0.63 / 0.75 |
| Lebanon | 0.72 / 0.89 | 0.73 / 0.88 |
| Syria | 0.57 / 0.84 | 0.71 / 0.88 |
| La Rioja | 0.79 / 0.68 | 0.73 / 0.66 |

### Neighbouring cells err together

Mean product of standardized errors of two cells in the same month (cell-months with a forecast of 1 or more); the same-cell row is the mean squared standardized error.

| Pair | Burning days | Hotspots |
|---|---|---|
| Adjacent cells | +0.13 | +0.49 |
| 2-3 cells apart | +0.03 | +0.17 |
| 4 or more cells apart | +0.04 | +0.05 |
| Same cell | +1.79 | +2.32 |

### No simple assumption fixes it

Whole-region months with a forecast of 10 or more, from the models' unrounded moments (so the first row can differ from the first table by a month). Treating everything as fully dependent holds every month, with a range too wide to use.

| Assumption | Burning days: held | mean half-width ÷ estimate | Hotspots: held | mean half-width ÷ estimate |
|---|---|---|---|---|
| Cells independent, satellites independent (as published) | 30 of 77 (39%) | 16% | 26 of 79 (33%) | 16% |
| Cells independent, satellites fully dependent | 34 of 77 (44%) | 17% | 27 of 79 (34%) | 17% |
| Cells fully dependent, satellites independent | 77 of 77 (100%) | 90% | 79 of 79 (100%) | 94% |
| Cells fully dependent, satellites fully dependent | 77 of 77 (100%) | 92% | 79 of 79 (100%) | 95% |

## Limits of this test

- 24 months per region, and months of one region are not independent of each other.
- Portugal, Lebanon and Syria were development regions: their 2012–2019 data helped choose the models. La Rioja was not. No region's 2020–2021 data was used to fit or choose them.
- MODIS is the reference, so this tests the range as a statement about the MODIS-equivalent count, not about fires.
- 2022 onward cannot be tested this way: there is no MODIS reference at nominal orbits.
- A calibrated range would need its spread and the dependence between cells and satellites estimated on 2012–2019, frozen, and tested once. That is future work; the published ranges are unchanged.
