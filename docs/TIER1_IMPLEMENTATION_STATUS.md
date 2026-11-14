# The 80% ranges are too narrow: wording only — 13 November 2026

- **Finding.** With 2020–2021 estimated exactly as 2022 onward is (the exporter run into a scratch folder with the
  observed era ended at 2019-12), the ranges held the observed MODIS value in 31 of 77 whole-region months in burning
  days (40%) and 27 of 80 in hotspots (34%), and in 34–74% of area-months with an estimate of 3 or more for single cells, blocks of cells
  and circles. Figures and causes: [DATA_CONTRACT.md](DATA_CONTRACT.md), `p10`/`p90`. The estimates are not affected.
- **Changed, wording only.** One shared note (`pipeline/regions.py`, refreshed with
  `python pipeline/export_v2.py --catalog-only`); in `web/app.js` the range label of estimated months ("often too
  narrow"), the chance hint, the trust-check text, one methodology sentence, one limit and the monthly CSV's methods
  line; one sentence in the README.
- **Not changed.** No value, range, verdict threshold, export or model. The correction itself (dispersion and
  dependence estimated on 2012–2019, frozen, then tested once) is future work.
- **Checks after the change:** `tools/probe_site.py` 432/432; `tools/check_history_unchanged.py` passes for all four
  regions; `tools/check_tier1_preservation.py` passes; `python -m unittest tools.test_tier1_preflight` 4/4. No test
  expectation was changed.
- **Evidence:** `python analysis/range_coverage/run_test.py` writes
  [REPORT.md](../analysis/range_coverage/REPORT.md) and `results.json`. It runs the exporter into a scratch folder and
  never writes `web/data/`. The test was not pre-registered: it was run after a review found the ranges too narrow.

# Documentation index — 12 November 2026

- New [docs/README.md](README.md): every document in `docs/`, what it is for, whether it is current, a record or
  generated, and the order the model tests ran in. The main README links to it in place of its partial list.
- Docs brought up to the final state: all four regions run to July 2026 (README, data contract examples and drift
  line, a final-state note at the top of the 2026 plan).
- **New check** (`tools/probe_site.py`): the index must list every Markdown file and folder in `docs/`, every link
  in it must resolve, and the README must link to it. Probe 432/432.

# Lebanon 2026 and map messages — 12 November 2026 (commits 75bb66c and 53112e2)

- **Lebanon January–July 2026** added, assigned with the Natural Earth 1:10m outline of commit `be165336bb`
  (30 August 2021), which passed the older-version test (0 mismatches in 2000–2022; 9 of 9 independent checks in
  2023–2025). Only Lebanon's 2026 clipping uses it. One Suomi NPP detection fell outside the historical grid and is
  left out. Every 2000–2025 value and both frozen models are unchanged. Details:
  [OBS2026_VALIDATION_PLAN.md](OBS2026_VALIDATION_PLAN.md), outcome of 12 November 2026.
- **Map messages** (`inspectMapPoint` in `web/app.js`): a positive cell value no longer repeats the generic
  completeness warning; a value that rounds to zero (under 0.05) says it does not confirm the area was fire-free; a
  cell with no records, or a month with no VIIRS satellite, says observations are unavailable. The map now draws a
  cell as faint at the same 0.05 limit (it was 0.005), so the drawing and the message agree. Missing-data dates are
  named only from FIRMS's own list (`web/data/firms_missing_dates.json`), for satellites the month's value uses, and
  are worded as FIRMS-reported dates, not outages verified independently; Suomi NPP 1–31 May 2026 is listed by FIRMS but contradicted by the standard files and gives no
  warning. The legend's general completeness limitation is unchanged.
- **Checks, after both changes:** `tools/probe_site.py` 431/431
  ([log](../analysis/obs2026/probe_lebanon2026_map_messages.log)); `tools/check_history_unchanged.py` passes for all
  four regions; `tools/check_tier1_preservation.py` passes; `python -m unittest tools.test_tier1_preflight` 4/4.
- **Changed test expectations** (reported): preservation lets Lebanon's four whole-record files and two
  zero-weight totals grow, as Portugal's do; the probe drops off-grid detections as the exporter does (and checks
  they equal `detections_outside_grid`); the "Lebanon example" month and the methodology's zero-weight line are
  computed from the data instead of the hard-coded October 2025 and "850 of 4,142"; the mouse-drawn rectangle
  scrolls its corners into view first (the second corner was 13 px below the viewport, so the click never reached
  the map); the absent-cell map check expects "no fire observations … available" instead of the generic warning.
  New checks: positive cells carry no generic warning, faint cells are exactly the values under 0.05 (a 0.005-0.05
  cell is faint and called near-zero), a FIRMS-listed date is named as FIRMS-reported, a contradicted one is not,
  and a simulated no-VIIRS month says observations are unavailable.

