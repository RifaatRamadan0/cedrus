# Tier 1 hackathon plan — completion update, 7 November 2026

This current completion record and the user-approved scope amendments supersede conflicting requirements in the historical plan below. The original plan is retained in full; completed audits remain unchanged. Stop conditions, frozen models, preservation of Portugal/Lebanon exports, no commits without approval, and no pushes remain in force.

## Latest scope: four new product regions

Israel and Palestine are excluded from product exports; raw files and completed audits remain. This supersedes six-region and Israel/Palestine test requirements below. Keep the five other city checks in both units, test Tel Aviv as outside coverage, and verify Lebanon / La Rioja and Lebanon / Syria switches by YYYY-MM in both units.

## Deferred items

- **Deferred — Israel:** Overlapping data footprints at 0.25 deg need a tie rule or polygon boundaries; deferred to keep the hackathon scope small.
- **Deferred — Palestine:** Overlapping data footprints at 0.25 deg need a tie rule or polygon boundaries; deferred to keep the hackathon scope small.

- **Deferred — Polygon boundary assets and Golan / Shebaa / West Bank / Gaza audits:** hackathon scope uses audited boxes and observed grid footprints; political/geographic boundary accuracy remains unverified.
- **Deferred — Combining records, background and uncertainty across countries:** the hackathon shows one source region at a time with an overlap warning and manual region switch.
- **Deferred — Request tokens and race tests for combined areas:** no combined-area feature ships; existing single-region request protections and regression tests remain.
- **Deferred — Creative-layer rework for combined areas:** creative features remain scoped to the selected single region.
- **Deferred — Per-month coverage ledger in exports:** the evidence ledger stays in analysis; visible notes disclose unknown completeness and link documented gaps.
- **Deferred — Suomi NPP gap impact check:** retained gap evidence is disclosed without a new sensitivity study in the hackathon scope.

## Completed hackathon work

1. **Complete — Audits and mapping:** corrected implementation status; finished Argentina 2018–2024 per-file filters/box audit and verified original-archive mapping into `data/raw/la_rioja`. Earlier source, type-filter and coverage-service audits remain intact.
2. **Complete — Four new product regions:** Syria, Jordan, Cyprus and La Rioja use audited boxes, display names and notes, with individual exports. Israel/Palestine are Deferred as above; their raw files and audit evidence remain. Portugal/Lebanon exports and catalog entries are unchanged.
3. **Complete — Shared notes:** every region displays "Counts all fires FIRMS detects, from any cause, including agricultural burning and conflict. Static heat sources (type 2) are excluded. Monthly completeness is unknown; known FIRMS data gaps are listed in the docs." The type-0 eligibility explanation remains visible.
4. **Complete — La Rioja notes:** retained the original evidence note and added "Annual totals in the 2020-2021 test were above the 80% range."
5. **Complete — Selection and dates:** positive sampled footprint share determines region selection, never fire totals; zero-share candidates use the outside-coverage path. The >10% alternative-footprint warning remains. Same-area manual region/unit switches align months by YYYY-MM; examples, initial load and new drawings use default months. Notes appear below the area summary.
6. **Complete — Browser and numerical verification:** four new regions reconcile whole-region CSVs in both units; La Rioja Aug–Feb sums, all region calendars/notes/creative features, five prescribed city selections, Tel Aviv/Mediterranean outside coverage, region/unit round trips and the console-error check pass. The unchanged original Lebanon-default assertion passes. The final full probe passed **468/468**, including 108 map-clarity checks across all six product regions in both units.
7. **Complete — Size and demo reports:** every new web-data file is inventoried; Syria hotspots 2019 is the sole file over 3 MB (3,548,856 bytes). La Rioja annual/monthly totals, empty/busiest months and zero-weight share versus Lebanon are reported.
8. **Complete — Known-event capture:** dates and sources verified for Latakia July 2025 and Cyprus July 2025; scratch-input `check_reality.py --fires` checks report capture only. No attribution, burned-area accuracy or flare-up validation is claimed.
9. **Complete — Review and approved commits:** user reviewed and approved six implementation groups, then the map-clarity follow-up. Seven commits are recorded below. No pushes. The obsolete `TIER1_COMMIT_GROUPS.md` was deleted at the user's request; historical machine-readable manifest remains.
10. **Complete — Map clarity:** orange dashed extent explicitly labelled as not a country boundary; faint outlines distinguish included near-zero cells from shaded dashed cells absent from the exported grid. Click explanations show inclusion and selected-month estimates when available, disclose unknown observation completeness, and clear when the selection changes. Shading is display-only and changes no data, models or totals.

