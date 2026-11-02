# Research archive

Everything we researched before and during the build, 23 Oct – 2 Nov 2026. For **what we decided and why**, read
the plans and results in `docs/` (they take precedence). This folder is the evidence behind them.

**Team booklet:** [../team/CEDRUS_Team_Update_v3.pdf](../team/CEDRUS_Team_Update_v3.pdf) (2 Nov, current) ·
[../team/CEDRUS_Strategy_and_Algorithm_v2.pdf](../team/CEDRUS_Strategy_and_Algorithm_v2.pdf) (31 Oct, superseded: it
predates the exams).

## The decision trail (in docs/)
| Step | Plan (written first) | Result |
|---|---|---|
| First test (Portugal) | [TEST_PLAN.md](../TEST_PLAN.md) | [RESULTS.md](../RESULTS.md) |
| Bake-off | [BAKEOFF_PLAN.md](../BAKEOFF_PLAN.md) | [BAKEOFF_RESULTS.md](../BAKEOFF_RESULTS.md): simple ratio A beat the detection-physics model B |
| Exam 1 | [CONFIRMATION_PLAN.md](../CONFIRMATION_PLAN.md) | [CONFIRMATION_RESULTS.md](../CONFIRMATION_RESULTS.md): **NOT CONFIRMED** |
| Round 2 + exam 2 | [ROUND2_PLAN.md](../ROUND2_PLAN.md) | [ROUND2_SELECTION.md](../ROUND2_SELECTION.md), [ROUND2_CONFIRMATION.md](../ROUND2_CONFIRMATION.md): **CONFIRMED** (hotspots, A2) |
| Tournament + exam 3 | [TOURNAMENT_PLAN.md](../TOURNAMENT_PLAN.md) | [TOURNAMENT_RESULTS.md](../TOURNAMENT_RESULTS.md), [ROUND3_CONFIRMATION.md](../ROUND3_CONFIRMATION.md): **CONFIRMED** (burning days, D-a) |

## This folder
| Path | What it is |
|---|---|
| `STRATEGY_v2_2026-10-31.md`, `ALGORITHM_v2_2026-10-31.md` | The strategy and algorithm drafts after the first adversarial review. **Superseded** by the exams: the learned-detection model they favoured lost the bake-off. |
| `context.md` | The shared brief every research agent was given |
| `codex/` | Three Codex (gpt-6-astra, web search) reports with their prompts: statistics (`out_codex_stats.md`), data and web stack (`out_codex_data.md`), red team (`out_codex_redteam.md`) |
| `competitors/` | Code-level teardown of the 8 strongest public repos (one file each), `SYNTHESIS.md` (head-to-head table), `sweep.tsv` (repo search). Notes only: their code is not copied here. |
| `physics/` | Scripts and outputs that tested the Sofiev & Kouznetsov (2026) detection-limit operator on Portugal, 2012–2019 only |
| `frontier/` | The frontier-methods scan: capture–recapture (rejected), the matched-pass detection curve, triple collocation; `NOTES.md` plus scripts and outputs |
| `judging/NOTES.md` | How Space Apps judging and awards work (2025 guides) and what past winners did |
| `review/` | The adversarial review of the v1 strategy and algorithm (it found 4 critical problems) |

## Key findings from reports that live only in this summary
- **Literature (first round):** the core references are Giglio et al. 2016 (MODIS C6), Schroeder et al. 2014 (VIIRS 375 m), Fu et al. 2020 (matched MODIS/VIIRS passes), Giglio et al. 2006 (fire seasonality), Sofiev & Kouznetsov 2026 (detection limits), and Chen et al. 2026 (GFED5NRT, which calibrates VIIRS per land cover and averages the two VIIRS satellites). No peer-reviewed harmonized MODIS+VIIRS hotspot-count series covering 2000 to the present was found.
- **Existing tools:**
  - None of FIRMS, GWIS, EFFIS or Global Forest Watch publishes a harmonized MODIS+VIIRS calendar for a user-drawn area.
  - INPE (Brazil) keeps a single "reference satellite" instead.
  - Lebanon: burning near forests is banned from 1 Jul to 31 Oct, and the University of Balamand FireLab issues daily fire-danger forecasts.
  - We found no published Lebanese fire calendar, but competitor apps and GWIS country profiles do cover Lebanon.
- **Challenge video (CONAE, Argentina; 28 Oct 2026):**
  - The authors want a burning-activity calendar for early warning, with the sensor of origin no longer mattering.
  - Their example is a July 2026 fire in Chilecito, La Rioja.
  - Resources publish on 13 Nov.
  - Submissions must describe AI use and cite every source.
- **Judging:**
  - Five criteria: Impact, Creativity, Validity (which includes usability), Relevance and Presentation.
  - The written project page counts most.
  - The demo is a video of 30 seconds or less **or** at most 7 slides.
  - Best fits for us: Best Use of Science, Best Use of Data, Local Impact.