# 2026 observations — 11 November 2026 (uncommitted)

January–July 2026 added for Portugal, Syria and La Rioja from FIRMS standard area data, assigned to each country
with Natural Earth outlines. Lebanon stays at 2025 (its southern border failed the assignment test, and a border
correction failed its own test); near-real-time data is not used (the static-source mask failed). Every 2000–2025
value is unchanged (`tools/check_history_unchanged.py`); frozen models unchanged. Plan, thresholds, results and
outcome: [OBS2026_VALIDATION_PLAN.md](OBS2026_VALIDATION_PLAN.md).

# Per-region accuracy evidence and Jordan/Cyprus removal — 10 November 2026 (uncommitted)

Only La Rioja had a 2020–2021 test on its own data, and only La Rioja said that 2022–2025 is not checked against
MODIS, although that limit applies to every region. Changes:

- **Forward tests** for Portugal, Lebanon, Syria, Jordan and Cyprus with the frozen models and La Rioja's
  protocol and pass rules, nothing tuned: [summary](../analysis/tier1/region_evidence/README.md). Portugal and
  Syria (burning days) pass. Lebanon, Jordan and Cyprus fail the ±10% total rule while beating the simple
  conversion; Syria hotspots fail the region-month rule.
- **Notes**: a shared note on every region about the 2022–2025 limit; a result note for Syria; the
  now-duplicated sentence was removed from La Rioja's note.