## Final validation and commits — 7 November 2026

- Full probe: **468 passed, 0 failed**, 346 seconds, round 1; final console-error check passed. Evidence: `analysis/tier1/probe_map_clarity_round1.log` and `analysis/tier1/map_clarity_summary.json`.
- Preservation: all 108 Portugal/Lebanon export files, both catalog entries and both frozen models unchanged. Evidence: `analysis/tier1/scope_revision_preservation.json`.
- Earlier reduced-scope full probe: 360/360 passed. The earlier skip-link failure did not recur in these passing runs; no timing workaround was introduced or claim made that its intermittent cause was diagnosed.
- Branch: `add-tier1-regions`; base: `84d2c0c`. Raw archives, `.env`, deferred web exports and `.claude/` remain excluded from commits.

| Commit | Completed group |
|---|---|
| `8a0d014` | Audits, filters, coverage and provenance |
| `3017410` | Region definitions and verified staged exporter |
| `c48a487` | Browser footprint selection and date alignment |
| `e7836f8` | Region, area-selection and round-trip checks |
| `2a860d6` | Four new region datasets and catalog |
| `d0f8c06` | Scope, validation and review documentation |
| `11bb436` | Map coverage clarity, 108 new checks and obsolete document removal |

The user approved committing this documentation-only plan synchronization and consistency corrections on 7 November 2026. The implementation commits are listed above; future commits still require approval. Nothing has been pushed.

## Remaining limitations

- Boxes and 0.25° historical detection footprints are approximate analysis extents, not national boundaries. La Rioja is a rectangular study area, not the exact province. Polygon work remains Deferred.
- An absent grid cell means no qualifying records in the imported dataset; it does not distinguish no fires from missing observations. Included cells can have near-zero monthly estimates. Observation/monthly completeness remains unknown; the FIRMS gap evidence and monthly ledger stay in analysis.
- Whole-region serialization reconciliation uses `0.005 * cells + 0.00005 * monthly_records + 0.0001`; Syria hotspots reached a 0.1235 monthly gap. Existing numerical tolerances were not loosened.
- La Rioja 2020–2021 validation does not establish local accuracy or 2022–2025 accuracy; retain the exported evidence notes. Known-event checks establish capture only.
- All eight Deferred items above remain retained and unfinished. Completion here refers only to the approved reduced hackathon scope.

---

## Historical original plan — retained for provenance, superseded above

The following text records the original proposals, not outstanding requirements for the completed hackathon scope. Deferred work is not marked complete by this update.

# Tier 1 regions: La Rioja, Syria, Jordan, Cyprus, Palestine, Israel

Updated 6 November 2026, including the user's addendum. This is an implementation plan, not execution of the work. The addendum's decision rules take precedence over earlier proposals.

## Context and scope

Expand CEDRUS beyond Portugal and Lebanon to the La Rioja area in Argentina and Syria, Jordan, Cyprus, Palestine and Israel. La Rioja is CONAE's challenge example; the neighbouring countries support the Beirut story.

Use actual boundary polygons to identify supported points and the country files needed for a drawn area. Combine records across countries. Determine archive coverage independently of fire detections.

Keep model methods, settings and prescribed 2012–2019 fitting windows frozen, using `pipeline/weights_bd.py` and `pipeline/weights_r2.py`. Fit each new region on its own data without tuning against new test results. Preserve Portugal and Lebanon exports and numerical outputs. Target: 9 November 2026 model freeze.

## Git and approval

