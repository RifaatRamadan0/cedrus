# Teardown: sagoresarkerbdcse/nasa ("FireCal AI")

Repo: https://github.com/sagoresarkerbdcse/nasa (89 files; last push 31 Oct 2026, a data-refresh bot). **Live URL: none found.**
Read 31 Oct 2026 as text. Local copies: `scratch/nasa_src/`. Their published model output: `scratch/nasa_data/harmonization.json` (generated 2026-10-08).

## 1. Harmonization as implemented

- **Unit:** the 0.01° cell-day "fire-day" (`pipeline/global-year.ts` around l.170-175: `floor((lon+180)*100)`), aggregated per country × month and per 1° cell × month. Time unit: month.
- **Direction:** MODIS (Terra+Aqua pooled) is mapped to VIIRS S-NPP-equivalent.
- **Model** (`src/lib/harmonize2.ts`): `V̂[m] = k[m]·M + floor[m]`.
  - `k[m]` uses a season window (month ±1 at ¼ weight; l.89-95) and is shrunk to the unit's annual ratio with N0 = 300 MODIS fire-days. That annual ratio is in turn shrunk to the parent's kAnnual (l.101-105).
  - `floor[m]` is the median over training years of `V − k·M`, clipped at 0 (l.118-125). This is a "small-fire floor" alternated with k for 4 iterations (l.133-138).
- **Hierarchy:** country → world, and 1° cell → 10° block → world (`pipeline/harmonization-build.ts:63-69, 136-179`). The world model has kAnnual 2.731 with monthly k from 2.49 to 3.14.
- **Training years:** 2013-2021 (`harmonize2.ts:51`). 2012 is dropped as partial, and 2022+ is held back because of drift (ATBD.md:47).
- **Filters** (`global-year.ts`, CSV loop): MODIS confidence ≥ 30 and VIIRS nominal/high; FIRMS type 2/3 dropped. **Type 1 (volcano) is kept** in the global pipeline. The README says gas flares and kilns are removed for Bangladesh (UNVERIFIED in code).
- **NOAA-20/21:** deliberately excluded "to keep one consistent sensor" (ATBD.md:204).
- **Terra/Aqua drift:**
  - Analysed but **not corrected** in the harmonized series. `src/lib/drift.ts` estimates overpass local time from the detections and regresses ln R on the time shift.
  - It reports that drift inflates MODIS by about 12% in 2024 (ATBD:185).
  - `harmonize.ts` never references drift. The only mitigation is excluding 2022+ from training.
- **Record start:** 2003. Terra-only 2000-2002 is dropped.
- **Outages** (`harmonize2.ts:340-384`):
  - A month-level rule: if the world V/M ratio is below **0.85×** that calendar month's training median, VIIRS for that month is scaled up by 1/q everywhere. If it is above 1.35×, the month is flagged as a MODIS gap.
  - Flagged months: 2012-01, 2012-03, 2022-07, 2022-08, 2024-07, and MODIS 2022-04.
  - The rule is coarse. A 15% shift in the global ratio, which could be real, rewrites the reference sensor using MODIS.

## 2. Validation and leakage

- **Split:** three blocked temporal folds (`harmonization-build.ts:72-83`):
  - train 2017-21, test 2013-16;
  - train 2013-17, test 2018-21;
  - train 2013-21, test 2022-24.
  The world root model is refitted on the train years only inside `blindTest` (`harmonize2.ts:257-260`), so there is **no prior leak** of the firecal kind.
- **Metric:** median |ln(pred/obs)| converted to %, computed over **country-months with VIIRS ≥ 100 fire-days** and country-years with VIIRS ≥ 1000 (`harmonize2.ts:257, 293, 302`; ATBD:66). Only 4,841 of roughly 11,000 country-months are scored in fold 1, so small and quiet months are excluded.
- **Reported numbers** (from `harmonization.json`; these match the README):

| Fold (test years) | v2 monthly median | v2 monthly P90 | v2 annual median | v1 global ratio, monthly |
|---|---|---|---|---|
| 2013-16 | 12.3% | 51% | 5.4% | 36.6% |
| 2018-21 | 12.8% | 58% | 6.0% | 39.2% |
| 2022-24 | 14.4% | 58.9% | 6.4% | 39.4% |

- **Leakage found (mild):**
  - The season-window weight was "chosen by the blind test over ±1 equal, ½ and none" (`harmonize2.ts:89`). That is hyperparameter selection on the reported test folds.
  - The 2022+ training exclusion was motivated by fold-3 coverage (ATBD:70).
  - N0 = 300 and the 0.35 sigma prior may have been tuned the same way (UNVERIFIED).
  - The detection model is fitted on all years, but it is diagnostic only and does not leak.
- **Not reproduced independently:** downloading `countries.json` over raw/gh kept failing, so I could only confirm that the published output matches the README.

## 3. Uncertainty and calibration

