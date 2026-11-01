# Round 2 confirmation: the frozen pair on the four new sealed regions

_Generated 2026-11-01T13:10:17+00:00 by `python -m pipeline.round2.confirm`. Rules: [ROUND2_PLAN.md](ROUND2_PLAN.md) (pre-registered at commit e7763f7); frozen pair from [ROUND2_SELECTION.md](ROUND2_SELECTION.md). Do not edit by hand._

- Frozen pair: **A2 + J-S** (a = 30). frozen.json generated 2026-11-01T11:02:35+00:00 at commit `3cfb1ff968eea0cc8ea6f1c3f9009e87682e53ff`.
- Run started 2026-11-01T13:10:01+00:00 (UTC) at commit `fa2c956ec655ca382dd1c43f23362ccf23ee99ec`.
- Windows: Test 1 2020–2021. Test 2 2020-01 … 2025-12. Seam 2020–2021. Drift 2022–2025 against 2012–2019.
- Invocations of this kind logged in data/processed/round2/confirm_runs.jsonl before this report: 1 started, 0 finished (this run's finish line is written right after the report).

## Overall: **CONFIRMED**

Regions included (4): central_spain, southern_italy, sw_australia, s_california.

| Part | Needed | Got | |
|---|---|---|---|
| Test 1 (a): cell-month WAPE ≤ F1 + 1.0 point and < F0 | ≤ 61.9% and < 370.9% | 55.8% | **pass** |
| Test 1 (b): 80% coverage on active rows | 0.70 … 0.90 | 0.829 | **pass** |
| Test 1 (c): pooled predicted total ÷ observed MODIS | 0.90 … 1.10 | 1.037 (16,398 ÷ 15,813) | **pass** |
| Test 1 (d): national-month WAPE ≤ F1 + 1.0 point | ≤ 26.2% | 19.2% | **pass** |
| Test 2: share of counted region-months whose 80% intervals overlap | ≥ 0.80 | 0.921 (210 of 228) | **pass** |

## Deviations / interpretations

Points the plan left open, settled by the most literal reading when the code was written (on development regions only, before any sealed file was read).

1. **Rows** are the selection's: cell × month × day/night from 2012-02, for every cell with a MODIS, Suomi NPP or NOAA-20 detection in 2012-02 … 2019-12. A cell first seen after 2019 has no row, so its detections are not scored. They are counted under Data below.
2. **Each region is fitted on its own rows only**, as a one-region table, so every fallback ("all regions") stays inside the region. The settings come from data/processed/round2/frozen.json: the model, the NOAA-20 method, a for A2 if chosen, and the bootstrap settings. Each bootstrap is seeded with 20261101 plus a CRC32 of its label (region and use).
3. **Outage rule**: the bake-off rule over the included regions combined. Test 1, the seam check and the drift check leave out months with a MODIS day at 0 while Suomi NPP is ≥ 50, or the reverse. Test 2 uses no MODIS, so it leaves out months with a Suomi NPP day at 0 while NOAA-20 is ≥ 50, or the reverse (as in the selection). Fitting uses all months.
4. **Test 1 (a) and (d)**: "at most F1's + 1.0 percentage point" means WAPE ≤ F1's WAPE + 0.010. "Below F0's" is strict. **(c)**: |Σ predicted ÷ Σ observed − 1| ≤ 0.10, pooled over the regions' Test 1 rows. **F1** is R1's point forecast, fitted on the region's own 2012–2019 rows: r·V when V > 0, b when V = 0. Round 1's F1 had no b term. **F0** is the raw Suomi NPP count.
5. **Coverage** is y in [q10, q90] on active rows (Y > 0 or V > 0). R1 and Rm use the moment-matched negative binomial with the parameter term, as in the selection. A2 uses A's Poisson–gamma.
6. **Test 2 intervals** are as in the selection: mean ± 1.2816·sd, with sd² = the summed row variances plus the bootstrap variance of the total. A region-month counts if both expected totals are ≥ 10, and it agrees if the 80% intervals overlap. The share is pooled over the regions.
7. **Seam check** uses Test 1's scored months. Its 80% interval includes the parameter term.
8. **Drift band**: monthly observed ÷ predicted for 2012–2019. Each year is predicted by the frozen model refitted without that year. The band is the 10th–90th percentile. Only months with a predicted total ≥ 10 count, and outage months are left out.
9. **Raw folders**: data/raw/spain and data/raw/italy (FIRMS country files), data/raw/australia_sw and data/raw/usa_socal (area-API box files). All four are clipped to the boxes in pipeline/regions.py.
10. **Completeness**: the confirmation refuses to start unless every MODIS and Suomi NPP file for 2012–2025 and every NOAA-20 file for 2018–2025 is in each sealed region's manifest. A half-finished download therefore cannot use up the one run.

## Test 1: accuracy against near-nominal MODIS, 2020–2021

Fit on 2012-02 … 2019-12, scored on 2020–2021 months without an outage day: 31,632 rows (6,757 active), 15,813 MODIS detections. Months left out: none.

| Forecast | Cell-month WAPE | National-month WAPE | Predicted total (observed 15,813) |
|---|---|---|---|
| A2, frozen model | 55.8% | 19.2% | 16,398 |
| F0 raw Suomi NPP count | 370.9% | 362.3% | 73,102 |
| F1 R1's point forecast | 60.9% | 25.2% | 16,365 |

A2 only: weighted CRPS 0.285, 80% coverage on active rows 82.9% (all rows, for information: 96.4%).

By region:

| Region | Rows | Active | MODIS (Y) | Cell-month WAPE model | F0 | F1 | National-month WAPE model | F0 | F1 | Predicted ÷ observed | Weighted CRPS | Coverage, active rows |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| central_spain | 7,584 | 852 | 1,101 | 94.2% | 234.7% | 98.3% | 28.0% | 192.6% | 33.8% | 0.946 | 0.095 | 75.6% |
| southern_italy | 4,080 | 1,481 | 3,740 | 49.8% | 281.7% | 55.0% | 22.5% | 276.7% | 25.9% | 0.873 | 0.450 | 82.5% |
| sw_australia | 12,912 | 3,341 | 7,138 | 63.4% | 486.6% | 69.2% | 19.4% | 481.3% | 25.7% | 1.187 | 0.333 | 84.7% |
| s_california | 7,056 | 1,083 | 3,834 | 36.6% | 281.6% | 40.6% | 12.9% | 273.1% | 21.4% | 0.944 | 0.195 | 83.9% |

## Test 2: satellite swap, 2020–2025

Suomi NPP: A2 fitted on 2012-02 … 2019-12. NOAA-20: J-S fitted on 2018-04 … 2019-12. Months left out (outage): 2022-07, 2022-08, 2023-07, 2023-09, 2024-05, 2024-06, 2024-07, 2024-09, 2024-11, 2025-11.

Pooled: 248 region-months, **228 counted, 210 agree (92.1%)**.

| Region | Region-months | Counted | Agree | Share | Σ Suomi NPP-based | Σ NOAA-20-based |
|---|---|---|---|---|---|---|
| central_spain | 62 | 61 | 61 | 100.0% | 2,431 | 2,546 |
| southern_italy | 62 | 44 | 42 | 95.5% | 6,499 | 6,889 |
| sw_australia | 62 | 62 | 50 | 80.6% | 27,991 | 27,120 |
| s_california | 62 | 61 | 57 | 93.4% | 6,699 | 6,305 |

By region and year (counted / agree):

| Region | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| central_spain | 11 / 11 | 12 / 12 | 10 / 10 | 10 / 10 | 7 / 7 | 11 / 11 |
| southern_italy | 10 / 9 | 8 / 7 | 7 / 7 | 6 / 6 | 5 / 5 | 8 / 8 |
| sw_australia | 12 / 12 | 12 / 11 | 10 / 7 | 10 / 9 | 7 / 5 | 11 / 6 |
| s_california | 12 / 11 | 12 / 11 | 10 / 9 | 9 / 8 | 7 / 7 | 11 / 11 |

Counted region-months that disagree:

| Region | Month | Suomi NPP-based (80% interval) | NOAA-20-based, J-S (80% interval) | Suomi NPP count | NOAA-20 count |
|---|---|---|---|---|---|
| southern_italy | 2020-06 | 106.0 (92.4 … 119.5) | 139.6 (123.1 … 156.1) | 430 | 546 |
| southern_italy | 2021-07 | 526.1 (494.8 … 557.4) | 660.0 (619.8 … 700.3) | 2,210 | 2,684 |
| sw_australia | 2021-10 | 276.9 (252.6 … 301.1) | 212.8 (192.4 … 233.2) | 1,541 | 1,128 |
| sw_australia | 2022-02 | 311.0 (278.3 … 343.7) | 226.1 (202.1 … 250.1) | 1,441 | 1,225 |
| sw_australia | 2022-09 | 222.2 (200.6 … 243.7) | 160.8 (143.2 … 178.3) | 1,796 | 1,483 |
| sw_australia | 2022-10 | 339.5 (311.7 … 367.2) | 273.9 (249.4 … 298.4) | 1,964 | 1,471 |
| sw_australia | 2023-02 | 50.2 (40.6 … 59.8) | 29.3 (22.1 … 36.5) | 229 | 150 |
| sw_australia | 2024-02 | 181.7 (155.7 … 207.7) | 112.0 (93.7 … 130.4) | 824 | 527 |
| sw_australia | 2024-03 | 447.4 (418.4 … 476.4) | 322.4 (297.0 … 347.8) | 1,627 | 1,360 |
| sw_australia | 2025-01 | 138.6 (120.7 … 156.4) | 99.0 (83.7 … 114.3) | 470 | 356 |
| sw_australia | 2025-03 | 449.9 (419.8 … 480.0) | 537.0 (501.4 … 572.5) | 1,557 | 1,905 |
| sw_australia | 2025-04 | 1,398.2 (1,347.9 … 1,448.6) | 1,270.6 (1,215.0 … 1,326.1) | 4,889 | 4,512 |
| sw_australia | 2025-10 | 410.4 (379.8 … 441.0) | 311.1 (285.1 … 337.2) | 2,178 | 1,753 |
| sw_australia | 2025-12 | 379.2 (348.2 … 410.2) | 288.5 (261.6 … 315.4) | 2,091 | 1,784 |
| s_california | 2020-07 | 53.5 (43.8 … 63.1) | 34.1 (26.3 … 41.8) | 173 | 132 |
| s_california | 2021-05 | 56.9 (46.7 … 67.1) | 32.9 (25.2 … 40.6) | 275 | 153 |
| s_california | 2022-06 | 71.2 (59.8 … 82.6) | 46.4 (37.0 … 55.7) | 301 | 221 |
| s_california | 2023-10 | 55.8 (45.9 … 65.8) | 37.2 (29.0 … 45.4) | 305 | 235 |

s per region (sd from the month-block bootstrap): central_spain day 0.970 (0.066), night 1.209 (0.246); southern_italy day 1.025 (0.044), night 1.028 (0.058); sw_australia day 0.989 (0.019), night 0.973 (0.019); s_california day 0.903 (0.071), night 0.916 (0.073).

## Report only: seam check, 2020 and 2021

Harmonized (the frozen model's predicted MODIS total from Suomi NPP) ÷ observed MODIS, with the 80% interval.

| Region | Year | Observed MODIS | Harmonized | Ratio | 80% interval of the ratio |
|---|---|---|---|---|---|
| central_spain | 2020 | 369 | 382 | 1.036 | 0.966 … 1.107 |
| central_spain | 2021 | 732 | 659 | 0.901 | 0.841 … 0.961 |
| southern_italy | 2020 | 1,235 | 1,317 | 1.066 | 1.027 … 1.105 |
| southern_italy | 2021 | 2,505 | 1,950 | 0.778 | 0.754 … 0.803 |
| sw_australia | 2020 | 3,778 | 4,373 | 1.158 | 1.132 … 1.183 |
| sw_australia | 2021 | 3,360 | 4,098 | 1.220 | 1.192 … 1.248 |
| s_california | 2020 | 3,294 | 3,072 | 0.933 | 0.882 … 0.984 |
| s_california | 2021 | 540 | 547 | 1.012 | 0.952 … 1.073 |

## Report only: drift divergence, 2022–2025

Monthly observed MODIS ÷ the frozen model's prediction from Suomi NPP. The 2012–2019 band is the 10th–90th percentile of the same ratio, leave-one-year-out.

| Region | 2012–2019 band (median) | Year | Months used | Median ratio | Months below band | Months above band |
|---|---|---|---|---|---|---|
| central_spain | 0.45 … 1.63 (0.88) | 2022 | 11 | 1.07 | 1 | 1 |
| central_spain | 0.45 … 1.63 (0.88) | 2023 | 11 | 0.62 | 3 | 0 |
| central_spain | 0.45 … 1.63 (0.88) | 2024 | 10 | 0.73 | 2 | 0 |
| central_spain | 0.45 … 1.63 (0.88) | 2025 | 11 | 0.78 | 2 | 0 |
| southern_italy | 0.64 … 1.27 (0.90) | 2022 | 8 | 0.96 | 2 | 0 |
| southern_italy | 0.64 … 1.27 (0.90) | 2023 | 8 | 0.85 | 1 | 0 |
| southern_italy | 0.64 … 1.27 (0.90) | 2024 | 8 | 0.76 | 1 | 1 |
| southern_italy | 0.64 … 1.27 (0.90) | 2025 | 7 | 0.94 | 1 | 0 |
| sw_australia | 0.70 … 1.20 (0.93) | 2022 | 11 | 0.81 | 4 | 0 |
| sw_australia | 0.70 … 1.20 (0.93) | 2023 | 11 | 0.98 | 2 | 3 |
| sw_australia | 0.70 … 1.20 (0.93) | 2024 | 10 | 0.90 | 2 | 0 |
| sw_australia | 0.70 … 1.20 (0.93) | 2025 | 11 | 0.86 | 3 | 0 |
| s_california | 0.50 … 1.47 (0.94) | 2022 | 11 | 0.80 | 1 | 1 |
| s_california | 0.50 … 1.47 (0.94) | 2023 | 10 | 0.86 | 2 | 1 |
| s_california | 0.50 … 1.47 (0.94) | 2024 | 10 | 0.81 | 1 | 1 |
| s_california | 0.50 … 1.47 (0.94) | 2025 | 11 | 1.17 | 0 | 3 |

## Data

| Region | Cells | Detections 2020–2025 in cells with rows (MODIS / Suomi NPP / NOAA-20) | In cells without rows (not scored) |
|---|---|---|---|
| central_spain | 158 | 3,081 / 8,820 / 9,339 | 0 / 2 / 2 |
| southern_italy | 85 | 8,972 / 35,344 / 37,468 | 0 / 0 / 0 |
| sw_australia | 269 | 27,436 / 140,687 / 139,910 | 3 / 38 / 38 |
| s_california | 147 | 9,286 / 34,229 / 36,284 | 4 / 4 / 16 |

Outage days: MODIS 2013-04-22, 2014-05-05, 2014-12-05, 2016-01-17, 2016-12-05, 2023-09-10, 2024-11-01, 2025-09-27; Suomi NPP (vs MODIS) 2022-08-06, 2022-08-07, 2024-07-10, 2024-07-11, 2024-07-14, 2024-07-26, 2024-07-27, 2024-07-28; Suomi NPP (vs NOAA-20) 2022-07-27, 2022-07-28, 2022-07-30, 2022-08-02, 2022-08-03, 2022-08-04, 2022-08-06, 2022-08-07, 2022-08-08, 2024-05-31, 2024-06-01, 2024-07-10, 2024-07-11, 2024-07-12, 2024-07-13, 2024-07-14, 2024-07-15, 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28, 2024-09-26, 2024-11-03, 2024-11-04, 2025-11-12; NOAA-20 2023-07-19, 2023-07-20, 2023-07-21, 2023-07-22, 2023-09-30.

Invocations of this kind logged before this report:

- start 2026-11-01T13:10:01+00:00 regions central_spain, southern_italy, sw_australia, s_california

## Timings

| Stage | Seconds |
|---|---|
| data | 15 |
| tests | 2 |
| total | 17 |
