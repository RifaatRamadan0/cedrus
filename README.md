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

The product covers **18 regions**. Every record starts between November 2000 and February 2001, but they end at
different times: four regions run to July 2026, the other 14 to late 2025, because no 2026 data has been added for
them yet.

| Region | Analysis area | First month | Last month |
|---|---|---|---|
| Portugal | rectangle, FIRMS country file | 2000-12 | 2026-07 |
| Lebanon | rectangle, FIRMS country file | 2000-12 | 2026-07 |
| Syria | rectangle, FIRMS country file | 2000-11 | 2026-07 |
| La Rioja area, Argentina | rectangle, FIRMS country file | 2000-11 | 2026-07 |
| Greece | whole FIRMS country file | 2000-11 | 2025-12 |
| Turkey | whole FIRMS country file | 2000-11 | 2025-12 |
| Morocco (FIRMS's file includes Western Sahara) | whole FIRMS country file | 2001-01 | 2025-12 |
| Tunisia | whole FIRMS country file | 2001-02 | 2025-12 |
| Northern Algeria | rectangle, FIRMS country file | 2000-11 | 2025-12 |
| Central Spain | rectangle, FIRMS country file | 2000-11 | 2025-12 |
| Southern Italy | rectangle, FIRMS country file | 2000-12 | 2025-12 |
| Southern France | rectangle, FIRMS country file | 2000-12 | 2025-11 |
| Central Chile | rectangle, FIRMS country file | 2000-11 | 2025-12 |
| Western Cape area, South Africa | rectangle, FIRMS area service | 2000-11 | 2025-12 |
| Southwest Australia | rectangle, FIRMS area service | 2000-11 | 2025-12 |
| South Australia (southeast) | rectangle, FIRMS area service | 2000-12 | 2025-12 |
| Southern California | rectangle, FIRMS area service | 2000-11 | 2025-12 |
| Northern California | rectangle, FIRMS area service | 2000-11 | 2025-12 |

A month counts only if MODIS has a detection in its first 3 days, which is why the first month differs. A rectangle
on a country file counts only that country's records; a rectangle from the FIRMS area service counts every fire
inside it, whatever the country. Each region's own notes on the site give its span, its sources and its forward-test
result; the results are collected in [the forward tests](analysis/tier1/region_evidence/README.md).

Israel and Palestine are Deferred. Jordan and Cyprus were tested and removed from the app: too few fires to measure accuracy (81 and 139 MODIS burning days in the 2020–2021 test) and grid-cell errors of about 163% and 100%. Their results stay in [the forward tests](analysis/tier1/region_evidence/README.md). Only Portugal, Lebanon, Syria and La Rioja include 2026 (January–July). Lebanon's 2026 detections are assigned with the Natural Earth outline as it was on 30 August 2021: the current outline moved part of the southern border by about 1 km and failed the assignment test, while the 2021 one matched every FIRMS Lebanon assignment in 2000–2025. Exact ranges are in [the data contract](docs/DATA_CONTRACT.md#current-product-records); how 2026 was added and tested is in [the 2026 plan](docs/OBS2026_VALIDATION_PLAN.md).

The orange dashed outline is an analysis extent, not a country boundary. Faint outlined cells are included in the exported grid with an estimate for the selected month that rounds to zero (under 0.05); shaded dashed cells have no qualifying records in that region's exported grid. Neither state establishes complete observations or confirms that a location was fire-free. Click the map for details; where FIRMS's own missing-data list names dates in that month for a satellite the month uses, the message gives them as FIRMS-reported missing data, not as independently verified outages. Monthly observation completeness remains unknown.

Latest full browser/data probe: **739/739 passed** (15 November 2026), including both units, all 18 regions, the map messages, the documentation index and the final console-error check. See [implementation status](docs/TIER1_IMPLEMENTATION_STATUS.md) and [the completed Tier 1 plan](docs/TIER1_PLAN.md). 2026 comes from FIRMS standard data through the keyed area API (the key stays in the ignored local `.env`); near-real-time data is not used.

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

### View the website

Python 3.10+ and a browser are enough to view the committed datasets:

```bash
python -m http.server 8000 -d web
```

Open http://localhost:8000. Opening index.html directly blocks data loading.
Map libraries and map tiles require internet access. The live-feed panel ("Right now") is
separate from the historical record and reads the committed `web/data/nrt.json` snapshot, which
covers Portugal and Lebanon only. A GitHub Action (`.github/workflows/nrt.yml`) rebuilds it once a
day at 06:30 UTC from NASA FIRMS's keyless 7-day NOAA-20 file, and the site is republished after
each run. A local server shows whichever snapshot is committed.

### Run software and browser checks

Create and activate a virtual environment, then install:

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python tools/probe_site.py --published-only
```

The probe starts its own HTTP server and saves screenshots under ignored `tools/shots/`.
To use an existing Chrome/Chromium installation, pass `--browser-executable PATH`.
Published-only mode explicitly skips raw-input refit checks while checking frozen settings,
published data and browser behavior. Omit that flag when the required raw observations
are available. Browser probes do not rerun sealed scientific experiments.

Historical preservation checks require the archived Git objects. For a shallow or
single-branch clone, fetch the archive explicitly:

```bash
git fetch origin refs/heads/archive/original-history:refs/remotes/origin/archive/original-history
git cat-file -e 4e3396040c4f23625df2c1eb85bf6a78fbf3e6d3^{commit}
python tools/check_history_unchanged.py
python tools/check_tier1_preservation.py --published-only
```

The published-only mode reports raw-input retention as not checked; omit the flag
to require those local inputs as well. The second preservation check writes an evidence report; use an isolated verification
checkout to avoid overwriting a retained historical report. Research chronology and
archive coverage are described in [docs/README.md](docs/README.md#research-chronology).

### Reproduce pipeline outputs

Install `requirements.txt` for pipeline-only work. Raw satellite observations are
not included; obtain the region inputs and verify their manifests before running
`python pipeline/export_v2.py`. FIRMS archive acquisition starts with
`python pipeline/01_download.py --country Portugal`; area/API acquisition requires
separately configured credentials. See [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md)
and the acquisition scripts for source and date coverage. Never commit credentials.
The exporter writes `web/data/`, so use a separate checkout for reproduction.

The frozen settings and run records under `data/processed/` are intentionally tracked
exceptions to the ignore rules. Preserve their bytes and expected hashes; do not
renormalize them. `.gitattributes` protects scientific data and code used by historical
checks across platforms.

The historical La Rioja diagnostic accepts its inputs explicitly:

```bash
python analysis/tier1/la_rioja_evidence/run_validation.py --data-dir PATH_TO_DIAGNOSTIC_INPUTS
```

That directory must contain the matching manifest and CSV files; ordinary website
JSON is not sufficient. Results default to ignored `data/processed/la_rioja_diagnostic/`.
This is a scientific rerun, not a setup or packaging test. Older experiment commands
and their evidence remain in the research documentation.

## What's in the repo

| Path | What it is |
|---|---|
| `web/` | The website: plain HTML/CSS/JS, no build step. Map uses MapLibre (from a CDN). |
| `web/data/` | Output of `export_v2.py`, in both units: per region the monthly record per 0.25° cell, every burning day and every detection with its weight, the drift check, provenance. Layout in `docs/DATA_CONTRACT.md`. |
| `pipeline/` | Python steps (above). `regions.py` holds the region boxes and the global grid. `weights_bd.py` is the burning-day model, D-a (round-3 confirmed; it refits through `pipeline/round3/model.py` and `pipeline/tournament/` and checks `data/processed/tournament/frozen_round3.json` by SHA-256); `weights_r2.py` is the hotspot model, the frozen round-2 choice (A2 + NOAA-20 via Suomi NPP; it imports `pipeline/round2/models.py` and checks `data/processed/round2/frozen.json` by SHA-256); `weights_a.py` is retained for reference; `weights_interim.py` still supplies the exporter’s bridging quantiles. |
| `tools/export_firms_missing_dates.py` | Writes `web/data/firms_missing_dates.json` (FIRMS's own list of dates with missing standard data, per satellite), which the map names as FIRMS-reported missing data, not independently verified outages. |
| `tools/probe_site.py` | Loads the site in headless Chrome, clicks through both units, checks the CSV downloads agree with the calendar (and, for burning days, with its own Python sum over the files), saves screenshots. |
| `data/` | Raw downloads and intermediate files are ignored; five frozen settings/run-record files are intentionally tracked. |
| `docs/` | Plans, results and references. Start at [docs/README.md](docs/README.md): what each document is for, which ones are current, and the order the tests ran in. Plans are never rewritten (add a dated section); generated results are never edited by hand. |

## Rules we work by

1. **Every number on the site traces to a file.** The pipeline records the URL and SHA-256 of
   every FIRMS file it used. They appear in `web/data/regions.json` and in the
   *Data & Methodology* dialog.
2. **Write the test before running it.** New claims ("our calendar predicts X") get a
   rule in `docs/TEST_PLAN.md` first, then the code.
3. **Always compare against a simple method.** If ours doesn't beat the simple method, we say so.
4. **Say what we don't know.** Neither detections nor burning days are burned area. Estimates start in 2022
   (MODIS drifted from its orbit); before that the record is MODIS itself. The 80% ranges of estimated months are too
   narrow: tested on 2020–2021 they held the observed value about half the time
   ([data contract](docs/DATA_CONTRACT.md)). These limits are shown on the site, not hidden.
5. **Plain language** on the website. Judges and fire managers aren't satellite experts.

## Working together

- Branch from `main` and open a pull request. Keep `main` working.
- The site is live at **https://rifaatramadan0.github.io/cedrus/**. It publishes to GitHub Pages
  from `main` with `.github/workflows/pages.yml`: on every push to `main`, after each daily
  snapshot run, and on demand (*Actions → Publish website → Run workflow*). The repository's
  Pages source is set to *GitHub Actions*; a fork needs that one-time setting
  (*Settings → Pages → Source: GitHub Actions*) and a public repository or a paid plan.
- Re-run the pipeline after changing anything in `pipeline/`, and commit the new `web/data/` and `docs/RESULTS.md`.

## Data credits

Fire detections: NASA FIRMS (Fire Information for Resource Management System),
MODIS Collection 6.1 and VIIRS 375 m active fire products (each file's own version string — 6.2, 6.03, 61.03 for MODIS, 2 for VIIRS — is kept in the data). Basemap: NASA GIBS Blue Marble.
Weather for the fire weather outlook: Open-Meteo (forecast and ERA5 archive), CC BY 4.0.

## Use of AI

AI assistants (Anthropic's Claude, OpenAI's Codex) helped write code, search the literature and draft text in this
repository. The method, the exam rules and the decisions are the team's, and every number can be rebuilt from the code
and data here. The demo videos' narration is an AI voice (ElevenLabs); no AI-generated images or video are used.