- **Method:**
  - A year-block bootstrap of k (B = 60, or 30 in folds), giving kLo/kHi (`harmonize2.ts:140-148`).
  - Prediction sigma from LOYO log residuals inside the training years: the 90th percentile of |r| / 1.645, shrunk to the parent with weight n/(n+12) (l.150-175).
  - The total log-sd is `sqrt(σ² + sdK² + 1/(v+1))`, and the 90% interval is applied in log(v+1) space (l.207-220). Annual intervals pool the variance with the parent (l.177-178).
- **Calibration is checked in code** (`harmonize2.ts:295-309`):

| Test years | 90% coverage, monthly | 90% coverage, annual |
|---|---|---|
| 2013-16 | 0.913 | 0.912 |
| 2018-21 | 0.866 | 0.886 |
| 2022-24 | 0.852 | 0.841 |

  The forward test under-covers. Coverage is computed only on months with V ≥ 100.

## 4. Web app

- **Stack:** React 19, Vite, Tailwind v4, Framer Motion, Leaflet/react-leaflet, d3-geo, Recharts, jsPDF. An Express server (`server/index.ts`) serves the AI analyst over SSE (OpenRouter or Anthropic, with a budget ledger and an offline fallback analyst), plus live data and health endpoints.
- **Scopes:**
  - World: 236 countries and a 1° grid.
  - Country.
  - Bangladesh high-detail: a 0.25° map with 0.01° fire-days, preset regions, and "draw your own area". Drawing exists only on the Bangladesh map (`MapPanel.tsx:91-94, 198`, centred on 23.6N 90.4E, minZoom 5).
- **Extras:** Lab page (detection curves, drift), Explain page (stories for 3 age groups plus a quiz), PDF brief, guided tour, NetCDF/COG/STAC dataset export (`pipeline/export_dataset.py`).
- **CSV** (`src/lib/download.ts:4-15`): the **monthly** harmonized record with `harmonized_lo90/hi90`, a source flag (viirs_observed, modis_harmonized or viirs_gap_adjusted), % versus the 10-year mean, and anomaly. There are no raw hotspots.
- **Performance:** at load the app fetches about 5.3 MB of JSON uncompressed (countries 1.8 MB, grid1 1.9 MB, grid 0.65 MB, points 0.5 MB, emissions 0.45 MB; `App.tsx:58-84`), plus heavy effects (boot screen, ember canvas, swath sweep).
- **Accessibility:**
  - Few aria attributes: 4 in CalendarPanel, 13 in MapPanel, 3 in App.
  - `prefers-reduced-motion` is handled in CSS (`index.css:298`).
  - The colour ramp runs dark ember → red → orange → yellow (`src/lib/color.ts`). It is monotone in luminance, but there is no CVD claim.
- **Live URL:** not deployed as far as I can find.
  - The repo homepage is empty, and the GitHub Pages API returns 404.
  - `sagoresarkerbdcse.github.io/nasa` returns 404.
  - Guessed vercel/netlify/render/railway names returned 404 or unrelated sites (`nasa.vercel.app` is "space-search", `firecal.vercel.app` is a FIRE finance calculator, `nasa-eight.vercel.app` is a WordPress site).
  - The analyst needs the Express backend in any case. A judge can currently only see the README.

## 5. Weaknesses a judge would notice

1. No working demo link.
2. Drawing an arbitrary area only works in Bangladesh.
3. The headline 12-14% is a country-scale metric that excludes months under 100 fire-days.
4. Interval coverage falls to 85% in 2022-24.
5. The record starts in 2003 (the challenge asks for the 2000s), and there is no NOAA-20/21 although S-NPP is ending.
6. Drift is measured but not corrected.
7. The 0.85 outage rule rewrites the reference sensor.
8. Volcano detections are kept.
9. The "HCI" confidence index uses ad-hoc weights 0.4/0.35/0.25 (`src/lib/harmonize.ts` around l.160).
10. Dense "mission-control" ornament, and the AI analyst could hallucinate (the briefs carry a disclaimer).

## 6. Best idea to borrow

**The same-overpass Aqua↔S-NPP matchup table** (`global-year.ts:28-36`, `src/lib/detection.ts`). It works as follows:
- A VIIRS fire object counts as co-observed when Aqua saw fire within 3×3 1° cells, in the same day/night pass, within 25 minutes.
- The object counts as detected when an Aqua pixel lies within 0.6 × the MODIS pixel size + 0.5 km.
- Objects are binned by FRP, MODIS pixel area, day/night and latitude band, and a ceiling × logistic model is fitted to them.

Results: 55.9M objects and 29.8% detected overall. FRP50 is 11.7 MW at nadir by day, 89 MW at the swath edge by day, 8 MW at nadir by night and 31 MW at the edge by night. Pseudo-R² is 0.17.

This is CEDRUS's intended Sofiev-style P_det operator, estimated empirically. They only display it and never use it to harmonize. We can borrow the matchup recipe to fit or validate our operator, with credit, and we must say clearly that we use P_det **in** the harmonization while they do not.

## Scores (1-5)

Scientific validity 4 · Uncertainty 4 · Calibration evidence 4 · Coverage 4 · App UX 2 (no deploy; rich if run locally) · CSV 4 · Accessibility 2 · Storytelling 4
