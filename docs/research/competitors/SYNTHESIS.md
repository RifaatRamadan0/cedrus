# Competitor teardown synthesis (31 Oct 2026)

Per-repo notes are in this folder (OWNER_REPO.md). Scores are 1-5 and come from the teardown agents' code reads; the CEDRUS column is my own assessment of hyounes-svg/cedrus @ 8fe8c64.

## Head-to-head

| Axis | kiln-watch | samuelakosa/firecal | Ember-Line | sagoresarker/nasa | stachulemko/firecal | Agun-Panjika | flare-chronos | squadron-zero (SHIFT) | CEDRUS today |
|---|---|---|---|---|---|---|---|---|---|
| Scientific validity | 4 | 3 | 3 | 4 | 3 | 3 | 1 | 4 | 3 |
| Uncertainty | 3 | 1 | 3 | 4 | 3 | 4 | 1 | 3 | 1 |
| Calibration evidence | 3 (published FAIL, 0.985) | 1 | 3 (0.899, not discriminating) | 4 (0.85-0.91) | 2 | 4 (80.1/81.3/85.7%) | 1 | 2 (code exists, unpublished) | 1 |
| Coverage | 1 (BD) | 5 (208 countries) | 2 (8 presets + draw) | 4 (global country/1°; draw BD only) | 4 (any, but local) | 1 (BD) | 2 (2 boxes) | 5 (global, 1° boxes) | 1 (PT) |
| App UX | 4 | 5 | 2 (backend dead) | 2 (not deployed) | 2 (local only) | 4 in screenshots, 0 live (404) | 1 | 3 (WebGL heavy, unverified) | 2 |
| CSV | 2 (area daily, no hotspots) | 3 (daily, no bands) | 3 (daily + bands) | 4 (monthly + 90% + source flag) | 3 (daily + p10/p90) | 2 (prebuilt aggregates) | 1 | 3 (daily + flags, no band) | 1 (none) |
| Accessibility | 4 | 4 | 4 (axe in CI) | 2 | 3 | 5 (keyboard calendar, table fallback, 0 axe findings) | 1 | 3 | 3 |
| Storytelling | 5 | 4 | 3 | 4 | 2 | 4 | 2 | 4 | 4 |
| Live today | yes | yes | broken (dead tunnel) | no | no | 404 | no | 200, unverified render | yes |

## Field-wide gaps (none of the 8 does these)
- Raw hotspot CSV for the user's selected area. Every one exports aggregates only, and kiln-watch withholds coordinates on purpose. The challenge asks for "downloadable CSV of hotspots".
- Anomaly stated with its uncertainty. Agun, Ember, samuelakosa and kiln all flag on the point estimate or a z-score.
- A detection-probability operator used *inside* the harmonization. sagoresarker estimates P50 FRP by scan and day/night (11.7 MW nadir-day, 89 MW edge-day, 8/31 MW night) and Ember gets a coincident-overpass curve, but both only display it.
- NOAA-21 calibrated. Only kiln tried, and it failed in 84/84 strata. A NOAA-20 handover tested out of sample exists only in SHIFT (2.5% error, fit 2019-23, test 2024-25).
- A nested or untouched holdout for model selection. Ember, Agun, SHIFT, stachulemko and sagoresarker all select or tune on their reported folds.

## New-repo sweep (gh search, created after 1 Aug 2026)
57 hits; nothing strong was created on 30-31 Oct. Recently pushed ones worth watching:
- shahmirkhan106/firelens: 5 regions, regrids both sensors to about 1 km before a linear fit, North India R2 0.586, demo video.
- Naser-Al-Noman/cauchys-comet: concept stage, no metrics, Vercel site.
- bhavishyaone1/FireChronicle: "pre-hackathon preparation".
- ImLWChuen/project-stardust-firewatch: 270 files, unread.
- faradayenergy.../nasa-modis-viirs-harmonization: 13 files, 39 commits.
The full list is in sweep.tsv.
