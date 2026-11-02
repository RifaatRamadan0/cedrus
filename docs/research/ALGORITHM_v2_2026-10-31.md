# CEDRUS: algorithm and test protocol (v2)

_v2, 31 Oct 2026. Revised after an adversarial review (review/), which found 4 critical and 7 major problems in v1. Every fix is listed in §9. The model is chosen by development cross-validation only; confirmation is pass/fail for that one frozen model._

## 0. Definitions

- **Unit: MODIS-equivalent hotspot count** per 0.25° cell per month, separately for day and night. This is what the challenge asks for.
- **Reference: nominal-orbit MODIS** (Terra about 10:30, Aqua about 13:30), as flown **before 2022**.
  - Aqua entered free drift in January 2022, and Terra's orbit was lowered in October 2022.
  - After that, real MODIS is no longer the reference; it is something we *watch* drift away (§4).
  - Direction: VIIRS → MODIS-equivalent, because degrading a sharper sensor is well-posed.
- **Data:** FIRMS standard archive.
  - Filters: `type == 0`, MODIS confidence ≥ 30, VIIRS confidence n/h.
  - A missing `type` (as in near-real-time data) is not read as 0.
  - Documented outage days are masked.
- **Per-hotspot weight.** Every VIIRS hotspot carries a harmonization weight w (its expected MODIS-equivalent contribution). For any drawn area, the harmonized value = the sum of weights inside the polygon. The map, the calendar and the CSV therefore always agree.

## 1. The model

### Layer 1: VIIRS fire units
For each satellite pass, link 375 m detections into units (connected components, 1.0 km link). The unit's FRP is the **sum** of its pixels' FRP. VIIRS splits one 750 m FRP equally among its 375 m pixels, so summing does not double-count (VIIRS C2 375 m User Guide v1.2, §3.1.3). Units with FRP = 0 (saturation or failed retrieval) form their own class.

### Layer 2: learned detection response (candidate B)
Learned from matched Suomi NPP / Aqua passes in **2012–2019 only**:
1. **Matching:**
   - Search window around each S-NPP unit = the Aqua pixel's own footprint (from the MODIS `scan` × `track` columns: about 1 km at nadir, up to about 2 × 4.8 km at the swath edge), plus 0.5 km for geolocation.
   - Same date and same day/night, |Δt| ≤ 60 min.
   - **One-to-one:** each Aqua pixel is assigned to its nearest unit only.
2. **Chance control:**
   - Repeat the matching against Aqua passes from ±1 day. The hit rate there is the chance-match rate, which we subtract by FRP bin.
   - Low-FRP hit rates (13% at 2–4 MW, against 0.2% in Sofiev 2026) are suspect until this control is run.
3. **Did Aqua actually look?** Use Aqua granule footprints from NASA's CMR catalogue (no key needed). Inferring coverage from Aqua *detections* would condition on the outcome.
4. **One regression:** matched Aqua pixel count per unit ~ log FRP + day/night, a Poisson regression on the debiased hits. This replaces v1's separate p, k and 1/q terms.
5. **Expected Aqua-equivalent** count per cell-month: Ê_A = Σ_units ĝ(FRP, dn). The scalar effects v1 tried to model (fires only Aqua saw, how many pixels a fire lights) go to the statistical layer.
6. **Terra-equivalent:** Ê_T = ρ(month, dn) · Ê_A, with ρ fitted by **calendar month** on 2012–2019, because the daily fire cycle changes with the season. Terra's 10:30/22:30 timing is never sampled by VIIRS, so this part is a ratio, not physics, and we say so.

### Layer 3: statistical layer
Y_cell,month,dn = nominal MODIS count (training years only).

  Y ~ NB2(μ, α),   log μ = log(Ê + b) + β_month + β_region

- **b** (background, so a cell can have MODIS fires when VIIRS saw none) is chosen on a grid by leave-one-year-out. statsmodels can't estimate a parameter inside the offset.
- **Region effects** are shrunk by a two-stage empirical-Bayes step (fit, then shrink toward the pooled value by their standard errors). statsmodels has no random effects.
- **Weights:** w_hotspot = μ̂ apportioned to the hotspots in that cell-month by their ĝ.

