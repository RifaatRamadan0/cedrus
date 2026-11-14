# Results — the MODIS retirement test

_Generated 2026-10-23T19:35:24+00:00 by `pipeline/03_harmonize.py`. Rules: [TEST_PLAN.md](TEST_PLAN.md)._

**Verdict: PASS** — M1 must beat both floors on the primary score.

Trained on 2012-02..2019-12 (23,158 MODIS, 62,152 Suomi NPP detections). Scored on 2020-01..2025-12 (12,713 MODIS detections to rebuild). k = 300 (chosen on training years).

| Model | Cell-month error (primary) | National monthly error | Season dates off by (days) |
|---|---|---|---|
| F0 joined record (floor) | 200.9% | 184.3% | 10.1 |
| F1 one ratio (floor) | 53.5% | 21.6% | 10.1 |
| M1 CEDRUS | 52.8% | 24.1% | 6.8 |

## Yearly national total, % error (predicted vs real MODIS)

| Model | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| F0 | +158.3 | +145.4 | +114.7 | +151.8 | +293.5 | +171.3 |
| F1 | -3.7 | -8.6 | -20.0 | -6.2 | +46.6 | +1.1 |
| M1 | -2.9 | -12.0 | -23.2 | -2.7 | +44.8 | +8.1 |

## Terra and Aqua drift — MODIS detections per Suomi NPP detection

| Year | Terra | Aqua |
|---|---|---|
| 2012 | 0.177 | 0.22 |
| 2013 | 0.182 | 0.215 |
| 2014 | 0.155 | 0.192 |
| 2015 | 0.19 | 0.202 |
| 2016 | 0.172 | 0.185 |
| 2017 | 0.194 | 0.163 |
| 2018 | 0.175 | 0.201 |
| 2019 | 0.166 | 0.195 |
| 2020 | 0.192 | 0.195 |
| 2021 | 0.196 | 0.211 |
| 2022 | 0.236 | 0.229 |
| 2023 | 0.184 | 0.213 |
| 2024 | 0.132 | 0.122 |
| 2025 | 0.186 | 0.183 |

## Satellite handover — same model fed NOAA-20 instead of Suomi NPP

Months with NOAA-20 in the archive: 2018-04..2025-12. NOAA-20 makes 1.031 detections per Suomi NPP detection.

- Cell-month error fed Suomi NPP: 51.4%
- Cell-month error fed NOAA-20: 49.6%

## Notes

- Season-date scores for F0 and F1 are identical by construction: multiplying a record by one number does not move the dates when 10/50/90 % of the year's fires are reached.
- Numbers are fire *detections* (satellite pixels flagged as burning), not burned area.
