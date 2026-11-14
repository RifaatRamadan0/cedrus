# Confirmation results: the frozen model on the four sealed regions

_Generated 2026-11-01T10:33:42+00:00 by `python -m pipeline.confirm.run`. Rules: [CONFIRMATION_PLAN.md](CONFIRMATION_PLAN.md), pre-registered at commit 0cdcdd6 before any sealed data was downloaded. Do not edit by hand._

```bash
python -m pipeline.confirm.run
```

- Run started 2026-11-01T10:33:29+00:00 (UTC); repository commit `57b6bbc2c9f40009ad2c438da463eb351c4d8895`.
- Model A code in `pipeline/bakeoff/` is unchanged since commit f0823f9 (`git diff --stat f0823f9 -- pipeline/bakeoff` is empty).
- Test windows: Test 1 scores 2020–2021. Test 2 compares 2020–2025. Seam check: 2020–2021. Drift check: 2022–2025 against 2012–2019.
- Confirmation invocations logged in data/processed/confirm/runs.jsonl: 1 started, 0 finished before this report was written (this run's finish line is written right after it).

## Overall: **NOT CONFIRMED**

Failing parts: Test 1 (a) cell-month WAPE vs floors; Test 2 swap agreement.

Regions included (4): morocco, tunisia, central_chile, western_cape.

| Part | Needed | Got | |
|---|---|---|---|
| Test 1 (a): A's cell-month WAPE below F1's and F0's | A < 60.1% and A < 265.8% | 67.4% | **fail** |
| Test 1 (b): 80% coverage on active rows | 0.70 … 0.90 | 0.850 | **pass** |
| Test 2: share of counted region-months whose 80% intervals overlap | ≥ 0.80 | 0.692 (157 of 227) | **fail** |

## Deviations / interpretations

Points the plan left open, settled by the most literal reading before any result was seen.

1. **Rows** are the bake-off's: cell × month × day/night from 2012-02, for every cell with a MODIS or VIIRS detection in 2012-02 … 2019-12. NOAA-20 detections in 2018–2019 count as VIIRS here. A cell first seen after 2019 has no row, so its detections are not scored. They are counted under Data below.
2. **Each region is fitted on its own rows only**, as a one-region table, so A's last-resort fallback ("all regions") is that region itself.
3. **Outage rule**: the bake-off rule per family, over the included regions combined. Test 1, the seam check and the drift check leave out months with a MODIS or Suomi NPP outage day. Test 2 does not use MODIS. It leaves out months with an outage day for Suomi NPP or for NOAA-20, where a NOAA-20 outage day means NOAA-20 had 0 while MODIS had ≥ 50 (the plan does not name a NOAA-20 rule). Fitting uses all months, as in the bake-off.
4. **Test 2 intervals** are mean ± 1.2816·√(summed variance), a normal approximation, not clipped at 0. The sum covers every row of the region-month, so it includes the Poisson(b_A) rows where the VIIRS count is 0 (variance b_A) as well as the negative-binomial rows. The NOAA-20 fit uses 2018-04 … 2019-12 rows only.
5. **A's V = 0 quirk is kept** (BAKEOFF_RESULTS, independent test). Every row with no VIIRS detection still predicts b_A, in Test 1 and in both Test 2 totals.
6. **Coverage** is as in the bake-off: y inside [q10, q90], with q the smallest k where F(k) ≥ 0.1 or 0.9. Only active rows (Y > 0 or V > 0) count for (b). All-row coverage is shown for information.
7. **F1**'s ratio is ΣY/ΣV over the 2012-02 … 2019-12 rows of the region, per day/night. **Weighted CRPS** uses w = 1 + the cell's mean Y over the same rows.
8. **Seam check** uses Test 1's scored months. Its interval is the same normal 80% interval.
9. **Drift band**: monthly observed ÷ predicted for 2012–2019, each year predicted by A refitted without that year (leave-one-year-out), so the band is out of sample like 2022–2025. Band = 10th–90th percentile. Only months whose predicted total is ≥ 10 are used, and outage months are left out.
10. **Raw folders** for Central Chile and Western Cape are data/raw/chile and data/raw/south_africa, clipped to the boxes in pipeline/regions.py.

## Test 1: accuracy against near-nominal MODIS, 2020–2021

Fit on 2012-02 … 2019-12, scored on every 2020–2021 month without an outage day: 55,440 rows (7,358 active), 12,636 MODIS detections. Months left out: 2022-04, 2025-07.

| Model | Cell-month WAPE | National-month WAPE | Predicted total (observed 12,636) |
|---|---|---|---|
| A, frozen model (a = 30) | 67.4% | 22.5% | 14,380 |
| F0 raw Suomi NPP count (floor) | 265.8% | 252.4% | 44,531 |
| F1 one ratio per region × day/night (floor) | 60.1% | 16.3% | 13,121 |

A only: weighted CRPS 0.191, CRPS 0.104, 80% coverage on active rows 85.0% (all rows, for information: 98.0%).

By region:

| Region | Rows | Active | MODIS (Y) | Cell-month WAPE A | F0 | F1 | National-month WAPE A | F0 | F1 | Weighted CRPS A | Coverage, active rows |
|---|---|---|---|---|---|---|---|---|---|---|---|
| morocco | 21,696 | 1,501 | 640 | 134.3% | 460.6% | 121.2% | 34.2% | 410.3% | 31.1% | 0.025 | 88.7% |
| tunisia | 9,504 | 963 | 1,033 | 73.3% | 380.8% | 75.5% | 22.5% | 369.2% | 37.7% | 0.070 | 87.0% |
| central_chile | 9,984 | 3,186 | 7,281 | 59.9% | 262.7% | 52.4% | 23.0% | 254.7% | 13.5% | 0.436 | 85.4% |
| western_cape | 14,256 | 1,708 | 3,682 | 69.0% | 205.8% | 60.1% | 19.5% | 187.6% | 13.4% | 0.192 | 79.7% |

## Test 2: satellite swap, 2020–2025

A fitted on Suomi NPP (2012-02 … 2019-12) and on NOAA-20 (2018-04 … 2019-12), each against MODIS. Each region-month gets two MODIS-equivalent totals, with 80% intervals. They agree if the intervals overlap. A region-month is counted only if both totals are ≥ 10. Months left out (outage): 2024-02.

Pooled: 284 region-months, **227 counted, 157 agree (69.2%)**.

| Region | Region-months | Counted | Agree | Share | Σ Suomi NPP-based total | Σ NOAA-20-based total |
|---|---|---|---|---|---|---|
| morocco | 71 | 57 | 49 | 86.0% | 2,060 | 2,347 |
| tunisia | 71 | 28 | 18 | 64.3% | 1,935 | 1,495 |
| central_chile | 71 | 71 | 40 | 56.3% | 31,786 | 28,405 |
| western_cape | 71 | 71 | 50 | 70.4% | 15,867 | 14,143 |

By region and year (counted / agree):

| Region | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| morocco | 9 / 7 | 9 / 6 | 10 / 10 | 12 / 10 | 9 / 8 | 8 / 8 |
| tunisia | 5 / 4 | 5 / 2 | 5 / 2 | 4 / 3 | 4 / 3 | 5 / 4 |
| central_chile | 12 / 7 | 12 / 6 | 12 / 6 | 12 / 6 | 11 / 6 | 12 / 9 |
| western_cape | 12 / 8 | 12 / 8 | 12 / 8 | 12 / 11 | 11 / 7 | 12 / 8 |

Counted region-months that disagree:

| Region | Month | Suomi NPP-based (80% interval) | NOAA-20-based (80% interval) | Suomi NPP count | NOAA-20 count |
|---|---|---|---|---|---|
| morocco | 2020-07 | 22.4 (16.3 … 28.5) | 37.6 (29.7 … 45.5) | 75 | 120 |
| morocco | 2020-10 | 33.3 (25.8 … 40.8) | 51.5 (42.1 … 60.9) | 188 | 242 |
| morocco | 2021-07 | 54.8 (45.1 … 64.5) | 91.3 (78.2 … 104.3) | 243 | 332 |
| morocco | 2021-08 | 67.8 (56.1 … 79.6) | 104.1 (88.8 … 119.4) | 238 | 370 |
| morocco | 2021-10 | 36.9 (29.0 … 44.7) | 56.2 (46.5 … 66.0) | 227 | 303 |
| morocco | 2023-07 | 59.6 (49.4 … 70.0) | 96.3 (82.0 … 110.8) | 250 | 341 |
| morocco | 2023-08 | 89.7 (76.6 … 102.7) | 125.3 (108.9 … 141.7) | 329 | 428 |
| morocco | 2024-07 | 20.2 (14.4 … 26.0) | 38.4 (30.4 … 46.5) | 72 | 137 |
| tunisia | 2020-08 | 233.8 (212.4 … 255.3) | 124.4 (109.0 … 139.8) | 851 | 681 |
| tunisia | 2021-06 | 61.1 (50.0 … 72.3) | 37.6 (29.1 … 46.1) | 396 | 384 |
| tunisia | 2021-08 | 216.3 (194.0 … 238.5) | 105.2 (90.5 … 119.9) | 767 | 571 |
| tunisia | 2021-09 | 50.3 (41.0 … 59.6) | 31.4 (24.0 … 38.7) | 257 | 230 |
| tunisia | 2022-06 | 33.5 (25.9 … 41.2) | 18.1 (12.6 … 23.7) | 238 | 235 |
| tunisia | 2022-08 | 107.4 (92.8 … 122.0) | 65.2 (54.3 … 76.0) | 303 | 332 |
| tunisia | 2022-09 | 61.7 (51.3 … 72.2) | 39.1 (30.7 … 47.5) | 298 | 284 |
| tunisia | 2023-07 | 63.2 (52.3 … 74.0) | 89.3 (74.7 … 103.9) | 202 | 302 |
| tunisia | 2024-08 | 39.9 (31.7 … 48.2) | 22.5 (16.4 … 28.6) | 126 | 114 |
| tunisia | 2025-07 | 48.0 (38.9 … 57.1) | 84.3 (70.2 … 98.3) | 167 | 306 |
| central_chile | 2020-01 | 409.8 (381.7 … 437.9) | 346.6 (319.4 … 373.8) | 1,246 | 1,227 |
| central_chile | 2020-03 | 644.7 (606.7 … 682.7) | 548.8 (510.7 … 587.0) | 2,265 | 2,052 |
| central_chile | 2020-10 | 396.7 (369.2 … 424.1) | 196.4 (177.6 … 215.2) | 879 | 891 |
| central_chile | 2020-11 | 234.9 (214.1 … 255.7) | 150.4 (133.5 … 167.3) | 489 | 496 |
| central_chile | 2020-12 | 161.8 (144.9 … 178.6) | 97.7 (84.7 … 110.6) | 386 | 338 |
| central_chile | 2021-01 | 526.7 (485.9 … 567.5) | 421.2 (383.8 … 458.6) | 1,622 | 1,454 |
| central_chile | 2021-03 | 579.4 (546.5 … 612.1) | 506.3 (469.6 … 543.0) | 1,545 | 1,531 |
| central_chile | 2021-05 | 337.1 (312.4 … 361.7) | 399.3 (371.7 … 427.0) | 1,055 | 1,147 |
| central_chile | 2021-10 | 244.3 (223.6 … 265.0) | 126.2 (111.4 … 141.0) | 617 | 621 |
| central_chile | 2021-11 | 238.6 (217.8 … 259.4) | 151.3 (134.7 … 167.9) | 495 | 528 |
| central_chile | 2021-12 | 590.3 (547.8 … 632.8) | 427.7 (392.8 … 462.6) | 1,739 | 1,722 |
| central_chile | 2022-01 | 296.2 (268.3 … 324.1) | 211.7 (188.3 … 235.1) | 869 | 723 |
| central_chile | 2022-03 | 657.0 (617.7 … 696.4) | 500.7 (465.7 … 535.6) | 2,368 | 2,005 |
| central_chile | 2022-08 | 55.7 (46.0 … 65.4) | 82.0 (70.1 … 93.9) | 191 | 268 |
| central_chile | 2022-10 | 295.7 (271.2 … 320.2) | 170.8 (151.2 … 190.3) | 616 | 670 |
| central_chile | 2022-11 | 250.9 (228.0 … 273.9) | 190.7 (169.2 … 212.1) | 604 | 682 |
| central_chile | 2022-12 | 994.4 (938.8 … 1,050.1) | 634.6 (593.0 … 676.3) | 2,828 | 2,494 |
| central_chile | 2023-01 | 529.6 (497.5 … 561.7) | 462.4 (429.6 … 495.2) | 1,622 | 1,626 |
| central_chile | 2023-03 | 541.7 (510.0 … 573.4) | 442.5 (408.1 … 476.9) | 1,686 | 1,521 |
| central_chile | 2023-09 | 87.7 (75.4 … 100.0) | 51.4 (42.1 … 60.8) | 228 | 148 |
| central_chile | 2023-10 | 280.2 (257.2 … 303.3) | 141.9 (125.7 … 158.1) | 647 | 598 |
| central_chile | 2023-11 | 291.6 (268.3 … 314.9) | 118.2 (103.7 … 132.8) | 567 | 366 |
| central_chile | 2023-12 | 359.6 (331.4 … 387.8) | 225.4 (203.9 … 246.9) | 919 | 768 |
| central_chile | 2024-05 | 540.5 (509.0 … 572.1) | 622.0 (586.7 … 657.3) | 1,785 | 1,981 |
| central_chile | 2024-07 | 75.0 (63.7 … 86.4) | 179.7 (161.4 … 197.9) | 276 | 663 |
| central_chile | 2024-10 | 294.0 (270.8 … 317.3) | 159.8 (142.9 … 176.7) | 573 | 662 |
| central_chile | 2024-11 | 258.3 (236.8 … 279.7) | 207.1 (187.6 … 226.6) | 521 | 679 |
| central_chile | 2024-12 | 326.3 (301.6 … 351.0) | 208.2 (188.6 … 227.8) | 765 | 676 |
| central_chile | 2025-10 | 311.5 (287.2 … 335.9) | 150.4 (133.7 … 167.0) | 612 | 590 |
| central_chile | 2025-11 | 438.8 (409.5 … 468.1) | 246.5 (224.7 … 268.2) | 916 | 783 |
| central_chile | 2025-12 | 344.7 (319.1 … 370.2) | 213.7 (193.8 … 233.6) | 847 | 804 |
| western_cape | 2020-02 | 224.1 (201.9 … 246.3) | 163.5 (144.5 … 182.4) | 775 | 667 |
| western_cape | 2020-03 | 444.2 (413.8 … 474.6) | 365.5 (336.8 … 394.2) | 968 | 966 |
| western_cape | 2020-05 | 253.4 (231.9 … 274.9) | 202.6 (183.1 … 222.2) | 528 | 489 |
| western_cape | 2020-11 | 64.2 (53.6 … 74.9) | 43.3 (34.7 … 52.0) | 172 | 126 |
| western_cape | 2021-02 | 369.3 (338.3 … 400.3) | 286.8 (259.0 … 314.6) | 1,237 | 1,199 |
| western_cape | 2021-03 | 559.8 (526.2 … 593.3) | 387.7 (357.3 … 418.1) | 1,146 | 947 |
| western_cape | 2021-05 | 282.3 (259.5 … 305.1) | 215.6 (195.5 … 235.8) | 606 | 539 |
| western_cape | 2021-11 | 68.2 (57.2 … 79.2) | 44.8 (36.0 … 53.6) | 172 | 134 |
| western_cape | 2022-02 | 355.9 (325.1 … 386.6) | 254.9 (230.6 … 279.1) | 1,026 | 974 |
| western_cape | 2022-03 | 610.5 (574.5 … 646.6) | 443.3 (410.0 … 476.6) | 1,334 | 1,123 |
| western_cape | 2022-05 | 294.1 (270.6 … 317.5) | 243.9 (222.2 … 265.7) | 663 | 631 |
| western_cape | 2022-10 | 64.2 (53.5 … 74.9) | 88.3 (75.5 … 101.0) | 175 | 203 |
| western_cape | 2023-03 | 197.7 (179.0 … 216.3) | 135.2 (119.2 … 151.3) | 329 | 295 |
| western_cape | 2024-03 | 740.9 (700.0 … 781.8) | 543.9 (507.3 … 580.4) | 1,675 | 1,373 |
| western_cape | 2024-04 | 567.6 (534.2 … 601.0) | 498.5 (464.3 … 532.8) | 1,445 | 1,468 |
| western_cape | 2024-05 | 306.0 (281.9 … 330.1) | 244.2 (222.5 … 265.9) | 744 | 698 |
| western_cape | 2024-10 | 86.4 (74.1 … 98.7) | 124.3 (109.3 … 139.3) | 221 | 277 |
| western_cape | 2025-01 | 306.5 (279.3 … 333.7) | 219.7 (196.8 … 242.6) | 970 | 749 |
| western_cape | 2025-02 | 431.1 (400.6 … 461.6) | 362.6 (332.1 … 393.1) | 1,319 | 1,410 |
| western_cape | 2025-03 | 756.2 (710.8 … 801.6) | 620.6 (576.0 … 665.1) | 1,804 | 1,761 |
| western_cape | 2025-10 | 286.7 (258.6 … 314.8) | 391.3 (352.3 … 430.2) | 712 | 869 |

## Report only: seam check, 2020 and 2021

Harmonized (A's predicted MODIS total from Suomi NPP) ÷ observed MODIS, per year, with the 80% interval.

| Region | Year | Observed MODIS | Harmonized | Ratio | 80% interval of the ratio |
|---|---|---|---|---|---|
| morocco | 2020 | 322 | 375 | 1.164 | 1.083 … 1.245 |
| morocco | 2021 | 318 | 337 | 1.059 | 0.983 … 1.135 |
| tunisia | 2020 | 389 | 445 | 1.143 | 1.069 … 1.218 |
| tunisia | 2021 | 644 | 562 | 0.873 | 0.819 … 0.927 |
| central_chile | 2020 | 4,117 | 4,690 | 1.139 | 1.109 … 1.170 |
| central_chile | 2021 | 3,164 | 3,717 | 1.175 | 1.146 … 1.203 |
| western_cape | 2020 | 1,589 | 1,889 | 1.189 | 1.151 … 1.227 |
| western_cape | 2021 | 2,093 | 2,365 | 1.130 | 1.096 … 1.164 |

## Report only: drift divergence, 2022–2025

Monthly observed MODIS ÷ A's prediction from Suomi NPP. The 2012–2019 band is the 10th–90th percentile of the same ratio, computed leave-one-year-out.

| Region | 2012–2019 band (median) | Year | Months used | Median ratio | Months below band | Months above band |
|---|---|---|---|---|---|---|
| morocco | 0.38 … 1.16 (0.76) | 2022 | 11 | 0.78 | 0 | 4 |
| morocco | 0.38 … 1.16 (0.76) | 2023 | 12 | 0.76 | 0 | 4 |
| morocco | 0.38 … 1.16 (0.76) | 2024 | 10 | 0.54 | 3 | 1 |
| morocco | 0.38 … 1.16 (0.76) | 2025 | 8 | 0.81 | 0 | 3 |
| tunisia | 0.34 … 1.41 (0.76) | 2022 | 6 | 1.29 | 0 | 3 |
| tunisia | 0.34 … 1.41 (0.76) | 2023 | 4 | 1.08 | 0 | 1 |
| tunisia | 0.34 … 1.41 (0.76) | 2024 | 5 | 0.93 | 0 | 1 |
| tunisia | 0.34 … 1.41 (0.76) | 2025 | 4 | 0.87 | 0 | 0 |
| central_chile | 0.72 … 1.14 (0.94) | 2022 | 11 | 0.77 | 5 | 0 |
| central_chile | 0.72 … 1.14 (0.94) | 2023 | 12 | 0.77 | 6 | 0 |
| central_chile | 0.72 … 1.14 (0.94) | 2024 | 12 | 0.86 | 4 | 2 |
| central_chile | 0.72 … 1.14 (0.94) | 2025 | 11 | 0.71 | 6 | 0 |
| western_cape | 0.71 … 1.17 (0.91) | 2022 | 11 | 0.90 | 2 | 1 |
| western_cape | 0.71 … 1.17 (0.91) | 2023 | 12 | 0.72 | 6 | 0 |
| western_cape | 0.71 … 1.17 (0.91) | 2024 | 12 | 0.75 | 4 | 1 |
| western_cape | 0.71 … 1.17 (0.91) | 2025 | 11 | 0.82 | 2 | 0 |

## Data

| Region | Cells | Detections 2020–2025 in cells with rows (MODIS / Suomi NPP / NOAA-20) | Detections 2020–2025 in cells without rows (not scored) |
|---|---|---|---|
| morocco | 452 | 2,165 / 10,161 / 11,173 | 18 / 90 / 83 |
| tunisia | 198 | 1,984 / 10,191 / 10,563 | 6 / 33 / 46 |
| central_chile | 208 | 27,908 / 100,443 / 96,892 | 0 / 3 / 3 |
| western_cape | 297 | 14,256 / 44,743 / 43,248 | 2 / 21 / 19 |

Outage days: MODIS 2022-04-16, 2025-07-02; Suomi NPP none; NOAA-20 2024-02-04.

Model A code fingerprints (SHA-256, first 16 hex): `models.py` e7b649b251485f6a, `scores.py` ec35f85ba5506d10, `validate.py` 8beb8404d98c84e5, `data.py` 055e989efaf173ca.

Confirmation invocations logged before this report:

- start 2026-11-01T10:33:29+00:00 regions morocco, tunisia, central_chile, western_cape

## Timings

| Stage | Seconds |
|---|---|
| data | 11 |
| tests | 1 |
| total | 13 |
