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
  one filtered detection (any sensor, any year) are listed; a missing cell means zero, not missing data.
- **Months:** `"YYYY-MM"`, index `j = 0` is `months.first`. The record starts 2000-11 (Terra's first full month).
- **Where the record ends:** at Suomi NPP's last complete month. A sensor file's final month counts as complete only
  if it has detections on at least 20 distinct days in the region; otherwise it is dropped, with every detection in it
  (all sensors). For MODIS the same rule ends the drift series. In both regions the files' final months had too few
  days, so the record ends **2025-11** and the drift series **2025-10** (details in `regions.json` `record_end`).
- **Source policy** (one flag per month, the same for every cell):

| Flag | Months | Harmonized estimate |
|---|---|---|
| `B` bridged | 2000-11 .. 2002-06 | Terra detections ÷ Terra's share for that calendar month (below) |
| `O` observed | 2002-07 .. 2021-12 | MODIS Terra + Aqua detections (nominal orbits) |
| `E` estimated | 2022-01 .. last | Suomi NPP VIIRS detections × the weight model (MODIS drifted) |

- **Terra share** (lead's ruling, 31 Oct): for calendar month m, from 2003–2011,
  `s_m = (T_m + 20 · s_pool) / (N_m + 20)`, where `N_m` = Terra + Aqua detections that month and
  `s_pool` = Terra / (Terra + Aqua) over all months. No month can reach 0 or 1.
- **Naive record** (for the toggle that shows the false jump): MODIS Terra + Aqua up to 2011-12 (Terra alone in
  bridged months, unscaled), raw Suomi NPP counts from 2012-01.
- **Weights `w`:** every detection carries its contribution to the harmonized estimate of its month:

| Detection | In a `B` month | In an `O` month | In an `E` month |
|---|---|---|---|
| Terra (T) | 1 / s_m | 1 | 0 |
| Aqua (A) | 0 | 1 | 0 |
| Suomi NPP (N) | 0 | 0 | model weight |
| NOAA-20 (J1) | 0 | 0 | 0 |

  So for any set of cells and months, **Σ harmonized estimate = Σ w + Σ bg**, up to rounding (`m` and `bg` to
  2 decimals per cell-month, `w` to 4 decimals per detection). `tools/probe_site.py` checks this through the two CSVs.

## `regions.json`

```jsonc
{
  "contract": "docs/DATA_CONTRACT.md", "version": 2, "generated_at": "2026-10-31T…Z",
  "regions": [{
    "id": "portugal", "name": "Portugal",
    "bbox": [lon_min, lat_min, lon_max, lat_max],
    "months": {"first": "2000-11", "last": "2025-11"},
    "record_end": {
      "suomi_npp_last_detection": "2025-12-31", "final_month_days": 8,
      "modis_last_detection": "2025-11-28", "modis_final_month_days": 12, "modis_complete_through": "2025-10",
      "detections_after_record_dropped": 29, "rule": "…>= 20 distinct days"
    },
    "default_view": {"bounds": [[lon_min, lat_min], [lon_max, lat_max]]},
    "model": "interim",                       // name of the weight model; "interim" until the bake-off winner replaces it
    "model_detail": {                         // from weights_interim.describe()
      "name", "train": ["2012-02", "2019-12"],
      "ratio": {"01D": 0.3337, "01N": 0.1084, …},       // MODIS-equivalent per Suomi NPP detection, calendar month x day(D)/night(N)
      "ratio_basis": {"01D": "<MODIS> MODIS / <V> Suomi NPP", …},  // raw training counts behind each ratio
      "shrinkage": "each ratio = (MODIS + 30 x pooled) / (Suomi NPP + 30), pooled per day/night",
      "pooled_ratio": {"D": 0.4759, "N": 0.2892},
      "overall_ratio", "train_detections": {"modis", "snpp"}, "interval": "…placeholder…"
    },
    "terra_share": {"years": [2003, 2011], "by_month": {"01": 0.4084, …}, "pooled": 0.4512, "prior_detections": 20,
                    "basis": {"01": "(89 Terra + 20 x 0.4512) / (220 MODIS + 20)", …}},
    "policy": {"bridged": [first, last], "observed": [first, last], "estimated": [first, last], "naive_switch": "2012-01"},
    "cells": 185,
    "hotspot_years": [2000, …, 2025],
    "sensors": {"T": "Terra MODIS", "A": "Aqua MODIS", "N": "Suomi NPP VIIRS", "J1": "NOAA-20 VIIRS"},
    "satellite_field": {"T": "Terra", "A": "Aqua", "N": "N", "J1": "N20"},   // the FIRMS `satellite` value, for CSV export
    "instrument_field": {"T": "MODIS", …},
    "versions": ["2.0", "6.03", "6.2", "61.03"],  // FIRMS `version` values; hotspot files store an index into this
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
  "months": {"first": "2000-11", "last": "2025-11", "n": 301},
  "flags": "BBBB…OOO…EEE",                    // one character per month: B / O / E
  "flag_codes": {"B": "bridged", "O": "observed", "E": "estimated"},
  "cells": {"ix": [-38, …], "iy": [147, …]},  // cell c = (ix[c], iy[c])
  "m":     [[…n values…], …],                 // per cell: harmonized estimate (expected value) = Σ w + bg, 2 decimals
  "bg":    [[…], …],                          // per cell: background term already inside m (interim model: all 0)
  "p10":   [[…], …],                          // per cell: 10th percentile
  "p90":   [[…], …],                          // per cell: 90th percentile
  "naive": [[…], …]                           // per cell: naive record, integers
}
```

- `p10`/`p90`: in `E` **and** `B` months, the 10th/90th percentile of a negative binomial with mean `m` and size 5 —
  an **interim placeholder, not fitted to data, replaced by the bake-off winner**. In `O` months `p10 = p90 = m`.
- `bg` is optional for readers: if absent, treat it as zero.
- Area values in the website: sum `m` over cells whose **centre** is inside the area (cell-level approximation);
  `lo = Σm − sqrt(Σ(m − p10)²)` (floored at 0), `hi = Σm + sqrt(Σ(p90 − m)²)` (approximate: cells treated as independent).

Sizes (31 Oct 2026): Portugal 1.01 MB (185 cells), Lebanon 0.15 MB (28 cells).

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
    "version": [...]                          // index into regions.json versions
  }
}
```

Rows are sorted by date, time, sensor. `type` is 0 for every row (filter). Only months inside the record are written.
Sizes: Portugal 14.5 MB over 26 files (largest 2025, about 2 MB), Lebanon 1.0 MB. The website loads a year only
when a download or the season dates need it.

## `<region>/drift.json` — is MODIS still MODIS?

```jsonc
{
  "region": "portugal",
  "months": {"first": "2012-02", "last": "2025-10", "n": 165},   // Suomi NPP's first full month .. MODIS's last complete month
  "observed_modis": [...],                    // Terra + Aqua detections in the region, per month
  "predicted_modis": [...],                   // Σ model weight over every Suomi NPP detection that month (2 decimals)
  "trailing12_ratio": [null × 11, ...],       // Σ observed / Σ predicted over the 12 months ending here
  "band": {"what": "…", "range": [0.8685, 1.0894], "fitted": ["2012-02", "2019-12"]},  // min–max of the trailing ratio, windows ending inside the fitting years
  "modis_archive_ends": "2025-11-28",
  "complete_rule": "a sensor file's final month counts only with detections on >= 20 distinct days"
}
```

## CSV downloads (written by the website)

- **Hotspots:** `latitude, longitude, brightness, bright_t31, bright_ti4, bright_ti5, scan, track, acq_date, acq_time,
  satellite, instrument, confidence, version, frp, daynight, type, sensor, source_flag, w` — every detection inside
  the exact area for the chosen years.
- **Monthly:** a `#` methods line, then `month, harmonized_estimate, p10, p90, naive, background, source_flag` for the
  area (cell-level approximation). `harmonized_estimate` already includes `background`.

## Swapping in the bake-off winner

`export_v2.py` talks to the model only through `pipeline/weights_interim.py`:

```python
model = fit(det, region)                     # det: filtered detections (columns month, moy, dn, fam, …); fit uses 2012-02..2019-12 only
w = hotspot_weights(model, rows)             # weight of each Suomi NPP row in an estimated month
bg = cell_month_background(model, grid)      # grid: one row per cell-month (ci, mi, month, w); expected detections no row carries
p10, p90 = cell_month_interval(model, cm)    # cm: DataFrame with column m (the cell-month expected value)
describe(model)                              # dict stored as regions.json model_detail
```

A replacement module with the same five functions and a different `NAME` changes `"model"` in `regions.json`
and nothing else in the contract. A model with a term for cells or months without VIIRS detections (bake-off
candidate A's `b_A`, candidate B's `b`) returns it from `cell_month_background`; it lands in `bg`, is included in `m`,
and the CSV check becomes Σ harmonized estimate = Σ w + Σ background.