- Inspect the branch, HEAD, working tree and available inputs first. The original base was `84d2c0c`, including creative layer `2d2a36f`; verify current state rather than assuming it.
- Create `add-tier1-regions` from the agreed base if absent. Preserve existing work. Leave `.claude/` uncommitted.
- No commits until the user approves. No pushes. Present the verified diff and proposed commit groups, and obtain approval for each commit.
- Proposed groups: region definitions and boundaries; source audit and export contract; cross-country browser aggregation and tests; reality-check tooling; new exported data; documentation and La Rioja evidence.

## La Rioja evidence supplied by the user

Models fitted on 2012–2019 were tested against actual MODIS observations from 2020–2021.

| Result | Burning days | Hotspots |
|---|---:|---:|
| Regional monthly error | 11.0% | 13.4% |
| Overall undercount | 4.4% | 4.8% |
| Coverage of the 80% uncertainty range | 81.2% | 79.6% |
| Satellite interval agreement, 2020–2025 | 93.1% | 93.1% |

The supplied assessment says performance is comparable to earlier regional tests. Burning days beat the simple conversion. Hotspots were slightly worse at local grid-cell level but within the allowed margin. Local grid-cell errors remain around 60%.

These results support adding La Rioja, particularly for regional monthly summaries. Accuracy in 2022–2025 was not directly established. Satellite interval agreement is consistency evidence, not independent accuracy.

Locate and link the existing evaluation report, code, metric definitions, sample counts, baseline, allowed margin and provenance before publishing the figures. Confirm its geography matches the export box. Until verified, attribute figures to the supplied summary, not a newly reproduced evaluation. If input changes affect the evaluation, rerun the same fixed evaluation without tuning.

La Rioja-specific note:

> Regional monthly summaries were tested against MODIS in 2020–2021. Local grid-cell errors remain substantial, around 60%. Accuracy for 2022–2025 has not been directly established. This region is outside the climates used in the earlier Mediterranean validation.

## 1. Region definitions and geographic support

Add the `product` role to Syria, Jordan, Cyprus, Palestine and Israel in `pipeline/regions.py`.

The exporter requires boxes. Proposed boxes, subject to source-row checks:

| Region | Box: lon_min, lat_min, lon_max, lat_max |
|---|---|
| Syria | `(35.5, 32.2, 42.5, 37.5)` |
| Jordan | `(34.8, 29.0, 39.5, 33.5)` |
| Cyprus | `(32.1, 34.4, 34.8, 35.8)` |
| Palestine | `(34.1, 31.1, 35.7, 32.7)` |
| Israel | `(34.2, 29.4, 35.95, 33.4)` |

Boxes shortlist data; they do not define countries. Research loaders also use these boxes. Compare clipped and unclipped source rows for every file so historical development inputs are not silently changed. If a proposed whole-country box drops any row, stop and report the file, count and coordinates; do not silently enlarge the box or continue.

Add `la_rioja` with `country: Argentina`, display name `La Rioja area, Argentina`, product role and proposed box `(-69.7, -32.8, -65.4, -27.7)`. This deliberately selects a rectangular subset of Argentina, including neighbouring provincial land. It is not the exact La Rioja province.

The intentional La Rioja crop is part of its definition: report retained/excluded Argentina counts. The stop condition for unintended box losses applies to whole-country boxes and any loss beyond La Rioja's explicitly intended crop.

### Boundary source and ownership rules

- Default to Natural Earth admin-0, public domain, unless a better-licensed source is justified. Verify that the selected release/layers actually provide all required regional geometries; report missing or ambiguous geometry instead of substituting silently.
- Bundle boundary assets and record source, release/date, license, attribution, checksum, coordinate system and region-ID mapping. Show the source in the app's data notes.
- Preserve multipolygons, islands and holes. Check any simplification near borders.
- Polygons only determine which country files a shape loads and whether a point is geographically supported. They do not reassign ownership of detections.
- Each detection belongs to its original FIRMS country file. Within loaded files, select records by the drawn shape, without clipping them again to a different polygon-based country assignment.
- Where polygons and FIRMS disagree, follow FIRMS assignment. Report the affected area and row counts, including checks around Golan Heights, Shebaa Farms, and the West Bank/Gaza edges. Record sensor/year breakdowns and the rule used for shared edges, gaps or overlaps.
- Explicitly test whether polygon-based candidate loading misses FIRMS-owned records near these discrepancies. Report any limitation; do not silently reassign records or expand the candidate rule without documenting it.
- For La Rioja, geographic support is Argentina intersected with the configured area box.

