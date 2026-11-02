# the-aris-club/flare-chronos — code teardown (31 Oct 2026)

Team from Vietnam (README and PDFs partly in Vietnamese). Last push 23 Oct 2026. MIT licence. Read as text via `gh api` only; local copies of the files read are in `competitors/scratch/fc/`.

## 0. The fact that changes everything: the data is one 5-day window per year

`apps/benchmark-cli/src/benchmark_cli/fetch_real_firms.py` (L26-139) and `data/raw/` hold **one 5-day FIRMS area-API slice per year per AOI**. The two AOIs are hard-coded bboxes:
- Mekong: window starting 15 March.
- "Southern Amazon arc": window starting 20 August.

On top of that there are seasonal 5-day slices for **2024 only** and three 7-day open feeds. The "26-year x 73-pentad Burning Activity Calendar" therefore observes **one pentad per measured year**. Only 11 Mekong years and 9 Amazon years are measured at all (`data/processed/empirical_results.json` `regime_shift_series.*.measured_years`).

Everything else is **synthesised** in `run_experiments.py::build_26yr_calendars_and_series` (L712-887):
- the regional seasonal envelope,
- times an annual scale anchored on MODIS,
- times seeded Gaussian noise (`_CALENDAR_NOISE_SEED=202610`, SD 0.11, floor 0.72; L92-102),
- times a hand-set **`_EL_NINO_PEAK_AMPLITUDE = 1.85`** applied to the chosen years 2007, 2010, 2015, 2016 and 2024 (L110, L812-818),
- `_AMAZON_CLIMATOLOGY_BASELINE_FRACTION = 0.58` and `_TERRA_ONLY_CORRECTION = {2001: 1.92, 2002: 1.32}` (L104-117).

The team documents this in `docs/adr/0009-measured-epochs-and-interpolated-years.md` and `docs/adr/0010-sfai-baseline-from-measured-epochs-only.md`. ADR-0010 says: "only one pentad per measured year is observed". It also records that an earlier published Amazon 2024 index carried an unexplained x1.55 multiplier.

## 1. Harmonization as implemented

- **Direction:** MODIS -> VIIRS-equivalent. VIIRS 375 m is the reference and S-NPP is the FRP target (`packages/harmonization-core/src/flare_chronos_core/radiometric_calibrator.py` L1-9, L111-121).
- **Count harmonization** (what the calendar actually uses), in `apps/benchmark-cli/src/benchmark_cli/sensitivity.py` L28-48:
  - Detections from all sensors in a window are clustered into "Fire Episodes". Two detections join when they are within 60 minutes of the cluster seed and within `r_eff_i + r_eff_j + 0.65 km`, or share an H3 res-8 cell (`deduplication.py` L90-178).
  - Each episode contributes `combined_prob / Omega`.
  - MODIS-only epochs are multiplied by a per-region "sub-pixel omission factor" **k = 3.35 (Mekong) / 1.82 (Amazon)**. These are the median over train epochs <=2020 of the factor that makes `sensor_invariance_ratio = 1`.
  - Multi-sensor epochs are divided by `1 + 0.24*(n_VIIRS - 1)` (`STREAM_OVERLAP_GAIN`, hand-set).
  - **Omega(year, lat)** is a hand-set era ladder (0.52 / 0.76 / 1.00 / 1.48 / 1.78 / 1.92 / 2.08) times `1 + 0.18(sec(lat) - 1)` (`deduplication.py` L29-75). It is optionally scaled by the ERA5 clear-sky share relative to its regional norm (L78-87; `data/cloud/era5_cloud_cover.json`). `sensitivity.py` L1-9 states "None is fitted" for Omega and the overlap gain.
- **Scan-angle FRP operator** (`radiometric_calibrator.py`):
  - The detection limit is `FRP_lim = l0(SZA) * A^1.04` for MODIS and `l0 * (A/0.1406)^0.94` for VIIRS. The constants are hand-typed and attributed to "Sofiev & Kouznetsov 2026" without a DOI in the code (L46-67).
  - Stage 1 applies `FRP * (1 + kappa*ln A)`, with kappa grid-searched over 0.10-0.55. The fitted value is **0.10, the lower bound**, so the operator does almost nothing.
  - Stage 2 is the blend `w*alpha*FRP^beta + (1-w)*EQM(FRP)`, fitted on Aqua/S-NPP "co-incident" 0.05 deg x date x day/night cells (`run_experiments.py` L256-345). The per-detection "VIIRS-equivalent count" `2.85 or 3.40 * A^0.38` (L150-151) is hard-coded and is **never used** downstream. I grepped for `calibrated_viirs_eq_count`: it is only stored.
