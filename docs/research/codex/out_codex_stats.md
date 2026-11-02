**Recommendation:** use a pooled negative-binomial residual model around the physical predictor, with a Poisson–gamma shrinkage baseline. Treat the reported 52.8% WAPE as an exploratory result; proximity to a Poisson noise floor is currently **unverified**.

**1. Harmonization model**

Define the target as detections under a **fixed MODIS observing configuration**. Changes in satellite availability, overpass time and usable coverage must not change its definition.

Sofiev–Kouznetsov does analyze **375 m VIIRS**, but its operator predicts observed **FRP**. Converting it into expected hotspot counts remains an **unvalidated extension**. Aggregate VIIRS FRP into matched MODIS footprints and overpasses before applying detection curves; summing probabilities over individual VIIRS pixels preserves resolution-driven multiplicity. Hotspot CSVs alone cannot establish cloud-free observation effort. [Paper and equations](https://doi.org/10.5194/gmd-19-10123-2026)

Let \(Y_{it}\) be reference MODIS counts and \(E_{it}\) the proposed physical expected count.

| Approach | Assessment |
|---|---|
| Poisson–gamma shrinkage | Fast, interpretable baseline; sparse cells borrow strength. Conditional Poisson assumptions can underestimate uncertainty. |
| Fay–Herriot | Gaussian model for direct estimates with known sampling variances; poorly suited to zero-heavy cell-month ratios. |
| NB GLM/GLMM | Preferred: count likelihood, overdispersion, physical offset and interpretable corrections. |
| Poisson/Tweedie GBM | Useful challenger; flexible interactions, but distributional uncertainty requires additional modeling/calibration. |

Fay–Herriot shrinks a direct estimate \(z_i\) toward \(x_i^\top\beta\):
\[
\hat\theta_i=\gamma_i z_i+(1-\gamma_i)x_i^\top\beta,\quad
\gamma_i=A/(A+D_i).
\]
Unstable ratio variances and zero denominators undermine this approximation here. [Small-area formulation](https://www150.statcan.gc.ca/n1/pub/12-001-x/2016001/article/14540/03-eng.htm)

**Baseline:** within cell/calendar-month, use VIIRS count \(V_t\) as conditional exposure:
\[
Y_t\mid r\sim\mathrm{Pois}(rV_t),\quad
r\sim\Gamma(a,a/r_0),
\]
\[
r\mid D\sim\Gamma\left(a+\sum Y_t,\;a/r_0+\sum V_t\right).
\]
Gamma uses shape–rate parameters; estimate national monthly \(r_0\) and shrinkage \(a\) exclusively within training folds. The posterior predictive distribution is NB. Positive MODIS counts when \(V=0\) require a separately estimated background component.

**Primary:**
\[
Y_{it}\sim NB2(\mu_{it},\alpha),\quad
\operatorname{Var}(Y_{it})=\mu_{it}+\alpha\mu_{it}^2,
\]
\[
\log\mu_{it}=\log E^*_{it}+\beta_0+\beta_{m(t)}
+\beta_{\mathrm{region}(i)}+x_{it}^{\top}\beta.
\]
Use \(E^*=E+b_{\mathrm{region},m}>0\), with background \(b\) estimated on training data; distinguish missing coverage from observed zeros. Include sensor identity and acquisition-time covariates. Add cell random intercepts only if supported computationally; many zeros alone do not justify zero inflation.

For 48 hours, use [`statsmodels.discrete.NegativeBinomial`](https://www.statsmodels.org/stable/generated/statsmodels.discrete.discrete_model.NegativeBinomial.html), which supports offsets and estimates dispersion. The [GLM NB family](https://www.statsmodels.org/stable/generated/statsmodels.genmod.families.family.NegativeBinomial.html) instead takes supplied dispersion. [`glmmTMB`](https://glmmtmb.github.io/glmmTMB/reference/nbinom2.html) is an R option; [`PyMC`](https://www.pymc.io/projects/docs/en/v5.24.0/api/distributions/generated/pymc.NegativeBinomial.html) supports hierarchical NB, but uses shape \(=1/\alpha\).

[LightGBM](https://lightgbm.readthedocs.io/en/stable/Parameters.html) supports Poisson, Tweedie and separate quantile objectives. Poisson loss estimates a mean without establishing Poisson predictive variance. Tweedie \(1<p<2\) has continuous positive support, making it more natural for FRP than integer counts.

**2. Predictive intervals and calibration**

Start with NB predictive quantiles, including parameter and physical-operator uncertainty.

- **Parametric bootstrap:** simulate training counts, refit, then simulate target counts. This depends on the fitted dependence assumptions.
- **Season-block bootstrap:** resample complete fire-years, keeping all cells and both sensors together. Preserve cross-year seasons. Use paired blocks for differences between models.
- **Split conformal/CQR:** calibrate held-out interval scores
  \[
  s_j=\max(L_j-Y_j,Y_j-U_j),\quad
  q=s_{(\lceil(K+1)(1-\eta)\rceil)}.
  \]
  Return \([L-q,U+q]\cap\mathbb N_0\). Quantile models provide \(L,U\); NB quantiles can also serve as starting bounds. [CQR](https://arxiv.org/abs/1905.03222)

Ordinary conformal guarantees require exchangeability. Seasonal pooling does not establish it; dependent-data methods require additional conditions. Nine exchangeable calibration blocks are the minimum for a finite standard 90% block-conformal bound; two calibration years are insufficient. [Temporal conformal](https://proceedings.mlr.press/v75/chernozhukov18a.html)

Check 50/80/90/95% coverage, width and tail misses by year, sensor, season, region and predicted-count bin. Use randomized PIT:
\[
U=F(Y-1)+W\,P(Y),\quad W\sim U(0,1).
\]
Inspect uniformity and residual dependence; obtain diagnostic uncertainty by blocks. [Count-forecast assessment](https://doi.org/10.1111/j.1541-0420.2009.01191.x)

**3. Proper scores and noise floors**

Prioritize CRPS; report negative log score and Dawid–Sebastiani:
\[
CRPS=E|X-y|-\tfrac12E|X-X'|,\quad
LS=-\log p(y),\quad DSS=(y-\mu)^2/v+\log v.
\]
DSS assesses only mean/variance.

For integer \(y\), both count CRPS closed forms can be written
\[
y[2F(y)-1]-2\mu G(y-1)+\mu-A.
\]
For Poisson, \(G=F\) and
\[
A=\mu e^{-2\mu}[I_0(2\mu)+I_1(2\mu)].
\]
For NB with size \(r=1/\alpha\), \(p=r/(r+\mu)\), \(G=F_{r+1,p}\), and
\[
A=\frac{\mu}{p}\,{}_2F_1(r+1,\tfrac12;2;-4(1-p)/p^2).
\]
Use [`scoringrules.crps_poisson`](https://scoringrules.readthedocs.io/en/latest/generated/scoringrules.crps_poisson.html) and [`crps_negbinom`](https://scoringrules.readthedocs.io/en/latest/generated/scoringrules.crps_negbinom.html). For predictive mixtures use ensemble CRPS; [`properscoring`](https://github.com/properscoring/properscoring) supports this, but lacks these dedicated count closed forms.

**Oracle benchmark:** assume known conditional rates \(\lambda_i\), simulate \(Y_i\sim Pois(\lambda_i)\), and score the true distributions. Expected oracle CRPS is \(A_i\) above. A mean-forecast WAPE reference is
\[
W_0\approx
\frac{\sum_i2\lambda_iP_{\lambda_i}(Y=\lfloor\lambda_i\rfloor)}
{\sum_i\lambda_i}.
\]
For the absolute-error optimum, replace means with Poisson medians. Simulate the actual random-denominator WAPE as well.

Estimated rates produce a **model-based benchmark**, not a proven floor. Repeat with NB and dependence; never substitute observed test counts for true rates.

**4. Anomalies and minimum detectable change**

Generate joint reconstructed-count draws \(H^{(b)}\), preserving shared harmonization errors. Resample baseline years when estimating climatological uncertainty:
\[
\hat P=\frac1B\sum_b
1\!\left[H_{\rm current}^{(b)}>
\operatorname{median}_jH_j^{(b)}\right].
\]
This concerns equivalent counts; comparing latent means answers a different question. Conformal coverage does not calibrate this probability automatically. Compare month-to-date with matching historical dates; percentage anomalies are undefined when the baseline median is zero.

Define “detectable” as **90% power, one-sided 5% significance**. For \(n\) independent baseline years:
\[
s_R^2\approx\frac1{R\mu}+\alpha+
\frac{1/\mu+\alpha}{n}+\tau_\Delta^2,
\qquad
\log R\approx z_{.95}s_1+z_{.90}s_R.
\]
Here \(\tau_\Delta^2\) is harmonization variance of the log contrast, including covariance. This approximation is unreliable at low counts.

The following are **computed exact Poisson results**, \(n=10\), equal exposure, no harmonization error:

| Baseline monthly mean | Smallest detectable increase |
|---:|---:|
| 1 | 607.4% |
| 2 | 366.2% |
| 5 | 195.3% |
| 10 | 126.2% |
| 20 | 83.0% |
| 50 | 49.2% |
| 100 | 33.5% |

Calculation: baseline total \(B\sim Pois(n\mu)\), current \(C\sim Pois(R\mu)\); under equality,
\(C\mid B+C\sim Bin(B+C,1/(n+1))\). Enumerate rejection probabilities and solve power \(=0.90\). [Exact conditional test](https://www.statsmodels.org/stable/generated/statsmodels.stats.rates.test_poisson_2indep.html)

For NB plus harmonization uncertainty, simulate the complete testing procedure and root-find \(R\); the table is an optimistic reference.

**5. Seams and trends**

Non-rejection cannot prove seam removal. Predefine an equivalence tolerance, such as a residual multiplicative jump within 0.9–1.1, and require its interval inside that band.

Use known-switch terms in an NB observation model, with seasonality and acquisition covariates. Validate artificial switches against continuing MODIS observations; a 2012 break alone cannot distinguish ecology from instrumentation.

Chow is a Gaussian linear-model test; [CUSUM’s standard implementation uses OLS residuals](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.breaks_cusumolsresid.html). [Bai–Perron](https://doi.org/10.1002/jae.659) searches multiple regression breaks; [Pettitt](https://doi.org/10.2307/2346729) detects a rank-based single change. Apply exploratory diagnostics to deseasonalized residuals with dependence-aware calibration.

For trends, prefer NB \(\log\mu=\cdots+\beta\,year\), reporting \(100(e^\beta-1)\%\)/year. Sen slope plus [Hamed–Rao MK](https://doi.org/10.1016/S0022-1694(97)00125-X) is a sensitivity analysis on annual or season-specific series.

**6. Validation protocol**

LOYO evaluates missing-year reconstruction, potentially using future information. Leave-one-fire-season-out preserves complete episodes. Rolling-origin validation matches retirement deployment. Buffered spatial blocks test geographic transfer; choose buffers from training residual correlation. [Roberts 2017](https://doi.org/10.1111/ecog.02881), [Ploton 2020](https://doi.org/10.1038/s41467-020-18321-y)

Freeze a retrospective protocol: training 2012–2017, calibration 2018–2019, evaluation 2020–2025; nested temporal tuning inside training. Fit all priors, backgrounds, preprocessing and physical corrections within folds. Report 2024 separately without excluding it. Compare paired block-bootstrap CRPS differences, coverage, WAPE and seasonal errors.

Because 2020–2025 results were already inspected, reserve untouched regions or future observations for genuinely confirmatory evaluation.

**7. Bimodal seasons**

Use training climatology to identify circular modes and split spring/summer seasons at intervening minima. Within each season,
\[
t_q=\inf\{t:C(t)/C_{\rm season}\ge q\}.
\]
Report 10/90% onset/end; 5/95% is tail-sensitive. Report each smoothed mode and activity share; a circular mean can fall between peaks. Bootstrap joint trajectories and recompute boundaries and modes.

[Giglio 2006](https://doi.org/10.1029/2005JG000142) documents sensor-dependent seasonality; [Benali 2017](https://doi.org/10.1111/geb.12586) explicitly analyzes bimodal regimes. Monthly data support month-scale timing, not independently verified day-scale precision.

**RECOMMENDED STATISTICAL PIPELINE**

1. **pandas/GeoPandas:** construct complete cell-month panels; flag coverage gaps and freeze observing configuration.
2. **NumPy/SciPy:** build footprint-based \(E\); fit training-only gamma-shrinkage baseline.
3. **statsmodels:** fit NB2 with `offset=np.log(E_star)`; estimate \(\alpha\).
4. **NumPy/SciPy:** bootstrap refits and predictive draws; calibrate AOI totals directly rather than summing cell intervals.
5. **scoringrules:** calculate CRPS/log scores; audit PIT, coverage and simulated noise benchmarks.
6. **SciPy:** compute anomaly probabilities and simulation-based detectable changes; display insufficient-reliability flags.
7. **statsmodels/pyMannKendall:** run seam equivalence, trend and season checks under the frozen validation protocol.