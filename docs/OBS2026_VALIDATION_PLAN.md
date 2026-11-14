# 2026 observations: validation plan

**Written 10 November 2026, before any validation data was downloaded.** Thresholds below are fixed and are not
changed after the results are seen. If a test fails, 2026 is not exported; the findings are reported first.

**Final state, 12 November 2026:** all four regions (Portugal, Lebanon, Syria, La Rioja) run to July 2026 from FIRMS
standard data; near-real-time data is not used. Portugal, Syria and La Rioja were added on 11 November (outcome
below); Lebanon, after two failed boundary tests, on 12 November with the Natural Earth outline of 30 August 2021
(last section). The sections below are kept as written, so earlier ones still say "Lebanon stays at 2025".

## Why the 2026 data needs new processing

The 2000–2025 record comes from FIRMS yearly **country files**: detections already assigned to one country, with
a `type` field. For 2026 none of that exists:

| | 2000–2025 | Jan–Jul 2026 | Aug 2026 onward |
|---|---|---|---|
| Source | Country file (no key) | Area API, standard processing (`*_SP`) | Area API, near-real-time (`*_NRT`) |
| Country assignment | Done by FIRMS | **None**: every detection in the box | **None** |
| `type` (static sources, volcano, offshore) | Yes | Yes | **No** |

Checked on 10 Nov 2026: no `*_2026_<Country>.csv` exists (HTTP 404); the country API answers "Invalid API call";
standard data ends 2026-07-31 (VIIRS) and 2026-08-31 (MODIS); NRT runs from 2026-08-01 (VIIRS) and 2026-09-01
(MODIS). In 2025, type 2 (static sources) was 59% of Syria's VIIRS detections and 2–3% elsewhere.

Two new steps are therefore needed, and each is tested where the right answer is known.

## Step 1: country clipping

Each area-API detection is kept only if it falls inside the region's country outline from Natural Earth
(`ne_10m_admin_0_countries.geojson`, 1:10m, public domain), then the region's box, as the exporter does.

**Test:** download 2025 through the area API (`MODIS_SP`, `VIIRS_SNPP_SP`, `VIIRS_NOAA20_SP`) for each region's
box, clip it, and compare it with the 2025 country file restricted to the same box. Records are matched on
latitude and longitude (4 decimals), date, time and satellite. Both sides use the pipeline's own filters
(type 0, confidence), because those are the records that reach the product.

