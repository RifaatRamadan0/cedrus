# Tournament results: the best harmonizer on development data

_Generated 2026-11-01T15:11:43+00:00 by `python -m pipeline.tournament.run`. Rules: [TOURNAMENT_PLAN.md](TOURNAMENT_PLAN.md), pre-registered at commit fa2c956 before any tournament code. Do not edit by hand._

```bash
python -m pipeline.tournament.run
python -m pipeline.tournament.test_tournament
```

- Run started 2026-11-01T15:10:59+00:00 (UTC) at commit `cc30c6e280ffbb91dd077d0623e59823f0bbc4a0` with uncommitted files under pipeline/tournament/ (this code is not committed yet).
- Development regions (17): portugal, lebanon, cyprus, jordan, israel, palestine, greece, syria, turkey, morocco, tunisia, central_chile, western_cape, central_spain, southern_italy, sw_australia, s_california. No sealed region was opened: every file access goes through `pipeline.round2.data.guard`, which refuses role "sealed".
- Fitting and tuning on 2012-02 … 2019-12 (812,630 rows, 804,076 in scored months). Swap stability on 2020-01 … 2021-12 (171,312 rows), no MODIS.
- Missing files: turkey: viirs-jpss1_2020_Turkey.csv.

## Deviations / interpretations

Points the plan left open, settled by the most literal reading while the code was written. They were fixed before the full run.