- **Geometry:** the MODIS bow-tie ΔS/ΔT formulas and their inversion, and the VIIRS 3-zone aggregation (`geometry_h3.py` L61-162). The elliptical footprint is spread across H3 res 7 and 8 with a 13-point stencil (L274-330). The **H3 fractional weights are computed and then never consumed** by the calendar or the experiments. The only reader is an AI tool that checks the weights sum to 1 (`apps/ai-service/src/ai_service/tools.py` L1035). The calendar works at **whole-AOI** level: HFD is episodes per 100 km² per day (`calendar_engine.py` L86-169).
- **Filters** (`confidence_filter.py`):
  - A logistic P(fire) for MODIS (`z = (conf - 38)/19 + 0.015*ΔT45` term). VIIRS l/n/h map to fixed anchors 0.28-0.94.
  - FIRMS type 1/2/3 are dropped, plus a persistent H3 res-8 registry (>=10 distinct months; it requires all 12 months covered, which only the 2024 slices provide).
  - The **SAA "cosmic-ray" filter** uses a box from 55S to 7N and 110W to 11E. That box **contains the whole Amazon AOI**, so night-time low-FRP detections there are rejected. The rejected share is **11-16% in the VIIRS epochs vs 3-4% in MODIS-only epochs** (`empirical_results.json` `amazon_empirical_epochs[].saa_rejected_share_pct`). That is a sensor-asymmetric removal of real small fires.
  - Day/night is redefined by SZA < 85°. It reclassified **0.0%** of detections in every epoch, so it has no effect.
- **NOAA-20/21:** pooled with S-NPP into episodes; there is no separate bridge. Omega is capped by the number of VIIRS streams present.
- **Terra/Aqua drift:** not modelled. The Omega ladder is flat for 2003-2011 and stays constant after that. An "orbital drift audit" AI tool just returns MODIS counts (`tools.py` L828-856). The FRP calibration assumes Aqua and S-NPP share the 13:30 overpass, which drift breaks after about 2022.
- **Training period:** FRP pairs <=2019 train and 2020-2026 test (`HOLDOUT_TRAIN_LAST_YEAR=2019`, `run_experiments.py` L74). The omission factor is trained on epochs <=2020 and tested on 2021+ (`FIT_TRAIN_LAST_YEAR`).

## 2. Validation and leakage

- **FRP calibration, temporal holdout** (`radiometric_calibrator.py::holdout_validation` L262-333). Group bootstrap by date and region gives a 95% CI on the RMSE gain. Published values (`empirical_results.json` `coincident_calibration.holdout`): n_train 5,331, n_test 6,222. The **raw RMSE is 154.2 MW and the harmonized RMSE 145.4 MW** (gain CI [6.6, 11.8] MW, i.e. about 6%). In-sample R² goes from 0.733 to 0.764. This is a small effect.
- **Leakage / selection on outcome:** the co-incident pairs are filtered **using the target** before the split. They keep only cells with `0.65*m_frp <= v_frp <= 4.2*m_frp` (`run_experiments.py` L330-335). This trims the hard cases on both sides, and the docstring concedes it (L279-282). The shipped model (`fit_coincident_aqua_snpp_model` on **all** pairs incl. 2020-2026, L345) produces the headline R² and KS figures, which are in-sample. The default model also carries hard-coded "validation" numbers (raw_r2 0.612, harmonized_r2 0.918, KS 0.384 -> 0.062) that are not measurements (`radiometric_calibrator.py` L70-92).
- **Count harmonization "sensor invariance":** the test compares the harmonized count from all sensors against the count from a MODIS-only view **of the same 5-day window** (`run_experiments.py` L536-552). Held-out results after the fit (`omission_factor_fit`): Mekong 2023-2026 gives 1.09 / 1.00 / 0.92 / 1.14 and Amazon 2024-2026 gives 0.85 / 0.91 / 0.86. That is 3 or 4 held-out points per region. The test tolerance was loosened to ±0.20 (`tests/test_effort_constant_fit.py` `HELD_OUT_TOLERANCE`). The check is valid in spirit (it is the "pretend MODIS is gone" idea), but n is tiny and the window is one week per year.
- **SFAI** (robust z-score, median and blended MAD/SD) is computed on observed cells only. A pentad needs at least 8 measured years (`calendar_engine.py` L22-50). The only observed cell at or above +2.2σ is Mekong 2007 (+2.9) (ADR-0010).
- **No metric of a harmonized series against independent truth** (burned area or similar).
- **The AI tools return literals.** Examples: `"mekong_max_harmonized_index": 297.8`, `"amazon_2024_saa_rejected_count": 18097` and magic constants 2.18 and 1.24 in the "retirement simulation" (`tools.py` L736-803). These are defaults that can drift from the data.