## 2. Source acquisition, filters and audit

Inventory existing raw data, manifests and frozen configuration files first; do not assume they are present or absent.

Reuse the country downloader:

```text
python pipeline/01_download.py --country Syria
python pipeline/01_download.py --country Jordan
python pipeline/01_download.py --country Cyprus
python pipeline/01_download.py --country Palestine
python pipeline/01_download.py --country Israel
python pipeline/01_download.py --country Argentina
python pipeline/export_v2.py --region <region id>
```

The exporter reads `data/raw/<region id>`. Supply Argentina files and manifest under `data/raw/la_rioja/` using a documented mapping or a verified copy/rename. Do not overwrite existing files. Preserve NASA filenames, URLs and checksums. Report measured download sizes/times rather than promising a duration.

Audit expected sensor-year files, successful downloads, legitimate unavailable years, unexpected missing files and failed requests. Retry transient failures; never silently treat failed downloads as quiet months. If a FIRMS country name cannot be found, stop and report rather than guessing an alternative.

### Data filters

- Before export, inspect `02_aggregate.py` and the production exporter to confirm how they handle FIRMS `type`.
- Only `type = 0` (presumed vegetation fire) may count. Report per-region counts for type 0, 1 (volcano), 2 (static land source), 3 (offshore), missing and unexpected values before filtering. Syria's oil-field detections are a priority.
- If a raw schema lacks the field, explicitly report that the type-0 requirement cannot be verified from that file. Do not silently count unverified rows as vegetation fires; investigate source/schema evidence before treating them as eligible.
- If the type filter is missing, add it for new regions only. Assess and report its potential impact on Portugal and Lebanon separately; do not re-export them.
- Retain the other prescribed filters: region box, MODIS confidence >= 30, VIIRS nominal/high confidence. Document exact implementation and retained counts.

## 3. Monthly archive coverage

Search FIRMS documentation and archive metadata for evidence of monthly completeness independently of detection dates. Record the sources searched and what they establish. File existence alone does not prove full monthly completeness.

If no completeness evidence exists, mark coverage `unknown` for each satellite and month, document this in the data contract, and continue. Unknown coverage is not a stop condition and must not be inferred from detections.

Distinguish covered-with-detections, covered-with-zero-detections, partial, missing and unknown. A quiet month with verified coverage remains in the record. Apply the frozen zero-detection/background rule; zero detections do not necessarily mean a zero harmonized estimate.

Separate these concepts in the schema:

- Availability of an archive/file and whether it was successfully retrieved.
- Evidence of complete satellite coverage for a month.
- Whether fire detections occurred.
- Whether an estimate can be computed from the available inputs.

Unknown completeness must not be labelled confirmed coverage or automatically converted into zero. Estimates computed from available archives may continue with an explicit unknown-coverage qualification. Missing inputs, empty sensor histories, inadequate fitting overlap and uncomputable estimates need explicit statuses. Do not treat an absent estimate as zero.

Document how source selection and satellite averaging work under known, partial and unknown coverage. Keep the prescribed fitting windows/settings unchanged. Report any conflict with the existing research-table coverage assumptions and its numerical impact instead of silently changing the evidence basis.

## 4. Exporter and data contract