### Layer 4: uncertainty (light and calibrated)
- **Parameter uncertainty:** 300 draws of the global parameters (curve coefficients, ρ, β, b), using a season-block bootstrap over the about 7.9 training years.
- **Noise:** NB, with α fitted in training.
- **Calibration:** one variance-inflation factor chosen so that leave-one-year-out 80% intervals cover 80%. Conformal methods are dropped, because 8 blocks cannot reach 90%.
- **What the browser stores:** per cell-month, the median and the 10th/90th percentiles of the draws. For drawn areas, the interval is approximated from the area's summed variance with the inflation factor, and labelled as approximate.

### Baseline (candidate A)
A Poisson–gamma shrinkage ratio per cell × month: our current M1, made formal, with NB predictive intervals.

**Footnote, not a candidate:** the Sofiev & Kouznetsov 2026 physics operator is computed as a cross-check only. LightGBM is cut.

## 2. Before 2003: the Terra-only years
From 2000 to June 2002 only Terra flew. Aqua accounts for about 51% of Terra+Aqua detections (Portugal 2012–19), so the record would show about a 2× step in July 2002.
- **Bridge:** MODIS-equivalent = Terra / (Terra share by month, 2003–2011). Flagged "bridged" on the calendar and in the CSV.
- **Baseline years for "normal" start in 2003.**

## 3. Continuing after Suomi NPP
- **NOAA-20:** its own Layer 2 curve, from matched Aqua/NOAA-20 passes in 2018–2021 (near-nominal Aqua).
- **NOAA-21:** it never overlapped nominal Aqua (its data starts 17 Jan 2024), so it is **bridged to NOAA-20 VIIRS-to-VIIRS**, fitted on development regions.
- **Combined:** the average of the available VIIRS satellites' MODIS-equivalent estimates, following GFED5NRT practice.

## 4. Drift divergence and outages
- **Drift divergence:**
  - Each month, observed real MODIS divided by predicted nominal MODIS, from 2012 to now, with its 2012–2019 band.
  - From 2022 the ratio leaves the band. That is the record of MODIS drifting, shown as a result.
  - It replaces v1's hit-rate alarm, which breaks once Aqua and VIIRS are more than about 60 minutes apart.
- **Outages:** mask the documented outages only (credit samuelakosa/firecal, stachulemko/firecal), including the five 2024 VIIRS outages. Re-check the 2024 outlier.

## 5. Calendar maths
- **Grid:** month × year, 2000 to now. Shows the harmonized median; bridged and provisional cells are marked.
- **Normal:**
  - the median *and* the mean per calendar month, over the baseline 2003 to (current year − 1);
  - flagged conflict periods are excluded (stretch goal: south Lebanon July–Aug 2006 and 2023 onwards).
- **Anomaly:**
  - % difference vs the multi-year mean (the challenge asks for this) and vs the median;
  - the month's percentile rank among baseline years;
  - P(above median) from the stored percentiles;
  - a diverging, accessible colour ramp for anomalies (ColorBrewer PuOr); cividis for counts;
  - uncertain cells fade toward neutral.
- **Trust check (reframed):**
  - R = harmonization interval half-width ÷ year-to-year spread of that month (the baseline interquartile range);
  - R < 0.5: "Reliable: our correction error is small compared with normal year-to-year variation";
  - 0.5–1: "Use with care";
  - R > 1: "Too uncertain to call above or below normal";
  - plus "Few fires here: N detections in a typical month" when N < 5.
  - Why the rewrite: v1's fixed-number table assumed simple Poisson counts. Real year-to-year spread is far larger (variance/mean 5–276), so it was wrong.
- **Season dates:**
  - one climatological season window per region (a fixed split, not fitted per year);
  - onset, middle and end at 10/50/90% of cumulative activity, computed only when the season has at least 20 detections.

## 6. Validation protocol (frozen before running)

**Development**, model selection: Portugal and the Eastern Mediterranean pooling set (Lebanon, Syria, Jordan, Israel/Palestine, Cyprus, southern Turkey, Greece).
- Leave-one-year-out within 2012–2019, plus a forward check (2012–16 → 2017–19).
- Everything is fitted inside folds.
- **Decision rule:** B replaces A only if mean CRPS improves by at least 5% (paired block bootstrap, 90% interval excluding 0) **and** leave-one-year-out 80% coverage is 75–85%. Otherwise ship A. CRPS is weighted by *training-period* cell activity, not the observed outcome.

**Confirmation**, pass/fail, run once for the single frozen model:
- **Sealed regions,** chosen by rule now and not opened until the model is frozen: Morocco, Tunisia, central Chile (Valparaíso to Biobío), South Africa's Western Cape.
  - All have Mediterranean climates, like Lebanon.
  - Chile is a South American check, close to the challenge authors.