- **False inclusion:** kept by the clip, absent from the country file, within 10 km of the outline's edge
  (a neighbour's fire counted).
- **False exclusion:** in the country file and returned by the area API, but removed by the clip (the region's
  own fire lost).
- **Source difference:** in the country file but not returned by the area API at all; or kept by the clip,
  absent from the country file and more than 10 km inside the outline (the two products differ, whatever the
  clipping does).

**Pass, for every region × sensor:**

- C1: (false inclusions + false exclusions) ≤ **2%** of the country file's filtered count for 2025.
- C2: in every region-month with at least 20 filtered country-file detections, the clipped monthly count is
  within **5%** of the country file's.
- C3: source differences ≤ **1%** of the country file's filtered count. Otherwise area-API data is not
  comparable with the archive, whatever the clipping does.

Reported, not pass/fail: mismatches by 0.25° cell, distance of each mismatch to the outline, and the border
stretches where they occur.

## Step 2: static-source mask (needed only for NRT months)

NRT has no `type`, so a detection is dropped when it falls on a place that standard data has marked as
non-vegetation before.

- **Mask:** every 0.01° square (about 1 km) holding at least one detection with `type` 1, 2 or 3 in the region's
  2012–2025 country files, all sensors. A detection is masked if its 0.01° square **or any of the 8
  neighbouring squares** is in the mask (primary rule). The same square alone (no neighbours) is reported as a
  sensitivity variant only.
- The mask uses 2012–2025 only, so the test below is out of sample.

**Test:** Jan–Jul 2026 standard area data, clipped as in Step 1, with confidence filters applied, scored as if it
had no `type`. Truth is its real `type`.

**Pass, for every region × sensor:**

- M1: the mask removes at least **95%** of type 1–3 detections.
- M2: the mask removes at most **1%** of type 0 detections.
- M3: in every region-month with at least 20 type-0 detections, the masked count is within **5%** of the
  type-filtered count.

## What cannot be tested yet

NRT and standard data do not overlap in time for any sensor (standard VIIRS ends 31 Jul, NRT VIIRS starts
1 Aug), so the difference between the two products cannot be measured now. Even if both steps pass, NRT months
are published only as **provisional**: labelled in the app and the CSV, and replaced by standard data when FIRMS
releases it. The frozen models are not refitted, and no 2000–2025 value may change.

## Result, 10 November 2026: both tests failed; nothing was exported

Full tables: [analysis/obs2026/REPORT.md](../analysis/obs2026/REPORT.md); raw numbers in `results.json`.

**Clipping: 11 of 12 region × sensor checks pass.** 2025 area-API data clipped to the Natural Earth outline
matched the 2025 country files record for record in Portugal, Syria and La Rioja (all sensors) and in Lebanon's
MODIS and NOAA-20 data. No source differences anywhere (C3 = 0%). The one failure is Lebanon / Suomi NPP: C1 is
0.97% (passes), but October 2025 is 57 against 52 (C2: 9.6%). All 6 mismatched Lebanon detections (5 Suomi NPP,
1 NOAA-20) are false inclusions within 1.3 km of the outline, in one 0.25° cell (142_133) on the southern
border, where Natural Earth's line differs from the one FIRMS uses for its country file.

**Mask: fails in every region, on false removals (M2).** The rule removes nearly all static detections (M1 is
met for most VIIRS rows) but also removes 2–31% of real fires: Portugal 1.8–3.0%, La Rioja 6.9–7.7%, Lebanon
4.8–20.7%, Syria 16–31%. Any square that was ever flagged once in 14 years, plus its neighbours, is too wide a
net: vegetation and crop fires also burn next to places that were flagged once. In Syria, where static sources
are 48% of Jan–Jul 2026 detections, monthly counts are off by up to 84% (M3).

Consequences under this plan: NRT months (Aug 2026 onward) cannot be published, because they would depend on the
mask. Jan–Jul 2026 standard data has `type` and needs no mask, but depends on the clipping, which failed one check.

## Addendum, 11 November 2026: Lebanon border correction (written before its test data was downloaded)

**Finding.** All 6 Lebanon false inclusions of 2025 (5 Suomi NPP detections from one pass on 4 Oct, 1 NOAA-20 on
9 Nov) are in the neighbouring country's 2025 FIRMS country file, not Syria's. They lie 0.2–1.2 km inside Natural
Earth's Lebanon outline, so FIRMS's southern line and Natural Earth's differ there by about a kilometre.

**Rule (Lebanon only).** For an area-API detection within **3 km** of Lebanon's outline edge, take every historical
FIRMS country-file detection (all sensors) within **1 km** of it, from Lebanon's files and from its two neighbours'
files. If the majority come from a neighbour's file, the detection is not Lebanon's. If there are none within 1 km,
or a tie, the outline decides. Detections more than 3 km from the edge are decided by the outline alone.

**Test, with the thresholds unchanged (C1 2%, C2 5%, C3 1%).**
- **Decisive:** 2024 area-API data for Lebanon (all three sensors, never downloaded before this addendum), with the
  historical reference built from every country-file year except 2024.
- Reported only: 2025, with a reference that excludes 2025. This is the year the rule was designed on, so it cannot
  count as evidence.

If 2024 fails any check, Lebanon stays at 2025 and the limitation is documented.

### Result of the Lebanon border test, 11 November 2026: FAIL; Lebanon stays at 2025

Full table: [analysis/obs2026/REPORT_lebanon_border.md](../analysis/obs2026/REPORT_lebanon_border.md).

| 2024, corrected (decisive) | C1 | C2 worst month | Pass |
|---|---:|---:|---|
| MODIS | 4.29% | 2.44% | no |
| Suomi NPP | 2.41% | 8.33% | no |
| NOAA-20 | 2.02% | 2.13% | no |

The correction made 2024 worse: 9–28 detections per sensor moved to the wrong side, because 2024 had many
detections close to the southern line on both sides and a historical majority within 1 km does not follow the
line closely enough.

Reported, not decisive: the outline alone passed every check in 2024 (C1 0–0.70%, C2 ≤ 4.17%). It failed the
pre-registered 2025 test, so it has one pass and one failure, and choosing it now, after seeing 2024, would mean
choosing the rule after the result. No 2026 data is added for Lebanon until FIRMS publishes its 2026 country file.
Portugal, Syria and La Rioja, which passed the original test, get January–July 2026.

## Outcome, 11 November 2026: January–July 2026 added for Portugal, Syria and La Rioja

**Data.** Standard area data for January–July 2026, assigned with the Natural Earth outline
(`pipeline/01d_build_country_year.py`), written as `<sensor>_2026_<Country>.csv` with a `derived:` manifest entry.
Detections inside the outline, before the type and confidence filters:

| Region | MODIS | Suomi NPP | NOAA-20 |
|---|---:|---:|---:|
| Portugal | 1,243 | 3,762 | 3,574 |
| Syria | 804 | 5,102 | 5,628 |
| La Rioja | 232 | 1,166 | 1,307 |

No near-real-time data is used, and Lebanon has no 2026 data (border test above).

**History kept exactly.** Two exporter rules would otherwise have changed 2000–2025:
- December 2025 in Syria and La Rioja would have switched from NOAA-20 only to both satellites once it stopped
  being the last month (the end-of-record rule needs a detection in a file's last 3 days).
- A cell first burned in 2026 (one in La Rioja) would have added its background to every earlier month.

`pipeline/export_v2.py` now decides coverage and the grid for months up to 2025-12 from the 2000–2025 files alone
(`HISTORY_END`). The one 2026 NOAA-20 detection outside the 2000–2025 grid is left out and counted in
`record_end.detections_outside_grid`. `tools/check_history_unchanged.py` compares every 2000–2025 array, flag,
note and year file with commit `4e33960` and passes for all four regions; it fails on a deliberate 0.01 change.
Both frozen models are unchanged. `tools/check_tier1_preservation.py` now byte-compares 104 of the 108 protected
files; Portugal's four whole-record files are covered by the history check instead.

## Addendum, 11 November 2026: other boundary datasets for Lebanon (written before any candidate was downloaded)

FIRMS does not document which boundary dataset or assignment method it uses for its country files (checked: the
archive download page, the country page, the API page and the FAQ). This test asks whether a published boundary
dataset reproduces FIRMS's historical assignment for Lebanon.

**Candidates**, in this order (the order also breaks ties). Each is used as a plain point-in-polygon test with
Lebanon's polygon from that dataset, exactly as `pipeline/outline.py` uses Natural Earth 1:10m now:

1. Natural Earth 1:10m admin-0 countries (the current outline)
2. Natural Earth 1:50m admin-0 countries
3. Natural Earth 1:110m admin-0 countries
4. GADM 4.1, level 0
5. geoBoundaries gbOpen, ADM0 (current release)
6. geoBoundaries gbHumanitarian, ADM0 (current release)
7. geoBoundaries CGAZ, ADM0 (the composite global layer)
8. FAO GAUL, level 0 (latest release that can be downloaded without an account)
9. US Department of State LSIB (Large Scale International Boundaries)

A candidate that cannot be downloaded is left out and the reason recorded; nothing is substituted after scoring
starts.

**Selection, on older years only (2000–2022).** Data: every detection from Lebanon's, Syria's and the southern
neighbour's FIRMS country files for 2000–2022, all three sensors, all `type` and confidence values (country
assignment does not depend on them), inside Lebanon's box. Truth: the detection is in Lebanon's file. A mismatch
is a detection whose truth and the candidate's inside/outside answer differ. **The candidate with the fewest
mismatches is selected**; ties go to the earlier candidate in the list. Selection uses no 2023–2025 data.

**Independent test, held-out years 2023, 2024 and 2025.** The selected candidate replaces the outline in the
clipping test (`validate_processing.clipping`), with the **unchanged thresholds C1 2%, C2 5%, C3 1%**, for each of
MODIS, Suomi NPP and NOAA-20 in each year: 9 checks, all must pass. 2023 area-API data is downloaded only after
the selection is made. 2024 and 2025 area data were already used in the earlier Lebanon tests, but only to score
Natural Earth 1:10m and the 1 km majority rule; no other candidate has been scored on them. 2023 is the only
fully unseen year, so a pass that relies on 2024–2025 alone would be weaker; all three years must pass.

The selected candidate is not adjusted after the test. If it fails any of the 9 checks, Lebanon stays at
December 2025. If it passes, the result is reported and nothing is exported until that is approved. The frozen
models and the 2000–2025 data are not touched either way.

### Result of the boundary comparison, 11 November 2026: FAIL; Lebanon stays at 2025

Full tables: [analysis/obs2026/REPORT_lebanon_boundaries.md](../analysis/obs2026/REPORT_lebanon_boundaries.md);
checksums of every candidate file in `data/raw/boundaries/candidates/manifest.json` (not committed).

**What was scored.** Eight of the nine candidates. Deviations from the list, all decided before scoring:
- LSIB v11.4 is left out: it is published as boundary lines only (no polygons, no coastline), so there is no
  Lebanon polygon to test, and building one from another dataset's coast would be a new, untested boundary.
- FAO publishes no level-0 geometry for GAUL 2024 (its "L0" file is a code list), so GAUL is Lebanon's eight
  level-1 units taken together, which covers the same area.
- CGAZ was read from its shapefile release (104 MB) rather than the GeoJSON (401 MB); it is the same layer.

**Selection, 2000–2022** (21,725 detections in Lebanon's box, 12,585 of them in Lebanon's file):

| Candidate | Mismatches |
|---|---:|
| **Natural Earth 1:10m (selected)** | **12** |
| Natural Earth 1:50m | 364 |
| FAO GAUL 2024 | 583 |
| geoBoundaries CGAZ | 585 |
| geoBoundaries gbHumanitarian | 699 |
| GADM 4.1 | 752 |
| geoBoundaries gbOpen | 773 |
| Natural Earth 1:110m | 2,600 |

All 12 Natural Earth 1:10m mismatches are neighbour-file detections 0.2–0.8 km inside its Lebanon outline, in
one 0.25° cell (142_133) on the southern border, the same cell as the 2025 mismatches.

**Independent test, 2023–2025, thresholds unchanged: 8 of 9 checks pass.** 2023 (never seen before) matches
record for record in all three sensors. 2024 passes with 5 (Suomi NPP) and 8 (NOAA-20) false inclusions. 2025
Suomi NPP fails C2: October 2025 is 57 against 52 (9.6%), from 5 false inclusions in one satellite pass.

**Remaining discrepancy.** Across 2000–2025, 31 detections are assigned differently, all of the same kind: in the
neighbour's country file but inside Natural Earth's Lebanon, within 1.4 km of the line, 30 of them in cell
142_133. No Lebanon detection was ever lost (no false exclusions), and the coast, the Syrian border and the
rest of the southern border match exactly. Natural Earth 1:10m is selected and not adjusted. It fails one of
the nine checks, so under the plan Lebanon stays at December 2025.

## Addendum, 12 November 2026: older Natural Earth 1:10m versions for Lebanon (written before any version was downloaded)

The boundary comparison above found that Natural Earth 1:10m is far closer to FIRMS's assignment than any other
dataset, but that the current file differs from FIRMS in one short stretch of the southern border. This test
asks whether an earlier version of the same file reproduces FIRMS's assignment there.

**Candidates.** Every version of `10m_cultural/ne_10m_admin_0_countries.shp` in the Natural Earth repository
(github.com/nvkelso/natural-earth-vector): the 23 commits that changed the file, from 22 January 2012 (release
1.4) to 22 April 2022 (the file in every release since 5.1.0, and the one in use now). The list is taken from
the repository's commit history for that path; nothing is added after scoring starts. Each version is read at
its commit (`.shp`, `.shx`, `.dbf`), and Lebanon is the feature whose `ADM0_A3` (or, if that field is missing,
`ISO_A3`, then `ADMIN`/`NAME`) identifies Lebanon. Versions whose Lebanon polygon is identical are scored once,
as one group. A version that cannot be downloaded or read is left out and the reason recorded.

**Selection, on older years only (2000–2022).** Identical to the boundary comparison: the same 21,725
detections from the three country files, all sensors, types and confidences, inside Lebanon's box; a mismatch is
a detection whose country file and the version's inside/outside answer disagree. **The version with the fewest
mismatches is selected.** Ties go to the newer version. If the selected Lebanon polygon is the one in use now,
the result is already known (it failed) and no new test is run.

**Independent test, 2023, 2024 and 2025.** Unchanged from the boundary comparison: the selected polygon replaces
the outline in `validate_processing.clipping`, **thresholds C1 2%, C2 5%, C3 1% unchanged**, three sensors × three
years = 9 checks, all must pass. The selected version is not adjusted after the test.

**What this test can and cannot show.** The 2023–2025 area data has already been used to score the current
Natural Earth file, so the held-out years are not unseen for this family of outlines. The choice is still made
only from 2000–2022 by the rule above, so the 2023–2025 results cannot influence which version is selected. As
supporting evidence (not a pass condition), the report gives how many of the 31 detections that the current file
assigns differently (2000–2025) the selected version gets right.

If the selected version fails any of the 9 checks, Lebanon stays at December 2025. If it passes, the result is
reported and nothing is exported until that is approved. The frozen models and the 2000–2025 data are not
touched either way.

### Result of the older-version test, 12 November 2026: PASS; nothing exported yet

Full tables: [analysis/obs2026/REPORT_lebanon_ne_versions.md](../analysis/obs2026/REPORT_lebanon_ne_versions.md);
checksums in `data/raw/boundaries/candidates/ne10m_history/manifest.json` (not committed).

**What was read.** All 23 versions. Only Lebanon's record was taken from each `.shp` (an HTTP Range request,
checked against the record number in the file). The 2020-12-13 `.dbf` is rejected by pyshp but is consistent
by its own header (155 fields, 2,188 bytes per record), so every version's `.dbf` is read with a small reader that
uses only the header and field descriptors. That reader gives the same Lebanon record as pyshp for the other 22.
This was settled before any scoring. The 23 versions hold 11 distinct Lebanon polygons.