- **Lebanon and Syria limitations** (user request): Lebanon now shows its forward-test result, and both show the
  shared border cells (11 of Lebanon's 28, holding 23% of its estimated values). Syria's note also names the
  excluded outage months. New `export_v2.py --catalog-only` rewrites `regions.json` notes without exporting any
  region, so Lebanon's data was not regenerated. **Changed check:** `check_tier1_preservation.py` now ignores
  `notes` when comparing the Portugal/Lebanon entries and instead requires them to equal `regions.py`; a test
  edit of Lebanon's `name` was still caught.
- **Jordan and Cyprus removed from the app** (user decision): too few fires to measure and grid-cell errors of
  about 163% and 100%. The rule was chosen after the results and is stated as such in the
  [summary](../analysis/tier1/region_evidence/README.md#jordan-and-cyprus-removed-from-the-app). They keep the
  `dev` role, raw files, audits and reports; `web/data/cyprus/` and `web/data/jordan/` were deleted. The exporter
  now leaves non-product regions out of the catalog instead of copying old entries forward.
- **Portugal's result** is shown with its limits: it met every pass rule, which is evidence for regional-level
  performance in 2020–2021, not for years after 2021 or single cells (78–80% error). A Spain border-cell note was
  left out because it could not be verified without country outlines.
- **Exporter fix** (`pipeline/export_v2.py`): the catalog and manifests were read without an encoding, so
  Windows used cp1256 and corrupted the "·" in the Portugal and Lebanon badges when they were copied across.
  Reads are now UTF-8, and the catalog is written in the committed format (indent 2, UTF-8 text, LF).
- Re-exported Syria and La Rioja (and, before the removal, Cyprus and Jordan): every data file is byte-identical; `regions.json` changes
  only in notes and timestamps. Preservation check passed.
- Probe: one new check per region and unit that the accuracy notes are shown. Full probe passed 476/476 with six
  regions ([log](../analysis/tier1/probe_accuracy_notes.log)). After the removal: the catalog check expects the
  four regions by ID; Amman and Nicosia became outside-coverage checks; a western-Iraq circle inside Syria's box
  now tests the "No fire records from Syria" refusal. Full probe passed 402/402 in 337 s
  ([log](../analysis/tier1/probe_region_removal.log)). After the Lebanon and Syria notes: 406/406 in 350 s ([log](../analysis/tier1/probe_lebanon_syria_notes.log)). After Portugal's note: **408/408 in 313 s** ([log](../analysis/tier1/probe_portugal_note.log)). Preservation check passed.

# Map clarity follow-up — 7 November 2026 (committed)

Implemented user-approved clarification across all six product regions and both units:

- Label the orange dashed line as analysis extent, not a national boundary; label drawn areas separately.
- Give included near-zero cells a faint outline and shade cells absent from the exported grid with dashed edges. The latter are display-only features clipped to the box; they do not add observations or model cells.
- Explain that blank areas are not confirmed fire-free and observation completeness is unknown.
- Map clicks explain grid inclusion, selected-month estimate where available, missing-record status, and the possibility of land outside the country inside the box. Clear stale inspection text/popups when month, area or region changes.

**Full probe passed 468/468 in 346 seconds, round 1**, including 108 new map-clarity checks across six regions/two units, existing region/city/creative checks and final console-error check. Syria screenshot reviewed. [Log](../analysis/tier1/probe_map_clarity_round1.log), [summary](../analysis/tier1/map_clarity_summary.json). Preservation checker passed. No export or model changes. User approved committing this follow-up on 7 November 2026; nothing was pushed. The obsolete commit-groups Markdown document was deleted at the user’s request.

Changed implementation: `web/app.js`, `web/index.html`, `web/styles.css`; tests: `tools/probe_tier1.py`; evidence: the linked log/summary and this status file. The six original Tier 1 commits below remain intact.

---

## Historical commit checkpoint — 7 November 2026

User approved committing all six reviewed groups. Changes are committed on `add-tier1-regions`; nothing was pushed. See the [historical six-group manifest](../analysis/tier1/commit_groups.json); it records the original commits, including the Markdown manifest later deleted by `11bb436`. All 317 reviewed files passed the exclusion and local-credential scan before staging. Raw archives, deferred web exports, `.env`, `.claude/` and frozen-model files are excluded. Preservation verification still passes; the full probe at that checkpoint passed 360/360; the latest result above is 468/468. Earlier “uncommitted” statements below describe their historical checkpoints.

---

## Historical pre-commit checkpoint — 6 November 2026

**Full probe passed: 360/360 checks, 0 failures, 235 seconds, round 1 of at most 3.** Stopped the run/fix cycle at this pass as requested. No commits or pushes.

The full catalog, all region/unit round trips, Beirut/Damascus/Homs/Amman/Nicosia in both units, Tel Aviv/Mediterranean outside-coverage checks in both units, and the final console-error check completed successfully. All four new regions passed both-unit calendar, notes, CSV reconciliation and whole-region creative checks. La Rioja Aug–Feb sums passed. [Complete log](../analysis/tier1/probe_batch_round1.log), [machine-readable result](../analysis/tier1/probe_batch_summary.json).

The skip-link check passed unchanged this round. Its earlier failure remains recorded below; no timing workaround was introduced, and no claim is made that its intermittent behavior has been diagnosed. No checks were removed or skipped and no expectations, wording assertions or numerical tolerances changed in this run mode.

## Fixes and reasons

- Restored aggregate failure collection in the probe so one failed assertion no longer stops later checks; this was the only code change in the final run-mode round.
- Added an explicit UTF-8 preservation checker to avoid false catalog differences from Windows default decoding.
- Rebased selected/focused months by YYYY-MM before new-calendar reads, preventing stale-index map/ramp errors after region/unit changes.
- Mapped cross-unit series comparisons by date instead of assuming identical array offsets.
- Limited region-month preservation to manual switches for the same area; examples, first load and new drawings retain baseline default-month behavior.
- Corrected the authorized CSV, methodology and README text expectations to the serialization formula; numerical tolerances remain unchanged.
- Added latitude/longitude/radius metadata to the Tel Aviv test so it calls the circle entry point as the app does.
- Rejected zero-footprint candidates in region selection so box overlap alone cannot select a region; the >10% warning rule is unchanged.
- Added the Mediterranean outside-coverage check in both units to cover a second uncovered location.

Remaining failing checks: **none**. Scope remains four new product regions; Israel/Palestine remain Deferred. Previous audits, raw archives and deferred exports are preserved locally.

Final [preservation verification](../analysis/tier1/scope_revision_preservation.json) passed: all 108 Portugal/Lebanon data files, their catalog entries, and both frozen models are unchanged. `.env` is ignored. The data inventory remains 222 new region files plus catalog (42,451,808 bytes); only Syria hotspots 2019 exceeds 3 MB (3,548,856 bytes).

## Historical proposed commit grouping (subsequently committed)

[Exact per-group file manifest and diff summary](../analysis/tier1/commit_groups.json). Raw archives, `data/raw/deferred_web_exports`, `.env`, `.claude/`, generated browser screenshots/downloads and frozen-model files are excluded. The original user-supplied plan outside the repo has also been updated, but cannot be part of a commit in this repository.

---

## Historical checkpoints and wording inventory (superseded by the result above)

# Latest checkpoint — zero-footprint fix, 6 November 2026

Implemented the requested fixes: `regionForRing()` returns no region when the highest current-unit footprint share is zero, using the existing outside-coverage path. The >10% overlap-warning rule is unchanged. Tel Aviv now supplies latitude, longitude and radius metadata to the circle entry point, preserving its outside-message expectation. Added the same 5 km outside-message check at Mediterranean coordinates (33.5, 33.5), in both units.

**Stopped on a new probe failure after 214 passing checks.** The existing skip-link assertion at `tools/probe_site.py:1066` found the first focused element had class `skip-link`, but after Enter the active element's ID was empty instead of `calendar-panel`. Cause is not established. No assertion was changed, no fix was attempted and no rerun was made after this failure.

The Tel Aviv/Mediterranean checks, full-catalog round trips and final console-error assertion were not reached in this run. The new fixes therefore remain unverified by a completed full probe. [Log](../analysis/tier1/probe_zero_footprint_fix.log), [summary](../analysis/tier1/probe_zero_footprint_fix_summary.json). `git diff --check` passed before the run. No commits or pushes.

---

## Previous checkpoint and wording inventory (historical)

# Tier 1 implementation status — rounding-wording audit, 6 November 2026

The remaining wording assertions now match the app and README exactly. No numerical tolerance or other assertion condition changed. In particular, the existing Portugal/Lebanon `gap.max() <= 0.1` numerical regression check remains unchanged; only its misleading label and docstring were corrected. The full probe rerun exited 1 after **323 passing checks**, on a non-wording exception in the first Tel Aviv check. All four new regions passed their both-unit calendar/notes/CSV/creative checks; the five prescribed cities passed in both units. `tools/probe_tier1.py:134` calls `useRing(ring, 'circle')` without latitude/longitude/radius metadata. The area is accepted and `areaName()` then calls `toFixed` on undefined latitude. Read-only footprint calculation shows Jordan is a bounding-box candidate with **zero footprint share in both units**; `regionForRing()` currently selects its top candidate even at zero share. Both the missing circle metadata and zero-share acceptance need attention; neither was changed after this failure.

Stopped as instructed. Full-catalog region-switch round trips and the final console-error assertion were not reached. [Probe log](../analysis/tier1/probe_rounding_wording_final.log), [summary and read-only footprint scores](../analysis/tier1/probe_rounding_wording_final_summary.json). No commits or pushes.

## All old-bound text matches before this edit

Line numbers below refer to the files before this update. Old phrases quoted here are historical records of the intentional change, not current guarantees.

- `tools/probe_site.py:455` — `"""Whole region: the sum of its cells equals the exact sum of the records' weights + background within 0.1 per month."""`
- `tools/probe_site.py:466` — `check(f"{region} {folder}: whole-region month = exact sum within 0.1 (as the site says)", gap.max() <= 0.1,`
- `tools/probe_site.py:1085` — `and "equals the exact sum within rounding (≤ 0.1 per month)" in dlg and "Drawn shapes and circles are exact sums" in dlg`
- `tools/probe_site.py:1095` — `and "whole-region totals equal the\nexact sum within rounding (≤ 0.1 per month)" in readme.replace("\r\n", "\n")`
- `docs/DATA_CONTRACT.md:9` — `Region and unit switches rebase selected months by YYYY-MM before reading the new calendar; see [implementation status](TIER1_IMPLEMENTATION_STATUS.md). Combined-country aggregation and boundary assets are Deferred. Per-record and background rounding can accumulate above 0.1/month (observed Syria hotspots: 0.1235); reconciliation uses the explicit serialized-value rounding bound. The exact test bound is given below.`
- `docs/DATA_CONTRACT.md:210` — `Syria hotspots reached a 0.1235 monthly discrepancy; 0.1/month is not a universal bound.`
- `docs/TIER1_IMPLEMENTATION_STATUS.md:7` — `Added two probe checks after the January selection: manual switch to Portugal retains January 2025; opening the Lebanon example then selects October 2025. The original default-month assertion and all numerical tolerances are unchanged. Full rerun: **216 passing checks, then one failure**. Both new checks passed, and the unchanged original Lebanon-default assertion also passed (October 2025). The probe then failed the methodology-dialog composite assertion, which still requires equals the exact sum within rounding (≤ 0.1 per month). The app uses the requested formula wording instead; that required substring is absent. This is a separate remaining wording assertion from the previously authorized CSV-only change.`
- `docs/TIER1_IMPLEMENTATION_STATUS.md:17` — `- Old expected text: equal to the exact sum within rounding; ≤0.1/month`
- `docs/TIER1_IMPLEMENTATION_STATUS.md:30` — `Ran tools/probe_site.py. It exited 1 after **158 passing checks and one failure**: Portugal whole region 2000-2025: methods line wording. The legacy assertion at tools/probe_site.py:160 still requires the literal ≤0.1/month, whereas the app's CSV now gives the requested bound 0.005 × cells + 0.00005 × monthly records + 0.0001. This is a wording assertion failure, not a numerical mismatch. No tolerance or assertion was changed after the failure, and no rerun was attempted.`
- `docs/TIER1_IMPLEMENTATION_STATUS.md:108` — `Monthly whole-region totals reconcile against serialized records and background within the independently specified rounding bound. Syria hotspots reached a 0.1235 monthly discrepancy, so existing blanket “≤0.1/month” wording elsewhere needs correction. No expectation was relaxed after this result. The final full probe and console-error check remain outstanding.`

No old-bound statement remained in `web/` or README: their text had already been updated. Data-contract matches were explanations rejecting the old bound; they now state the formula directly. Previous status matches described earlier failures; this current status replaces those stale checkpoints while retaining their evidence links below. Unrelated model thresholds are not rounding-bound text and were not changed.

## Every old and new expected text

- Old: `equal to the exact sum within rounding; ≤0.1/month`
  New: `equal to the exact sum within rounding; bound: 0.005 × cells + 0.00005 × monthly records + 0.0001`
- Old: `equals the exact sum within rounding (≤ 0.1 per month)`
  New: `equals the exact sum within rounding (bound: 0.005 × cells + 0.00005 × monthly records + 0.0001; Syria hotspots reached a 0.1235 monthly gap)`
- Old: `whole-region totals equal the\nexact sum within rounding (≤ 0.1 per month)`
  New: `whole-region totals equal the\nexact sum within rounding (bound: 0.005 × cells + 0.00005 × monthly records + 0.0001; Syria hotspots reached 0.1235)`

The CSV expectation was updated earlier; this edit updates only the dialog and README text expectations. The unchanged numerical test's old label was `whole-region month = exact sum within 0.1 (as the site says)`; its new label is `whole-region month = exact sum within the unchanged Portugal/Lebanon baseline cap`. The docstring now distinguishes that fixed baseline cap from the general serialization formula.

## Current implementation and preserved evidence

Four new product regions: Syria, Jordan, Cyprus and La Rioja. Israel and Palestine are Deferred with the requested reason in both plan copies; raw files and finished audits remain. Their former web exports are outside the served tree, in ignored `data/raw/deferred_web_exports/` after recursive deletion was blocked by the environment. No Portugal/Lebanon exports or frozen models were regenerated.

The date-switch fix rebases calendar indices by YYYY-MM. Manual region/unit switches for the same area preserve an available selected date; examples, first load and new drawings use defaults. Diagnosis: the probe selected January 2025 for its Lebanon few-fires check; unconditional preservation in `useRegion()` then incorrectly retained it when opening the example. Baseline `84d2c0c` did not preserve the month for examples. The manual-picker opt-in fix passed both new regression checks and the unchanged October 2025 Lebanon-default assertion in the previous run.

- [UTF-8 preservation check](../analysis/tier1/scope_revision_preservation.json): 108 Portugal/Lebanon files, catalog entries and both frozen models unchanged.
- [Finished audit checkpoint](TIER1_AUDIT_CHECKPOINT.md), [scope and Deferred items](TIER1_PLAN.md).
- [Prior default-month-fix probe](../analysis/tier1/probe_default_month_fix.log): 216 passes before the now-authorized dialog wording failure; [summary](../analysis/tier1/probe_default_month_fix_summary.json).
- [File inventory](../analysis/tier1/web_file_inventory.csv): 222 new region files plus catalog; 42,451,808 bytes. Syria hotspots 2019 is the only file above 3 MB, at 3,548,856 bytes.
- [La Rioja demo](../analysis/tier1/la_rioja_demo.json): yearly/monthly CSVs, empty/busiest months and zero-weight comparison remain in analysis.
- [Known-event capture](../analysis/tier1/events/REPORT.md): scratch-input Latakia and Cyprus checks report capture only.

Proposed commit groups remain audit/provenance, regions/exporter, browser, probe/reality checks, four-region datasets/catalog, and documentation. An exact file manifest will be prepared after a full passing probe. Exclude raw archives, deferred web archive, `.env`, and `.claude/`.
