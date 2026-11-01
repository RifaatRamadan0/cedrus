# Round 2 plan: choosing the harmonizer again, after the failed confirmation

**Pre-registered 1 Nov 2026.** Written after `docs/CONFIRMATION_RESULTS.md` (NOT CONFIRMED) and before any round-2 code exists. It was also written before any round-2 sealed data was downloaded. Changes after this commit only go in dated sections at the end. Results are published whatever they show.

## Why round 2
The frozen model A failed its confirmation on Morocco, Tunisia, central Chile and the Western Cape.
- **Accuracy:** a single ratio per region × day/night (floor F1) beat A on cell-month WAPE (60.1% vs 67.4%) and on national-month WAPE (16.3% vs 22.5%).
- **Totals:** A over-predicted totals by 14%.
- **Satellite swap:** Suomi NPP- and NOAA-20-based records agreed in only 69% of months (80% needed).

Those four regions are **spent**: they are never used again as a confirmation. They may be used as development data in this round, because their results are already known.

## Data and rules carried over
- FIRMS standard data.
- Filters: `type == 0`, MODIS confidence ≥ 30, VIIRS confidence n/h.
- Global 0.25° grid.
- Rows are cell × month × day/night.
- Target Y is Terra + Aqua MODIS.
- The outage rule is the bake-off's.

All of this follows `docs/BAKEOFF_PLAN.md` unless stated here.

## Development regions (selection uses only these)
- Portugal, Lebanon, Cyprus, Jordan, Israel, Palestine, Greece, Syria, Turkey.
- Morocco, Tunisia, central Chile and Western Cape (spent).

## New sealed regions (chosen by rule now; not downloaded until this plan is committed; not read until the model is frozen)
Rule: Mediterranean-climate fire regions, not in any earlier set, fetched as fixed boxes.

| Region | Source | Box (lon_min, lat_min, lon_max, lat_max) |
|---|---|---|
| Central Spain | FIRMS country file `Spain`, clipped | (−6.0, 38.5, −2.0, 41.0) |
| Southern Italy (Sicily and Calabria) | FIRMS country file `Italy`, clipped | (12.3, 36.6, 16.7, 39.0) |
| Southwest Australia | FIRMS area API box | (114.5, −35.5, 119.0, −30.5) |
| Southern California | FIRMS area API box | (−121.0, 32.5, −116.0, 35.5) |

## Candidates for converting Suomi NPP to MODIS-equivalent
All are fitted on 2012-02 … 2019-12.

- **R1: one ratio per region × day/night.**
  - r = ΣY/ΣV over rows with V > 0. Prediction for rows with V > 0: mean r·V.
  - Rows with V = 0 predict b, the mean Y over training rows with V = 0, per region × day/night.
  - Predictive distribution: negative binomial with α fitted by maximum likelihood per region × day/night on training rows.
  - Parameter uncertainty is added: Var = NB variance + V²·Var(r̂). Var(r̂) comes from a year-block bootstrap of r over the training years, using 200 resamples.
- **Rm: one ratio per region × calendar month × day/night.** Same as R1, with the ratio and b per calendar month.
- **A2: model A with its V = 0 quirk removed.**
  - The ratio sums use rows with V > 0 only.
  - The a grid is widened to {10, 30, 100, 300, 1000}, chosen by inner leave-one-year-out (LOYO).
  - Rows with V = 0 predict b as in Rm.
  - The predictive distribution is A's Poisson–gamma.

## NOAA-20 calibration candidates (for continuing the record after Suomi NPP)
- **J-M:** fit NOAA-20 directly against MODIS on 2018-04 … 2019-12, with the same method as the chosen Suomi NPP candidate. This is what round 1 did.
- **J-S:** fit NOAA-20 to Suomi NPP on 2018-04 … 2019-12. The VIIRS-to-VIIRS ratio is s per region × day/night, s = ΣV_SNPP / ΣV_N20. Then apply the chosen Suomi NPP model to s·V_N20. Uncertainty of s comes from a month-block bootstrap.

## Selection (development regions only)
1. **Suomi NPP candidates.**
   - Score each candidate by outer LOYO over 2012–2019, with everything fitted inside the folds, plus the forward check (fit 2012–2016, score 2017–2019).
   - Primary score: pooled weighted CRPS (weights from training activity, as in the bake-off).
   - **Choose the simplest candidate whose pooled weighted CRPS is within 2% of the best.** Simplicity order: R1 < Rm < A2.
   - Also report:
     - cell-month WAPE and national-month WAPE;
     - total bias;
     - 80% coverage on active rows (Y > 0 or V > 0);
     - results by region.
2. **NOAA-20 method.** With the chosen Suomi NPP model:
   - Compute the swap agreement on the development regions for 2020-01 … 2021-12. This uses no MODIS, and the window is outside both fits.
   - Agreement means the 80% intervals overlap, and only region-months with both totals ≥ 10 are counted.
   - Choose J-S if its agreement is greater than or equal to J-M's; otherwise choose J-M.
3. **Freeze.** Commit the chosen pair (code and settings) before reading any sealed-region file.

## Confirmation on the new sealed regions (run once)
The frozen pair is refitted on each sealed region's own 2012–2019 rows (NOAA-20: 2018-04 … 2019-12). Nothing is tuned.

- **Test 1 (accuracy, 2020–2021, against near-nominal MODIS).** Pass if all four hold:
  - (a) cell-month WAPE is at most F1's + 1.0 percentage point, and below F0's;
  - (b) 80% coverage on active rows is between 0.70 and 0.90;
  - (c) the pooled predicted total is within ±10% of observed MODIS;
  - (d) national-month WAPE is at most F1's + 1.0 point.

  F0 is raw Suomi NPP; F1 is R1's point forecast. If R1 is chosen, (a) and (d) hold by construction, and the report says so.
- **Test 2 (satellite swap, 2020-01 … 2025-12).** At least 80% of counted region-months agree, with intervals that include parameter uncertainty and the same counting rule as above.
- **CONFIRMED** if Tests 1 and 2 both pass.

## Report only
- Seam ratios for 2020–2021.
- Drift divergence for 2022–2025, where MODIS 2022–2025 was downloaded.
