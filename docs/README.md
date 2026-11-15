# Documentation index

Every document in `docs/`, what it is for, and whether it describes the current state or is kept as a record.

Two kinds of document matter most here:

- **Plans** were written *before* their test ran, and the git history shows it. They are never rewritten; a later
  change goes in a dated section at the end. That is what makes their results believable.
- **Generated results** are written by the script named at their top. Don't edit them by hand; re-run the script.

Labels below: **current** = describes the product as it is now; **record** = kept as written, may be out of date;
**generated** = rewritten only by its script.

## Start here

| Question | Read |
|---|---|
| What is the product and how do I run it? | [../README.md](../README.md) |
| What do the website's data files contain, and where does each region's record end? | [DATA_CONTRACT.md](DATA_CONTRACT.md) |
| Which regions are in scope, and what are the known limitations? | [TIER1_PLAN.md](TIER1_PLAN.md), top sections |
| What changed most recently, and did the tests pass? | [TIER1_IMPLEMENTATION_STATUS.md](TIER1_IMPLEMENTATION_STATUS.md), newest first |
| How was January–July 2026 added and tested? | [OBS2026_VALIDATION_PLAN.md](OBS2026_VALIDATION_PLAN.md), final state at the top |
| Why should anyone trust the harmonized numbers? | The decision trail below, in order |

## The decision trail: how the models were chosen

Each step's plan was committed before its code or data existed. Read them in this order.

| # | Step | Plan (written first) | Result | Outcome |
|---|---|---|---|---|
| 1 | First test, Portugal | [TEST_PLAN.md](TEST_PLAN.md) | [RESULTS.md](RESULTS.md) (generated) | Passed, but for an earlier method (a ratio per cell). Kept as a record, not the evidence for the current models. |
| 2 | Bake-off | [BAKEOFF_PLAN.md](BAKEOFF_PLAN.md) | [BAKEOFF_RESULTS.md](BAKEOFF_RESULTS.md) (generated) | The simple shrinkage ratio A beat the detection-physics model B. |
| 3 | Exam 1 | [CONFIRMATION_PLAN.md](CONFIRMATION_PLAN.md) | [CONFIRMATION_RESULTS.md](CONFIRMATION_RESULTS.md) (generated) | **Not confirmed:** A failed on the four sealed regions. |
| 4 | Round 2 and exam 2 | [ROUND2_PLAN.md](ROUND2_PLAN.md) | [ROUND2_SELECTION.md](ROUND2_SELECTION.md), [ROUND2_CONFIRMATION.md](ROUND2_CONFIRMATION.md) (both generated) | **Confirmed:** A2 + NOAA-20 via Suomi NPP. Runs the **hotspot** view. |
| 5 | Tournament and exam 3 | [TOURNAMENT_PLAN.md](TOURNAMENT_PLAN.md) | [TOURNAMENT_RESULTS.md](TOURNAMENT_RESULTS.md), [ROUND3_CONFIRMATION.md](ROUND3_CONFIRMATION.md) (both generated) | **Confirmed:** D-a. Runs the **burning-day** view, the default. |

The code for steps 2–5 is in `pipeline/bakeoff/`, `pipeline/confirm/`, `pipeline/round2/`, `pipeline/tournament/`
and `pipeline/round3/`; each folder's `README.md` says how to re-run it.

## Product build and 2026 data

| File | What it is | Label |
|---|---|---|
| [DATA_CONTRACT.md](DATA_CONTRACT.md) | Layout of every file in `web/data/`, each region's record range, the source policy per month, map states and the reconciliation bounds. | current |
| [TIER1_PLAN.md](TIER1_PLAN.md) | The hackathon build: current scope (18 regions since 14 November 2026), deferred items, completed work and remaining limitations at the top; the original plan below it, superseded. | current (top), record (below) |
| [TIER1_IMPLEMENTATION_STATUS.md](TIER1_IMPLEMENTATION_STATUS.md) | Change log, newest first: what changed, test results, and every changed test expectation. | current |
| [TIER1_AUDIT_CHECKPOINT.md](TIER1_AUDIT_CHECKPOINT.md) | The three audits of 6 November 2026: the type-filter impact on Portugal and Lebanon, FIRMS availability and missing-data services, and the 2000–2017 source audit. | record |
| [OBS2026_VALIDATION_PLAN.md](OBS2026_VALIDATION_PLAN.md) | Plan and results for adding 2026: country clipping, the static-source mask, and the three Lebanon boundary tests. Earlier sections keep their original results. | current (top and last section) |
| [ROADMAP.md](ROADMAP.md) | The early step-by-step plan. Its checkboxes and commands are historical. | record |

## Folders

