# Data contract — the static files the website reads (v2)

Written by `pipeline/export_v2.py` into `web/data/`. The website (`web/app.js`) reads nothing else.
Rebuild with:

```bash
python pipeline/export_v2.py                  # every product region with raw files in data/raw/<region>/
python pipeline/export_v2.py --region lebanon # one region; the others in regions.json are kept
```

All files are UTF-8 JSON, no NaN or Infinity (the writer refuses them).

## Units and rules shared by every file

- **Unit:** fire detections (satellite pixels flagged as burning), in **MODIS-equivalent** counts. Not burned area.
- **Harmonized estimate (expected value):** the value shown and exported for every cell-month and area-month.
  It is an expected value, not a median: `m = Σ w + bg` (weights of the detections in that cell-month, plus the
  model's background term).
- **Filters** (same as `pipeline/02_aggregate.py`): the region's box from `pipeline/regions.py`
  (lon_min ≤ lon < lon_max, lat_min ≤ lat < lat_max); `type == 0`; MODIS `confidence >= 30`; VIIRS confidence `n` or `h`.
- **Grid:** global 0.25° cells, `ix = floor(lon / 0.25)`, `iy = floor(lat / 0.25)`. Cell `(ix, iy)` spans
  lon `ix*0.25 .. (ix+1)*0.25`, lat `iy*0.25 .. (iy+1)*0.25` (row `iy` counts **north**). Only cells with at least
  one filtered detection (any sensor, any year) are listed; a missing cell means zero, not missing data. The listed
  cells are also the region's **data footprint**: the website treats any part of a drawn area outside them (or outside
  the box) as outside the region's FIRMS country file.
- **Months:** `"YYYY-MM"`, index `j = 0` is `months.first`. The record starts at MODIS's first complete month by the
  rule below: both regions' files start after 3 November 2000, so the record starts **2000-12**.
