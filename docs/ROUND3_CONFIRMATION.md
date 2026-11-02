# Round 3 confirmation: D-a (burning days) on the four round-3 sealed regions

_Generated 2026-11-02T09:16:30+00:00 by `python -m pipeline.round3.confirm`. Rules: [TOURNAMENT_PLAN.md](TOURNAMENT_PLAN.md) (pre-registered at commit fa2c956; the round-3 entrant by the ruling added 1 Nov 2026), with round 2's tests and pass rules ([ROUND2_PLAN.md](ROUND2_PLAN.md)) applied in burning days; entrant frozen in [TOURNAMENT_RESULTS.md](TOURNAMENT_RESULTS.md). Do not edit by hand._

- Entrant: **D-a + J-S** (C3, FRP-class A2-style ratios, in burning days; a = 10). frozen_round3.json SHA-256 `f3130df9ed80894e0176866cd3c8e51a3c4a7233c3cb40dd1c7b93651d4357a2` (checked); its tournament run 2026-11-01T15:11:43+00:00 at commit `cc30c6e280ffbb91dd077d0623e59823f0bbc4a0`.
- Tournament code hash now `cd4a4b5470a2c3e3`, at the freeze `cd4a4b5470a2c3e3` (same as at the freeze).
- Run started 2026-11-02T09:16:07+00:00 (UTC) at commit `2a59a3e90e6fd4115df7eac0813ae2c3f4259b43`.
- Unit: burning days, for the model, MODIS, F0 and F1. Windows: Test 1 2020–2021. Test 2 2020-01 … 2025-12. Seam 2020–2021. Drift 2022–2025 against 2012–2019.
- Invocations of this kind logged in data/processed/round3/confirm_runs.jsonl before this report: 1 started, 0 finished (this run's finish line is written right after the report).

## Overall: **CONFIRMED**

Regions included (4): northern_algeria, southern_france, south_australia, n_california.

| Part | Needed | Got | |
|---|---|---|---|
| Test 1 (a): cell-month WAPE ≤ F1 + 1.0 point and < F0 | ≤ 37.2% and < 110.5% | 29.7% | **pass** |
| Test 1 (b): 80% coverage on active rows | 0.70 … 0.90 | 0.838 | **pass** |
| Test 1 (c): pooled predicted total ÷ observed MODIS burning days | 0.90 … 1.10 | 1.069 (39,482 ÷ 36,939) | **pass** |
| Test 1 (d): national-month WAPE ≤ F1 + 1.0 point | ≤ 21.3% | 11.6% | **pass** |
| Test 2: share of counted region-months whose 80% intervals overlap | ≥ 0.80 | 0.973 (213 of 219) | **pass** |

## Deviations / interpretations

Points the plan left open, settled by the most literal reading when the code was written (on development regions only, before any sealed file was read).

1. **Entrant**: D-a, the tournament's C3 (FRP-class A2-style ratios) in the burning-day unit, as ruled in TOURNAMENT_PLAN.md (ruling added 1 Nov 2026). It is read from data/processed/tournament/frozen_round3.json, and the run refuses to start unless that file's SHA-256 is the one recorded at the freeze in TOURNAMENT_RESULTS.md. a is the file's frozen setting. The refit is `pipeline.tournament.candidates.fit("C3", …, setting=a)`. Nothing is tuned.
2. **Rows** are round 2's: cell × month × day/night from 2012-02, for every cell with a MODIS, Suomi NPP or NOAA-20 detection in 2012-02 … 2019-12. A cell first seen after 2019 has no row, so its detections are not scored. They are counted under Data below. **Unit**: the tournament's burning days. A 0.01° cell counts once per date and day/night if it has any detection of the family (MODIS = Terra and Aqua together). The cell-day counts are summed per row. A burning day takes the FRP class of its largest-FRP detection. Y, V and V20 and the class counts are all burning days.
3. **Each region is fitted on its own rows only**, as a one-region table, so every fallback ("all regions") stays inside the region. D-a is fitted on 2012-02 … 2019-12. s for J-S is fitted on 2018-04 … 2019-12 in burning days. Each bootstrap is seeded with 20261101 plus a CRC32 of its label ("round3", region, use).
4. **Outage rule**: round 2's. It is the bake-off rule over the included regions combined, on detections (the unit does not change which days are outages). Test 1, the seam check and the drift check leave out months with a MODIS day at 0 while Suomi NPP is ≥ 50, or the reverse. Test 2 uses no MODIS, so it leaves out months with a Suomi NPP day at 0 while NOAA-20 is ≥ 50, or the reverse. Fitting uses all months.
5. **Test 1 (a)–(d)**: round 2's pass rules, with every quantity in burning days. "At most F1's + 1.0 percentage point" means WAPE ≤ F1's WAPE + 0.010. "Below F0's" is strict. **(c)**: |Σ predicted ÷ Σ observed MODIS burning days − 1| ≤ 0.10, pooled over the regions' Test 1 rows. **F0** is the raw Suomi NPP burning-day count. **F1** is R1's point forecast (round 2's `fit_ratio`, unchanged) fitted on the region's own 2012–2019 rows in burning days: r·V when V > 0, b when V = 0.
6. **Coverage** is y in [q10, q90] on active rows (Y > 0 or V > 0). D-a's forecast is the sum of its class negative binomials, moment-matched to one negative binomial. V = 0 rows use Poisson(b_A). The split into active rows with V > 0 and with V = 0 (MODIS-only rows) is reported only.
7. **Test 2 intervals** are round 2's: mean ± 1.2816·sd, with sd² = the summed row predictive variances plus the bootstrap variance of the total from s. D-a has no bootstrap of its own, as A2 in round 2. A region-month counts if both expected totals are ≥ 10 (burning days), and it agrees if the 80% intervals overlap. The share is pooled over the regions.
8. **Seam check** uses Test 1's scored months. Its 80% interval is the summed row predictive variance.
9. **Drift band**: monthly observed ÷ predicted MODIS burning days for 2012–2019. Each year is predicted by D-a refitted without that year, with the same a. The band is the 10th–90th percentile. Only months with a predicted total ≥ 10 count, and outage months are left out.
10. **Swap metrics** (report only): |log(NOAA-20-based total ÷ Suomi NPP-based total)| over Test 2's region-months where both totals are > 0, as in the tournament. The median and the 90th percentile are reported, the 90th by numpy's linear interpolation. The same is shown where both are ≥ 10, and for the 2020–2021 months alone (the tournament's window).
11. **f0 check** (report only): a row's f0 part is the FRP ≤ 0 class's own term of D-a's class sum, V_f0·(a + SY_f0) ÷ (a ÷ r0_f0 + SV_f0); V = 0 rows have none. Summed per region-month, it is listed where it is more than 25% of the predicted total (total > 0). This is done on Test 1's rows (Suomi NPP) and on Test 2's rows (Suomi NPP-based and NOAA-20-based).
12. **Raw folders**: data/raw/algeria and data/raw/france (FIRMS country files), data/raw/australia_sa and data/raw/usa_norcal (area-API box files). All four are clipped to the boxes in pipeline/regions.py.
13. **Completeness**: the confirmation refuses to start unless every MODIS and Suomi NPP file for 2012–2025 and every NOAA-20 file for 2018–2025 is in each sealed region's manifest. A half-finished download therefore cannot use up the one run.

## Test 1: accuracy against near-nominal MODIS, 2020–2021, in burning days

Fit on 2012-02 … 2019-12, scored on 2020–2021 months without an outage day: 35,280 rows (6,297 active), 36,939 MODIS burning days. Months left out: none.

| Forecast | Cell-month WAPE | National-month WAPE | Predicted total (observed 36,939) |
|---|---|---|---|
| D-a, frozen model | 29.7% | 11.6% | 39,482 |
| F0 raw Suomi NPP burning days | 110.5% | 104.7% | 75,603 |
| F1 R1's point forecast, burning days | 36.2% | 20.3% | 34,069 |

D-a only: weighted CRPS 0.330, 80% coverage on active rows 83.8% (all rows, for information: 97.1%).

Report only, coverage of active rows split by Suomi NPP:

| Active rows | Rows | 80% coverage |
|---|---|---|
| V > 0 | 5,871 | 89.1% |
| V = 0 (MODIS only) | 426 | 10.6% |

By region:

| Region | Rows | Active | MODIS (Y) | Cell-month WAPE model | F0 | F1 | National-month WAPE model | F0 | F1 | Predicted ÷ observed | Weighted CRPS | Coverage, active rows | Coverage, active V > 0 | Coverage, active V = 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| northern_algeria | 15,600 | 2,619 | 5,626 | 49.5% | 134.3% | 64.6% | 10.6% | 120.7% | 33.0% | 1.026 | 0.215 | 82.6% | 88.4% | 0.0% |
| southern_france | 4,704 | 656 | 633 | 105.0% | 182.5% | 121.8% | 29.6% | 118.3% | 56.6% | 0.954 | 0.096 | 83.1% | 91.6% | 31.9% |
| south_australia | 8,544 | 925 | 1,631 | 65.4% | 125.8% | 82.6% | 18.8% | 96.6% | 40.2% | 1.041 | 0.098 | 84.3% | 90.5% | 18.8% |
| n_california | 6,432 | 2,097 | 29,049 | 22.2% | 103.5% | 26.2% | 11.0% | 101.7% | 16.0% | 1.081 | 0.857 | 85.2% | 88.6% | 0.0% |

D-a's fit per region: northern_algeria a 10, map evaluations 100, last relative change 8.1e-09, converged True, r0 groups on fallback 24; southern_france a 10, map evaluations 28, last relative change 1.4e-09, converged True, r0 groups on fallback 31; south_australia a 10, map evaluations 52, last relative change 6.1e-08, converged True, r0 groups on fallback 32; n_california a 10, map evaluations 190, last relative change 6.1e-08, converged True, r0 groups on fallback 24.

F1 per region (r day / night; b day / night): northern_algeria 0.520 / 0.217; 0.031 / 0.004; southern_france 0.412 / 0.111; 0.075 / 0.002; south_australia 0.547 / 0.213; 0.029 / 0.001; n_california 0.581 / 0.355; 0.054 / 0.002.

## Test 2: satellite swap, 2020–2025, in burning days

Suomi NPP: D-a fitted on 2012-02 … 2019-12. NOAA-20: J-S, s fitted on 2018-04 … 2019-12. Months left out (outage): 2022-08, 2024-07, 2024-09.

Pooled: 276 region-months, **219 counted, 213 agree (97.3%)**.

| Region | Region-months | Counted | Agree | Share | Σ Suomi NPP-based | Σ NOAA-20-based |
|---|---|---|---|---|---|---|
| northern_algeria | 69 | 61 | 58 | 95.1% | 8,470 | 8,890 |
| southern_france | 69 | 43 | 43 | 100.0% | 1,512 | 1,559 |
| south_australia | 69 | 46 | 45 | 97.8% | 3,944 | 4,208 |
| n_california | 69 | 69 | 67 | 97.1% | 39,059 | 40,032 |

By region and year (counted / agree):

| Region | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| northern_algeria | 10 / 10 | 12 / 11 | 11 / 11 | 11 / 10 | 8 / 8 | 9 / 8 |
| southern_france | 8 / 8 | 7 / 7 | 8 / 8 | 8 / 8 | 5 / 5 | 7 / 7 |
| south_australia | 8 / 8 | 7 / 6 | 6 / 6 | 9 / 9 | 8 / 8 | 8 / 8 |
| n_california | 12 / 11 | 12 / 11 | 11 / 11 | 12 / 12 | 10 / 10 | 12 / 12 |

Counted region-months that disagree (counts are burning days):

| Region | Month | Suomi NPP-based (80% interval) | NOAA-20-based, J-S (80% interval) | Suomi NPP count | NOAA-20 count |
|---|---|---|---|---|---|
| northern_algeria | 2021-08 | 1,690.3 (1,615.8 … 1,764.8) | 1,461.7 (1,363.2 … 1,560.3) | 2,657 | 2,326 |
| northern_algeria | 2023-07 | 410.6 (375.0 … 446.2) | 731.2 (667.8 … 794.6) | 566 | 908 |
| northern_algeria | 2025-06 | 54.1 (44.3 … 63.9) | 83.2 (70.1 … 96.3) | 232 | 263 |
| south_australia | 2021-05 | 121.4 (106.7 … 136.0) | 163.5 (140.4 … 186.6) | 200 | 259 |
| n_california | 2020-01 | 53.8 (43.8 … 63.7) | 80.7 (68.1 … 93.4) | 144 | 178 |
| n_california | 2021-05 | 76.9 (65.0 … 88.9) | 54.6 (44.6 … 64.6) | 246 | 205 |

s per region, burning days (sd from the month-block bootstrap): northern_algeria day 1.040 (0.042), night 1.103 (0.073); southern_france day 0.939 (0.067), night 0.958 (0.070); south_australia day 1.041 (0.084), night 1.052 (0.073); n_california day 1.013 (0.018), night 1.001 (0.012).

## Report only: swap metrics, |log(NOAA-20-based ÷ Suomi NPP-based)|

Per region-month of Test 2. On development data (2020–2021, both totals > 0), D-a's median was 0.108 (TOURNAMENT_RESULTS.md, burning-day leaderboard) and its 90th percentile 0.46 (same file, independent test).

| Regions | Window | Both > 0 | Median | 90th percentile | Maximum | Both ≥ 10 | Median | 90th percentile |
|---|---|---|---|---|---|---|---|---|
| all regions | 2020–2025 | 276 | 0.102 | 0.299 | 0.999 | 219 | 0.084 | 0.266 |
| all regions | 2020–2021 | 96 | 0.107 | 0.338 | 0.999 | 76 | 0.084 | 0.268 |
| northern_algeria | 2020–2025 | 69 | 0.112 | 0.230 | 0.577 | 61 | 0.112 | 0.235 |
| southern_france | 2020–2025 | 69 | 0.102 | 0.299 | 0.434 | 43 | 0.096 | 0.286 |
| south_australia | 2020–2025 | 69 | 0.176 | 0.409 | 0.999 | 46 | 0.164 | 0.370 |
| n_california | 2020–2025 | 69 | 0.047 | 0.155 | 0.407 | 69 | 0.047 | 0.155 |

## Report only: the f0 (FRP ≤ 0) tail risk

The independent test recorded that the FRP ≤ 0 class has an unstable ratio, and that one such burning day inside a big fire can add a lot to a row. This lists the region-months where the f0 part is more than 25% of D-a's predicted total. Test 1, pooled: the f0 part is 0.1% of the predicted total.

Region-months with a predicted total > 0: Test 1, Suomi NPP 96; Test 2, NOAA-20-based (J-S) 276; Test 2, Suomi NPP-based 276.

None.

## Report only: seam check, 2020 and 2021

Harmonized (D-a's predicted MODIS burning days from Suomi NPP) ÷ observed MODIS burning days, with the 80% interval.

| Region | Year | Observed MODIS | Harmonized | Ratio | 80% interval of the ratio |
|---|---|---|---|---|---|
| northern_algeria | 2020 | 3,395 | 3,370 | 0.993 | 0.968 … 1.017 |
| northern_algeria | 2021 | 2,231 | 2,404 | 1.077 | 1.039 … 1.116 |
| southern_france | 2020 | 201 | 231 | 1.150 | 1.050 … 1.250 |
| southern_france | 2021 | 432 | 373 | 0.863 | 0.788 … 0.937 |
| south_australia | 2020 | 1,143 | 1,149 | 1.006 | 0.887 … 1.125 |
| south_australia | 2021 | 488 | 549 | 1.125 | 1.060 … 1.190 |
| n_california | 2020 | 17,700 | 19,142 | 1.081 | 1.050 … 1.112 |
| n_california | 2021 | 11,349 | 12,264 | 1.081 | 1.030 … 1.131 |

## Report only: drift divergence, 2022–2025

Monthly observed MODIS burning days ÷ D-a's prediction from Suomi NPP. The 2012–2019 band is the 10th–90th percentile of the same ratio, leave-one-year-out.

| Region | 2012–2019 band (median) | Year | Months used | Median ratio | Months below band | Months above band |
|---|---|---|---|---|---|---|
| northern_algeria | 0.52 … 1.40 (0.92) | 2022 | 11 | 0.81 | 1 | 1 |
| northern_algeria | 0.52 … 1.40 (0.92) | 2023 | 11 | 0.87 | 2 | 0 |
| northern_algeria | 0.52 … 1.40 (0.92) | 2024 | 9 | 0.75 | 1 | 1 |
| northern_algeria | 0.52 … 1.40 (0.92) | 2025 | 9 | 0.88 | 0 | 2 |
| southern_france | 0.36 … 1.42 (0.91) | 2022 | 9 | 1.33 | 0 | 3 |
| southern_france | 0.36 … 1.42 (0.91) | 2023 | 8 | 1.00 | 0 | 2 |
| southern_france | 0.36 … 1.42 (0.91) | 2024 | 6 | 1.10 | 0 | 0 |
| southern_france | 0.36 … 1.42 (0.91) | 2025 | 8 | 0.64 | 1 | 2 |
| south_australia | 0.50 … 1.42 (0.94) | 2022 | 5 | 0.89 | 1 | 0 |
| south_australia | 0.50 … 1.42 (0.94) | 2023 | 10 | 0.70 | 2 | 1 |
| south_australia | 0.50 … 1.42 (0.94) | 2024 | 9 | 0.78 | 1 | 1 |
| south_australia | 0.50 … 1.42 (0.94) | 2025 | 9 | 0.88 | 2 | 2 |
| n_california | 0.70 … 1.23 (0.97) | 2022 | 11 | 0.97 | 0 | 1 |
| n_california | 0.70 … 1.23 (0.97) | 2023 | 12 | 1.03 | 0 | 4 |
| n_california | 0.70 … 1.23 (0.97) | 2024 | 11 | 0.97 | 2 | 1 |
| n_california | 0.70 … 1.23 (0.97) | 2025 | 12 | 0.73 | 3 | 0 |

## Data

| Region | Cells | Detections 2020–2025 in cells with rows (MODIS / Suomi NPP / NOAA-20) | Burning days 2020–2025 on rows (MODIS / Suomi NPP / NOAA-20) | Detections in cells without rows (not scored) |
|---|---|---|---|---|
| northern_algeria | 325 | 9,170 / 34,935 / 35,504 | 8,499 / 21,934 / 22,938 | 2 / 60 / 47 |
| southern_france | 98 | 1,753 / 4,924 / 5,599 | 1,679 / 3,649 / 4,130 | 0 / 0 / 0 |
| south_australia | 178 | 3,913 / 12,772 / 13,467 | 3,657 / 8,088 / 8,471 | 33 / 162 / 116 |
| n_california | 134 | 45,624 / 185,271 / 196,504 | 38,521 / 76,282 / 79,842 | 0 / 5 / 4 |

Outage days: MODIS 2014-03-03, 2022-10-15; Suomi NPP (vs MODIS) 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28; Suomi NPP (vs NOAA-20) 2022-08-09, 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28, 2024-09-26; NOAA-20 none.

Invocations of this kind logged before this report:

- start 2026-11-02T09:16:07+00:00 regions northern_algeria, southern_france, south_australia, n_california

## Timings

| Stage | Seconds |
|---|---|
| data | 18 |
| tests | 5 |
| total | 25 |