| Folder | What it holds |
|---|---|
| [research/](research/README.md) | Research archive, 23 October – 2 November 2026: literature, competitor teardowns, the adversarial review, judging notes. It has its own index. The plans and results above take precedence over it. |
| [tasks/](tasks/) | Task briefs: [RIFAAT_REGIONS_AND_DRIFT.md](tasks/RIFAAT_REGIONS_AND_DRIFT.md) (more regions, MODIS drift numbers, NOAA-21), and for the data analyst: [ANALYST_LEBANON.md](tasks/ANALYST_LEBANON.md) (Lebanon's fire history and how far a small area can be trusted) and [ANALYST_REALITY_CHECK.md](tasks/ANALYST_REALITY_CHECK.md) (does the calendar match known fires; checked by `tools/check_reality.py`). |
| [team/](team/) | Team booklets: `CEDRUS_Team_Update_v3.pdf` (2 November, current) and `CEDRUS_Strategy_and_Algorithm_v2.pdf` (31 October, superseded); `source/` holds what they were built from. |
| [design/](design/) | Design reference, desktop and mobile previews, and `Fire_Made_Visible.pdf`. |
| [submission/](submission/) | Space Apps submission drafts: [PROJECT_PAGE.md](submission/PROJECT_PAGE.md) (every project-page field), [VIDEO_30S.md](submission/VIDEO_30S.md) (30-second demo script) and [SLIDES_7.md](submission/SLIDES_7.md) (7-slide outline). |

## Evidence outside `docs/`

| Folder | What it holds |
|---|---|
| `analysis/obs2026/` | The reports behind the 2026 plan: `REPORT.md` (processing validation) and the three Lebanon reports (`REPORT_lebanon_border.md`, `REPORT_lebanon_boundaries.md`, `REPORT_lebanon_ne_versions.md`), with their scripts and results. |
| `analysis/tier1/` | Per-region forward tests (`region_evidence/README.md`), the known-event check (`events/REPORT.md`), the La Rioja diagnostic (`la_rioja_evidence/REPORT.md`) and the FIRMS coverage snapshots (`coverage_services/`). |
| `analysis/range_coverage/` | The test that found the 80% ranges too narrow (13 November 2026): `REPORT.md`, `results.json` and the script that writes them, `run_test.py`. |
| `analysis/reality/` | Reference fire lists for the reality check (`known_fires.csv`, `official_yearly.csv`). |

## Research chronology

See [`archive/original-history`](https://github.com/RifaatRamadan0/cedrus/tree/archive/original-history) for dated test plans, model settings, and evaluation results through 10 November 2026 (`4e33960`). Later validation reports are included on `main`; their original commit chronology is outside this archive.

| Step | Commit | Date |
|---|---|---|
| Test plan for the first (MODIS retirement) test | [`5ba030e`](https://github.com/RifaatRamadan0/cedrus/commit/5ba030efbb79eb0a8787c9cabec9cab2648aa297) | 23 Oct 2026 |
| Exam 1 plan, before its sealed regions were downloaded | [`0cdcdd6`](https://github.com/RifaatRamadan0/cedrus/commit/0cdcdd675b2595978bf0ca50a1f435ca86970a84) | 31 Oct 21:33 |
| Exam 1 result: NOT CONFIRMED, published as run | [`b31a114`](https://github.com/RifaatRamadan0/cedrus/commit/b31a11480d7fa994ee15f4f1b9f9650242f95d60) | 1 Nov 12:34 |
| Round 2 plan | [`e7763f7`](https://github.com/RifaatRamadan0/cedrus/commit/e7763f70ee337a7822c7a52eaa3d966db2225f4b) | 1 Nov 12:39 |
| Round 2 model settings frozen | [`617daff`](https://github.com/RifaatRamadan0/cedrus/commit/617daff1e6f0ec185b4bd613f35f69fdab6b9876) | 1 Nov 13:19 |
| Tournament plan, before the round-2 result | [`fa2c956`](https://github.com/RifaatRamadan0/cedrus/commit/fa2c956ec655ca382dd1c43f23362ccf23ee99ec) | 1 Nov 15:09 |
| Exam 2 result: CONFIRMED | [`b066e04`](https://github.com/RifaatRamadan0/cedrus/commit/b066e046720a53c77967933da785dae6a1b52c46) | 1 Nov 15:10 |
| Tournament result | [`af757f9`](https://github.com/RifaatRamadan0/cedrus/commit/af757f9fd55650834747606e96594950f357d57d) | 1 Nov 17:14 |
| Round 3 model settings frozen | [`80e297f`](https://github.com/RifaatRamadan0/cedrus/commit/80e297f98aaae0fa4c3785f05a1572e0ab4fd288) | 1 Nov 17:26 |
| Exam 3 result: CONFIRMED | [`f986257`](https://github.com/RifaatRamadan0/cedrus/commit/f986257e156be9c13e926104b9cb944eea0e36c1) | 2 Nov 11:16 |
| Archive tip: per-region test results | [`4e33960`](https://github.com/RifaatRamadan0/cedrus/commit/4e3396040c4f23625df2c1eb85bf6a78fbf3e6d3) | 10 Nov 20:27 |

Commit dates alone do not prove that no earlier fitting happened; each plan says what it was written before, and the frozen settings are checked by SHA-256 when the exporter runs.

## Adding a document

Add a line for it here. `tools/probe_site.py` fails if a Markdown file or folder in `docs/` is missing from this
index, or if a link here points to a file that does not exist.
