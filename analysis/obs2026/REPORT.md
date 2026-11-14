# 2026 processing validation

Rules: [plan](../../docs/OBS2026_VALIDATION_PLAN.md). Clipping: **FAIL**. Mask: **FAIL**.

## Step 1: country clipping (2025)

| Region | Sensor | Country file | False incl. | False excl. | C1 | Worst month (C2) | Source diff. (C3) | Pass |
|---|---|---:|---:|---:|---:|---:|---:|---|
| portugal | modis | 4,637 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| portugal | snpp | 12,577 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| portugal | noaa20 | 12,721 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| lebanon | modis | 87 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| lebanon | snpp | 514 | 5 | 0 | 0.97% | 9.62% | 0.00% | **no** |
| lebanon | noaa20 | 545 | 1 | 0 | 0.18% | 0.93% | 0.00% | yes |
| syria | modis | 1,078 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| syria | snpp | 3,317 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| syria | noaa20 | 3,726 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| la_rioja | modis | 784 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| la_rioja | snpp | 3,326 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |
| la_rioja | noaa20 | 3,320 | 0 | 0 | 0.00% | 0.00% | 0.00% | yes |

## Step 2: static-source mask (Jan–Jul 2026, primary 3×3 rule)

| Region | Sensor | Type 1–3 | Type 0 | Removed static (M1) | Removed type 0 (M2) | Worst month (M3) | Pass | 1×1 recall / false removal |
|---|---|---:|---:|---:|---:|---:|---|---|
| portugal | modis | 9 | 1,181 | 33.33% | 1.78% | 23.81% | **no** | 0.00% / 0.51% |
| portugal | snpp | 97 | 3,474 | 100.00% | 2.42% | 27.37% | **no** | 100.00% / 1.04% |
| portugal | noaa20 | 115 | 3,272 | 98.26% | 3.00% | 28.43% | **no** | 98.26% / 1.34% |
| lebanon | modis | 1 | 21 | 100.00% | 4.76% | 0.00% | **no** | 0.00% / 0.00% |
| lebanon | snpp | 5 | 223 | 80.00% | 13.45% | 17.91% | **no** | 60.00% / 8.07% |
| lebanon | noaa20 | 0 | 203 | 100.00% | 20.69% | 20.75% | **no** | 100.00% / 13.79% |
| syria | modis | 49 | 738 | 59.18% | 16.12% | 17.39% | **no** | 30.61% / 3.66% |
| syria | snpp | 2,102 | 2,299 | 100.00% | 30.84% | 84.21% | **no** | 99.33% / 18.18% |
| syria | noaa20 | 2,441 | 2,404 | 99.96% | 28.08% | 76.92% | **no** | 99.30% / 16.51% |
| la_rioja | modis | 49 | 172 | 97.96% | 7.56% | 7.41% | **no** | 81.63% / 2.91% |
| la_rioja | snpp | 34 | 1,015 | 85.29% | 6.90% | 10.26% | **no** | 85.29% / 3.05% |
| la_rioja | noaa20 | 35 | 1,156 | 100.00% | 7.70% | 14.93% | **no** | 100.00% / 3.29% |
