# Tier 1 audit checkpoint — 6 November 2026

Completed the three requested audits in order. Paused here as requested, before
boundaries or exports. No product regions, model settings, existing export data,
or analyst sheets were changed. No commits or pushes were made.

## 1. Portugal and Lebanon: type-filter impact

Verified each restored raw file against the source SHA-256 in the **committed**
`regions.json`, then counted all types before filtering. These are observations,
not distinct fires, burned area, or harmonized estimates.

| Region | Type 0: vegetation | Type 1: volcano | Type 2: static land | Type 3: offshore | Missing | Unexpected |
|---|---:|---:|---:|---:|---:|---:|
| Portugal | 229,073 | 10 | 7,328 | 148 | 0 | 0 |
| Lebanon | 16,257 | 0 | 1,558 | 131 | 0 | 0 |

Isolating the type filter **after** the existing box and confidence filters:

| Region | Type 1 removed | Type 2 removed | Type 3 removed | Total removed |
|---|---:|---:|---:|---:|
| Portugal | 0 | 7,293 | 124 | 7,417 |
| Lebanon | 0 | 1,555 | 121 | 1,676 |

These are marginal source-row exclusions, not an estimate of the effect on fitted
weights or harmonized totals. No counterfactual model was fitted and no re-export
was performed. Both existing loaders already apply type 0 when the column exists;
all restored schemas have the column. Their missing-column behavior remains a
future hardening concern, not a contamination found in these inputs.

**No non-type-0 rows reach the committed record exports.** Compared all hotspot
records with a multiset of type-0 raw observations after box/confidence filtering
and the committed record window. Matching includes satellite, date, time,
coordinates, day/night, FRP, confidence, brightnesses, scan/track and version at
export precision. There were no extra/missing observations and no matching
non-type-0 fingerprints. Independently reconstructed burning-day groups from
type-0 inputs and matched location/date/family/day-night, detection count,
maximum FRP and FRP class exactly.

| Region | Committed hotspot rows matched | Burning-day records matched | Unmatched or non-type-0 matches |
|---|---:|---:|---:|
| Portugal | 214,712 | 135,574 | 0 |
| Lebanon | 14,976 | 12,285 | 0 |

The earlier 233/233 probe run also reconciled numerical weights and monthly
record/background totals; this audit did not rewrite or regenerate them.

Detailed evidence:

- [864-row type/sensor/year CSV](../analysis/tier1/existing_type_counts.csv), including
  separate Terra and Aqua rows, all six type categories, counts after each filter,
  and counts inside the committed record window.
- [Impact and reconciliation results](../analysis/tier1/existing_type_impact.json).
- [Read-only audit code](../tools/audit_existing_types.py).

## 2. FIRMS availability and missing-data services

Read `FIRMS_MAP_KEY` from ignored `.env` without printing it. Queried the three
standard-product availability endpoints successfully (HTTP 200). Queried the
missing-data page's actual public AJAX endpoint, which does not require the key,
with its documented page request header. Stored sanitized response snapshots and
checksums. No key appears in reports, logs, or source files.

| Standard product | Service minimum date | Service maximum date |
|---|---|---|
| MODIS_SP | 2000-11-01 | 2026-08-31 |
| VIIRS_SNPP_SP | 2012-01-20 | 2026-07-31 |
| VIIRS_NOAA20_SP | 2018-04-01 | 2026-07-31 |