- **Partially exposed** (reported, not confirmatory): Argentina and Cyprus, which the competitor teardown analysed; Portugal (2020–2025 already inspected); Lebanon (raw counts already viewed by our analyst).
- **Tests:**
  1. **Accuracy:** fit 2012–2019, score 2020–2021 (near-nominal MODIS) with CRPS, 80% coverage, WAPE and season-date error.
  2. **Satellite-swap consistency (drift-proof):** the MODIS-equivalent record from S-NPP vs the one from NOAA-20, for 2018–2025. They must agree within their intervals. This test never touches MODIS, so drift can't affect it.
  3. **Seam test at 2012:** the out-of-sample jump with an interval; we report the number and don't claim "proven continuous".
  4. **Drift divergence 2022–2025:** shown as a chart. It is a result, not a score.
- **Pass:** test 1 coverage of 70–90% and CRPS better than A, and test 2 agreement in at least 80% of months. Published either way.

## 7. Product (MVP for 15 Nov)
- **Static site:** MapLibre + Terra Draw + Observable Plot, with per-region data files (per-cell monthly percentiles; per-hotspot rows with weights).
  - No DuckDB-WASM and no backend.
  - Cold load under 5 s.
- **Areas:** draw, lat/lon plus radius, or country.
- **Default view:** a busy example (Portugal's August peak). Chilecito July 2026 is a one-click example, labelled "provisional (near real-time)".
- **Calendar and panels:**
  - month × year calendar;
  - a naive ↔ harmonized toggle;
  - this month vs median and vs mean, with percentile and P(above median);
  - the trust check;
  - season dates;
  - the drift-divergence chart.
- **CSV:** (1) the raw hotspots in the area, with all original columns plus sensor, era/source flag and weight w; (2) the harmonized monthly series with intervals and a source flag (observed MODIS / VIIRS-estimated / bridged / provisional).
- **Accessibility:** a keyboard-navigable calendar with a table fallback (pattern credited to Agun-Panjika), and one manual accessibility pass.

**Cut (stretch only):** LightGBM; land cover; conformal; spatial-block CV; bimodal season split; full outage inference; conflict overlay; Arabic and Spanish interface; CI accessibility checks; NB trend analysis; claims about errors in the Sofiev paper.

## 8. Credits
- **Kiln Watch:** publishing failed tests; the cloud-free denominator idea.
- **samuelakosa/firecal and stachulemko/firecal:** outage handling.
- **SHIFT:** the sensor-switch jump test.
- **Ember-Line:** matching coincident Aqua/S-NPP passes.
- **sagoresarker/nasa:** detection-vs-FRP analysis; CSV with intervals.
- **Agun-Panjika:** the accessible calendar and source-flag pattern (idea only; they have no licence).
- **Science:** Sofiev & Kouznetsov 2026; Giglio et al. 2016; Schroeder et al. 2014; GFED5NRT (Chen et al. 2026).

## 9. What the review changed (v1 → v2)

| Problem in v1 | Fix in v2 |
|---|---|
| Confirmation scored against drifted MODIS | Score accuracy on 2020–21 only; add the satellite-swap test; show 2022–25 as drift divergence |
| NOAA-21 matched to an Aqua it never overlapped nominally | Bridge NOAA-21 to NOAA-20 |
| Trust-check table assumed Poisson; real counts vary 5–276× more | Reframed as correction error vs year-to-year spread |
| "Untouched" regions had been touched | Sealed new regions; Argentina and Cyprus marked partially exposed |
| Model chosen using confirmation regions | Chosen by development cross-validation only; confirmation is pass/fail |
| 1/q and k terms double-counted or untestable | One regression with one-to-one matching; scalar effects go to the NB layer |
| A fixed 2 km match radius; chance matches; coverage inferred from the outcome | Footprint-sized window, a ±1-day chance control, CMR granule coverage |
| One Terra ratio; the 2000–2002 Terra-only step ignored | ρ by month; a bridged and flagged 2000–2002; baseline from 2003 |
| statsmodels claims | b chosen on a grid; empirical-Bayes shrinkage |
| Conformal with too few blocks; joint draws too heavy for the browser | Variance inflation; per-cell percentiles; per-hotspot weights |
| Over-claims | Removed: "first calendar", "physics model" (now "learned detection response, physics-informed"), "nobody exports hotspots", claims about the Sofiev paper |
| Risky default view | A busy default; Chilecito as a one-click example |