**Selection, 2000–2022** (the same 21,725 detections):

| Lebanon polygon in commits | Mismatches |
|---|---:|
| 2021-09-03 to 2022-04-22 (in use now), and 2021-11-14, 2021-12-07 | 12 each |
| **2021-01-06 to 2021-08-30 (6 commits; selected as the newest with the fewest)** | **0** |
| 2020-12-13; 2018-05-15; 2014-12-31 to 2017-10-05; 2012-11-04 to 2017-08-14; 2013-06-02; 2012-08-19 | 0 each |
| 2012-01-22 (release 1.4) | 5 |

Every version from 19 August 2012 to 30 August 2021 reproduces FIRMS's assignment for all 21,725 detections. The
12 mismatches first appear in the commit of 3 September 2021, which redrew disputed areas on Lebanon's southern
border; all 12 are detections from the southern neighbour's file.

**Independent test, 2023–2025, thresholds unchanged, polygon of commit be165336bb (2021-08-30): 9 of 9 pass.**
Every check is an exact record-for-record match, with no false inclusions or exclusions in any sensor or year.
All 31 detections that the current file assigns differently are assigned correctly.

**Check after the test (decides nothing).** Each of the other six zero-mismatch polygons was also run through the
same 2023–2025 test: all give zero mismatches. So the pass does not depend on which tied polygon the tie-break
picked.

