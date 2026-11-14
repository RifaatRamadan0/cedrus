# Confirmation plan: the sealed-region test of the frozen model

**Pre-registered 31 Oct 2026, before any data for the sealed regions was downloaded.** Run once. Results are published whatever they show.

## Frozen model
Candidate **A** (Poisson–gamma shrinkage ratio) from `docs/BAKEOFF_PLAN.md`, with a = 30. It is applied exactly as in `pipeline/bakeoff/models.py` at commit f0823f9, including the V = 0 quirk documented in BAKEOFF_RESULTS. Because A's parameters are local (per region and per cell), it is **refitted on each sealed region's own 2012–2019 data with the same code and a = 30**. Nothing is tuned.

## Sealed regions (one region = one FIRMS country file, clipped to its box)
| Region | FIRMS file | Box (lon_min, lat_min, lon_max, lat_max) |
|---|---|---|
| Morocco | Morocco | whole file |
| Tunisia | Tunisia | whole file |
| Central Chile | Chile | (−73.0, −38.5, −70.0, −32.0) |
| Western Cape | South_Africa | (17.5, −35.0, 24.0, −31.0) |

The same filters, grid, rows, day/night split and outage rule apply as in BAKEOFF_PLAN, with the outage rule evaluated over the sealed regions combined.

## Test 1: accuracy against near-nominal MODIS
- **Setup.** Fit on 2012–2019; score every month of 2020–2021. Aqua began free drift in January 2022, so 2020–2021 is the last near-nominal window.
- **Floors.** F0 = the raw Suomi NPP count. F1 = one ratio per region × day/night (ΣY/ΣV over 2012–2019).
- **Scores:**
  - weighted CRPS (A only);
  - cell-month WAPE of the predictive mean (A, F0, F1);
  - national-month WAPE;
  - 80% coverage on **active rows only** (Y > 0 or V > 0).
- **Pass if all hold,** pooled over the four regions:
  - (a) A's cell-month WAPE is lower than F1's and lower than F0's;
  - (b) active-row 80% coverage is within 0.70–0.90.

## Test 2: satellite swap (drift-proof)
- **Fit.** A is fitted separately for Suomi NPP (2012-02..2019-12) and for NOAA-20 (2018-04..2019-12), each against MODIS, same code, a = 30.
- **Compare.** For each region-month from 2020-01 to 2025-12, compare the two MODIS-equivalent totals (sums of predictive means), with 80% intervals from summing the NB variances.
- **Agreement.** A region-month agrees if the two 80% intervals overlap. Only months where both expected totals are ≥ 10 are counted.
- **Pass if** at least 80% of the counted region-months agree. This test never uses MODIS after 2019, so MODIS drift can't affect it.

## Report only (no pass/fail)
- **Seam check.** Harmonized ÷ observed MODIS annual totals for 2020 and 2021, with intervals.
- **Drift divergence.** Monthly observed MODIS ÷ A-predicted, 2022–2025, against the 2012–2019 band.

## Overall
**CONFIRMED** if Tests 1 and 2 both pass. Otherwise **NOT CONFIRMED**, with the failing parts named. Results go to `docs/CONFIRMATION_RESULTS.md`.
