# Lebanon: older Natural Earth 1:10m versions

Rules: [plan addendum](../../docs/OBS2026_VALIDATION_PLAN.md). Selection on 2000–2022 country files; test on 2023–2025 area-API data with the unchanged C1–C3 thresholds.

Selection points: 21,725. Versions with an identical Lebanon polygon are one row.

## Selection (2000–2022)

| Commits (newest first) | Mismatches | Lebanon's, outside | Neighbour's, inside | Where |
|---|---:|---:|---:|---|
| 5faefd9a6c (2022-04-22), a7c8ff86de (2022-03-17), 3aa16bdc7a (2021-11-09), 6bd810ae44 (2021-09-03) — in use now | 12 | 0 | 12 | south (incl. Shebaa area) 12 |
| dfa866485b (2021-12-07) | 12 | 0 | 12 | south (incl. Shebaa area) 12 |
| 402b35abd0 (2021-11-14) | 12 | 0 | 12 | south (incl. Shebaa area) 12 |
| be165336bb (2021-08-30), de9e8d0741 (2021-08-01), 0edfe737ff (2021-05-29), c034dccd73 (2021-02-14), 0eca99ed93 (2021-01-20), 709ffdf7e5 (2021-01-06) **(selected)** | 0 | 0 | 0 |  |
| e5f6e02319 (2020-12-13) | 0 | 0 | 0 |  |
| a632044a31 (2018-05-15) | 0 | 0 | 0 |  |
| f1cf55a25f (2017-10-05), 4db6e25860 (2014-12-31) | 0 | 0 | 0 |  |
| 8dc5287cad (2017-08-14), d19dfc7f9a (2012-11-05), 58b6cdc00a (2012-11-04), 04b377f5cc (2012-11-04) | 0 | 0 | 0 |  |
| 68f72292bd (2013-06-02) | 0 | 0 | 0 |  |
| 71967a117e (2012-08-19) | 0 | 0 | 0 |  |
| 3564a7c7bb (2012-01-22) | 5 | 5 | 0 | east / north (Syria) 3, coast 2 |

## Independent test — **PASS**

| Year | Sensor | Country file | False incl. | False excl. | C1 | Worst month (C2) | C3 | Pass |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 2023 | modis | 68 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2023 | snpp | 590 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2023 | noaa20 | 559 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2024 | modis | 210 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2024 | snpp | 1,162 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2024 | noaa20 | 1,137 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2025 | modis | 87 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2025 | snpp | 514 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2025 | noaa20 | 545 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
