# Roadmap

We go one step at a time. A step is done when its check passes, not when the
code exists. Put your name next to a step before you start it.

## Before the event

**Check the 2026 Space Apps rules on work done before the hackathon.** If code
written in advance isn't allowed, the early steps here become research and
planning, and we rebuild during the 48 hours.

## Step 1: real data end to end (Portugal) · done

- [x] Download the FIRMS archive (MODIS, Suomi NPP, NOAA-20), with a SHA-256 recorded for every file
- [x] Filter and count detections per 0.25° cell
- [x] Write the retirement test, commit it, then run it ([TEST_PLAN](TEST_PLAN.md), [RESULTS](RESULTS.md))
- [x] Website reads the real record: map, chart, calendar, latest-year comparison, methodology dialog

### What step 1 found (read before starting step 2)

- **VIIRS flags about 2.7× as many fire pixels as MODIS** in Portugal (one-ratio fit: MODIS ≈ 0.37 × VIIRS). Joining the records without correcting overstates 2020–2025 by about 200 %.
- **The test passed, but narrowly.** Per-cell ratios beat one national ratio by under one point (52.8 % vs 53.5 % cell-month error). Leave-one-year-out picked the largest `k` we allowed (300), meaning the data prefer pulling hard towards the national monthly ratio. Most of the gain comes from the **month**, not the cell: the season dates move from 10.1 to 6.8 days off. Step 5 is where the model has to earn its keep.
- **2024 is the outlier:** every method overshoots MODIS by about 45 %. Terra and Aqua each saw only about 0.12 detections per Suomi NPP detection that year, against about 0.19 normally. Possible causes: the September 2024 fires (huge fires saturate differently), Terra/Aqua drift, or the switch to MODIS version 61.03 in 2023. **Open question; whoever takes it, write the check in TEST_PLAN first.**
- **The NOAA-20 handover looks fine**: the Suomi NPP model fed NOAA-20 scores 49.6 % vs 51.4 %.
- **The "normal start" date is loose (Apr 11 ± 63 days)** because Portugal has spring agricultural burning before the summer fire season. A summer-season-only calendar, or a two-season calendar, would be more useful to fire managers.
- Cell-month errors around 50 % are mostly noise from small counts. Coarser cells or quarterly sums would score lower, but that's a choice to make in the plan, not after seeing scores.

## Step 2: does it hold up somewhere else? · owner: _

- [ ] Lebanon analysis, see [tasks/ANALYST_LEBANON.md](tasks/ANALYST_LEBANON.md). Run the pipeline with `--country Lebanon` (our home audience: the October 2019 fires, the south since 2023). Small country, so check whether 0.25° cells are too coarse.
- [ ] Run one large, very different fire region (Brazil or Australia).
- [ ] Add a dated section to TEST_PLAN before looking at the new results.
- **Check:** the retirement test passes or fails in each region, and the website shows that verdict.

## Step 3: the morning gap · owner: _

Terra passes at about 10:30 in the morning; Aqua and the VIIRS satellites at about 13:30. When Terra goes, morning fires go unseen.
- [ ] Count Terra-only detections by region and month.
- [ ] Show it on the site: "X % of fires here are seen only in the morning."
- **Check:** the number is computed from data, with the method written in TEST_PLAN first.

## Step 4: the satellite handover · owner: _

- [ ] Suomi NPP → NOAA-20 → NOAA-21: does the model need a separate ratio per satellite? (RESULTS.md has the first number.)
- **Check:** the same score on NOAA-20 and NOAA-21 months as on Suomi NPP months, or a separate ratio for each that beats the shared one.

## Step 5: a better model · owner: _

The current model is one ratio per cell and calendar month. Ideas to try, each one only if it beats the current model on the same test:
- [ ] Split by fire strength (FRP), since VIIRS's extra detections are the small, weak fires
- [ ] Split by land cover (forest, shrub, cropland)
- [ ] Day and night separately
- [ ] Edge-of-swath correction (MODIS pixels grow large at the edge of the scan)

## Step 6: the live season (early warning) · owner: _

- [ ] Get a free FIRMS MAP_KEY: https://firms.modaps.eosdis.nasa.gov/api/map_key/
- [ ] Pull this year's near-real-time detections and compare them with the normal curve: "this season is running N days early."
- **Check:** backtest on past years. Would the warning have fired before the big fire weeks?

## Step 7: an independent check · owner: _

- [ ] Compare the corrected record with burned area from MCD64A1 (not built from the same hotspots).
- **Check:** the corrected record tracks burned area at least as well as raw MODIS does.

## Step 8: presentation · owner: _

- [ ] 30-second video (check the 2026 submission guide for format)
- [ ] Slides: problem, the retirement test result, the calendar, a local story
- [ ] Opening line: *"On 1 November, a satellite that watched Earth's fires for 14 years stopped delivering data. MODIS is next. We tested what survives."*