Under the plan, the result is reported and Lebanon's January–July 2026 export waits for approval. The frozen
models, the 2000–2025 data and the outline used for the other regions are unchanged.

## Outcome, 12 November 2026: January–July 2026 added for Lebanon

Approved on 12 November 2026 after the older-version test passed. Lebanon's 2026 detections are assigned with the
Natural Earth 1:10m outline of commit `be165336bb` (30 August 2021) and nothing else; the current outline stays in
use for every other country and for the map.

- **Boundary record** (`pipeline/outline.py`, `LEBANON_2021`; files in `data/raw/boundaries/ne10m_be165336bb/`,
  not committed): source
  `https://raw.githubusercontent.com/nvkelso/natural-earth-vector/be165336bbc6d3c28fb75348fa223339308b7742/10m_cultural/ne_10m_admin_0_countries.{shp,shx,dbf}`;
  SHA-256 `.shp` `7b306090a2114e46…`, `.shx` `d12bed229116f995…`, `.dbf` `79253ccd579d52b1…`; git blob of the
  `.shp` `b59994c3c9029d03ac9932dd7adf79b3110dd644`; Lebanon is record 12 (`ADM0_A3` = `LBN`), polygon SHA-256
  `fc650ad77adb60f5…`, the polygon that was tested. The loader refuses if any of these differ. Lebanon's record in the
  full file is byte-identical to the one read during the test.
