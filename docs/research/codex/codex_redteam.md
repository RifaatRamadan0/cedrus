ROLE: You are an adversarial senior scientist (red team). The team has tentatively chosen a physics-based forward observation operator (VIIRS detections -> probability MODIS would detect each fire, via FRP and pixel-area detection limits from Sofiev & Kouznetsov 2026) plus a negative-binomial residual and calibrated intervals. Your job is to find out whether there is a BETTER algorithm, and to argue for it honestly. Use web search extensively. Final answer markdown, at most 1800 words, with citations.

1. Steelman the alternatives, with evidence of how well each works on comparable problems:
   - statistical ratio / shrinkage approaches (what top hackathon competitors use; empirical Bayes per region x month);
   - gradient-boosted or ML mapping (LightGBM Tweedie/Poisson; quantile regression forests);
   - quantile/distribution mapping (CDF matching as used in climate model bias correction and in satellite soil-moisture / precipitation / SST record merging, e.g. ESA CCI soil moisture, GPCP, ERSST, MSU/AMSU temperature record merging, sea-ice concentration continuity, AVHRR-MODIS NDVI continuity, nighttime lights DMSP-VIIRS harmonization (Li et al. 2020 Sci Data "A harmonized global nighttime light dataset 1992-2018"), Landsat-Sentinel HLS);
   - "common-denominator" approaches: degrade VIIRS to MODIS sensitivity by FRP threshold or by aggregating to 1 km fire cell-days (binary presence per cell-day instead of pixel counts);
   - using fire cell-days or burned-area-calibrated counts as the unit instead of raw pixel counts;
   - reference-satellite approach (INPE: keep one reference satellite, report percent change);
   - hybrid: physics operator as an offset/feature inside a GBM or NB model.
2. What did the most successful long-record merging efforts in other fields learn (nighttime lights DMSP->VIIRS is the closest analogue: different sensitivity, saturation, overlap years)? What transfers to fire hotspots?
3. Weaknesses of the physics operator for THIS task: FIRMS lacks MODIS scan angle for non-detections; FRP of 375 m pixels derives from shared 750 m M13; cloud/overpass differences; detection curves fitted globally may not hold locally; 48-hour build risk. Which weaknesses are fatal vs manageable?
4. Unit choice: should the harmonized calendar count pixels, fire cell-days (presence/absence per 1 km or 0.1 deg cell per day), or fire "events"? Which makes the sensors most comparable and is most useful to fire managers? Evidence.
5. Decision procedure: design a fair bake-off we can run on FIRMS data (training 2012-2019 only, with nested leave-one-year-out and spatial blocks; held-out 2020-2025 touched once), metrics (CRPS, coverage, seam break test, annual totals, season dates), and a decision rule. Include a recommended shortlist of 3-4 candidates to run.

End with "VERDICT": your honest recommendation of the algorithm (or hybrid) most likely to be both scientifically best and buildable in 48 hours, and what result in the bake-off would change your mind.