- Use `cfg.get("name", cfg["country"])` for display names and export optional notes.
- Every region must display: "Counts all fires FIRMS detects, from any cause, including agricultural burning and conflict."
- Keep the type-0 vegetation-fire rule visible alongside that cause note, so it is not read as including excluded volcano/static/offshore detections. The pipeline does not classify fire causes.
- Display La Rioja's specific evidence note in addition to the shared note.
- Export or reference boundary provenance and per-satellite/month coverage status and evidence, with documented schema/version compatibility.
- Preserve per-country weights, source flags, background, uncertainty and provenance needed for combination.
- Document actual regional start/end dates rather than assuming every region reaches December 2025.
- Preserve other index entries during single-region export. Write outputs safely to avoid publishing interrupted partial datasets.

Do not re-export Portugal or Lebanon. Preserve existing numerical data and model metadata. Add general notes, boundary references and coverage annotations additively or via companion metadata without altering their numbers; document every such metadata change. Audit their coverage/filter assumptions separately and report numerical corrections that would require a later decision.

## 5. Browser: combined drawn areas

Replace the single winner returned by `regionForRing` with the participating country files determined from actual polygon intersections. Bounding boxes are candidate indexes only; historic fire footprint or fire totals must never decide country membership.

- Inside one country, use that country's records. Across countries, combine all relevant files.
- Clearly identify unsupported geography and partial/unknown temporal coverage. Do not present a supported subtotal as the complete total for the whole shape.
- A historically fire-free location inside a boundary remains geographically supported; separately describe model/background limitations outside the trained/exported footprint.
- Keep each country's fitted weights. Do not fit a model to each drawing.
- Respect FIRMS source ownership and apply exact record-in-shape checks for loaded files. Use the established square-center convention for burning days.
- Audit duplicate records across files. Prevent duplicate contributions using source-aware identities; do not merge legitimate distinct satellites, times or nearby observations. Report ownership conflicts rather than resolving them by fire totals.
- Allocate background for each source-country contribution without double-counting coarse cells shared across countries. Explain its spatial approximation and how it follows the source-ownership policy; record sums may be exact while partial-cell background remains approximate.
- Align months explicitly and expose missing/uncomputable contributions. Never silently fill missing countries or months with zero.
- Calendar, map, seasonal summary, comparisons and all CSVs must use the same combined series. Include contributing region IDs, source provenance and coverage status in exports.

### Uncertainty

Show the 80% range per country. If displaying a combined range, label it exactly "approximate, not validated". Document the aggregation assumption and shared calibration uncertainty. Do not simply add interval endpoints or claim validated combined 80% coverage.

### Loading and creative features

Extend request tokens across candidate selection, file loading and rendering. New drawings, region choices or unit switches invalidate older requests. Cache loads while preventing stale responses from overriding the latest choice. If a required file fails to load, show retry/partial status rather than a complete combined result.

Review `web/fx.js` and all single-`state.meta` assumptions. Support combined labels, relevant notes and geometry for story mode, playback, fingerprint PNG and ignition rim. They must reflect the same combined data, not one country's bounding rectangle.

## 6. Reality checks and documentation

Make `tools/check_reality.py` accept both region IDs and display names while retaining existing sheet compatibility.

Only compare matching geography, time and definitions. National figures do not validate a sub-national box, and La Rioja province figures do not exactly match the rectangular area. Use matching boundaries or disclose the mismatch. Burned area and detection/burning-day counts are different quantities; treat their comparison as a consistency check.

Update README and `docs/DATA_CONTRACT.md` with regions, boundary source/license, data setup, Argentina mapping, filters, coverage decision rules, cross-country aggregation, duplicates, background approximation, uncertainty labels, region notes and La Rioja evidence. Update the separate gap-list artifact only if requested.

## 7. Verification