## 3. Uncertainty and calibration

The only interval is the bootstrap 95% CI on the FRP RMSE gain. **There are no prediction intervals on any count, calendar cell or anomaly, and no coverage check.** P(fire) is a heuristic, not calibrated against anything. Scores: uncertainty 1, calibration 1.

## 4. Web app / deployment

- **There is no fire-calendar web app.** The README promises "DuckDB/Parquet cube + REST API + Deck.gl UI", but no frontend exists in the tree (262 files; no JS or TS app). The only UI is `apps/ai-service/src/ai_service/demo/index.html` (10 KB): a FastAPI page showing a LangGraph "Dual-Cognitive Harness" run, with classification, tool calls, a reasoning trace, numeric verification and Approve/Decline buttons (`api.py`, `serve.py`). It is served at 127.0.0.1:8765, with JWT bearer auth (`AI_SERVICE_JWT_KEY`, HS256 by default; `api.py` L29-113) or `AI_SERVICE_AUTH=disabled`, which is loopback only.
- **No hosted deployment:** the GitHub repo has `homepage: null`, `has_pages: false`, 0 deployments and 0 environments. There is no Dockerfile or Railway/Vercel/Fly config in the tree. Workflows are CI, release and version bump only. I found no live URL, so a judge sees only the README and the PDFs.
- **Area selection:** none. There are two hard-coded bboxes (`firms_ingestion.BBOX_MEKONG` / `BBOX_AMAZON`).
- **CSV:** none produced for users. Outputs are JSON (`data/processed/burning_calendar.json`, `empirical_results.json`) and static matplotlib figures (`docs/figures/fig1-5`). The raw FIRMS CSVs are committed with SHA256 pins (`data/raw/SHA256SUMS`, `tests/test_raw_data_integrity.py`).
- **Accessibility:** not applicable or minimal. The demo page has basic buttons and no ARIA (grep of `demo/index.html`).

## 5. Weaknesses a judge would notice

1. The calendar is mostly modelled noise plus hand-set El Niño multipliers. Only 1 of 73 pentads per measured year is observed, and 15 of 26 Mekong years and 17 of 26 Amazon years are interpolated. A judge who opens the ADRs will see this.
2. The SAA box covers the whole Amazon AOI and deletes 11-16% of VIIRS detections there.
3. The "physics" layers (H3 fractional allocation, VIIRS-equivalent count, SZA day/night) are computed but unused or have no effect. The scan-tail kappa sits at its lower bound.
4. Omega and the overlap gain are hand-set. The FRP calibration gain is about 6%.
5. There is no app, no map, no area selection, no CSV, no uncertainty, and no deployment. Effort went into an LLM agent harness with 20 use cases and JWT, which the challenge does not ask for.
6. The jargon is heavy (HFD/HRF/SFAI, "Dual-System Cognitive AI Harness").

## 6. Best idea to borrow

**The same-window MODIS-only vs all-sensor "sensor-invariance ratio"** (`run_experiments.py` L536-552, `sensitivity.py`). Re-score each multi-sensor period using only its MODIS subset and require the harmonized ratio to be about 1, with the factor fitted on early years and scored on later ones. It is a cheap, intuitive "retire MODIS" test that judges understand. A second idea worth borrowing is **seed-anchored overpass-train de-duplication** (60-minute window, footprint-radius distance). It gives a principled answer to NOAA-20/21/S-NPP double counting if we ever count "fire episodes". Both ideas are MIT-licensed, so credit them if used.

## Scores (1-5)

Scientific validity 1 · Uncertainty 1 · Calibration evidence 1 · Coverage (regions) 2 (2 fixed AOIs, 5-day windows) · App UX 1 · CSV 1 · Accessibility 1 · Storytelling 2 (polished PDFs and ADRs, but the narrative oversells and the 26-year claim collapses on reading)
