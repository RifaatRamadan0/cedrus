# CEDRUS

**Roots in Nature. Data for a Safer Tomorrow.**
NASA Space Apps Challenge 2026 · Beirut · Challenge: *Harmonization of MODIS and VIIRS Hot Spots*

Satellites have watched Earth's fires for 25 years, but the record is split
between two kinds of instrument. MODIS (on Terra and Aqua, since 2000) is being
retired. VIIRS (Suomi NPP since 2012, then NOAA-20 and NOAA-21) sees smaller
fires, so a record that simply switches from one to the other jumps upward in
2012. That jump is the instrument changing, not the fires.

Suomi NPP stops delivering data on **2 Nov 2026**, and MODIS is
next. CEDRUS builds one fire record that survives the handover, **tests it
honestly**, and turns it into a fire calendar for any area.

## Two ways to count fires

The calendar opens in **burning days**: how many days each ~1 km square had a fire detected, in MODIS-equivalent
terms. A 0.01° square counts once per day and time of day for each satellite family, however many detections fall in
it. One click switches to **hotspots**: every satellite fire detection, in MODIS-equivalent counts, because those are
the numbers the challenge asks for. Both views keep the same region-specific record, the same areas
and checks, and the hotspot CSV can be downloaded in both. Drawn areas are exact sums; whole-region totals equal the
exact sum within rounding (bound: 0.005 × cells + 0.00005 × monthly records + 0.0001; Syria hotspots reached 0.1235). Layout of the files: [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md).

## Current regions and map coverage

