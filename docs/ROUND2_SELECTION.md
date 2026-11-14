# Round 2 selection: R1 / Rm / A2 and the NOAA-20 method (development regions only)

_Generated 2026-11-01T11:02:35+00:00 by `python -m pipeline.round2.select`. Rules: [ROUND2_PLAN.md](ROUND2_PLAN.md), pre-registered at commit e7763f7 before any round-2 code. Do not edit by hand._

```bash
python -m pipeline.round2.select
```

- Run started 2026-11-01T11:00:39+00:00 (UTC) at commit `3cfb1ff968eea0cc8ea6f1c3f9009e87682e53ff` with uncommitted files under pipeline/round2/ (this code is not committed yet).
- **Chosen: A2 + J-S.** Suomi NPP model A2 model A, V = 0 quirk removed; NOAA-20 method J-S.
- Regions included (13): portugal, lebanon, cyprus, jordan, israel, palestine, greece, syria, turkey, morocco, tunisia, central_chile, western_cape.
- No sealed region (central_spain, southern_italy, sw_australia, s_california) was opened. Every file access goes through `pipeline.round2.data.guard`, which refuses sealed regions.
- Before the first full run, the code was run once on a development subset (portugal, lebanon, turkey; `--regions`, output in data/processed/round2/selection_subset.md) to debug it. After that run, and after the first full run, only report wording and the fields written to frozen.json changed; no fitting or scoring code, rule or setting did. This file is a re-run of the same seeded code.

Missing for the swap window (those region-years are not in the swap): turkey: viirs-jpss1_2020_Turkey.csv.

## Deviations / interpretations

Points where the plan was silent or open to more than one reading. Each was settled by the most literal reading while the code was written, before any score was seen.

