# Bake-off plan: baseline A vs learned detection response B

**Pre-registered 31 Oct 2026, before any model below has been fitted.** The git history shows this file
was committed before `pipeline/bakeoff/` existed. Changes after that are made only as dated sections at the end.

## Question
Does the learned detection response (B) predict nominal-orbit MODIS counts from Suomi NPP VIIRS better
than a shrinkage ratio (A), by enough to justify its extra complexity?

## Data
- FIRMS standard country archives, years **2012–2019 only** (Suomi NPP from 2012-02).
- Filters: `type == 0`; MODIS `confidence >= 30`; VIIRS confidence `n`/`h`.
- **Development regions** (one region = one FIRMS country file): Portugal (mainland box lon −9.6..−6.1,
  lat 36.9..42.2), Lebanon, Cyprus, Jordan, Israel, Palestine, Greece, Syria, Turkey.
- **Sealed regions** (Morocco, Tunisia, central Chile, South Africa's Western Cape): not downloaded or read in this bake-off.
- **Grid:** global 0.25° cells (`ix = floor(lon/0.25)`, `iy = floor(lat/0.25)`).
- **Rows:** cell × month × day/night, for every cell in a region with at least one MODIS or VIIRS detection in 2012–2019.
- **Target Y:** Terra + Aqua MODIS detections in that row.
- **Outage rule:** a sensor-day with zero detections across all development regions combined, while the
  other sensor family has ≥ 50, is an outage. Rows are scored only on months with no outage day for either family.

## Candidate A: Poisson–gamma shrinkage ratio
- Prior ratio r0 = ΣY / ΣV per region × calendar month × day/night.
- Per cell × calendar month × day/night, over the training years:
  - posterior shape = a + ΣY;
  - posterior rate = a/r0 + ΣV.
- Prediction for a held-out row with VIIRS count V > 0: negative binomial with
  size = a + ΣY and p = rate / (rate + V).
- If V = 0: Poisson(b_A), where b_A = mean of Y over training rows with V = 0, per region × calendar month × day/night.
- `a` is chosen from {1, 3, 10, 30} by inner leave-one-year-out on the training years only.

## Candidate B: learned detection response + negative binomial
1. **Fire units.**
   - A pass = Suomi NPP detections with the same date and day/night, and `acq_time` within 30 min.
   - A unit = connected components of detections within 1.0 km of each other inside one pass.
   - Unit FRP = sum of its pixels' FRP. FRP ≤ 0 gets its own indicator.
2. **Matching.**
   - Candidate Aqua MODIS pixels: same date and day/night, |Δt| ≤ 60 min.
   - An Aqua pixel matches a unit if its distance to the unit's nearest pixel is ≤ ½·√(scan² + track²) + 0.5 km,
     using that Aqua pixel's own `scan` and `track`.
   - One-to-one: each Aqua pixel is assigned only to its nearest unit.
   - Matched count m_u = number of Aqua pixels assigned to unit u.
3. **Chance control.** Repeat step 2 with Aqua pixels from date − 1 and date + 1, keeping the time-of-day
   rule; c_u = average of the two counts.
4. **Response.**
   - Fit two Poisson GLMs per day/night, on training years: m_u and c_u each ~ log(FRP) + 1[FRP ≤ 0].
   - g(FRP) = max(ĝ_match − ĝ_chance, 0.001).
5. **Exposure.** Ê = Σ g(FRP_u) over the units in that row.
6. **Negative-binomial layer.**
   - Y ~ NB2(μ, α), with log μ = log(Ê + b) + β[calendar month × day/night] + β[region × day/night].
   - The month terms absorb the Terra/Aqua ratio and pixel multiplicity.
   - b is chosen from {0.01, 0.03, 0.1, 0.3} by inner leave-one-year-out.
   - Region effects are shrunk by empirical Bayes:
     - τ² = max(0, var(β̂) − mean(se²));
     - β* = β̂ · τ² / (τ² + se²);
     - μ is then recomputed with the shrunk effects.
   - Prediction: NB2(μ*, α).

**Coverage simplification (declared now):** the plan's CMR granule check of where Aqua actually looked is
**not** used in this bake-off. At these latitudes Aqua views every point at least daily. Any scalar effect of
unobserved days is absorbed by the negative-binomial month terms.

## Validation
- **Outer leave-one-year-out**: hold out each of 2012 … 2019 in turn; fit everything on the other years.
  "Everything" means r0, a, b_A, units' response g, b, β, α and the shrinkage.
- **Forward check**: fit 2012–2016, score 2017–2019.
- **Scores per held-out row:**
  - CRPS of the predictive distribution, computed exactly by summing over k = 0 … K, with K the 0.9999 quantile
    (or y + 50 if larger);
  - whether y is inside the central 80% interval (10th–90th percentiles);
  - absolute error of the predictive mean.
- **Primary score:** mean CRPS weighted by w = 1 + (that cell's mean Y over the training years of the fold).
  The weight uses training activity, not the held-out outcome.
- **Also reported:**
  - unweighted mean CRPS;
  - 80% coverage;
  - cell-month WAPE;
  - national-month WAPE per region;
  - all of the above per region and per year.

## Decision rule
- **B is chosen only if all three hold:**
  - (i) weighted CRPS of B ÷ weighted CRPS of A ≤ 0.95 on the leave-one-year-out pool;
  - (ii) the 90% paired block-bootstrap interval of that ratio has its upper end below 1.00. Use 2000
    resamples, with held-out years as blocks;
  - (iii) B's 80% coverage is between 0.75 and 0.85.
- **Otherwise A is chosen.**
- **Ties to simplicity:** if B passes (i)–(ii) but fails (iii), A is chosen, and the coverage miss is reported.
- **Published either way:** both models' full results go into `docs/BAKEOFF_RESULTS.md`, whatever wins.

## What happens after
The chosen model is frozen (code plus parameters, committed). It is then run once on the sealed regions,
training on 2012–2019 and scoring 2020–2021, together with the Suomi NPP ↔ NOAA-20 swap test, as defined in the strategy.