The product includes Portugal, Lebanon, Syria and the La Rioja area in Argentina. Israel and Palestine are Deferred. Jordan and Cyprus were tested and removed from the app: too few fires to measure accuracy (81 and 139 MODIS burning days in the 2020–2021 test) and grid-cell errors of about 163% and 100%. Their results stay in [the forward tests](analysis/tier1/region_evidence/README.md). Exported records start in November or December 2000 and end in November or December 2025, depending on the region; exact ranges are in [the data contract](docs/DATA_CONTRACT.md#current-product-records).

The orange dashed outline is an analysis extent, not a country boundary. Faint outlined cells are included in the exported grid with a near-zero estimate for the selected month; shaded dashed cells have no qualifying records in that region's exported grid. Neither state establishes complete observations or confirms that a location was fire-free. Click the map for details. Monthly observation completeness remains unknown.

Latest full browser/data probe: **408/408 passed**, including both units, all four regions and the final console-error check. See [implementation status](docs/TIER1_IMPLEMENTATION_STATUS.md) and [the completed Tier 1 plan](docs/TIER1_PLAN.md). Live 2026 ingestion is not implemented; the local ignored FIRMS key has been used for availability/gap audits.

## How we know it works: pre-registered tests, one of them failed

Each sealed exam was written down before it was run, and each sealed region was opened once. Figures from development
data (the regions the models were chosen on) are marked as such; they are not exam results.

1. **Round 1 failed.** Model A (a shrinkage ratio that beat a learned detection-physics model in the pre-registered
   bake-off, [docs/BAKEOFF_RESULTS.md](docs/BAKEOFF_RESULTS.md)) failed its sealed confirmation: on regions it had
   never seen, one ratio per region beat it, and its NOAA-20 handover agreed only 69%
   ([docs/CONFIRMATION_RESULTS.md](docs/CONFIRMATION_RESULTS.md)).
2. **Round 2 confirmed, for hotspots.** A2 removed A's double-counting quirk and calibrated NOAA-20 against Suomi NPP,
   which raised handover agreement to 92.6% on the development data
   ([docs/ROUND2_SELECTION.md](docs/ROUND2_SELECTION.md); frozen at commit 617daff). On four new sealed regions
   (central Spain, southern Italy, southwest Australia, southern California): **CONFIRMED**, all five pre-registered
   tests passed ([docs/ROUND2_CONFIRMATION.md](docs/ROUND2_CONFIRMATION.md)). It runs the hotspot view.
3. **The tournament found burning days harmonize better.** Nine candidates on 17 development regions, in both units:
   the best burning-day model, D-a (fire-power-class ratios), reached a skill of 30.6% against its one-ratio baseline,
   the hotspot champion 23.5%; the plan needed 10% more in relative terms (25.8%), and an independent tester's common
   footing still gives 28.4%
   ([docs/TOURNAMENT_RESULTS.md](docs/TOURNAMENT_RESULTS.md)).
4. **Round 3 confirmed, for burning days.** D-a, frozen (commit 80e297f), sat one sealed exam on four more regions it
   had never seen (northern Algeria, southern France, South Australia, northern California): **CONFIRMED**, all five
   tests passed. Cell-month error 29.7% (one ratio per region: 36.2%); 80% ranges held the observed value in 83.8% of
   active cell-months (required 70–90%); predicted total 1.069 × observed (required 0.90–1.10); national-month error
   11.6% (required ≤ 21.3%); NOAA-20 handover agreement 97.3%, 213 of 219 months (required ≥ 80%)
   ([docs/ROUND3_CONFIRMATION.md](docs/ROUND3_CONFIRMATION.md)). It runs the burning-day view, which is why that view
   is the default.

[docs/RESULTS.md](docs/RESULTS.md) is an earlier test of an earlier method (a ratio per cell, the MODIS
retirement test of [docs/TEST_PLAN.md](docs/TEST_PLAN.md)); it is kept as a record, not as the evidence for
the current site.

## Quick start

You need Python 3.10+ and a browser.

```bash
pip install -r requirements.txt

python pipeline/01_download.py                     # NASA FIRMS archives for Portugal (~30 MB, no key needed)
python pipeline/01_download.py --country Lebanon   # and for Lebanon
python pipeline/02_aggregate.py                    # filter + count detections per 0.25° cell per day
python pipeline/03_harmonize.py                    # the retirement test -> docs/RESULTS.md
python -m pipeline.bakeoff.run                     # the pre-registered bake-off (docs/BAKEOFF_PLAN.md)
python pipeline/export_v2.py                       # files the website reads -> web/data/ (docs/DATA_CONTRACT.md)

python -m http.server 8000 -d web                  # then open http://localhost:8000
python tools/probe_site.py                         # headless check of the site (Playwright + Chrome) -> tools/shots/
```

`pipeline/04_export_web.py` writes the files the previous version of the site read
(`web/data/portugal.json`, no longer shipped); the current site reads only what `export_v2.py` writes.

The processed website data is committed in `web/data/`, so you can skip the
pipeline and just run the last line to work on the website.

Open the site through `http://localhost`, not by double-clicking `index.html`:
browsers block a page opened from disk from loading its data files.

## What's in the repo

| Path | What it is |
|---|---|
| `web/` | The website: plain HTML/CSS/JS, no build step. Map uses MapLibre (from a CDN). |
| `web/data/` | Output of `export_v2.py`, in both units: per region the monthly record per 0.25° cell, every burning day and every detection with its weight, the drift check, provenance. Layout in `docs/DATA_CONTRACT.md`. |
| `pipeline/` | Python steps (above). `regions.py` holds the region boxes and the global grid. `weights_bd.py` is the burning-day model, D-a (round-3 confirmed; it refits through `pipeline/round3/model.py` and `pipeline/tournament/` and checks `data/processed/tournament/frozen_round3.json` by SHA-256); `weights_r2.py` is the hotspot model, the frozen round-2 choice (A2 + NOAA-20 via Suomi NPP; it imports `pipeline/round2/models.py` and checks `data/processed/round2/frozen.json` by SHA-256); `weights_a.py` (round 1) and `weights_interim.py` are kept for reference and unused. |
| `tools/probe_site.py` | Loads the site in headless Chrome, clicks through both units, checks the CSV downloads agree with the calendar (and, for burning days, with its own Python sum over the files), saves screenshots. |
| `data/` | Raw downloads and intermediate files. **Not committed** (in `.gitignore`); run the pipeline to rebuild. |
| `docs/TEST_PLAN.md` | The test rules. Never edit old rules; add a dated section. |
| `docs/RESULTS.md` | Generated by `03_harmonize.py`. Don't edit by hand. |
| `docs/ROADMAP.md` | What's next, step by step, and who's doing it. |
| `docs/design/` | Original design reference and prototype screenshots. |

## Rules we work by

1. **Every number on the site traces to a file.** The pipeline records the URL and SHA-256 of
   every FIRMS file it used. They appear in `web/data/regions.json` and in the
   *Data & Methodology* dialog.
2. **Write the test before running it.** New claims ("our calendar predicts X") get a
   rule in `docs/TEST_PLAN.md` first, then the code.
3. **Always compare against a simple method.** If ours doesn't beat the simple method, we say so.
4. **Say what we don't know.** Neither detections nor burning days are burned area. Estimates start in 2022
   (MODIS drifted from its orbit); before that the record is MODIS itself. These limits are shown on the site, not hidden.
5. **Plain language** on the website. Judges and fire managers aren't satellite experts.

## Working together

- Branch from `main` and open a pull request. Keep `main` working.
- The site publishes to GitHub Pages from `main`, using `.github/workflows/pages.yml`.
  This needs a public repo, or a paid plan for a private one. One-time setup:
  *Settings → Pages → Source: GitHub Actions*.
- Re-run the pipeline after changing anything in `pipeline/`, and commit the new `web/data/` and `docs/RESULTS.md`.

## Data credits

Fire detections: NASA FIRMS (Fire Information for Resource Management System),
MODIS Collection 6.1 and VIIRS 375 m active fire products (each file's own version string — 6.2, 6.03, 61.03 for MODIS, 2 for VIIRS — is kept in the data). Basemap: NASA GIBS Blue Marble.