- **Complete months** (lead's ruling): a sensor file's final month counts only if the file has a detection dated in
  that month's last 3 days; its first month only if it has one in the first 3 days. Every other month inside the
  file's span counts. The same rule sets the record's first month (MODIS) and its last (VIIRS).
  The record ends at the last month a VIIRS satellite covers — **2025-12** for both regions; 2026 to the present needs
  NASA's FIRMS near-real-time API key (pending). Details per sensor in `regions.json` `record_end`.
- **Which VIIRS satellite covers a month:** it is inside its complete span, and it is not an outage month (zero
  detections in the region while the other VIIRS satellite has 20 or more; none found so far).
- **Source policy** (one flag per month, the same for every cell):

| Flag | Months | Harmonized estimate |
|---|---|---|
| `B` bridged | 2000-12 .. 2002-06 | Terra detections ÷ Terra's share for that calendar month (below) |
| `O` observed | 2002-07 .. 2021-12 | MODIS Terra + Aqua detections (nominal orbits) |
| `E` estimated (S-NPP+NOAA-20) | 2022-01 .. | average of the Suomi NPP-based and the NOAA-20-based MODIS-equivalent estimates of model A |
| `N` estimated (S-NPP only) | 2022-01 .. | Suomi NPP-based estimate; NOAA-20 does not cover the month (Lebanon 2025-12) |
| `J` estimated (NOAA-20 only) | 2022-01 .. | NOAA-20-based estimate; Suomi NPP does not cover the month (after Suomi NPP ends) |
| `X` no data | 2022-01 .. | no VIIRS satellite covers the month (none so far) |

- **Terra share:** for calendar month m, from 2003–2011, `s_m = (T_m + 20 · s_pool) / (N_m + 20)`, where `N_m` =
  Terra + Aqua detections that month and `s_pool` = Terra / (Terra + Aqua) over all months. No month reaches 0 or 1.
- **Naive record** (for the toggle that shows the false jump): MODIS Terra + Aqua up to 2011-12 (Terra alone in
  bridged months, unscaled), raw Suomi NPP counts from 2012-01.
- **Model: A — shrinkage ratio (bake-off winner)** (`pipeline/weights_a.py`, which imports `fit_A` / `predict_A`
  from `pipeline/bakeoff/models.py`; evidence in `docs/BAKEOFF_RESULTS.md`). Fitted separately for Suomi NPP
  (2012-02..2019-12) and NOAA-20 (2018-04..2019-12) against Terra + Aqua, per footprint cell × calendar month ×
  day/night, a = 30. `pipeline/weights_interim.py` is the earlier placeholder, kept for reference and unused.
  **Frozen by construction:** each fit uses only the cells with a MODIS or that-satellite detection inside its window
  (its own footprint, as in the bake-off). Detections after the window, and cells that first burn after it, cannot
  change r0, b_A or the cell sums; a cell outside the fit's footprint gets A's region-level forecast for its slot
  (ratio r0, background b_A). `tools/probe_site.py` adds a synthetic 2023 detection in a new cell and checks the
  fitted arrays stay bit-identical.
- **Weights `w`:** every detection carries its contribution to the harmonized estimate of its month
  (`r_N`, `r_J1` = model A's posterior mean MODIS per detection of that satellite, for the detection's cell,
  calendar month and day/night: (a + ΣMODIS) / (a / r0 + ΣVIIRS); 0 where r0 = 0):

| Detection | `B` | `O` | `E` | `N` | `J` |
|---|---|---|---|---|---|
| Terra (T) | 1 / s_m | 1 | 0 | 0 | 0 |
| Aqua (A) | 0 | 1 | 0 | 0 | 0 |
| Suomi NPP (N) | 0 | 0 | ½ · r_N (r_N alone where NOAA-20's r0 = 0) | r_N | 0 |
| NOAA-20 (J1) | 0 | 0 | ½ · r_J1 (0 where its r0 = 0) | 0 | r_J1 |

- **Combination rule, decided 31 Oct 2026 after observing NOAA-20's short 21-month fit window.** Model A gives
  each VIIRS satellite a prior ratio r0 per region × calendar month × day/night slot (ΣMODIS / ΣVIIRS in its fit
  window). NOAA-20's window has months and times of day with no MODIS fire at all, so its r0 is 0 there and A gives
  its detections weight 0. In a month both satellites cover, a satellite enters a slot's average **only if its
  r0 > 0 in that slot**; if exactly one qualifies it carries the slot alone (share 1); if none qualifies, A's literal
  behaviour stays (detections weigh 0, background as fitted, shared between the covering satellites). Model A itself
  is not changed. Which satellites each slot uses is in `regions.json` `combination`; months where a satellite was
  left out carry a note in `monthly.json` `slot_notes` and in both CSVs' `source_flag`. Lebanon: 12 of 24 slots use
  Suomi NPP alone or neither; Portugal: November nights use Suomi NPP alone.
- **Background `bg`:** model A's forecast where a covering satellite saw nothing in a footprint cell × month ×
  day/night: b_A (the mean MODIS count in training rows with no VIIRS detection), times the satellite's share of that
  slot (½ or 1, by the combination rule). Only estimated months have one. Portugal's background adds 586 detections
  over 2022–2025, Lebanon's 25.

  So for any set of cells and months, **Σ harmonized estimate = Σ w + Σ bg**, up to rounding (`m` and `bg` to
  2 decimals per cell-month, `w` to 4 decimals per detection). `tools/probe_site.py` checks this through the two CSVs.

## `regions.json`

```jsonc
{
  "contract": "docs/DATA_CONTRACT.md", "version": 2, "generated_at": "2026-10-31T…Z",
  "regions": [{
    "id": "portugal", "name": "Portugal",
    "bbox": [lon_min, lat_min, lon_max, lat_max],
    "months": {"first": "2000-12", "last": "2025-12"},
    "record_end": {
      "suomi_npp": {"first": "2012-02", "last": "2025-12", "first_detection": "2012-01-20", "last_detection": "2025-12-31"},
      "noaa20":    {"first": "2018-04", "last": "2025-12", "first_detection": "2018-04-03", "last_detection": "2025-12-30"},
      "modis":     {"first": "2000-12", "last": "2025-11", "first_detection": "2000-11-06", "last_detection": "2025-11-28"},
      "detections_outside_record_dropped": 3, "viirs_outage_months": [], "rule": "…", "after": "2026 … API key (pending)"
    },
    "default_view": {"bounds": [[lon_min, lat_min], [lon_max, lat_max]]},
    "model": "A — shrinkage ratio (bake-off winner)",
    "model_detail": {                         // from weights_a.describe()
      "name": "A — shrinkage ratio (bake-off winner)", "a": 30,
      "satellites": {
        "snpp":   {"train": ["2012-02", "2019-12"], "prior_ratio_r0": {"01D": 0.328, …}, "background_bA": {"01D": …, …},
                   "r0_fallback_months": 0, "train_detections": {"modis": …, "snpp": …}, "train_rows": …},
        "noaa20": {"train": ["2018-04", "2019-12"], …same keys…}
      },
      "method": "…", "interval": "…", "evidence": "docs/BAKEOFF_RESULTS.md",
      "check": {"max_gap_between_A_predictive_mean_and_m": 0.0706, "background_total": 585.98}  // m vs A's own mean: rounding only
    },
    "combination": {"rule": "…", "slots_when_both_cover": {"01D": ["snpp", "noaa20"], …, "11N": ["snpp"], …}},
    "terra_share": {"years": [2003, 2011], "by_month": {"01": 0.4084, …}, "pooled": 0.4512, "prior_detections": 20,
                    "basis": {"01": "(89 Terra + 20 x 0.4512) / (220 MODIS + 20)", …}},
    "policy": {"bridged": [first, last], "observed": [first, last], "estimated": [first, last], "naive_switch": "2012-01"},
    "cells": 185,
    "hotspot_years": [2000, …, 2025],
    "sensors": {"T": "Terra MODIS", "A": "Aqua MODIS", "N": "Suomi NPP VIIRS", "J1": "NOAA-20 VIIRS"},
    "satellite_field": {"T": "Terra", "A": "Aqua", "N": "N", "J1": "N20"},   // the FIRMS `satellite` value, for CSV export
    "instrument_field": {"T": "MODIS", …},
    "versions": ["2", "6.03", "6.2", "61.03"],  // FIRMS `version` strings exactly as in the files; hotspots store an index
    "detections": {"N": …, "J1": …, "A": …, "T": …},  // after filters, 2000-11 .. months.last
    "provenance": {
      "source", "filters", "unit",
      "files": [{"name", "url", "sensor", "rows", "sha256", "retrieved", "sha256_ok"}]  // from data/raw/<region>/manifest.json;
    },                                                                                   // sha256_ok = the file on disk still matches
    "generated_at": "…"
  }]
}
```

## `<region>/monthly.json` — the harmonized estimate per cell

```jsonc
{
  "region": "portugal", "cell_deg": 0.25,
  "months": {"first": "2000-12", "last": "2025-12", "n": 301},
  "flags": "BBBB…OOO…EEE",                    // one character per month: B / O / E / N / J / X (table above)
  "flag_codes": {"B": "bridged", "O": "observed", "E": "estimated (S-NPP+NOAA-20)", "N": "estimated (S-NPP only)",
                 "J": "estimated (NOAA-20 only)", "X": "no data"},
  "slot_notes": {"2022-11": "night: S-NPP only", …},  // months where the combination rule left a satellite out of a time of day
  "cells": {"ix": [-38, …], "iy": [147, …]},  // cell c = (ix[c], iy[c])
  "m":     [[…n values…], …],                 // per cell: harmonized estimate (expected value) = Σ w + bg, 2 decimals
  "bg":    [[…], …],                          // per cell: background term already inside m (model A: b_A where VIIRS saw nothing)
  "p10":   [[…], …],                          // per cell: 10th percentile
  "p90":   [[…], …],                          // per cell: 90th percentile
  "naive": [[…], …]                           // per cell: naive record, integers
}
```

- `p10`/`p90`: in `E`, `N` and `J` months, from model A's predictive distribution per cell × month × day/night
  (negative binomial with size a + ΣMODIS and p = rate / (rate + V) where V > 0; Poisson(b_A) where V = 0), day and
  night added, the two satellites averaged (mean = Σ share × mean, variance = Σ share² × variance, as if independent),
  then the 10th/90th percentile of the negative binomial with that mean and variance (Poisson when the variance is not
  above the mean). **Approximate.** In `B` months: a placeholder, negative binomial with mean `m` and size 5 (model A
  describes VIIRS, not Terra alone). In `O` months `p10 = p90 = m`.
- `bg` is optional for readers: if absent, treat it as zero.

Sizes (31 Oct 2026): Portugal 1.03 MB (185 cells), Lebanon 0.16 MB (28 cells).

## How the website turns these into an area's calendar

- **Whole region:** the sum of its cells (`m`, `naive`, `bg`); the 80% range adds each cell's half-widths in quadrature.
  This equals the exact sum of every detection's weight, up to the 2-decimal rounding of `m`.
- **Drawn shape or circle (exact):** the website loads every hotspot year (cached, with a progress bar) and adds up
  `w` of the detections inside the shape, month by month, plus `bg` of each touched cell times the share of the cell
  inside the shape. The naive record counts the naive-record detections inside the shape. The 80% range scales each
  touched cell's half-widths by (the shape's weight in that cell ÷ the cell's `m`) and combines them in quadrature
  (approximate). An area with no detection inside is shown as "no detections here".
- **Quiet months:** an expected value under 0.5 counts as zero, before and after 2022 alike, for the colour and for
  every comparison (baseline, anomaly, rank, chance above the median, trust check). Where the baseline median is under
  5 ("few fires"), anomaly mode draws the month neutral with the few-fires mark and the panel gives the count against
  the typical range (interquartile range) in words, without a percentage or a chance. No percentage is ever taken
  against a normal under 1.
- **Failed loads:** if a hotspot year cannot be loaded, the area shows no numbers (no calendar, no panel values),
  the downloads are disabled, and the area names the year with a retry button.
- **Shapes:** a shape that reaches both product regions is shown for one, with a note; a shape containing a whole
  region says so instead of reporting a share "outside".
- **Outside the data:** the share of a drawn area outside the box or outside the data footprint (cells listed above)
  is shown as a warning and in the area's name; fires there are not in the country file and are not counted.

## `<region>/hotspots/<year>.json` — every filtered detection, columnar

```jsonc
{
  "region": "portugal", "year": 2017, "n": 31234,
  "cols": {
    "lat": [...], "lon": [...],               // degrees, 5 decimals
    "doy": [...],                             // day of year (1 = 1 Jan); acq_date = year + doy
    "time": [...],                            // acq_time HHMM UTC as an integer (130 = 01:30)
    "sensor": [...],                          // index into ["T", "A", "N", "J1"]
    "dn": [...],                              // 0 = day, 1 = night
    "frp": [...],                             // MW, 2 decimals
    "conf": [...],                            // MODIS: integer 30..100; VIIRS: "n" or "h"
    "w": [...],                               // contribution to the harmonized estimate, 4 decimals (table above)
    "bright": [...], "bright2": [...],        // MODIS brightness / bright_t31; VIIRS bright_ti4 / bright_ti5 (K)
    "scan": [...], "track": [...],            // pixel size, km
    "version": [...]                          // index into regions.json versions (exact FIRMS strings)
  }
}
```

Rows are sorted by date, time, sensor. `type` is 0 for every row (filter). Only months inside the record are written.
Sizes: Portugal 14.6 MB over 26 files (largest 2025, about 2 MB), Lebanon 1.0 MB.

## `<region>/drift.json` — is MODIS still MODIS?

```jsonc
{
  "region": "portugal",
  "months": {"first": "2012-02", "last": "2025-11", "n": 166},   // Suomi NPP's first full month .. MODIS's last complete month
  "observed_modis": [...],                    // Terra + Aqua detections in the region, per month
  "predicted_modis": [...],                   // MODIS predicted by model A (weights + background) from each covering VIIRS
                                              // satellite, averaged when both cover the month (as the estimated record), 2 decimals
  "trailing12_ratio": [null × 11, ...],       // Σ observed / Σ predicted over the 12 months ending here
  "band": {"what": "…", "range": [lo, hi], "fitted": ["2012-02", "2019-12"]},  // min–max of the trailing ratio, windows ending in 2012-02..2019-12
  "predicted_from": "model A from Suomi NPP and NOAA-20 (weights + background), averaged in months both cover",
  "model": "A — shrinkage ratio (bake-off winner)",
  "modis_archive_ends": "2025-11-28",
  "complete_rule": "a file's final month counts if it has a detection in that month's last 3 days"
}
```

Lebanon's MODIS file ends 2025-11-23, so its drift series ends 2025-10.

## CSV downloads (written by the website)

- **Hotspots:** `latitude, longitude, brightness, bright_t31, bright_ti4, bright_ti5, scan, track, acq_date, acq_time,
  satellite, instrument, confidence, version, frp, daynight, type, sensor, source_flag, w` — every detection inside
  the exact area for the chosen years; `version` exactly as in the FIRMS file; `source_flag` is the month's flag name,
  followed by its slot note in parentheses where the combination rule left a satellite out.
- **Monthly:** a `#` methods line, then `month, harmonized_estimate, p10, p90, naive, background, source_flag` for the
  area (4 decimals for the estimate and the background). `harmonized_estimate` already includes `background`;
  `source_flag` carries the slot note as in the hotspot CSV.

## The model interface

`export_v2.py` talks to the model only through `pipeline/weights_a.py` (the same functions as `weights_interim.py`):

```python
model = fit(det, region)                     # det: filtered detections (columns month, moy, dn, fam, …); fits never see 2020+
w = hotspot_weights(model, rows)             # full weight of each Suomi NPP or NOAA-20 row; the export applies the ½ share
bg = cell_month_background(model, grid)      # grid: one row per cell-month: ci, moy, m, share_N, share_J1, V_N_D, V_N_N, V_J1_D, V_J1_N
p10, p90 = cell_month_interval(model, grid)  # same grid rows (estimated months)
describe(model)                              # dict stored as regions.json model_detail
```

A replacement module with the same functions and a different `NAME` changes `"model"` in `regions.json`
and nothing else in the contract. The bake-off as pre-registered fitted model A to Suomi NPP only; the product also
fits it to NOAA-20 (2018-04..2019-12, 21 months), which the bake-off did not test.
