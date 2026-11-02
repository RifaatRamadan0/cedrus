# Adversarial review of STRATEGY.md + ALGORITHM.md (31 Oct 2026)

Checks run (training years 2012-2019 only; scripts in this folder):
- mdc_check.py: Poisson MDC table reproduced exactly at n=10 (607/366/195/126/83/49/34%). n=20 gives 576/349/189/122/81/48/33%.
- overdisp_check.py: Portugal MODIS (type 0, conf>=30), interannual var/mean of 0.25 deg cell-month counts:
  mean 1-3: 5.3; 3-8: 16.4; 8-20: 43.1; 20-60: 162; national month var/mean 276, CV 1.06.
  Under NB with that dispersion a single-month 90%-power MDC is effectively unbounded (>+19,000%).
- Confirmation-region exposure: competitors/scratch/firecal_data/Argentina.json and Cyprus.json (monthly, harmonization,
  unusual, climatology) downloaded 31 Oct 19:23-19:24; competitors/samuelakosaonyejekwe_firecal.md:32 re-ran LOYO on
  Argentina (4.8%) and Cyprus (13.7%).
- physics/out/sanity_2012_2019_k1.0.json: Aqua 12,091 vs Terra 11,524 detections (2012-19) -> Aqua ~51% of Terra+Aqua,
  so Terra-only 2000-Jun 2002 sits ~2x low unless bridged. MODIS edge pixel area 9.7 km2 vs 2 km match radius.
- frontier/dual_observer_operator.py: tested q is a scalar at cell-day level, not the FRP-conditioned pixel version in ALGORITHM.md.
See the review delivered to the caller for findings.