- **Build** (`pipeline/01d_build_country_year.py --region lebanon --year 2026 --through 2026-07`): MODIS 21 of 35
  box detections inside the outline, Suomi NPP 270 of 406, NOAA-20 227 of 407. The manifest's `via` names the
  commit and the `.shp` checksum.
- **Outside the historical grid:** one detection: Suomi NPP, 24 June 2026 11:11 UTC, 33.5852 N 36.0372 E, FRP 12.8 MW,
  nominal confidence, 0.1 km inside Lebanon's eastern border, in cell 144_134, which had no Lebanon fires in
  2000–2025. It is left out and counted in `record_end.detections_outside_grid`; the grid is unchanged.
- **Record end:** all three sensors to 2026-07 (last detection 31 July 2026); no VIIRS outage month.
- **History and models:** `tools/check_history_unchanged.py` passes for all four regions (Lebanon: 50 year files
  byte-identical, every 2000–2025 value, flag and note identical); both frozen models unchanged.
  `tools/check_tier1_preservation.py` passes.

**Changed checks** (reported, not approved in advance):
- `tools/check_tier1_preservation.py`: Lebanon's four whole-record files (`monthly`, `monthly_bd`, `drift`,
  `drift_bd`) now grow like Portugal's and are left to the history check instead of being byte-compared; its year
  files to 2025 are still byte-compared. Two catalog totals over 2022 to the last month,
  `burning_days.zero_weight.weight_zero` (850 → 950) and `.months_noted` (28 → 34), are added to the growing fields,
  beside the already-listed `share` and `viirs_burning_days` of the same block. The per-month notes are compared by
  the history check.
- `tools/probe_site.py`: the burning-day model check rebuilt Lebanon's grid from every raw detection and failed on
  the one off-grid 2026 detection. It now drops detections outside the exported grid, as the exporter does, and
  checks that they are exactly the catalog's `detections_outside_grid` and all after 2025.

**Final checks**, after this change and the map-message change (12 November 2026): `tools/probe_site.py` 431/431
([log](../analysis/obs2026/probe_lebanon2026_map_messages.log)); `tools/check_history_unchanged.py` passes for all
four regions; `tools/check_tier1_preservation.py` passes; frozen models unchanged.