The [availability service](https://firms.modaps.eosdis.nasa.gov/api/data_availability/)
provides global product date extents. It does not establish complete daily or
monthly spatial coverage of country files. The MODIS extent combines Terra and
Aqua and does not establish an individual satellite's operational start date.
The 2026 maxima are metadata only; no 2026 detections were acquired or integrated.

The [missing-data service](https://firms.modaps.eosdis.nasa.gov/api/missing_data/)
lists dates with missing database data, separately for standard and NRT products.
We used only its **standard** columns. It returned 169 standard entries across its
full date range; 123 concern the four production satellites during 2000–2025:

| Satellite | Listed dates with missing data, 2000–2025 | Affected months and number of listed dates |
|---|---:|---|
| Terra | 56 | 2001-06: 15; 2001-07: 2; 2002-03: 8; 2002-04: 1; 2003-12: 7; 2008-12: 2; 2016-02: 9; 2022-10: 12 |
| Aqua | 26 | 2002-07: 2; 2002-08: 7; 2002-09: 1; 2022-04: 16 |
| Suomi NPP | 35 | 2012-03: 1; 2022-07: 5; 2022-08: 10; 2024-05: 2; 2024-06: 3; 2024-07: 10; 2024-09: 1; 2024-11: 3 |
| NOAA-20 | 6 | 2023-07: 4; 2023-09: 1; 2024-02: 1 |

These establish known global gaps; they do not establish that an entire day is
missing everywhere or identify which country archives are affected. Absence from
the list is not a country-month completeness certificate. Consequently, country
monthly completeness remains **`unknown` for all regions in scope**. Keep known
global-gap evidence alongside that status; do not discard it or replace it with
zero detections. The source/archive availability decision remains separate.

The [1,248-row satellite/month ledger](../analysis/tier1/coverage_services/satellite_month_evidence.csv)
covers every month of 2000–2025 for Terra, Aqua, Suomi NPP and NOAA-20. It records
product-date-span membership (outside/partial/inside), exact listed missing dates,
and unknown country completeness. The same global evidence applies to Portugal,
Lebanon, Syria, Jordan, Cyprus, Palestine, Israel and the Argentina/La Rioja source;
the services do not supply country-specific completeness observations.

[Request provenance](../analysis/tier1/coverage_services/requests.json),
[parsed summary](../analysis/tier1/coverage_services/summary.json),
[query code](../tools/query_firms_coverage.py),
[parsing code](../tools/summarize_firms_coverage.py).
The ledger does not change the old exporter or research-table coverage assumptions.

## 3. Source audit: 2000–2017

All **144 expected files** passed checksum, schema, type, confidence and box
auditing: 18 MODIS plus six Suomi NPP annual files for each of six sources.
The 180 other sensor/year slots precede FIRMS product availability (Suomi NPP
2000–2011; NOAA-20 2000–2017) and are explicitly recorded as unavailable. They
were not converted to zero-fire observations. There are no unexpected missing
files or unresolved request failures in this requested range.

| Source | Files | Raw rows | Box retained | Box excluded | After box/type 0/confidence |
|---|---:|---:|---:|---:|---:|
| Syria | 24 | 91,429 | 91,429 | 0 | 67,490 |
| Jordan | 24 | 4,145 | 4,145 | 0 | 2,212 |
| Cyprus | 24 | 3,510 | 3,510 | 0 | 2,360 |
| Palestine | 24 | 2,605 | 2,605 | 0 | 2,278 |
| Israel | 24 | 11,928 | 11,928 | 0 | 6,672 |
| Argentina → La Rioja box | 24 | 2,290,133 | 60,316 | 2,229,817 | 56,225 |

All five whole-country boxes retain every source row, including rows subsequently
excluded by the fire-type/confidence filters. Every audited schema has `type`;
missing and unexpected type counts are zero. The existing 2018–2025 neighboring
audits plus this audit now cover all five neighbors' 2000–2025 production archives.

Argentina's exclusions are the explicitly intended rectangle. Reused original
country files from the supplied validation folder, verified their manifest hashes,
and independently compared the existing cropped files row-for-row against that
rectangle. All 24 crops match exactly: **no losses beyond the crop and no extra
rows**. Original NASA names, URLs and checksums are retained. The validation
folder was not modified; production `data/raw/la_rioja` mapping is still pending.

| Source | Bytes | Decimal MB | Sum of per-file elapsed seconds | Measurement |
|---|---:|---:|---:|---|
| Syria | 7,134,019 | 7.134019 | 71.684 | Download + audit |
| Jordan | 326,509 | 0.326509 | 27.539 | Download + audit |
| Cyprus | 276,790 | 0.276790 | 25.198 | Download + audit |
| Palestine | 206,225 | 0.206225 | 25.697 | Download + audit |
| Israel | 933,198 | 0.933198 | 33.157 | Download + audit |
| Argentina | 182,696,866 | 182.696866 | 15.529 | Cached originals: read + audit |

Total audited source bodies: **191,573,607 bytes** (191.573607 decimal MB).
Newly downloaded neighboring files total 8,876,741 bytes. Twenty-one individual
Argentina raw files exceed 3 decimal MB; all are listed with exact sizes in the
summary. These are source-body sizes, not browser or HTTP wire measurements.
Elapsed sums exclude work between files and are not total wall-clock duration.

Detailed evidence:

- [Summary and large-file flags](../analysis/tier1/source_audit_2000_2017_summary.json).
- [Per-file inventory, sizes, URLs and hashes](../analysis/tier1/source_audit_2000_2017_inventory.csv).
- [Neighbor filter counts and unavailable slots](../analysis/tier1/box_audit_2000_2017_neighbours.json).
- [Argentina filter counts and unavailable slots](../analysis/tier1/box_audit_2000_2017_argentina.json).
- [Exact crop reconciliation](../analysis/tier1/argentina_crop_2000_2017.json).

## Pause and verification

Four focused source-gate/lookup tests pass. Real-data checks passed for all 144
source hashes, all 24 crops, all existing hotspot and burning-day record matches,
and coverage-table structure/month enumeration. All 108 Portugal/Lebanon export
hashes and both frozen JSON hashes still match the baseline. No web files were
changed. A new browser run was unnecessary because this checkpoint only added
read-only auditing; the previous 233/233 result remains the baseline, not a claim
about new product behavior. `.env` remains ignored and untracked, and a local
credential scan found no key in audit outputs or source files.

**Paused at the requested checkpoint.** Boundaries, new exports and browser
aggregation have not started. Also still pending: detailed Argentina 2018–2024
filter/box audit (those originals were checksum-verified with the validation
evidence, but not audited to the same per-file filter contract), production
Argentina mapping, coverage-aware export design, geographic discrepancies,
cross-country reconciliation, events and load measurements. No model or export
changes are proposed to resolve the `unknown` coverage status at this checkpoint.