1. **Existing regions:** compare Portugal/Lebanon files and numerical outputs with the recorded base. Document allowed additive metadata separately. No re-export.
2. **Input audit:** verify manifests/checksums, download outcomes, type counts, confidence filters and monthly coverage statuses. Missing completeness metadata becomes unknown, never detection-inferred coverage.
3. **Boxes:** verify every neighbour's whole-country box retains every source row. Report intentional Argentina-to-La-Rioja cropping separately. Stop on unintended losses.
4. **Frozen fitting:** verify frozen JSON checksums, windows, training sufficiency and unsupported slots. No post-2019 fitting or tuning. Stop on checksum failure.
5. **Regression:** run `python tools/probe_site.py` and relevant existing model checks with required inputs present. Record actual results/counts instead of assuming 233 checks. Stop if the probe regression fails; preserve diagnostics and do not publish or commit.
6. **Reconciliation:** in both units, compare every new region's whole-region CSV with its files plus background. For cross-border drawings, independently sum all source-country contributions and check agreement within rounding and stated background approximation. Test duplicate handling and missing/unknown months.
7. **Geography:** retain the original city coordinates as point-membership checks: Beirut/Tyre; Damascus/Homs/Daraa; Nahariya/Tel Aviv/Haifa/Beersheba; Ramallah/Hebron/Gaza City/Jericho; Amman/Irbid. Derive a 5 km circle's participating countries from intersections rather than assuming its center country is its only contributor. Add deliberate cross-border shapes, quiet areas, unsupported areas, islands/holes and shared edges. Report polygon/FIRMS discrepancies with area and row counts and follow FIRMS ownership.
8. **Browser:** exercise each region and both units with no console errors. Verify combined labels, notes, CSVs and all creative features. Draw A then B quickly, switch units during loading and simulate a required-country failure; only the latest valid result may render as complete.
9. **La Rioja evidence/demo:** verify/link supplied 2020–2021 results. Report activity by year/month, empty months, season pattern, regional fallback cells and zero-weight share. Compare with Lebanon's measured current share, not an assumed constant. Retain the user decision on demo prominence.
10. **Cross-year season:** a La Rioja season from August of year Y through February of Y+1 must equal the sum of those seven months, with consistent coverage status and no omission or double-counting at New Year. Check both units and the displayed/exported seasonal total.
11. **Known events:** retain Syria May–June 2019 wheat-field fires and Cyprus July 2021 Arakapas fire for observed-year checks. Add at least one independently verified, sufficiently detectable event in 2022–2025 for each new region. Candidates to verify first: Latakia, Syria (July 2025); Limassol, Cyprus (July 2025); Jerusalem hills (April–May 2025). These are candidates, not confirmed evidence. Find supported candidates for Jordan, Palestine and La Rioja as well; report any unfilled requirement without inventing an event. Verify dates, location, size and sources before checking the relevant records/estimates. Use scratch `--fires` inputs and leave analyst sheets untouched. Check event capture separately from flare-up status: a real event need not make its month anomalous.
12. **Load size:** report the size in bytes and MB of every new data file, including boundary assets. For a specified drawing around Beirut (record exact shape/coordinates), measure total bytes actually loaded with an empty cache, including candidate datasets and shared assets; state measurement scope and account for transfer size versus uncompressed size. Report data-only and total page-load figures where measurable. Flag any individual file or measured load above 3 MB, stating whether MB is decimal. Also report repeat/cached behavior and which country files were loaded.

## Stop conditions and explicit non-stops

Stop and report, without guessing, if:

- A required FIRMS country name is not found.
- A whole-country box drops any source row, or a crop loses rows beyond its intended definition.
- A frozen-model checksum fails.
- The probe regression fails.

A stop means report evidence and required correction; do not continue exports/publication or adjust expectations to manufacture a pass. Preserve existing files and diagnostics.

Unknown monthly completeness is explicitly not a stop condition: mark it unknown, document it and continue under the qualified estimation policy. A load over 3 MB is a required flag, not an automatic stop. Unverified event candidates remain unverified, and unmet acceptance checks must be reported.

## Outside scope

2026 data/NRT integration, NOAA-21 model integration, Tier 2/3 regions, retuning frozen models, re-exporting Portugal/Lebanon, commits without approval, and any pushes.

## Delivery

Present the reviewable diff, source/filter/coverage audit, boundary discrepancy report, exported file inventory and sizes, Beirut load measurement, regression and cross-country reconciliation results, linked La Rioja evidence, event checks, remaining limitations and proposed commits. Do not claim full completion while required acceptance checks remain unresolved.