1. **Rows** are round 2's (`pipeline.round2.data.rows`): cell × month × day/night from 2012-02, for every 0.25° cell with a MODIS, Suomi NPP or NOAA-20 detection in 2012-02 … 2019-12, in the 17 regions with role "dev" in pipeline/regions.py, each clipped to its box. Only files for 2012–2021 are read. Round 2's pixel cache keeps no FRP or scan, so the same files are read again through round 2's guard and the bake-off's filters; the pixel counts Y, V and V20 are round 2's own function's output.
2. **Outage rule**: the bake-off's own code over the 17 regions combined. Months with an outage day are left out of every score, inner tuning included; fitting uses all months. The swap window uses round 2's swap rule (Suomi NPP at 0 while NOAA-20 ≥ 50, or the reverse). **Turkey 2020 is not in the swap**: its NOAA-20 file (viirs-jpss1_2020_Turkey.csv) is missing, so that region-year is left out of the swap rows and of the swap outage count.
3. **Primary score**: weighted CRPS with w = 1 + the cell's mean Y over the fold's training rows (in the unit being scored). "Pooled" is the leave-one-year-out pool (2012 … 2019 held out in turn), as in round 2. The forward check is reported and does not enter any rule. "Within 2%" is weighted CRPS ≤ 1.02 × the best.
4. **C0** is round 2's A2 code with a = 30 fixed (the frozen setting), not re-tuned. **C1 / C2** are round 2's R1 / Rm code unchanged (shared α, the year-block parameter term). All three are fitted on one table of the 17 regions, as round 2 fitted its 13.
5. **C3 / C4 classes**: C3 has four FRP classes, FRP ≤ 0, 0 < FRP < 5, 5 ≤ FRP < 20 and FRP ≥ 20 MW. C4 has the plan's three scan classes, scan < 0.5, 0.5 ≤ scan ≤ 0.65 and scan > 0.65 km (the 0.5 and 0.65 values, which occur because scan is given to 2 decimals, fall in the middle class). The FRP ≤ 0 class is C3's only; in C4 such a detection stays in its scan class.
6. **C3 / C4 ratios**: MODIS is not split by class, so "each class with its own A2-style ratio" needs the class share of Y. It is allocated in proportion to V_k × the class's current posterior mean and iterated to a fixed point: one step of the map changes the class means by less than 10⁻⁷ of the largest, at most 3,000 map evaluations. The plain iteration needed 1,300–2,250 steps on one development fold (60–130 s per fit), so it is accelerated by SQUAREM (Varadhan and Roland 2008, scheme S3), which reaches the same fixed point under the same stopping rule. With one class this is A2 exactly. Per class: prior r0_k = ΣY_k/ΣV_k per region × calendar month × day/night (fallback region × day/night, then all regions × day/night), posterior shape a + ΣY_k and rate a/r0_k + ΣV_k per cell × calendar month × day/night, sums over training rows with V > 0. A row's forecast is the sum over its classes of NB(shape_k, rate_k/(rate_k + V_k)), moment-matched to one negative binomial. V = 0 rows: Poisson(b_A) as A2. a is chosen from {10, 30, 100, 300, 1000} by inner leave-one-year-out, ties to the smaller a. The allocated class sums are treated as observed in the posterior (a plug-in, not a full posterior over the allocation).
7. **C5**: the 3 × 3 neighbourhood includes the cell itself and only cells of the same region that have rows. Neighbourhood ratio r_nb = (a_n + ΣY_nb)/(a_n/r0 + ΣV_nb) per cell × calendar month × day/night with A2's r0; cell posterior shape a + ΣY, rate a/r_nb + ΣV. Both strengths come from A2's grid, the 25 pairs chosen by inner leave-one-year-out (ties to the smaller a, then the smaller a_n). As a_n grows, C5 becomes A2.
8. **C6**: log μ = log(Σ_k β_k V_k + b) + γ[calendar month × day/night] + δ[region], with all seven class counts (four FRP, three scan). Both class sets add up to V, so the β have one flat direction; μ does not. β ≥ 0 (β = e^θ). b is fixed at 1: with γ free, a free b would only rescale (β, b) against γ. "Region terms" are one per region (not region × day/night). Region effects are centred (their mean moved into γ) and shrunk as the bake-off's B: τ² = max(0, var(δ̂) − mean(se²)), δ* = δ̂ · τ²/(τ² + se²), with se from the expected information. α is not refitted after shrinking. Forecast NB2(μ*, α). Fitted by maximum likelihood (L-BFGS-B, analytic gradient) on all training rows; nothing tuned.
9. **C7**: backend **lightgbm**. LightGBM was not importable at first; it was installed with pip (4.7.0) into the interpreter on PATH, so no substitution was needed. Features: the seven class counts, day/night, calendar month (numeric), region (categorical) and the cell's history ratio ΣY/ΣV over the fold's training rows with V > 0 (missing where the cell has none). The ratio is computed on the training years and used for training and scored rows alike, so a training row's own Y is inside its feature (the literal reading). Settings are fixed, not tuned: Poisson objective, 300 trees, learning rate 0.05, 31 leaves, at least 100 rows per leaf, deterministic, one thread. α per region × day/night by maximum likelihood on the residuals of inner leave-one-year-out fits (each training year predicted by trees fitted on the other training years, scored months only); a region × day/night with no informative row takes all regions' α for that day/night.
10. **C8**: per region × day/night, pooled over cells and months of the training rows. Each distinct Suomi NPP count v maps to the mean MODIS count over the same quantile band (rows sorted by V; Y sorted on its own), so the map is monotone and keeps the training total. Zero-aware: V = 0 maps to the mean of the lowest P(V = 0) share of Y, which is 0 whenever MODIS has at least as many zero rows. Frozen rules between and beyond the training values: linear between neighbouring values (from (0, 0) if 0 was never seen); above the largest, proportional, m(v) = m(v_max)·v/v_max. Forecast: negative binomial with that mean and α per region × day/night by maximum likelihood on the training rows (as R1); rows with mean 0 are all mass at 0.
11. **Burning days**: a 0.01° cell (floor(lon/0.01), floor(lat/0.01)) counts once per date and day/night if it has any detection of the family; MODIS is Terra and Aqua together. The cell-day counts are summed per 0.25° cell × month × day/night on the same rows. For class counts a burning day takes the FRP and scan classes of its largest-FRP detection, so its classes still add up to its total. Weights use the training-mean burning days. s for J-S is refitted in this unit. **D-a and D-b are the two lowest pooled weighted CRPS among C0–C8** (not the selection rule's choice); each is refitted from scratch in this unit, its tuning redone there.
12. **Coverage** is y in [q10, q90] on active rows (Y > 0 or V > 0). For information it is split into active rows with V > 0 and active rows with V = 0 (MODIS-only rows).
13. **Swap stability**: each candidate is fitted on all 2012-02 … 2019-12 rows (tuned candidates by inner leave-one-year-out over 2012–2019; C0 keeps a = 30). s = ΣV_SNPP/ΣV_N20 per region × day/night over 2018-04 … 2019-12 (round 2's fit_s). The candidate is applied to Suomi NPP and to s × NOAA-20, every class count multiplied by the same s. Each region-month total is the sum of the rows' predictive means. The median |log(NOAA-20-based ÷ Suomi NPP-based)| is taken over the region-months where both totals are > 0. The same median over region-months where both are ≥ 10 (round 2's counting rule) is shown for information.
14. **Headroom floor**: per row, Σ_k F(k)(1 − F(k)) with F the Poisson CDF at the champion's predictive mean. This is the expected CRPS when y really is Poisson with that mean, using the same summed CRPS as the scores. It is weighted and pooled like the primary score, over the leave-one-year-out pool. **It is an optimistic lower bound**: it ignores real extra-Poisson variability, and its mean is the champion's own, not the truth.
15. **Burning-days rule**: (i) "exceeds by at least 10% in relative terms" is SS_bd ≥ 1.10 × SS_pixel, with SS = 1 − weighted CRPS ÷ that unit's R1 weighted CRPS on the leave-one-year-out pool; (ii) "at least as good" is median |log| ≤ the pixel champion's; (iii) active-row coverage in [0.70, 0.90], inclusive. The burning-days candidate tested is the one of D-a / D-b with the higher skill.
16. **Seeds**: every bootstrap (R1/Rm year blocks, s month blocks) draws from numpy's default_rng seeded with 20261101 plus a CRC32 of its label (unit, fold, candidate).

## Decision

### 1. Pixel champion

Pooled leave-one-year-out weighted CRPS. Best: C3 (0.2580); bar = 1.02 × best = 0.2632. Rule: the simplest candidate within 2% of the best, in the order C1 < C2 < C0 < C5 < C3 < C4 < C8 < C6 < C7.

| Order | Candidate | Pooled weighted CRPS | ÷ best | Within 2% of best? |
|---|---|---|---|---|
| 1 | C1 R1 one ratio per region × day/night | 0.3437 | 1.3318 | no |
| 2 | C2 Rm one ratio per region × calendar month × day/night | 0.3181 | 1.2327 | no |
| 3 | C0 A2, frozen round-2 settings (a = 30) | 0.2637 | 1.0217 | no |
| 4 | C5 A2 with 3×3 neighbour shrinkage | 0.2630 | 1.0194 | **yes** |
| 5 | C3 FRP-class A2 ratios | 0.2580 | 1.0000 | **yes** |
| 6 | C4 pixel-size (scan) class A2 ratios | 0.2664 | 1.0324 | no |
| 7 | C8 zero-aware monotone quantile mapping | 0.2988 | 1.1581 | no |
| 8 | C6 NB regression on class counts, EB-shrunk region terms | 0.3482 | 1.3494 | no |
| 9 | C7 gradient-boosted Poisson trees | 0.3176 | 1.2310 | no |

The first candidate in the order that is within 2% is **C5** (A2 with 3×3 neighbour shrinkage).

### 2. Burning days as the primary unit?

Best two pixel candidates (lowest pooled weighted CRPS): C3 → D-a, C5 → D-b; R1 → D-R1. The burning-days candidate tested is **D-a** (the higher skill).

| Clause | Needed | Got | |
|---|---|---|---|
| (i) skill at least 10% above the pixel champion's | ≥ +25.8% (pixel champion +23.5%) | +30.6% | **yes** |
| (ii) swap stability at least as good (median abs log) | ≤ 0.1186 | 0.1084 | **yes** |
| (iii) active-row coverage in 0.70 … 0.90 | 0.70 … 0.90 | 0.834 | **yes** |

→ Primary unit: **burning days**. **Open, not decided by this run:** the plan does not say which model sits round 3 when burning days become primary: the pixel champion of rule 1 (C5, in hotspots) or the burning-days model whose skill passed rule 2 (D-a). Both are recorded in champion.json.

### 3. Headroom and the stopping rule

Champion C5: pooled weighted CRPS 0.2630; Poisson counting-noise floor 0.1490 (an optimistic lower bound). **Headroom = (0.2630 − 0.1490) ÷ 0.2630 = 43.4%.** Stop rule: stop searching when headroom < 15% or on 9 Nov 2026. Headroom is not below 15%: by this rule the search **may continue** until 9 Nov 2026.

### 4. Freeze

The champion's settings are in `data/processed/tournament/champion.json`. The plan requires the champion to be frozen (code and settings committed) before round 3's sealed regions are downloaded; this run does not commit anything.

## Spot check: C0 against round 2

C0 restricted to round 2's 13 development regions: pooled leave-one-year-out weighted CRPS **0.2492** on 680,184 rows; round 2's A2: 0.2492 on 680,184 rows. Reproduced to four decimals.

## Leaderboard: pixel unit (hotspots), pooled leave-one-year-out 2012 … 2019

804,076 scored rows (129,170 active: 119,319 with V > 0, 9,851 MODIS-only), 276,023 MODIS detections. Skill = 1 − weighted CRPS ÷ C1's. Sorted by the primary score.

| Candidate | Pooled weighted CRPS | ÷ best | Skill vs C1 (R1) | CRPS | Coverage, active rows | Coverage, active V > 0 | Coverage, active V = 0 | Cell-month WAPE | National-month WAPE | Total bias | Swap median abs log (both > 0) | Swap median abs log (both ≥ 10) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C3 FRP-class A2 ratios | 0.2580 | 1.0000 | +24.9% | 0.1449 | 82.4% | 88.6% | 7.7% | 57.5% | 13.5% | +2.9% | 0.1367 | 0.1112 |
| C5 A2 with 3×3 neighbour shrinkage | 0.2630 | 1.0194 | +23.5% | 0.1485 | 82.0% | 88.2% | 7.7% | 58.6% | 14.7% | +1.5% | 0.1186 | 0.0971 |
| C0 A2, frozen round-2 settings (a = 30) | 0.2637 | 1.0217 | +23.3% | 0.1485 | 82.3% | 88.4% | 7.7% | 58.8% | 14.8% | +1.3% | 0.1191 | 0.0955 |
| C4 pixel-size (scan) class A2 ratios | 0.2664 | 1.0324 | +22.5% | 0.1499 | 82.0% | 88.2% | 7.7% | 59.1% | 14.9% | +0.9% | 0.1281 | 0.0963 |
| C8 zero-aware monotone quantile mapping | 0.2988 | 1.1581 | +13.0% | 0.1562 | 83.5% | 90.4% | 0.0% | 55.6% | 19.4% | +0.4% | 0.2128 | 0.1507 |
| C7 gradient-boosted Poisson trees | 0.3176 | 1.2310 | +7.6% | 0.1638 | 87.2% | 93.8% | 7.2% | 61.1% | 16.2% | -0.4% | 0.1205 | 0.1042 |
| C2 Rm one ratio per region × calendar month × day/night | 0.3181 | 1.2327 | +7.4% | 0.1608 | 87.6% | 94.4% | 5.4% | 59.9% | 14.8% | -0.7% | 0.1136 | 0.0975 |
| C1 R1 one ratio per region × day/night | 0.3437 | 1.3318 | +0.0% | 0.1673 | 87.6% | 94.6% | 3.1% | 62.8% | 21.9% | -0.3% | 0.1184 | 0.0974 |
| C6 NB regression on class counts, EB-shrunk region terms | 0.3482 | 1.3494 | -1.3% | 0.1729 | 87.2% | 94.4% | 0.0% | 65.1% | 23.9% | +4.3% | 0.1262 | 0.1073 |

### Forward check (fit 2012–2016, score 2017–2019), for information

307,944 scored rows (49,873 active).

| Candidate | Pooled weighted CRPS | ÷ best | Skill vs C1 (R1) | CRPS | Coverage, active rows | Coverage, active V > 0 | Coverage, active V = 0 | Cell-month WAPE | National-month WAPE | Total bias | Swap median abs log (both > 0) | Swap median abs log (both ≥ 10) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C3 FRP-class A2 ratios | 0.2729 | 1.0000 | +20.2% | 0.1559 | 82.3% | 88.6% | 5.7% | 56.8% | 15.3% | +5.3% | 0.1367 | 0.1112 |
| C0 A2, frozen round-2 settings (a = 30) | 0.2743 | 1.0052 | +19.8% | 0.1594 | 82.0% | 88.3% | 5.7% | 57.2% | 15.7% | +0.6% | 0.1191 | 0.0955 |
| C5 A2 with 3×3 neighbour shrinkage | 0.2749 | 1.0075 | +19.6% | 0.1597 | 81.7% | 88.0% | 5.7% | 56.8% | 15.6% | +0.9% | 0.1186 | 0.0971 |
| C4 pixel-size (scan) class A2 ratios | 0.2772 | 1.0160 | +18.9% | 0.1613 | 81.6% | 87.9% | 5.7% | 57.5% | 15.9% | -0.1% | 0.1281 | 0.0963 |
| C8 zero-aware monotone quantile mapping | 0.3012 | 1.1038 | +11.9% | 0.1617 | 83.9% | 90.8% | 0.0% | 53.5% | 18.5% | +0.4% | 0.2128 | 0.1507 |
| C2 Rm one ratio per region × calendar month × day/night | 0.3196 | 1.1715 | +6.5% | 0.1681 | 87.7% | 94.5% | 5.1% | 57.5% | 15.5% | -0.8% | 0.1136 | 0.0975 |
| C7 gradient-boosted Poisson trees | 0.3243 | 1.1887 | +5.1% | 0.1770 | 86.8% | 93.4% | 6.4% | 59.4% | 16.1% | -0.7% | 0.1205 | 0.1042 |
| C1 R1 one ratio per region × day/night | 0.3418 | 1.2527 | +0.0% | 0.1735 | 87.8% | 94.8% | 2.9% | 60.4% | 21.5% | +0.7% | 0.1184 | 0.0974 |
| C6 NB regression on class counts, EB-shrunk region terms | 0.3584 | 1.3135 | -4.9% | 0.1856 | 87.2% | 94.4% | 0.0% | 63.9% | 24.5% | +6.2% | 0.1262 | 0.1073 |

## Leaderboard: burning-day unit, pooled leave-one-year-out 2012 … 2019

804,076 scored rows (129,170 active), 258,638 MODIS burning days. Skill = 1 − weighted CRPS ÷ D-R1's. Raw CRPS is not comparable across units; skill is.

| Candidate | Pooled weighted CRPS | ÷ best | Skill vs D-R1 | CRPS | Coverage, active rows | Coverage, active V > 0 | Coverage, active V = 0 | Cell-month WAPE | National-month WAPE | Total bias | Swap median abs log (both > 0) | Swap median abs log (both ≥ 10) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D-a (C3 FRP-class A2 ratios) | 0.2275 | 1.0000 | +30.6% | 0.1309 | 83.4% | 89.7% | 7.7% | 57.0% | 13.3% | +1.6% | 0.1084 | 0.0848 |
| D-b (C5 A2 with 3×3 neighbour shrinkage) | 0.2436 | 1.0708 | +25.7% | 0.1414 | 82.5% | 88.7% | 7.7% | 61.3% | 17.1% | -0.2% | 0.1006 | 0.0806 |
| D-R1 (C1 R1 one ratio per region × day/night) | 0.3278 | 1.4409 | +0.0% | 0.1625 | 88.1% | 95.3% | 1.2% | 67.8% | 25.9% | -0.6% | 0.1071 | 0.0849 |

### Forward check, burning days

| Candidate | Pooled weighted CRPS | ÷ best | Skill vs D-R1 | CRPS | Coverage, active rows | Coverage, active V > 0 | Coverage, active V = 0 | Cell-month WAPE | National-month WAPE | Total bias | Swap median abs log (both > 0) | Swap median abs log (both ≥ 10) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D-a (C3 FRP-class A2 ratios) | 0.2400 | 1.0000 | +26.0% | 0.1386 | 83.0% | 89.5% | 5.5% | 55.8% | 15.0% | +2.5% | 0.1084 | 0.0848 |
| D-b (C5 A2 with 3×3 neighbour shrinkage) | 0.2553 | 1.0634 | +21.3% | 0.1513 | 82.1% | 88.4% | 5.5% | 60.5% | 19.7% | -2.9% | 0.1006 | 0.0806 |
| D-R1 (C1 R1 one ratio per region × day/night) | 0.3244 | 1.3515 | +0.0% | 0.1681 | 88.5% | 95.5% | 3.0% | 66.1% | 27.3% | -2.4% | 0.1071 | 0.0849 |

## Headroom of every candidate (information)

| Unit | Candidate | Pooled weighted CRPS | Poisson floor | Headroom | Floor on V > 0 rows only |
|---|---|---|---|---|---|
| pixels | C0 A2, frozen round-2 settings (a = 30) | 0.2637 | 0.1487 | 43.6% | 0.6547 |
| pixels | C1 R1 one ratio per region × day/night | 0.3437 | 0.1510 | 56.1% | 0.6644 |
| pixels | C2 Rm one ratio per region × calendar month × day/night | 0.3181 | 0.1467 | 53.9% | 0.6446 |
| pixels | C3 FRP-class A2 ratios | 0.2580 | 0.1446 | 44.0% | 0.6343 |
| pixels | C4 pixel-size (scan) class A2 ratios | 0.2664 | 0.1480 | 44.4% | 0.6513 |
| pixels | C5 A2 with 3×3 neighbour shrinkage | 0.2630 | 0.1490 | 43.4% | 0.6563 |
| pixels | C6 NB regression on class counts, EB-shrunk region terms | 0.3482 | 0.1471 | 57.8% | 0.6457 |
| pixels | C7 gradient-boosted Poisson trees | 0.3176 | 0.1484 | 53.3% | 0.6423 |
| pixels | C8 zero-aware monotone quantile mapping | 0.2988 | 0.1193 | 60.1% | 0.5987 |
| burning days | D-a (C3 FRP-class A2 ratios) | 0.2275 | 0.1407 | 38.1% | 0.6234 |
| burning days | D-b (C5 A2 with 3×3 neighbour shrinkage) | 0.2436 | 0.1471 | 39.6% | 0.6554 |
| burning days | D-R1 (C1 R1 one ratio per region × day/night) | 0.3278 | 0.1518 | 53.7% | 0.6777 |

## Pixel unit by region (leave-one-year-out pool): weighted CRPS

| Region | Rows | Active | Y | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| portugal | 34,404 | 6,836 | 22,305 | 0.342 | 0.397 | 0.380 | 0.348 | 0.337 | 0.344 | 0.420 | 0.412 | 0.357 |
| lebanon | 5,264 | 1,258 | 512 | 0.075 | 0.077 | 0.074 | 0.075 | 0.076 | 0.075 | 0.077 | 0.077 | 0.084 |
| cyprus | 3,948 | 589 | 349 | 0.066 | 0.068 | 0.067 | 0.068 | 0.074 | 0.066 | 0.065 | 0.069 | 0.071 |
| jordan | 13,348 | 1,205 | 309 | 0.026 | 0.027 | 0.026 | 0.025 | 0.025 | 0.026 | 0.028 | 0.025 | 0.028 |
| israel | 9,400 | 1,900 | 949 | 0.087 | 0.087 | 0.088 | 0.089 | 0.089 | 0.088 | 0.087 | 0.086 | 0.094 |
| palestine | 4,512 | 976 | 313 | 0.060 | 0.060 | 0.060 | 0.062 | 0.063 | 0.060 | 0.060 | 0.059 | 0.064 |
| greece | 72,944 | 7,781 | 10,822 | 0.102 | 0.116 | 0.112 | 0.100 | 0.103 | 0.102 | 0.118 | 0.122 | 0.111 |
| syria | 53,016 | 8,996 | 15,150 | 0.212 | 0.218 | 0.218 | 0.202 | 0.214 | 0.213 | 0.214 | 0.227 | 0.218 |
| turkey | 266,208 | 41,519 | 77,489 | 0.307 | 0.507 | 0.446 | 0.301 | 0.312 | 0.306 | 0.462 | 0.421 | 0.401 |
| morocco | 84,976 | 5,807 | 2,145 | 0.021 | 0.023 | 0.022 | 0.020 | 0.021 | 0.021 | 0.022 | 0.023 | 0.023 |
| tunisia | 37,224 | 3,660 | 2,662 | 0.049 | 0.055 | 0.050 | 0.046 | 0.049 | 0.049 | 0.054 | 0.050 | 0.053 |
| central_chile | 39,104 | 12,203 | 38,657 | 0.511 | 0.621 | 0.594 | 0.497 | 0.518 | 0.508 | 0.699 | 0.594 | 0.547 |
| western_cape | 55,836 | 9,031 | 29,539 | 0.302 | 0.325 | 0.318 | 0.299 | 0.304 | 0.305 | 0.380 | 0.341 | 0.311 |
| central_spain | 29,704 | 3,555 | 3,111 | 0.083 | 0.086 | 0.086 | 0.079 | 0.084 | 0.084 | 0.082 | 0.089 | 0.085 |
| southern_italy | 15,980 | 5,438 | 11,042 | 0.330 | 0.344 | 0.339 | 0.329 | 0.332 | 0.332 | 0.388 | 0.338 | 0.348 |
| sw_australia | 50,572 | 14,991 | 51,863 | 0.465 | 0.472 | 0.449 | 0.453 | 0.463 | 0.459 | 0.551 | 0.469 | 0.463 |
| s_california | 27,636 | 3,425 | 8,806 | 0.160 | 0.188 | 0.183 | 0.147 | 0.174 | 0.164 | 0.169 | 0.206 | 0.142 |

## Pixel unit by region: active-row coverage

| Region | Rows | Active | Y | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| portugal | 34,404 | 6,836 | 22,305 | 77.1% | 85.2% | 84.0% | 77.1% | 77.2% | 76.9% | 84.6% | 84.4% | 79.8% |
| lebanon | 5,264 | 1,258 | 512 | 90.9% | 92.6% | 92.8% | 91.1% | 91.2% | 91.4% | 91.8% | 92.6% | 89.7% |
| cyprus | 3,948 | 589 | 349 | 84.2% | 85.4% | 85.6% | 82.5% | 83.2% | 84.0% | 85.6% | 85.2% | 84.4% |
| jordan | 13,348 | 1,205 | 309 | 89.4% | 87.5% | 88.6% | 89.0% | 89.0% | 89.4% | 89.5% | 89.0% | 88.4% |
| israel | 9,400 | 1,900 | 949 | 87.1% | 88.4% | 88.2% | 86.5% | 86.5% | 86.9% | 88.7% | 88.7% | 86.1% |
| palestine | 4,512 | 976 | 313 | 91.5% | 92.8% | 91.7% | 90.5% | 90.4% | 91.5% | 91.9% | 90.9% | 90.2% |
| greece | 72,944 | 7,781 | 10,822 | 82.0% | 86.2% | 85.6% | 82.1% | 81.9% | 81.9% | 84.6% | 84.9% | 82.5% |
| syria | 53,016 | 8,996 | 15,150 | 81.9% | 89.3% | 89.1% | 82.6% | 81.4% | 81.5% | 88.2% | 87.7% | 83.6% |
| turkey | 266,208 | 41,519 | 77,489 | 82.0% | 86.4% | 87.0% | 82.1% | 81.9% | 81.9% | 85.8% | 86.3% | 82.3% |
| morocco | 84,976 | 5,807 | 2,145 | 89.1% | 89.2% | 89.4% | 88.6% | 88.7% | 89.1% | 87.7% | 87.9% | 88.4% |
| tunisia | 37,224 | 3,660 | 2,662 | 88.9% | 90.7% | 91.3% | 88.9% | 88.6% | 88.9% | 89.3% | 91.1% | 88.6% |
| central_chile | 39,104 | 12,203 | 38,657 | 83.1% | 91.4% | 89.6% | 83.4% | 82.8% | 82.7% | 88.8% | 89.6% | 83.9% |
| western_cape | 55,836 | 9,031 | 29,539 | 77.4% | 85.1% | 85.1% | 77.7% | 77.1% | 76.5% | 84.9% | 85.8% | 80.5% |
| central_spain | 29,704 | 3,555 | 3,111 | 75.8% | 78.1% | 78.0% | 75.8% | 75.5% | 75.6% | 78.8% | 76.6% | 78.8% |
| southern_italy | 15,980 | 5,438 | 11,042 | 84.2% | 89.2% | 89.0% | 84.4% | 84.2% | 84.3% | 90.7% | 89.2% | 84.2% |
| sw_australia | 50,572 | 14,991 | 51,863 | 81.5% | 89.6% | 89.9% | 82.0% | 81.4% | 81.2% | 91.8% | 90.1% | 85.8% |
| s_california | 27,636 | 3,425 | 8,806 | 83.6% | 89.0% | 88.9% | 83.4% | 83.5% | 83.2% | 87.0% | 88.2% | 86.7% |

## Pixel unit by held-out year: weighted CRPS

| Year | Rows | Active | Y | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2012 | 85,540 | 13,233 | 24,397 | 0.229 | 0.288 | 0.265 | 0.225 | 0.241 | 0.231 | 0.287 | 0.269 | 0.259 |
| 2013 | 102,648 | 16,682 | 31,429 | 0.247 | 0.341 | 0.312 | 0.246 | 0.247 | 0.245 | 0.331 | 0.309 | 0.289 |
| 2014 | 102,648 | 14,366 | 23,582 | 0.205 | 0.264 | 0.242 | 0.197 | 0.208 | 0.204 | 0.268 | 0.237 | 0.238 |
| 2015 | 102,648 | 17,551 | 44,476 | 0.319 | 0.455 | 0.415 | 0.312 | 0.319 | 0.318 | 0.452 | 0.412 | 0.378 |
| 2016 | 102,648 | 17,465 | 38,608 | 0.295 | 0.390 | 0.360 | 0.288 | 0.297 | 0.295 | 0.387 | 0.364 | 0.335 |
| 2017 | 102,648 | 17,688 | 54,165 | 0.349 | 0.452 | 0.421 | 0.339 | 0.353 | 0.349 | 0.485 | 0.422 | 0.387 |
| 2018 | 102,648 | 14,929 | 26,464 | 0.206 | 0.260 | 0.244 | 0.202 | 0.210 | 0.205 | 0.273 | 0.240 | 0.229 |
| 2019 | 102,648 | 17,256 | 32,902 | 0.257 | 0.296 | 0.282 | 0.254 | 0.256 | 0.257 | 0.298 | 0.285 | 0.274 |

## Burning-day unit by region: weighted CRPS

| Region | Rows | Active | Y | C3 | C5 | C1 |
|---|---|---|---|---|---|---|
| portugal | 34,404 | 6,836 | 20,354 | 0.287 | 0.313 | 0.392 |
| lebanon | 5,264 | 1,258 | 499 | 0.072 | 0.075 | 0.076 |
| cyprus | 3,948 | 589 | 330 | 0.063 | 0.064 | 0.066 |
| jordan | 13,348 | 1,205 | 306 | 0.025 | 0.025 | 0.027 |
| israel | 9,400 | 1,900 | 922 | 0.083 | 0.085 | 0.085 |
| palestine | 4,512 | 976 | 310 | 0.063 | 0.062 | 0.060 |
| greece | 72,944 | 7,781 | 10,314 | 0.094 | 0.100 | 0.115 |
| syria | 53,016 | 8,996 | 14,349 | 0.184 | 0.202 | 0.207 |
| turkey | 266,208 | 41,519 | 74,562 | 0.273 | 0.283 | 0.487 |
| morocco | 84,976 | 5,807 | 2,058 | 0.019 | 0.021 | 0.023 |
| tunisia | 37,224 | 3,660 | 2,506 | 0.041 | 0.047 | 0.054 |
| central_chile | 39,104 | 12,203 | 35,194 | 0.442 | 0.485 | 0.619 |
| western_cape | 55,836 | 9,031 | 27,021 | 0.256 | 0.286 | 0.305 |
| central_spain | 29,704 | 3,555 | 2,996 | 0.075 | 0.083 | 0.085 |
| southern_italy | 15,980 | 5,438 | 10,615 | 0.315 | 0.327 | 0.346 |
| sw_australia | 50,572 | 14,991 | 48,726 | 0.384 | 0.409 | 0.418 |
| s_california | 27,636 | 3,425 | 7,576 | 0.113 | 0.151 | 0.178 |

## Swap stability by region (median abs log, both totals > 0), pixel unit

| Region | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| portugal | 0.083 | 0.077 | 0.087 | 0.087 | 0.077 | 0.091 | 0.092 | 0.086 | 0.164 |
| lebanon | 0.180 | 0.217 | 0.177 | 0.157 | 0.226 | 0.180 | 0.218 | 0.222 | 0.385 |
| cyprus | 0.559 | 0.547 | 0.528 | 0.507 | 0.665 | 0.549 | 0.552 | 0.460 | 0.757 |
| jordan | 0.140 | 0.159 | 0.142 | 0.253 | 0.254 | 0.141 | 0.165 | 0.303 | 0.353 |
| israel | 0.271 | 0.229 | 0.270 | 0.305 | 0.269 | 0.268 | 0.271 | 0.231 | 0.261 |
| palestine | 0.237 | 0.178 | 0.252 | 0.263 | 0.275 | 0.250 | 0.154 | 0.198 | 0.513 |
| greece | 0.090 | 0.085 | 0.092 | 0.090 | 0.095 | 0.091 | 0.099 | 0.089 | 0.143 |
| syria | 0.157 | 0.179 | 0.164 | 0.202 | 0.175 | 0.165 | 0.134 | 0.146 | 0.316 |
| turkey | 0.068 | 0.059 | 0.062 | 0.078 | 0.067 | 0.069 | 0.075 | 0.064 | 0.060 |
| morocco | 0.169 | 0.151 | 0.169 | 0.189 | 0.217 | 0.168 | 0.090 | 0.118 | 0.392 |
| tunisia | 0.121 | 0.164 | 0.127 | 0.187 | 0.127 | 0.124 | 0.115 | 0.142 | 0.309 |
| central_chile | 0.075 | 0.071 | 0.075 | 0.079 | 0.082 | 0.071 | 0.089 | 0.068 | 0.094 |
| western_cape | 0.093 | 0.098 | 0.090 | 0.080 | 0.082 | 0.092 | 0.098 | 0.096 | 0.130 |
| central_spain | 0.090 | 0.082 | 0.086 | 0.117 | 0.090 | 0.087 | 0.129 | 0.079 | 0.212 |
| southern_italy | 0.080 | 0.094 | 0.081 | 0.091 | 0.090 | 0.080 | 0.100 | 0.104 | 0.182 |
| sw_australia | 0.056 | 0.063 | 0.057 | 0.051 | 0.063 | 0.057 | 0.078 | 0.045 | 0.060 |
| s_california | 0.158 | 0.150 | 0.157 | 0.181 | 0.204 | 0.156 | 0.208 | 0.115 | 0.333 |

Region-months in the swap: 396 (used, both > 0: C0 395, C1 396, C2 395, C3 395, C4 395, C5 395, C6 396, C7 396, C8 362).

## Inside each fold (tuned settings)

| Unit | Candidate | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | forward | final |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pixels | C3 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| pixels | C4 | 10 | 30 | 30 | 10 | 30 | 30 | 30 | 30 | 30 | 30 |
| pixels | C5 | (100, 100) | (100, 100) | (100, 100) | (100, 100) | (100, 100) | (100, 100) | (100, 100) | (100, 100) | (100, 100) | (100, 100) |
| burning days | C3 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| burning days | C5 | (100, 30) | (100, 30) | (100, 30) | (100, 30) | (100, 30) | (100, 30) | (100, 30) | (100, 30) | (100, 30) | (100, 30) |

C3 / C4: a. C5: (a, a_n). Other candidates have no tuned setting (C0: a = 30 frozen; C7: fixed tree settings, α from inner residuals).

| Unit | Candidate | Fold | Detail |
|---|---|---|---|
| pixels | C3 | 2012 | a 10, map evaluations 382, last relative change 9.7e-08, converged True |
| pixels | C3 | 2013 | a 10, map evaluations 286, last relative change 9.8e-08, converged True |
| pixels | C3 | 2014 | a 10, map evaluations 475, last relative change 5.6e-08, converged True |
| pixels | C3 | 2015 | a 10, map evaluations 331, last relative change 3.9e-08, converged True |
| pixels | C3 | 2016 | a 10, map evaluations 628, last relative change 5.0e-08, converged True |
| pixels | C3 | 2017 | a 10, map evaluations 649, last relative change 9.8e-08, converged True |
| pixels | C3 | 2018 | a 10, map evaluations 1024, last relative change 9.4e-08, converged True |
| pixels | C3 | 2019 | a 10, map evaluations 343, last relative change 9.5e-08, converged True |
| pixels | C3 | forward | a 10, map evaluations 403, last relative change 1.0e-07, converged True |
| pixels | C3 | final | a 10, map evaluations 754, last relative change 1.0e-07, converged True |
| pixels | C4 | 2012 | a 10, map evaluations 220, last relative change 9.9e-08, converged True |
| pixels | C4 | 2013 | a 30, map evaluations 118, last relative change 9.1e-08, converged True |
| pixels | C4 | 2014 | a 30, map evaluations 97, last relative change 4.0e-08, converged True |
| pixels | C4 | 2015 | a 10, map evaluations 337, last relative change 8.4e-08, converged True |
| pixels | C4 | 2016 | a 30, map evaluations 106, last relative change 6.8e-08, converged True |
| pixels | C4 | 2017 | a 30, map evaluations 151, last relative change 1.0e-07, converged True |
| pixels | C4 | 2018 | a 30, map evaluations 100, last relative change 7.4e-08, converged True |
| pixels | C4 | 2019 | a 30, map evaluations 157, last relative change 7.7e-08, converged True |
| pixels | C4 | forward | a 30, map evaluations 100, last relative change 3.3e-08, converged True |
| pixels | C4 | final | a 30, map evaluations 106, last relative change 5.4e-08, converged True |
| pixels | C6 | 2012 | converged True, max abs gradient 0.0009, α 1.303, τ² 0.1662, β Vf0 42.1, Vf1 1.85, Vf2 5.61, Vf3 11.5, Vs0 3.42, Vs1 3.81, Vs2 2.58 |
| pixels | C6 | 2013 | converged True, max abs gradient 0.00091, α 1.310, τ² 0.1761, β Vf0 20.6, Vf1 1.99, Vf2 5.92, Vf3 11.5, Vs0 3.3, Vs1 3.58, Vs2 3 |
| pixels | C6 | 2014 | converged True, max abs gradient 0.0017, α 1.275, τ² 0.1803, β Vf0 53.9, Vf1 1.82, Vf2 5.6, Vf3 11.2, Vs0 3.4, Vs1 3.8, Vs2 2.75 |
| pixels | C6 | 2015 | converged True, max abs gradient 0.00096, α 1.344, τ² 0.1783, β Vf0 49.7, Vf1 1.75, Vf2 5.63, Vf3 11.6, Vs0 3.39, Vs1 3.83, Vs2 2.52 |
| pixels | C6 | 2016 | converged True, max abs gradient 0.0043, α 1.319, τ² 0.1793, β Vf0 44.5, Vf1 1.88, Vf2 5.63, Vf3 11.6, Vs0 3.52, Vs1 3.83, Vs2 3.02 |
| pixels | C6 | 2017 | converged True, max abs gradient 0.00084, α 1.302, τ² 0.1687, β Vf0 67.8, Vf1 1.86, Vf2 5.56, Vf3 11.8, Vs0 3.49, Vs1 3.81, Vs2 2.68 |
| pixels | C6 | 2018 | converged True, max abs gradient 0.0025, α 1.315, τ² 0.1815, β Vf0 49.9, Vf1 1.92, Vf2 5.6, Vf3 11.5, Vs0 3.33, Vs1 3.67, Vs2 2.87 |
| pixels | C6 | 2019 | converged True, max abs gradient 0.00091, α 1.363, τ² 0.1843, β Vf0 46.5, Vf1 1.96, Vf2 5.56, Vf3 11.4, Vs0 3.28, Vs1 3.74, Vs2 2.77 |
| pixels | C6 | forward | converged True, max abs gradient 0.0097, α 1.361, τ² 0.1864, β Vf0 77.8, Vf1 2, Vf2 5.35, Vf3 11.7, Vs0 3.3, Vs1 3.71, Vs2 2.8 |
| pixels | C6 | final | converged True, max abs gradient 0.0023, α 1.317, τ² 0.1762, β Vf0 47.2, Vf1 1.86, Vf2 5.63, Vf3 11.5, Vs0 3.41, Vs1 3.78, Vs2 2.8 |
| burning days | C3 | 2012 | a 10, map evaluations 529, last relative change 8.0e-08, converged True |
| burning days | C3 | 2013 | a 10, map evaluations 505, last relative change 7.2e-08, converged True |
| burning days | C3 | 2014 | a 10, map evaluations 364, last relative change 8.2e-08, converged True |
| burning days | C3 | 2015 | a 10, map evaluations 388, last relative change 4.0e-08, converged True |
| burning days | C3 | 2016 | a 10, map evaluations 364, last relative change 3.8e-08, converged True |
| burning days | C3 | 2017 | a 10, map evaluations 430, last relative change 4.9e-08, converged True |
| burning days | C3 | 2018 | a 10, map evaluations 397, last relative change 3.5e-08, converged True |
| burning days | C3 | 2019 | a 10, map evaluations 451, last relative change 9.3e-08, converged True |
| burning days | C3 | forward | a 10, map evaluations 511, last relative change 7.0e-08, converged True |
| burning days | C3 | final | a 10, map evaluations 370, last relative change 9.3e-08, converged True |

## Data

| Region | Cells | Rows 2012-02 … 2019-12 | MODIS (Y) | Suomi NPP (V) | NOAA-20 | MODIS burning days | Suomi NPP burning days | NOAA-20 burning days |
|---|---|---|---|---|---|---|---|---|
| portugal | 183 | 34,770 | 23,158 | 62,152 | 6,274 | 21,147 | 32,170 | 3,595 |
| lebanon | 28 | 5,320 | 512 | 3,721 | 865 | 499 | 3,015 | 709 |
| cyprus | 21 | 3,990 | 349 | 1,792 | 352 | 330 | 1,333 | 287 |
| jordan | 71 | 13,490 | 309 | 2,352 | 662 | 306 | 2,016 | 553 |
| israel | 50 | 9,500 | 952 | 5,409 | 1,120 | 925 | 4,186 | 930 |
| palestine | 24 | 4,560 | 313 | 2,516 | 665 | 310 | 2,068 | 576 |
| greece | 388 | 73,720 | 10,978 | 37,448 | 5,969 | 10,466 | 27,495 | 4,780 |
| syria | 282 | 53,580 | 15,165 | 76,546 | 23,865 | 14,364 | 54,246 | 17,099 |
| turkey | 1416 | 269,040 | 78,136 | 243,698 | 46,540 | 75,188 | 183,749 | 36,852 |
| morocco | 452 | 85,880 | 2,159 | 12,344 | 3,063 | 2,072 | 9,536 | 2,526 |
| tunisia | 198 | 37,620 | 2,663 | 15,168 | 2,584 | 2,507 | 11,337 | 2,127 |
| central_chile | 208 | 39,520 | 39,475 | 124,251 | 18,997 | 35,972 | 70,833 | 12,728 |
| western_cape | 297 | 56,430 | 30,039 | 95,381 | 18,066 | 27,487 | 50,521 | 9,271 |
| central_spain | 158 | 30,020 | 3,151 | 9,192 | 2,182 | 3,034 | 6,656 | 1,406 |
| southern_italy | 85 | 16,150 | 11,130 | 44,779 | 8,375 | 10,701 | 33,091 | 6,525 |
| sw_australia | 269 | 51,110 | 52,668 | 239,775 | 63,971 | 49,486 | 126,900 | 33,396 |
| s_california | 147 | 27,930 | 8,839 | 36,012 | 6,532 | 7,606 | 15,759 | 3,064 |

Outage days (bake-off rule, 17 regions combined): MODIS none; Suomi NPP 2012-03-25. Months not scored: 2012-03. Swap outage months: none.

s = ΣV_SNPP / ΣV_N20 over 2018-04 … 2019-12 (sd from the month-block bootstrap):

| Region | s day, pixels (sd) | s night, pixels (sd) | s day, burning days (sd) | s night, burning days (sd) |
|---|---|---|---|---|
| portugal | 0.999 (0.062) | 0.942 (0.144) | 0.965 (0.035) | 0.937 (0.043) |
| lebanon | 1.048 (0.109) | 0.802 (0.061) | 0.967 (0.101) | 0.892 (0.082) |
| cyprus | 1.535 (0.343) | 0.614 (0.142) | 1.325 (0.264) | 0.614 (0.170) |
| jordan | 0.925 (0.069) | 0.771 (0.107) | 0.925 (0.071) | 0.779 (0.119) |
| israel | 1.077 (0.105) | 1.141 (0.085) | 0.992 (0.082) | 1.049 (0.068) |
| palestine | 1.060 (0.066) | 1.030 (0.079) | 1.036 (0.070) | 0.926 (0.070) |
| greece | 0.953 (0.023) | 0.987 (0.099) | 0.929 (0.020) | 0.949 (0.065) |
| syria | 1.074 (0.053) | 1.455 (0.156) | 1.055 (0.049) | 1.457 (0.139) |
| turkey | 1.019 (0.020) | 1.019 (0.025) | 0.987 (0.017) | 0.997 (0.021) |
| morocco | 1.119 (0.081) | 1.030 (0.042) | 1.053 (0.058) | 0.982 (0.037) |
| tunisia | 1.038 (0.069) | 0.985 (0.053) | 0.975 (0.053) | 0.982 (0.058) |
| central_chile | 1.022 (0.033) | 1.007 (0.024) | 0.994 (0.019) | 1.002 (0.018) |
| western_cape | 1.001 (0.050) | 0.998 (0.044) | 0.972 (0.027) | 0.987 (0.037) |
| central_spain | 0.970 (0.067) | 1.209 (0.261) | 0.970 (0.064) | 1.494 (0.151) |
| southern_italy | 1.025 (0.046) | 1.028 (0.061) | 1.001 (0.031) | 0.994 (0.038) |
| sw_australia | 0.989 (0.018) | 0.973 (0.016) | 0.991 (0.016) | 0.961 (0.008) |
| s_california | 0.903 (0.067) | 0.916 (0.064) | 0.976 (0.046) | 0.941 (0.032) |

Per-row scores: data/processed/tournament/rows_{px,bd}_{loyo,forward}.pkl; swap totals: swap_{px,bd}.pkl; everything above: results.json; the champion's refit settings: champion.json (data/ is not committed).

## Timings

Laptop run, 6 worker processes. Each fitted fold is cached, keyed by a hash of the fitting code, so a re-run that changes only the report refits nothing. Jobs fitted by this invocation: pixels 0, burning days 0.

Seconds per fitted job, summed (as fitted, 6 jobs at a time): pixel unit 18,883, burning-day unit 7,617.

This invocation:

| Stage | Seconds |
|---|---|
| data | 2 |
| pixel unit folds | 1 |
| burning-day unit folds | 0 |
| total | 40 |
