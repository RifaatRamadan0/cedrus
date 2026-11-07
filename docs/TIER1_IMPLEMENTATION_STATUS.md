# Map clarity follow-up — 7 November 2026 (committed)

Implemented user-approved clarification across all six product regions and both units:

- Label the orange dashed line as analysis extent, not a national boundary; label drawn areas separately.
- Give included near-zero cells a faint outline and shade cells absent from the exported grid with dashed edges. The latter are display-only features clipped to the box; they do not add observations or model cells.
- Explain that blank areas are not confirmed fire-free and observation completeness is unknown.
- Map clicks explain grid inclusion, selected-month estimate where available, missing-record status, and the possibility of land outside the country inside the box. Clear stale inspection text/popups when month, area or region changes.

**Full probe passed 468/468 in 346 seconds, round 1**, including 108 new map-clarity checks across six regions/two units, existing region/city/creative checks and final console-error check. Syria screenshot reviewed. [Log](../analysis/tier1/probe_map_clarity_round1.log), [summary](../analysis/tier1/map_clarity_summary.json). Preservation checker passed. No export or model changes. User approved committing this follow-up on 7 November 2026; nothing was pushed. The obsolete commit-groups Markdown document was deleted at the user’s request.

Changed implementation: `web/app.js`, `web/index.html`, `web/styles.css`; tests: `tools/probe_tier1.py`; evidence: the linked log/summary and this status file. The six original Tier 1 commits below remain intact.

---

# Commit checkpoint — 7 November 2026

User approved committing all six reviewed groups. Changes are committed on `add-tier1-regions`; nothing was pushed. See [commit groups, messages and exact file lists](../analysis/tier1/commit_groups.json). All 317 reviewed files passed the exclusion and local-credential scan before staging. Raw archives, deferred web exports, `.env`, `.claude/` and frozen-model files are excluded. Preservation verification still passes; the last full probe passed 360/360. Earlier “uncommitted” statements below describe their historical checkpoints.

---

# Final Tier 1 checkpoint — 6 November 2026

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

## Proposed commits

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
