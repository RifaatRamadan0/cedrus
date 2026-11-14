# Lebanon: other boundary datasets

Rules: [plan addendum](../../docs/OBS2026_VALIDATION_PLAN.md). Selection on 2000–2022 country files; independent test on 2023–2025 area-API data with the unchanged C1–C3 thresholds.

Selection points: 21,725 detections in Lebanon's box from Lebanon's and its two neighbours' files (12,585 in Lebanon's file).

## Selection (2000–2022)

| Candidate | Mismatches | Lebanon's, outside | Neighbour's, inside | Where |
|---|---:|---:|---:|---|
| Natural Earth 1:10m **(selected)** | 12 | 0 | 12 | south (incl. Shebaa area) 12 |
| Natural Earth 1:50m | 364 | 233 | 131 | east / north (Syria) 197, coast 86, south 63, south (incl. Shebaa area) 18 |
| FAO GAUL 2024 (level 1 units of Lebanon, merged) | 583 | 177 | 406 | east / north (Syria) 339, south 183, south (incl. Shebaa area) 35, coast 26 |
| geoBoundaries CGAZ ADM0 | 585 | 171 | 414 | east / north (Syria) 312, south 191, coast 47, south (incl. Shebaa area) 35 |
| geoBoundaries gbHumanitarian ADM0 | 699 | 189 | 510 | east / north (Syria) 462, south 183, south (incl. Shebaa area) 28, coast 26 |
| GADM 4.1 level 0 | 752 | 140 | 612 | east / north (Syria) 427, south 180, south (incl. Shebaa area) 130, coast 15 |
| geoBoundaries gbOpen ADM0 | 773 | 181 | 592 | east / north (Syria) 455, south 224, coast 55, south (incl. Shebaa area) 39 |
| Natural Earth 1:110m | 2,600 | 2,060 | 540 | east / north (Syria) 1239, coast 1132, south 116, south (incl. Shebaa area) 113 |
| US State Dept LSIB v11.4 | not scored | | | RuntimeError: LSIB v11.4 is lines only (POLYLINE shapefile, no coastline); no Lebanon polygon to test |

## Independent test: Natural Earth 1:10m — **FAIL**

| Year | Sensor | Country file | False incl. | False excl. | C1 | Worst month (C2) | C3 | Pass |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 2023 | modis | 68 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2023 | snpp | 590 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2023 | noaa20 | 559 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2024 | modis | 210 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2024 | snpp | 1,162 | 5 | 0 | 0.43% | 4.17% | 0.00% | yes |
| 2024 | noaa20 | 1,137 | 8 | 0 | 0.70% | 1.26% | 0.00% | yes |
| 2025 | modis | 87 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| 2025 | snpp | 514 | 5 | 0 | 0.97% | 9.62% | 0.00% | **no** |
| 2025 | noaa20 | 545 | 1 | 0 | 0.18% | 0.93% | 0.00% | yes |