1. **Rows** run 2012-02 … 2019-12 for fitting and scoring (Suomi NPP's first full month, as in the bake-off), and 2020-01 … 2021-12 for the swap only. A region's cells are every 0.25° cell with a MODIS, Suomi NPP or NOAA-20 detection in 2012-02 … 2019-12. NOAA-20 is a VIIRS instrument, so it counts here (the bake-off read Suomi NPP only; round 1's confirmation counted NOAA-20 too). Each region's files are clipped to its box in pipeline/regions.py. The spent regions' raw folders are data/raw/chile and data/raw/south_africa. Only files for 2012–2021 are read, even where later years are on disk.
2. **Outage rule, stage 1**: the bake-off's own code (`pipeline.bakeoff.data.outages`), over all included regions combined. Months with an outage day are left out of every score, including A2's inner tuning. Fitting uses all months, as in the bake-off.
3. **Outage rule, swap**: the plan says the swap uses no MODIS, so the bake-off rule is applied to the two satellites being compared. A Suomi NPP outage day has Suomi NPP at 0 while NOAA-20 has ≥ 50, and a NOAA-20 outage day is the reverse. Regions are combined. A region-year with a missing file is left out of this count, so the missing file cannot look like an outage. Round 1's confirmation used MODIS ≥ 50 here instead.
4. **R1 / Rm ratio and b**: r = ΣY/ΣV over training rows with V > 0, per group. b = mean Y over training rows with V = 0, per group. A group with no such row falls back to region × day/night (Rm only), then to all regions × day/night, as A does. Fallback use is counted per fold below.
5. **α (R1 and Rm)**: NB2 (variance μ + αμ²). It is fitted by maximum likelihood per region × day/night, with every training row's mean held at its fitted r·V or b, over log α in [−20, 6] (the bake-off's bounds). Rows with mean 0 carry no information and are dropped from that fit. Rm keeps α per region × day/night, because the plan moves only the ratio and b to calendar months. The same α applies to V = 0 rows, which are NB(b, α).
6. **Var(r̂)**: the variance (ddof 1) of r over 200 year-block bootstrap resamples. The blocks are the training years of that fit: 7 in a leave-one-year-out fold, 5 in the forward check, 8 for the final fit. The same fallbacks apply inside each resample. The plan's term V²·Var(r̂) is 0 when V = 0, so rows with V = 0 carry no parameter term, and b's own uncertainty is not added.
7. **R1 / Rm predictive distribution for CRPS and coverage**: the negative binomial with the row's mean μ and variance σ² = μ + αμ² + V²·Var(r̂), moment-matched as size = μ²/(σ² − μ) and p = μ/σ². If σ² ≤ μ(1 + 10⁻⁹), it is Poisson(μ). If μ = 0, all the mass is at 0. CRPS is the bake-off's exact sum.
8. **A2**: "the ratio sums" are read as every ΣY of A: the prior r0 = ΣY/ΣV per region × calendar month × day/night, and the cell sums in the posterior shape a + ΣY. Both are taken over rows with V > 0. ΣV is unchanged. Rows with V = 0 keep A's distribution, Poisson(b_A). b_A is the same quantity as Rm's b: the mean Y over training rows with V = 0 per region × calendar month × day/night, falling back to region × day/night. Where r0 = 0 the forecast is all mass at 0, as in A. a is chosen from {10, 30, 100, 300, 1000} by inner leave-one-year-out (weighted CRPS, weights from the inner training years, ties to the smaller a). A2 is built by calling the bake-off's `fit_A` / `predict_A` on a table whose Y is 0 on V = 0 rows. b_A is taken from a second `fit_A` call on the real Y.
9. **Primary score and rule**: weighted CRPS with w = 1 + the cell's mean Y over the fold's training rows. "Pooled" is read as the leave-one-year-out pool (2012 … 2019 held out in turn), as in the bake-off's decision. The rule "within 2% of the best" is weighted CRPS ≤ 1.02 × the best. The forward check is reported and does not enter the rule.
10. **Reported scores**: coverage is y in [q10, q90] on active rows (Y > 0 or V > 0); all-row coverage is shown for information. Cell-month WAPE adds day and night per cell × month before taking |error|; national-month WAPE is per region × month. Both are divided by ΣY. Total bias = Σ predicted ÷ Σ observed − 1.
11. **Suomi NPP fit for stage 2** is the chosen model refitted on all 2012-02 … 2019-12 rows of the development regions. If A2 were chosen, its a would come from leave-one-year-out over the eight years.
12. **J-M** fits the chosen method to NOAA-20 against MODIS on 2018-04 … 2019-12. "The same method" is read literally, so Var(r̂) is again a year-block bootstrap, and that window has only two year-blocks (2018, 2019). J-M's parameter variance is therefore a rough estimate. A2's a would be tuned by leave-one-year-out over 2018/2019.
13. **J-S**: s = ΣV_SNPP/ΣV_N20 per region × day/night over every row of 2018-04 … 2019-12. Var(s) comes from 200 resamples of the 21 month-blocks. The chosen Suomi NPP model is applied to s·V20 (which need not be a whole number), with the Suomi NPP fit's α.
14. **Intervals of a region-month total**: mean ± 1.2816·sd (normal, not clipped at 0). sd² = the summed NB (or Poisson) variances of the rows + the bootstrap variance of the total itself. The second term is the variance over replicates of Σ k·r*·s*: r* is year-block (R1/Rm), s* is month-block (J-S), and the two are drawn independently and paired by replicate index. All rows sharing an r (or s) move together within a replicate. The plan's row formula V²·Var(r̂) does not say how rows combine in a sum. Adding each row's term separately would treat a shared parameter as independent, so it is not done. r and s are treated as independent, although both use Suomi NPP 2018–2019. With A2 there is no r bootstrap: A's posterior already sits in each row's variance.
15. **Counting and agreement**: a region-month counts if both expected totals (the S-NPP-based one and that method's NOAA-20-based one) are ≥ 10. J-S and J-M are counted separately, so their counted sets can differ. It agrees if the two closed 80% intervals overlap. J-S is chosen if its share ≥ J-M's share.
16. **Seeds**: every bootstrap draws from numpy's default_rng, seeded with 20261101 plus a CRC32 of its label (fold, model), so a re-run gives the same numbers.

## Decision 1: the Suomi NPP model

Pooled leave-one-year-out (2012 … 2019), weighted CRPS. Best: A2 (0.249); bar = 1.02 × best = 0.254. Rule: the simplest candidate within 2% of the best, in the order R1 < Rm < A2.

| Order | Candidate | Pooled weighted CRPS | ÷ best | Within 2% of best? |
|---|---|---|---|---|
| 1 | R1 one ratio per region × day/night | 0.3448 | 1.3834 | no |
| 2 | Rm one ratio per region × calendar month × day/night | 0.3164 | 1.2695 | no |
| 3 | A2 model A, V = 0 quirk removed | 0.2492 | 1.0000 | **yes** |

The first candidate in the order that is within 2% is **A2**.

## Decision 2: the NOAA-20 method

Chosen Suomi NPP model (A2) fitted on 2012-02 … 2019-12. NOAA-20 fits use 2018-04 … 2019-12. The swap compares the region-month totals for 2020-01 … 2021-12. No MODIS is used, and the window is outside both fits. Months left out (swap outage): none.

| Method | Region-months | Counted (both totals ≥ 10) | Agree | Share |
|---|---|---|---|---|
| J-M | 300 | 168 | 121 | 72.0% |
| J-S | 300 | 176 | 163 | 92.6% |

Rule: choose J-S if its share ≥ J-M's. 92.6% ≥ 72.0%: **yes** → **J-S**.

## Stage 1: pooled leave-one-year-out (2012 … 2019)

680,184 scored rows (101,761 active), 201,201 MODIS detections.

| Model | Weighted CRPS (primary) | CRPS | 80% coverage, active rows | 80% coverage, all rows (information) | Cell-month WAPE | National-month WAPE | Total bias | Predicted total |
|---|---|---|---|---|---|---|---|---|
| R1 one ratio per region × day/night | 0.345 | 0.151 | 87.5% | 98.1% | 65.7% | 22.5% | -0.5% | 200,293 |
| Rm one ratio per region × calendar month × day/night | 0.316 | 0.145 | 87.5% | 98.1% | 62.7% | 14.3% | -0.7% | 199,830 |
| A2 model A, V = 0 quirk removed | 0.249 | 0.131 | 82.4% | 97.4% | 61.2% | 14.3% | +1.7% | 204,593 |

## Stage 1: forward check (fit 2012–2016, score 2017–2019)

A2's a = 30 (leave-one-year-out inside 2012–2016). 260,496 scored rows (38,746 active), 79,134 MODIS detections.

| Model | Weighted CRPS (primary) | CRPS | 80% coverage, active rows | 80% coverage, all rows (information) | Cell-month WAPE | National-month WAPE | Total bias | Predicted total |
|---|---|---|---|---|---|---|---|---|
| R1 one ratio per region × day/night | 0.330 | 0.151 | 87.7% | 98.2% | 64.0% | 22.7% | +1.9% | 80,623 |
| Rm one ratio per region × calendar month × day/night | 0.305 | 0.146 | 87.5% | 98.1% | 60.8% | 15.6% | +0.1% | 79,223 |
| A2 model A, V = 0 quirk removed | 0.247 | 0.134 | 82.2% | 97.4% | 60.2% | 16.0% | +1.9% | 80,640 |

### Forward check by region

| Region | Rows | Active | MODIS (Y) | Weighted CRPS R1 | Rm | A2 | Coverage (active) R1 | Rm | A2 | Cell-month WAPE R1 | Rm | A2 | National-month WAPE R1 | Rm | A2 | Total bias R1 | Rm | A2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| portugal | 13,176 | 2,698 | 8,699 | 0.405 | 0.392 | 0.389 | 85.5% | 82.8% | 76.6% | 56.9% | 53.4% | 54.3% | 18.7% | 16.7% | 15.9% | +2.7% | -10.3% | -8.7% |
| lebanon | 2,016 | 433 | 143 | 0.063 | 0.061 | 0.064 | 92.6% | 93.5% | 91.5% | 143.9% | 132.2% | 132.9% | 63.2% | 46.6% | 47.1% | +17.3% | +10.5% | +10.6% |
| cyprus | 1,512 | 188 | 74 | 0.044 | 0.043 | 0.044 | 87.2% | 87.2% | 86.2% | 168.7% | 158.0% | 158.3% | 91.5% | 76.6% | 77.0% | +36.8% | +26.3% | +26.1% |
| jordan | 5,112 | 430 | 132 | 0.031 | 0.030 | 0.031 | 89.1% | 88.6% | 88.8% | 166.8% | 159.9% | 156.6% | 83.8% | 78.3% | 78.5% | -13.5% | -15.4% | -14.7% |
| israel | 3,600 | 688 | 331 | 0.081 | 0.081 | 0.082 | 87.4% | 87.5% | 86.3% | 122.9% | 122.8% | 122.0% | 36.1% | 30.8% | 30.3% | -0.6% | +1.7% | +2.1% |
| palestine | 1,728 | 394 | 121 | 0.062 | 0.061 | 0.063 | 90.6% | 91.1% | 90.6% | 139.1% | 133.4% | 132.5% | 54.9% | 56.0% | 55.6% | -1.3% | +2.8% | +3.4% |
| greece | 27,936 | 2,739 | 3,117 | 0.091 | 0.089 | 0.084 | 86.5% | 86.0% | 83.0% | 93.5% | 88.9% | 89.0% | 31.3% | 19.0% | 19.6% | +6.6% | -1.7% | -0.0% |
| syria | 20,304 | 3,642 | 7,446 | 0.261 | 0.260 | 0.259 | 90.8% | 90.4% | 80.5% | 70.6% | 69.9% | 69.0% | 23.5% | 23.3% | 22.4% | +6.0% | +3.5% | +3.6% |
| turkey | 101,952 | 15,551 | 23,656 | 0.425 | 0.377 | 0.271 | 85.4% | 86.1% | 81.4% | 84.0% | 78.7% | 76.4% | 29.8% | 14.8% | 16.7% | +8.5% | +7.2% | +11.2% |
| morocco | 32,544 | 2,428 | 851 | 0.024 | 0.024 | 0.023 | 89.0% | 89.2% | 88.7% | 147.9% | 139.2% | 138.2% | 38.6% | 25.6% | 24.7% | +2.8% | -1.2% | -0.5% |
| tunisia | 14,256 | 1,323 | 923 | 0.050 | 0.045 | 0.043 | 91.3% | 92.3% | 90.0% | 102.9% | 85.3% | 84.8% | 60.4% | 38.3% | 38.2% | +1.6% | +0.4% | +1.9% |
| central_chile | 14,976 | 4,668 | 19,987 | 0.795 | 0.748 | 0.594 | 93.3% | 91.6% | 84.1% | 40.6% | 36.6% | 37.0% | 17.7% | 9.7% | 9.3% | -6.0% | -1.3% | -0.5% |
| western_cape | 21,384 | 3,564 | 13,654 | 0.369 | 0.365 | 0.332 | 86.2% | 86.0% | 77.2% | 45.6% | 47.6% | 47.6% | 12.1% | 15.7% | 16.2% | -2.1% | -5.0% | -4.3% |

## Stage 1 by region (leave-one-year-out pool)

| Region | Rows | Active | MODIS (Y) | Weighted CRPS R1 | Rm | A2 | Coverage (active) R1 | Rm | A2 | Cell-month WAPE R1 | Rm | A2 | National-month WAPE R1 | Rm | A2 | Total bias R1 | Rm | A2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| portugal | 34,404 | 6,836 | 22,305 | 0.397 | 0.380 | 0.342 | 85.2% | 84.0% | 77.1% | 50.4% | 49.2% | 49.9% | 17.6% | 16.1% | 15.4% | +0.4% | -2.1% | -0.4% |
| lebanon | 5,264 | 1,258 | 512 | 0.077 | 0.074 | 0.075 | 92.6% | 92.8% | 90.9% | 118.7% | 110.5% | 111.3% | 55.8% | 42.2% | 42.2% | -1.3% | -1.6% | -1.5% |
| cyprus | 3,948 | 589 | 349 | 0.068 | 0.067 | 0.066 | 85.4% | 85.7% | 84.2% | 116.6% | 110.9% | 111.2% | 60.2% | 52.8% | 53.4% | -1.0% | -1.3% | -0.2% |
| jordan | 13,348 | 1,205 | 309 | 0.027 | 0.026 | 0.026 | 87.5% | 88.6% | 89.4% | 176.0% | 167.2% | 163.7% | 81.9% | 69.6% | 69.8% | -1.0% | -0.7% | +2.6% |
| israel | 9,400 | 1,900 | 949 | 0.087 | 0.088 | 0.087 | 88.4% | 88.2% | 87.1% | 121.8% | 120.4% | 119.2% | 34.1% | 34.9% | 34.5% | -0.1% | -1.0% | -0.8% |
| palestine | 4,512 | 976 | 313 | 0.060 | 0.060 | 0.060 | 92.8% | 91.7% | 91.5% | 132.4% | 128.8% | 128.6% | 58.7% | 57.9% | 57.8% | -1.5% | -4.7% | -4.3% |
| greece | 72,944 | 7,781 | 10,822 | 0.116 | 0.112 | 0.102 | 86.2% | 85.6% | 82.0% | 79.7% | 77.4% | 76.1% | 22.1% | 13.3% | 13.1% | -0.5% | -0.3% | +0.2% |
| syria | 53,016 | 8,996 | 15,150 | 0.218 | 0.218 | 0.212 | 89.3% | 89.1% | 81.9% | 75.8% | 75.6% | 73.8% | 24.3% | 24.5% | 23.3% | -1.1% | -2.4% | -2.8% |
| turkey | 266,208 | 41,519 | 77,489 | 0.507 | 0.446 | 0.307 | 86.4% | 87.0% | 82.0% | 74.6% | 69.9% | 66.5% | 27.4% | 12.5% | 12.7% | -0.2% | -0.1% | +4.6% |
| morocco | 84,976 | 5,807 | 2,145 | 0.023 | 0.022 | 0.021 | 89.2% | 89.4% | 89.1% | 145.6% | 136.1% | 135.1% | 44.3% | 26.8% | 25.9% | -0.5% | -0.3% | +0.5% |
| tunisia | 37,224 | 3,660 | 2,662 | 0.055 | 0.050 | 0.049 | 90.7% | 91.3% | 88.9% | 97.9% | 85.0% | 84.1% | 51.5% | 30.4% | 30.2% | -1.3% | -1.6% | -0.8% |
| central_chile | 39,104 | 12,203 | 38,657 | 0.621 | 0.594 | 0.511 | 91.4% | 89.6% | 83.1% | 48.6% | 45.8% | 45.9% | 16.6% | 10.2% | 10.0% | -2.0% | -1.1% | -0.2% |
| western_cape | 55,836 | 9,031 | 29,539 | 0.325 | 0.318 | 0.302 | 85.1% | 85.1% | 77.4% | 51.8% | 51.8% | 51.8% | 13.4% | 13.6% | 14.1% | +0.8% | +0.3% | +1.5% |

## Stage 1 by held-out year

| Year | Rows | Active | MODIS (Y) | Weighted CRPS R1 | Rm | A2 | Coverage (active) R1 | Rm | A2 | Cell-month WAPE R1 | Rm | A2 | National-month WAPE R1 | Rm | A2 | Total bias R1 | Rm | A2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2012 | 72,360 | 10,252 | 16,314 | 0.280 | 0.255 | 0.210 | 87.5% | 87.7% | 83.2% | 75.0% | 72.5% | 71.4% | 23.5% | 13.7% | 14.6% | +3.6% | +4.7% | +6.3% |
| 2013 | 86,832 | 13,733 | 26,860 | 0.373 | 0.340 | 0.259 | 87.9% | 87.5% | 82.8% | 65.0% | 62.2% | 60.4% | 20.4% | 11.3% | 11.1% | -3.2% | -2.7% | +0.1% |
| 2014 | 86,832 | 11,048 | 16,130 | 0.262 | 0.238 | 0.193 | 86.9% | 87.0% | 83.1% | 80.5% | 76.9% | 75.1% | 27.5% | 16.7% | 17.1% | +5.5% | +5.7% | +8.2% |
| 2015 | 86,832 | 13,870 | 32,730 | 0.465 | 0.422 | 0.306 | 87.8% | 87.5% | 81.4% | 61.5% | 58.3% | 55.3% | 21.8% | 14.5% | 13.1% | -7.7% | -7.1% | -3.6% |
| 2016 | 86,832 | 14,112 | 30,033 | 0.408 | 0.375 | 0.294 | 87.4% | 87.6% | 82.1% | 62.4% | 60.2% | 58.6% | 20.8% | 11.3% | 11.6% | +1.4% | +1.9% | +4.2% |
| 2017 | 86,832 | 13,651 | 38,736 | 0.441 | 0.406 | 0.318 | 86.4% | 86.3% | 81.0% | 54.1% | 50.0% | 49.2% | 23.1% | 14.7% | 14.0% | -7.3% | -6.6% | -4.8% |
| 2018 | 86,832 | 11,537 | 18,321 | 0.251 | 0.233 | 0.184 | 88.0% | 87.9% | 83.4% | 73.2% | 70.5% | 69.8% | 23.5% | 18.8% | 19.5% | +10.3% | +6.7% | +9.2% |
| 2019 | 86,832 | 13,558 | 22,077 | 0.273 | 0.258 | 0.227 | 88.2% | 88.1% | 83.0% | 73.4% | 71.4% | 71.0% | 21.8% | 16.3% | 17.3% | +6.8% | +3.4% | +5.1% |

## Inside each fold

| Held out | a (A2) | Inner weighted CRPS of A2 by a | Rows on a fallback ratio R1 / Rm / A2 | Rows on a fallback b R1 / Rm | Rows with A2's r0 = 0 | Regions × day/night with α from all regions R1 / Rm | Seconds |
|---|---|---|---|---|---|---|---|
| 2012 | 30 | 10: 0.2592, 30: 0.2578, 100: 0.2606, 300: 0.2653, 1000: 0.2711 | 0 / 0 / 0 | 0 / 0 | 153 | 0 / 0 | 23.4 |
| 2013 | 30 | 10: 0.2488, 30: 0.2475, 100: 0.2505, 300: 0.2552, 1000: 0.2603 | 0 / 0 / 0 | 0 / 0 | 209 | 0 / 0 | 23.4 |
| 2014 | 30 | 10: 0.2655, 30: 0.2641, 100: 0.2667, 300: 0.2709, 1000: 0.2762 | 0 / 0 / 0 | 0 / 0 | 239 | 0 / 0 | 23.0 |
| 2015 | 30 | 10: 0.2371, 30: 0.2353, 100: 0.2374, 300: 0.2413, 1000: 0.2457 | 0 / 0 / 0 | 0 / 0 | 220 | 0 / 0 | 24.5 |
| 2016 | 30 | 10: 0.2403, 30: 0.2389, 100: 0.2415, 300: 0.2463, 1000: 0.2524 | 0 / 0 / 0 | 0 / 0 | 226 | 0 / 0 | 24.7 |
| 2017 | 30 | 10: 0.2383, 30: 0.2370, 100: 0.2391, 300: 0.2429, 1000: 0.2477 | 0 / 0 / 0 | 0 / 0 | 239 | 0 / 0 | 25.2 |
| 2018 | 30 | 10: 0.2666, 30: 0.2650, 100: 0.2676, 300: 0.2723, 1000: 0.2779 | 0 / 0 / 0 | 0 / 0 | 200 | 0 / 0 | 24.5 |
| 2019 | 30 | 10: 0.2597, 30: 0.2581, 100: 0.2607, 300: 0.2654, 1000: 0.2713 | 0 / 0 / 0 | 0 / 0 | 199 | 0 / 0 | 24.6 |
| forward | 30 | 10: 0.2726, 30: 0.2703, 100: 0.2720, 300: 0.2758, 1000: 0.2810 | 0 / 0 / 0 | 0 / 0 | 727 | 0 / 0 | 21.9 |

## Stage 2 by region

| Region | J-M counted | J-M agree | J-M share | J-S counted | J-S agree | J-S share |
|---|---|---|---|---|---|---|
| portugal | 23 | 18 | 78.3% | 23 | 23 | 100.0% |
| lebanon | 6 | 6 | 100.0% | 7 | 7 | 100.0% |
| cyprus | 0 | 0 | n/a | 1 | 1 | 100.0% |
| jordan | 1 | 1 | 100.0% | 0 | 0 | n/a |
| israel | 11 | 10 | 90.9% | 11 | 11 | 100.0% |
| palestine | 5 | 5 | 100.0% | 5 | 5 | 100.0% |
| greece | 20 | 15 | 75.0% | 22 | 22 | 100.0% |
| syria | 19 | 12 | 63.2% | 24 | 19 | 79.2% |
| turkey | 12 | 7 | 58.3% | 12 | 11 | 91.7% |
| morocco | 13 | 11 | 84.6% | 13 | 11 | 84.6% |
| tunisia | 10 | 6 | 60.0% | 10 | 8 | 80.0% |
| central_chile | 24 | 12 | 50.0% | 24 | 23 | 95.8% |
| western_cape | 24 | 18 | 75.0% | 24 | 22 | 91.7% |

s = ΣV_SNPP / ΣV_N20 over 2018-04 … 2019-12 (sd from the month-block bootstrap):

| Region | s day (sd) | s night (sd) |
|---|---|---|
| portugal | 0.999 (0.058) | 0.942 (0.144) |
| lebanon | 1.048 (0.106) | 0.802 (0.060) |
| cyprus | 1.535 (0.413) | 0.614 (0.150) |
| jordan | 0.925 (0.068) | 0.771 (0.098) |
| israel | 1.077 (0.090) | 1.141 (0.087) |
| palestine | 1.060 (0.061) | 1.030 (0.081) |
| greece | 0.953 (0.025) | 0.987 (0.099) |
| syria | 1.074 (0.049) | 1.455 (0.165) |
| turkey | 1.019 (0.022) | 1.019 (0.024) |
| morocco | 1.119 (0.075) | 1.030 (0.043) |
| tunisia | 1.038 (0.063) | 0.985 (0.058) |
| central_chile | 1.022 (0.035) | 1.007 (0.023) |
| western_cape | 1.001 (0.047) | 0.998 (0.044) |

Counted region-months that disagree, J-M:

| Region | Month | Suomi NPP-based (80% interval) | NOAA-20-based, J-M (80% interval) | Suomi NPP count | NOAA-20 count |
|---|---|---|---|---|---|
| portugal | 2020-06 | 37.8 (29.8 … 45.9) | 22.1 (16.0 … 28.2) | 107 | 119 |
| portugal | 2020-08 | 250.9 (229.3 … 272.4) | 199.1 (176.6 … 221.7) | 545 | 574 |
| portugal | 2020-10 | 82.0 (70.2 … 93.8) | 119.8 (104.7 … 134.9) | 153 | 186 |
| portugal | 2021-07 | 71.0 (59.8 … 82.2) | 49.0 (38.7 … 59.2) | 138 | 109 |
| portugal | 2021-08 | 140.1 (123.2 … 157.1) | 101.4 (86.0 … 116.8) | 314 | 275 |
| israel | 2021-05 | 32.3 (24.7 … 39.8) | 62.9 (50.5 … 75.3) | 216 | 224 |
| greece | 2020-01 | 57.5 (47.4 … 67.6) | 33.3 (25.3 … 41.4) | 350 | 368 |
| greece | 2020-02 | 70.5 (59.6 … 81.5) | 108.1 (93.9 … 122.3) | 249 | 286 |
| greece | 2021-02 | 72.3 (61.2 … 83.4) | 103.1 (88.8 … 117.4) | 255 | 257 |
| greece | 2021-05 | 77.7 (63.0 … 92.4) | 46.6 (30.3 … 62.9) | 453 | 480 |
| greece | 2021-06 | 45.8 (36.9 … 54.7) | 17.8 (12.4 … 23.3) | 116 | 83 |
| syria | 2020-06 | 873.1 (830.3 … 915.8) | 745.8 (700.5 … 791.2) | 3,156 | 2,787 |
| syria | 2020-08 | 346.9 (321.9 … 372.0) | 444.3 (413.1 … 475.4) | 1,821 | 1,644 |
| syria | 2020-10 | 369.4 (342.7 … 396.2) | 489.2 (446.4 … 532.1) | 2,059 | 2,405 |
| syria | 2021-02 | 33.3 (25.8 … 40.8) | 11.6 (7.2 … 16.1) | 140 | 151 |
| syria | 2021-05 | 95.3 (82.3 … 108.4) | 162.5 (142.1 … 182.9) | 539 | 628 |
| syria | 2021-09 | 41.2 (32.8 … 49.5) | 62.6 (51.7 … 73.5) | 201 | 276 |
| syria | 2021-10 | 51.0 (41.6 … 60.4) | 81.4 (69.0 … 93.9) | 257 | 372 |
| turkey | 2021-01 | 316.2 (291.5 … 340.9) | 184.1 (162.8 … 205.5) | 1,108 | 1,169 |
| turkey | 2021-02 | 192.9 (174.8 … 210.9) | 243.9 (222.8 … 265.0) | 764 | 821 |
| turkey | 2021-04 | 108.1 (94.7 … 121.4) | 69.5 (58.7 … 80.2) | 268 | 319 |
| turkey | 2021-05 | 259.9 (239.0 … 280.9) | 209.4 (190.2 … 228.7) | 782 | 767 |
| turkey | 2021-06 | 1,411.0 (1,358.7 … 1,463.3) | 1,283.1 (1,227.2 … 1,339.0) | 2,282 | 2,427 |
| morocco | 2021-07 | 45.5 (36.7 … 54.3) | 72.1 (59.8 … 84.4) | 243 | 332 |
| morocco | 2021-08 | 59.1 (48.3 … 69.9) | 90.1 (73.0 … 107.3) | 238 | 370 |
| tunisia | 2020-08 | 229.3 (208.1 … 250.6) | 119.1 (102.3 … 135.8) | 851 | 681 |
| tunisia | 2021-06 | 44.1 (34.9 … 53.3) | 24.7 (17.5 … 31.9) | 396 | 384 |
| tunisia | 2021-08 | 211.0 (189.1 … 232.9) | 99.3 (82.5 … 116.0) | 767 | 571 |
| tunisia | 2021-09 | 47.7 (38.7 … 56.8) | 30.3 (22.8 … 37.8) | 257 | 230 |
| central_chile | 2020-01 | 404.8 (376.9 … 432.7) | 329.8 (298.7 … 361.0) | 1,246 | 1,227 |
| central_chile | 2020-03 | 631.7 (594.2 … 669.2) | 530.7 (485.6 … 575.8) | 2,265 | 2,052 |
| central_chile | 2020-10 | 341.5 (316.3 … 366.8) | 174.9 (156.1 … 193.7) | 879 | 891 |
| central_chile | 2020-11 | 195.3 (176.6 … 214.0) | 138.4 (120.6 … 156.1) | 489 | 496 |
| central_chile | 2020-12 | 143.7 (127.9 … 159.5) | 88.8 (76.0 … 101.6) | 386 | 338 |
| central_chile | 2021-01 | 520.5 (480.0 … 561.0) | 389.4 (340.7 … 438.2) | 1,622 | 1,454 |
| central_chile | 2021-03 | 573.2 (540.6 … 605.9) | 494.1 (450.9 … 537.4) | 1,545 | 1,531 |
| central_chile | 2021-05 | 332.5 (308.0 … 357.0) | 399.8 (370.2 … 429.4) | 1,055 | 1,147 |
| central_chile | 2021-08 | 103.6 (90.2 … 117.1) | 138.4 (121.7 … 155.2) | 417 | 499 |
| central_chile | 2021-10 | 213.3 (194.0 … 232.6) | 113.6 (99.0 … 128.1) | 617 | 621 |
| central_chile | 2021-11 | 197.7 (178.9 … 216.4) | 138.8 (121.8 … 155.8) | 495 | 528 |
| central_chile | 2021-12 | 505.6 (467.4 … 543.8) | 385.9 (343.1 … 428.7) | 1,739 | 1,722 |
| western_cape | 2020-02 | 220.6 (198.6 … 242.6) | 151.1 (131.0 … 171.2) | 775 | 667 |
| western_cape | 2020-05 | 243.9 (222.9 … 264.9) | 194.1 (173.4 … 214.8) | 528 | 489 |
| western_cape | 2021-02 | 364.3 (333.6 … 395.0) | 266.0 (234.1 … 297.9) | 1,237 | 1,199 |
| western_cape | 2021-03 | 551.2 (518.0 … 584.5) | 393.0 (356.8 … 429.1) | 1,146 | 947 |
| western_cape | 2021-05 | 271.6 (249.3 … 294.0) | 201.9 (181.0 … 222.8) | 606 | 539 |
| western_cape | 2021-11 | 66.2 (55.4 … 77.0) | 44.5 (35.3 … 53.6) | 172 | 134 |

Counted region-months that disagree, J-S:

| Region | Month | Suomi NPP-based (80% interval) | NOAA-20-based, J-S (80% interval) | Suomi NPP count | NOAA-20 count |
|---|---|---|---|---|---|
| syria | 2020-05 | 262.1 (239.4 … 284.9) | 215.7 (192.3 … 239.0) | 1,504 | 1,159 |
| syria | 2020-10 | 369.4 (342.7 … 396.2) | 530.2 (485.8 … 574.6) | 2,059 | 2,405 |
| syria | 2021-05 | 95.3 (82.3 … 108.4) | 130.5 (113.3 … 147.7) | 539 | 628 |
| syria | 2021-06 | 230.5 (209.8 … 251.1) | 281.7 (254.4 … 308.9) | 923 | 955 |
| syria | 2021-10 | 51.0 (41.6 … 60.4) | 80.8 (68.2 … 93.4) | 257 | 372 |
| turkey | 2021-07 | 1,490.3 (1,413.4 … 1,567.3) | 1,669.1 (1,575.3 … 1,762.9) | 5,081 | 5,554 |
| morocco | 2021-07 | 45.5 (36.7 … 54.3) | 68.0 (56.2 … 79.9) | 243 | 332 |
| morocco | 2021-08 | 59.1 (48.3 … 69.9) | 91.3 (76.3 … 106.4) | 238 | 370 |
| tunisia | 2020-08 | 229.3 (208.1 … 250.6) | 185.4 (163.0 … 207.9) | 851 | 681 |
| tunisia | 2021-08 | 211.0 (189.1 … 232.9) | 146.8 (127.1 … 166.4) | 767 | 571 |
| central_chile | 2021-05 | 332.5 (308.0 … 357.0) | 387.8 (357.0 … 418.6) | 1,055 | 1,147 |
| western_cape | 2021-03 | 551.2 (518.0 … 584.5) | 460.6 (420.6 … 500.6) | 1,146 | 947 |
| western_cape | 2021-08 | 88.5 (75.3 … 101.8) | 120.1 (102.6 … 137.5) | 258 | 397 |

## Data

| Region | Cells | Rows 2012-02 … 2019-12 | MODIS (Y) | Suomi NPP (V) | NOAA-20 2018-04 … 2019-12 |
|---|---|---|---|---|---|
| portugal | 183 | 34,770 | 23,158 | 62,152 | 6,274 |
| lebanon | 28 | 5,320 | 512 | 3,721 | 865 |
| cyprus | 21 | 3,990 | 349 | 1,792 | 352 |
| jordan | 71 | 13,490 | 309 | 2,352 | 662 |
| israel | 50 | 9,500 | 952 | 5,409 | 1,120 |
| palestine | 24 | 4,560 | 313 | 2,516 | 665 |
| greece | 388 | 73,720 | 10,978 | 37,448 | 5,969 |
| syria | 282 | 53,580 | 15,165 | 76,546 | 23,865 |
| turkey | 1,416 | 269,040 | 78,136 | 243,698 | 46,540 |
| morocco | 452 | 85,880 | 2,159 | 12,344 | 3,063 |
| tunisia | 198 | 37,620 | 2,663 | 15,168 | 2,584 |
| central_chile | 208 | 39,520 | 39,475 | 124,251 | 18,997 |
| western_cape | 297 | 56,430 | 30,039 | 95,381 | 18,066 |

Rows 2012-02 … 2019-12: 687,420, of which 680,184 are in scored months.

Stage 1 outage days (bake-off rule): MODIS none; Suomi NPP 2012-03-25. Months not scored: 2012-03.
Swap outage days: Suomi NPP none; NOAA-20 none.

The frozen settings are in `data/processed/round2/frozen.json` (not committed: data/ is ignored). The confirmation (`python -m pipeline.round2.confirm`) refits from them on each sealed region.

## Timings

Laptop run, 3 worker processes for the folds.

| Stage | Seconds |
|---|---|
| data | 5 |
| outer folds and forward check | 77 |
| scores | 6 |
| NOAA-20 stage | 28 |
| total | 115 |

## Independent test of this selection (added 1 Nov 2026, before the model was frozen and before any sealed data was read)

A separate tester re-ran the committed code from a clean tree, reimplemented R1, Rm and A2 independently, and attacked the selection.

**Verdict: the selection stands.** A2 + J-S.
- **Reproduced:** the headline numbers came out bit-identical. A2 wins in every outer fold, and still wins without the largest regions (Rm/A2 = 1.05 even without Turkey, Chile, Portugal and the Western Cape).
- **Margin overstated:** R1 and Rm share one dispersion α between rows with and without VIIRS detections, which makes their CRPS worse than it should be. With separate α, Rm/A2 = 1.14, not 1.27. The decision is unchanged (the threshold is 1.02).
- **The swap test is lenient (a weakness of the plan):** a systematic NOAA-20 bias of about ±10% would still pass the 80% bar. The confirmation also reports the median |log(NOAA-20 total ÷ Suomi NPP total)|, for information.
- **The coverage test (b) blends two groups:** rows with VIIRS detections, covered 89%, and rows where only MODIS saw fire, covered 5–8% almost by construction. A region with many MODIS-only rows could fail (b) for reasons that are not about calibration.
- **Minor:**
  - A2's rows with V = 0 use Poisson(b_A) rather than the plan's literal NB(b, α); the pooled CRPS difference is 0.0001.
  - Forecasts with all their mass at zero where r0 = 0 cost 0.00007 CRPS.
  - J-M's narrower parameter uncertainty does not explain its loss: on matched months it is 71.7% vs J-S 92.2%, and its median |log N/S| is 0.176 vs 0.098.
- **No leakage found.** The sealed guard refused every attempt, and no sealed-region artifact exists.

**Freeze:** the chosen settings (`data/processed/round2/frozen.json`: A2 with a = 30, NOAA-20 via J-S) are force-added and committed with this note, before any sealed file is read.
