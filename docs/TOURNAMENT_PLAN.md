# Tournament plan: searching for the best harmonizer without wearing out the exams

**Pre-registered 1 Nov 2026, before the round-2 confirmation result was seen** and before any tournament code exists. Changes go only in dated sections at the end.

## Principle
- **Unlimited candidates, development data only.** Testing many candidates on development data costs nothing.
- **Sealed regions are used once each, by one champion.** Re-sitting sealed exams with new versions until one passes would prove nothing.
- **Measure the headroom.** We estimate how close the champion is to the best any method could do, which tells us when to stop.

## Data
- **Development regions:**
  - Portugal, Lebanon, Cyprus, Jordan, Israel, Palestine, Greece, Syria, Turkey.
  - The spent round-1 regions (Morocco, Tunisia, central Chile, Western Cape).
  - **The round-2 sealed regions, once their confirmation has been run** (central Spain, southern Italy, SW Australia, southern California): they then become spent.
- **Years:**
  - All fitting and tuning uses 2012-02 … 2019-12.
  - Swap-stability scoring uses 2020-01 … 2021-12, with no MODIS involved.
- **Filters, rows, outages and target Y:** as in `docs/BAKEOFF_PLAN.md`.

## Candidates (Suomi NPP → MODIS-equivalent)
| Id | Idea |
|---|---|
| C0 | **A2**, the round-2 champion, frozen settings |
| C1 | R1, one ratio per region × day/night (baseline) |
| C2 | Rm, per region × calendar month × day/night (baseline) |
| C3 | **FRP-class ratios**: VIIRS detections split into fire-power classes (FRP < 5, 5–20, ≥ 20 MW, plus FRP ≤ 0), each class with its own A2-style shrunk ratio |
| C4 | **Pixel-size ratios**: VIIRS detections split by along-scan pixel size (scan < 0.5 km, 0.5–0.65 km, > 0.65 km), each with its own A2-style ratio |
| C5 | **Neighbour shrinkage**: A2, but each cell shrinks toward its 3×3 neighbourhood's ratio, which in turn shrinks toward the region's |
| C6 | **NB regression**: log μ = log(Σ_k β_k V_k + b), where V_k are the C3 and C4 class counts, plus month × day/night and region terms with empirical-Bayes shrinkage |
| C7 | **LightGBM Poisson**: features are the C3 and C4 class counts, day/night, month, region, and the cell's training-period MODIS/VIIRS history ratio (computed inside the folds). Intervals come from an NB whose dispersion is fitted on inner-fold residuals |
| C8 | **Quantile mapping**: pooled per region × day/night, zero-aware, monotone, with frozen tail rules |

**Second unit: burning days.**
- **Definition:** a 0.01° cell counts once per day if it has any detection. The cell-day counts are then summed per 0.25° cell × month × day/night.
- **Candidates:** the best two of C0–C8 are refitted in this unit (D-a, D-b), plus R1 in this unit (D-R1).

## Scores (outer leave-one-year-out plus the forward check, everything fitted inside folds)
- **Primary, within a unit:** pooled weighted CRPS (weights from training activity).
- **Across units:** CRPS skill against that unit's R1, SS = 1 − CRPS / CRPS(R1). Because burning days and pixels are different targets, units are compared by skill, never by raw CRPS.
- **Also reported:**
  - active-row 80% coverage, cell-month WAPE, national-month WAPE and total bias;
  - **swap stability**: median |log(NOAA-20-based total ÷ Suomi NPP-based total)| over development region-months, 2020–2021, where NOAA-20 goes through J-S as in round 2.
- **Headroom:**
  - For each row, a Poisson counting-noise floor: E_{y~Pois(μ)}[CRPS(Pois(μ), y)], with μ = the champion's predictive mean. It is reported pooled and weighted.
  - headroom = (champion CRPS − floor) ÷ champion CRPS.
  - This floor is optimistic (a lower bound): it ignores real extra-Poisson variability.

## Selection
1. **Pixel champion:** the simplest candidate within 2% of the best pooled weighted CRPS among C0–C8. Simplicity order: C1 < C2 < C0 < C5 < C3 < C4 < C8 < C6 < C7.
2. **Burning-days unit:** adopted as the calendar's **primary** unit only if all of these hold:
   - its best skill exceeds the pixel champion's skill by at least 10% in relative terms;
   - its swap stability is at least as good;
   - its active-row coverage lies in 0.70–0.90.
   Otherwise burning days may be offered as a **secondary view**. "Number of hotspots" stays primary, because that is what the challenge asks for.
3. **The champion is frozen,** code and settings committed, before round 3's sealed regions are downloaded.

## Round 3 sealed exam (one champion, once)
- **Regions, chosen now by rule** (Mediterranean-climate fire regions not used before, fixed boxes):

| Region | Source | Box (lon_min, lat_min, lon_max, lat_max) |
|---|---|---|
| Northern Algeria | FIRMS country file `Algeria`, clipped | (−1.0, 34.5, 8.5, 37.1) |
| Southern France (Provence and Languedoc) | FIRMS country file `France`, clipped | (3.0, 42.5, 7.7, 44.5) |
| South Australia | FIRMS area API box | (136.5, −36.5, 141.0, −33.0) |
| Northern California | FIRMS area API box | (−123.5, 37.5, −120.5, 40.5) |

- **Tests and pass rules:** identical to round 2's (Test 1 (a)–(d) and Test 2), with the same frozen-refit procedure.
- **Also reported:** the same median |log| swap metric and the coverage split by V > 0 and V = 0.

## Stopping rule
- **Stop searching** when the champion's headroom is below 15%, **or** on 9 Nov 2026, whichever comes first.
- **At most one more sealed exam (round 3) before the event.**
- **What ships:**
  - the round-3 champion if it passes;
  - otherwise the best champion that passed a sealed exam (round 2's A2, if it passed);
  - otherwise the round-3 champion, labelled honestly as not confirmed.

## Ruling added 1 Nov 2026, after the tournament ran and before any round-3 sealed data was downloaded

The tournament picked C5 as the pixel champion (1.0194 × best, against a 1.02 bar; C0 = A2 sits at 1.0217). Burning days passed all three adoption clauses with D-a (C3 refitted in burning days). The plan did not say who sits round 3 in that case. Ruling:
1. **Round 3's single sealed exam goes to D-a,** the burning-days champion, because burning days would become the calendar's primary unit. Same tests and pass rules as round 2, applied in the burning-days unit; the floors F0 and F1 are computed in the same unit.
2. **The hotspot-count view keeps A2, the round-2 confirmed model.** C5 is not exam-tested, because only one sealed exam is allowed. Its margin over A2 (0.3% CRPS) is within noise. This choice follows the plan's "what ships" fallback: the best champion that passed a sealed exam.
3. **If D-a fails round 3,** the calendar's primary unit stays hotspot counts on A2, and burning days is shown only as a secondary, unconfirmed view.
4. **An independent test runs first.** A fresh tester checks the tournament before D-a is frozen. If the tester finds the burning-days adoption unsafe (for example, skill not comparable across units), clause 2 of the selection is re-evaluated before freezing, and the reason is recorded here.
