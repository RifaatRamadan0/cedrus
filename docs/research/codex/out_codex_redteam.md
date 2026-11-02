**My recommendation is a partially pooled negative-binomial count model, with aggregated FRP and the physics score tested as optional predictors.** The evidence does not justify making a per-VIIRS-pixel detection operator the foundation of the calendar. The strongest challenger is LightGBM; quantile mapping also deserves a serious test.

Your Portugal results are team-reported, not independently reproduced here. Competitors’ percentages are not comparable unless target units, aggregation and validation splits match.

**What the alternatives can credibly offer**

| Approach | Strongest case and relevant evidence | Limitation for CEDRUS |
|---|---|---|
| **Ratios / empirical Bayes shrinkage** | Pooling region×month ratios controls variance where local counts are sparse. Kiln Watch reports later-season concordance improving **0.61→0.96**, using calibrated fire cell-days and observation denominators. These are repository-reported results, not an independent audit. [Repository](https://github.com/Aalvee-Aarham/kiln-watch) | Cannot adapt readily to changing fire-size distributions or sampling. Your 53.5→52.8% WAPE improvement is small; uncertainty on that difference matters. Other supplied competitors’ performance claims remain unverified here. |
| **LightGBM / quantile regression forests** | In satellite precipitation correction, QRF reduced daily RMSE **5.5→3.3 mm/day**, versus **6.0** for IMERG-F. A separate continental-US study found LightGBM superior to QRF at extreme quantiles. This supports nonlinear conditional mapping, not a promised fire-error reduction. [Zhang et al.](https://doi.org/10.1029/2022WR032117), [Tyralis et al.](https://doi.org/10.1109/JSTARS.2023.3297013) | Trees extrapolate poorly beyond training extremes. Use Poisson for integer-count means; Tweedie is more natural for zero-plus-continuous targets such as FRP. Neither objective automatically supplies calibrated intervals. [LightGBM documentation](https://lightgbm.readthedocs.io/en/stable/Parameters.html) |
| **Quantile/distribution mapping** | There is **direct fire evidence**: Kaur et al. corrected MODIS swath-dependent FRP bias using quantile mapping, trained on 2016 and evaluated on 2017. At 1° resolution, bias was nearly eliminated below 40° viewing angle; correction at 0.1° remained substantially incomplete. [DOI:10.3390/rs11101205](https://doi.org/10.3390/rs11101205) | This validates FRP correction, not hotspot-count correction. Eight observations per cell×calendar-month cannot support a local empirical CDF. Pool regions/seasons, model zeros separately, and specify tail extrapolation. |
| **Common denominator: thresholds / cell-days** | Spatial aggregation suppresses the multiplication of detections caused by finer pixels. Thresholding deliberately retains fires both instruments can plausibly observe. These are transparent, inexpensive baselines. | A fixed FRP cutoff cannot equalize viewing angle, clouds or overpass time. Aggregating to 1 km equalizes reporting support, not sensitivity. |
| **Reference satellite** | INPE explicitly recommends its reference-satellite series for comparisons over years. This avoids jumps from simply adding satellites. [INPE FAQ](https://data.inpe.br/queimadas/faq/) | Percent change does not remove drift or sensitivity changes. Aqua anchoring still needs a calibrated successor and a separate bridge to Terra-only years. |
| **Physics-informed NB / GBM** | Physical summaries can explain changing sensitivity while regional statistical terms absorb remaining differences. This is my preferred engineering compromise. | Its superiority is **a hypothesis**, not an established result. Learn the physics feature’s influence; a fixed offset forces its errors into every prediction. |

CAMS has published a validated FRP bias-correction methodology for incorporating VIIRS and now assimilates MODIS and VIIRS. **The exact deployed correction formula was not verified**; my earlier commentary overstated that detail. [Methodology](https://doi.org/10.24380/semg-wi2a), [operational documentation](https://confluence.ecmwf.int/plugins/viewsource/viewpagesrc.action?pageId=638816437)

**What successful long records actually teach**

Li et al.’s nighttime-lights record did more than match distributions: it blurred/aggregated VIIRS toward DMSP spatial response, log-transformed radiance, then fitted a sigmoid reproducing DMSP saturation. Continuity was better for brighter pixels; low-light rural estimates remained uncertain. **Transfer:** match spatial support before mapping, retain explicit low-signal reliability flags, and acknowledge that a legacy-equivalent product sacrifices new-sensor information. Fire’s rapid evolution makes temporal matching harder than for annual lights. [Li et al., 2020](https://doi.org/10.1038/s41597-020-0510-y)

ESA CCI soil moisture combines CDF alignment with uncertainty-weighted merging informed by triple collocation. Its lesson is to separate systematic calibration from random uncertainty—not to assume CDF matching solves both. [Gruber et al., 2019](https://doi.org/10.5194/essd-11-717-2019)

These records are not all quantile-mapping successes:

- **HLS** harmonizes atmospheric effects, viewing geometry, spectral response and grids explicitly. [NASA algorithms](https://hls.gsfc.nasa.gov/algorithms/)
- **MSU/AMSU** requires diurnal-drift correction; overlap offsets alone cannot protect trends. [Mears and Wentz](https://doi.org/10.1175/JCLI-D-16-0768.1)
- **GPCP** uses reference calibration and intercalibrated retrievals. **ERSSTv5 is not a satellite-merging example:** its inputs are ships, buoys and Argo, excluding satellite SST. [GPCP](https://doi.org/10.1175/JCLI-D-23-0123.1), [NOAA presentation](https://www.clivar.org/sites/default/files/3huang.enso.2018.pdf)

Ordinary quantile mapping can alter trends; quantile-delta mapping was designed to preserve relative changes. Neither should be allowed to force each new fire year back toward the historical distribution. [Cannon et al., 2015](https://doi.org/10.1175/JCLI-D-14-00754.1)

**Where the proposed operator breaks**

Sofiev–Kouznetsov derives detection curves from FRP distributions and demonstrates **FRP cross-mapping**, using full retrieval masks and geolocation. Its 2020 comparison uses symmetric visibility filtering and a **1.2 diurnal adjustment**. This does not establish calibrated probabilities for monthly hotspot counts. Its inputs also extend through **2023 for MODIS and 2024 for VIIRS**: published empirical coefficients do not satisfy a strict 2012–2019 training embargo. Re-estimate within the embargo or label that candidate “externally informed.” [Paper](https://doi.org/10.5194/gmd-19-10123-2026)

The practical distinctions are:

- **Fatal to literal pixel-probability interpretation:** 375 m FRP is apportioned from a shared 750 m M13 retrieval. Summing nonlinear detection probabilities over those rows is not equivalent to evaluating a MODIS footprint. Aggregate first; FIRMS alone cannot reconstruct exact native footprints. Zero FRP can also represent retrieval failure, not negligible fire. [NASA ATBD](https://viirsland.gsfc.nasa.gov/PDF/VIIRS_activefire_375m_ATBD.pdf)
- **Fatal to identifying actual fire occurrence from CSV alone:** absence of a detection conflates no fire, clouds, missing observation and insufficient sensitivity. Non-detection footprints and observing opportunities are absent. Statistical prediction remains possible; exact observation probabilities are unsupported.
- **Manageable:** local vegetation/background differences, imperfect geometry and day/night variation—through pooling, features, sensitivity analyses and empirical calibration.
- **High build risk:** acquiring masks, matching footprints and validating those steps within 48 hours. An NB layer cannot repair a wrongly defined target. Fit NB to nonnegative counts, **not signed residuals**.

**Choose the unit deliberately**

For the calendar, I recommend **monthly sums of observed fire cell-days on a fixed equal-area 1 km grid**, with sensor configuration standardized. This measures spatial extent and persistence of detected activity while reducing pixel fragmentation. Test grid-origin sensitivity and 2 km aggregation; 0.1° cells can saturate at one detection despite substantial additional activity.

This recommendation is an inference, not proof of sensor equivalence or demonstrated manager preference. Keep **MODIS-equivalent hotspot counts** alongside it to meet the challenge literally. Never label cell-days “number of fires.”

Events are attractive operationally, but clustering thresholds, missed days and merged fire fronts make historical event counts fragile. Burned-area calibration changes the target to area affected; use it as an external check, not a universal multiplier. NASA explicitly warns that burned area per active-fire pixel is not constant. [NASA guidance](https://appliedsciences.nasa.gov/sites/default/files/2025-05/Part%203%20FIRMS%202025%20Q%26A%20Session.docx.pdf)

**A fair, executable bake-off**

1. **Freeze the targets and data rules.** Run separate pixel-count and cell-day leaderboards; never compare their WAPEs directly. Fix confidence/type filters, local-day boundaries, satellite configurations and outage handling. Treat Terra, Aqua and each VIIRS platform separately before combining. Flag the pre-Aqua bridge and NOAA-21 transfer as separate validation problems.

2. **Use nested validation within 2012–2019.** Outer leave-one-year-out evaluates temporal transfer. Within each outer training set, tune using remaining-year folds and contiguous spatial blocks with buffers. Evaluate spatial transfer separately with entire blocks withheld across years. Fit all ratios, CDFs, scalers and calibration distributions inside folds. Add a forward-time check, such as 2012–2016→2017–2019.

3. **Run four candidates:**
   - **A:** region×month empirical-Bayes ratios, with predictive count uncertainty.
   - **B:** pooled NB using VIIRS counts, aggregated FRP, day/night composition and seasonal terms; ablate the physics feature.
   - **C:** shallow LightGBM Poisson with the same predictors and separately calibrated predictive distributions.
   - **D:** pooled zero-aware monotone quantile mapping with predictive uncertainty and frozen tail rules.

   Give B’s published physics coefficients a separate externally informed result unless they meet the embargo.

4. **Score what users need.** Primary: mean CRPS, reporting both activity-weighted and region-balanced results. Also report 50/80/95% coverage and interval width, WAPE, annual-total bias, and errors in dates reaching 10/50/90% of annual activity. Evaluate zero and extreme months separately. Check seam magnitude with block-bootstrap equivalence intervals; a nonsignificant Chow test does not establish continuity.

5. **Handle the holdout honestly.** Portugal 2020–2025 has already been inspected, including 2024. It cannot become untouched again. Freeze the new protocol, evaluate those years once more, and reserve previously unexamined regions for confirmation. Report 2020–2023 and 2024–2025 separately: NASA documents major sampling impacts in late 2024, so matching late MODIS is not necessarily matching stable fire activity. [NASA drift notice](https://landweb.modaps.eosdis.nasa.gov/displayissue?id=1254)

6. **Predeclare the decision rule.** Proposed gates: at least **5% relative CRPS improvement** over A, supported by paired year/spatial-block resampling; 90% coverage within **85–95%** overall; no material deterioration in annual totals, season timing or key regions. Otherwise choose the simpler model. These are engineering thresholds, not published standards.

Calibrate drawn-area totals using jointly resampled spatial/season blocks; independent cell intervals will be too optimistic. Estimate minimum detectable change through simulation at stated power and false-alarm rate. Your “50% Poisson floor” is unverified: Poisson variation alone does not determine cross-sensor WAPE.

**VERDICT**

Build the **pooled NB model with aggregated FRP features and block-calibrated uncertainty**, retaining shrinkage ratios as fallback. Treat the physics score as an ablation, not a compulsory offset. I would switch to LightGBM, quantile mapping or the operator hybrid if it passes the frozen CRPS, coverage and continuity gates across both time and geography. Novelty is insufficient evidence.