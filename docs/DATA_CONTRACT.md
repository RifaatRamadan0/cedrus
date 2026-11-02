# Data contract — the static files the website reads (v2)

Written by `pipeline/export_v2.py` into `web/data/`. The website (`web/app.js`) reads nothing else.
Rebuild with:

```bash
python pipeline/export_v2.py                  # every product region with raw files in data/raw/<region>/
python pipeline/export_v2.py --region lebanon # one region; the others in regions.json are kept
```

All files are UTF-8 JSON, no NaN or Infinity (the writer refuses them).

## Two units, one record (lead's decision, 2 Nov 2026)

The calendar has two views of the same record, policy and areas, switched with one click. By the "what ships" rule of
`docs/TOURNAMENT_PLAN.md`, the round-3 champion passed (`docs/ROUND3_CONFIRMATION.md`), so its unit is the default.

| View | Unit | Model | Files |
|---|---|---|---|
| **Burning days** (default) | MODIS-equivalent burning days | D-a + NOAA-20 via Suomi NPP, round-3 confirmed (`pipeline/weights_bd.py`) | `monthly_bd.json`, `drift_bd.json`, `burning/<year>.json`; `regions.json` `burning_days` |
| **Hotspots** | MODIS-equivalent detections (the challenge's unit) | A2 + NOAA-20 via Suomi NPP, round-2 confirmed (`pipeline/weights_r2.py`) | `monthly.json`, `drift.json`, `hotspots/<year>.json`; `regions.json` top-level model fields |

`regions.json` `default_unit` is `"burning_days"`. The website remembers a reader's choice for the browser tab's session
(`sessionStorage` key `cedrus.unit`). Everything in "Units and rules shared by every file" below holds for both views,
with "detection" read as "burning day" in the burning-day files; the differences are in "The burning-day view" further
down. The hotspot files are unchanged by the second view (byte-identical on re-export).

## Units and rules shared by every file

- **Unit (hotspot view):** fire detections (satellite pixels flagged as burning), in **MODIS-equivalent** counts. Not burned area.
- **Unit (burning-day view):** **MODIS-equivalent burning days**: how many days each 0.01° square (about 1 km) had a
  fire detected. Not burned area either. Defined under "The burning-day view".
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
| `E` estimated (S-NPP+NOAA-20) | 2022-01 .. | average of the Suomi NPP-based and the NOAA-20-based MODIS-equivalent estimates (round-2 model) |
| `N` estimated (S-NPP only) | 2022-01 .. | Suomi NPP-based estimate; NOAA-20 does not cover the month (Lebanon 2025-12) |
| `J` estimated (NOAA-20 only) | 2022-01 .. | NOAA-20-based estimate; Suomi NPP does not cover the month (after Suomi NPP ends) |
| `X` no data | 2022-01 .. | no VIIRS satellite covers the month (none so far) |

- **Terra share:** for calendar month m, from 2003–2011, `s_m = (T_m + 20 · s_pool) / (N_m + 20)`, where `N_m` =
  Terra + Aqua detections that month and `s_pool` = Terra / (Terra + Aqua) over all months. No month reaches 0 or 1.
- **Naive record** (for the toggle that shows the false jump): MODIS Terra + Aqua up to 2011-12 (Terra alone in
  bridged months, unscaled), raw Suomi NPP counts from 2012-01.
- **Model: A2 + NOAA-20 via Suomi NPP (round-2 choice, frozen)** (`pipeline/weights_r2.py`, which imports
  `fit_A2` / `predict_A2` / `fit_s` from `pipeline/round2/models.py`; selection in `docs/ROUND2_SELECTION.md`, frozen
  at commit 617daff). The export reads a, the fit windows and the bootstrap settings from
  `data/processed/round2/frozen.json` and stops unless that file's SHA-256 is
  `bedc56d5ba85b851931cd6912dfcab832dc38b26a8fe80712a72974cf46e0686`.
  - **A2** = the bake-off's A with its ratio sums (prior r0 and the cell sums) taken over rows with Suomi NPP > 0
    only; rows with Suomi NPP = 0 predict Poisson(b), b = A's b_A. Fitted on Suomi NPP against Terra + Aqua,
    2012-02..2019-12, per cell × calendar month × day/night, a = 30.
  - **NOAA-20 via Suomi NPP (J-S)**: s = ΣSuomi NPP / ΣNOAA-20 per region × day/night over 2018-04..2019-12
    (month-block bootstrap for Var(s)); a NOAA-20 detection is multiplied by s and goes through A2.
  - Round 1's model A (`pipeline/weights_a.py`) failed its sealed confirmation (`docs/CONFIRMATION_RESULTS.md`);
    it and `pipeline/weights_interim.py` are kept for reference and unused.
  - **Frozen by construction:** the fit uses only cells with a MODIS, Suomi NPP or NOAA-20 detection in
    2012-02..2019-12. Detections after the window, and cells that first burn after it, cannot change r0, b, the cell
    sums or s; a cell outside the fit's footprint gets A2's region-level forecast for its slot (ratio r0,
    background b). `tools/probe_site.py` adds a synthetic 2023 detection in a new cell and checks the fitted arrays
    stay bit-identical.
- **Weights `w`:** every detection carries its contribution to the harmonized estimate of its month
  (`r` = A2's posterior mean MODIS per Suomi NPP detection for the detection's cell, calendar month and day/night,
  (a + ΣMODIS) / (a / r0 + ΣSuomi NPP) over rows with Suomi NPP > 0, 0 where r0 = 0; `s` = NOAA-20's factor for its
  day/night):

| Detection | `B` | `O` | `E` | `N` | `J` |
|---|---|---|---|---|---|
| Terra (T) | 1 / s_m | 1 | 0 | 0 | 0 |
| Aqua (A) | 0 | 1 | 0 | 0 | 0 |
| Suomi NPP (N) | 0 | 0 | ½ · r | r | 0 |
| NOAA-20 (J1) | 0 | 0 | ½ · s · r | 0 | s · r |

- **Combination rule, decided 31 Oct 2026 after observing NOAA-20's short 21-month fit window** (kept for the
  round-2 model): in a month both satellites cover, a satellite enters a slot's average only if its ratio is above
  0 there (r0 for Suomi NPP, s · r0 for NOAA-20); if exactly one qualifies it carries the slot alone; if none
  qualifies, the model's literal behaviour stays (detections weigh 0, background as fitted). With J-S both satellites
  share A2's r0, so in practice a slot has both or neither: Lebanon has 8 slots with r0 = 0 (01D, 01N, 02N, 03D,
  03N, 04N, 05N, 06N), Portugal none. `regions.json` `combination` lists the slots; `monthly.json` `slot_notes` and
  both CSVs' `source_flag` name the months concerned.
- **Background `bg`:** the model's forecast where a covering satellite saw nothing in a footprint cell × month ×
  day/night: b (A's b_A, the mean MODIS count in training rows with no Suomi NPP detection), times the satellite's
  share of that slot. Only estimated months have one. Portugal's background adds 641 detections over 2022–2025,
  Lebanon's 21.

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
    "model": "A2 + NOAA-20 via Suomi NPP (round-2 choice, frozen)",
    "model_detail": {                         // from weights_r2.describe()
      "name": "A2 + NOAA-20 via Suomi NPP (round-2 choice, frozen)", "badge": "MODEL A2 · ROUND 2, FROZEN", "a": 30,
      "frozen": {"file": "data/processed/round2/frozen.json", "sha256": "bedc56d5…", "commit": "617daff",
                 "selection": "docs/ROUND2_SELECTION.md"},
      "satellites": {
        "snpp":   {"train": ["2012-02", "2019-12"], "method": "A2", "prior_ratio_r0": {"01D": …, …},
                   "background_b": {"01D": …, …}, "train_detections": {"modis": …, "snpp": …}},
        "noaa20": {"train": ["2018-04", "2019-12"], "method": "J-S: x s (NOAA-20 to Suomi NPP), then A2",
                   "s": {"D": …, "N": …}, "s_sd": {"D": …, "N": …}, "prior_ratio_r0": {"01D": s x r0, …},
                   "train_detections": {"snpp": …, "noaa20": …}}
      },
      "fit_cells": …, "cells_outside_fit_region_level": …,
      "method": "…", "interval": "…", "evidence": ["docs/ROUND2_SELECTION.md", "docs/CONFIRMATION_RESULTS.md"],
      "check": {"max_gap_between_model_predictive_mean_and_m": 0.0824, "background_total": 640.71}  // rounding only
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
  "bg":    [[…], …],                          // per cell: background term already inside m (the model's b where VIIRS saw nothing)
  "p10":   [[…], …],                          // per cell: 10th percentile
  "p90":   [[…], …],                          // per cell: 90th percentile
  "naive": [[…], …]                           // per cell: naive record, integers
}
```

- `p10`/`p90`: in `E`, `N` and `J` months, from the model's predictive distribution per cell × month × day/night
  (A2: negative binomial with size a + ΣMODIS and p = rate / (rate + V) where V > 0, Poisson(b) where V = 0; for
  NOAA-20, V = s · V20 and the variance gains (r · V20)² · Var(s)), day and night added, the two satellites averaged
  (mean = Σ share × mean, variance = Σ share² × variance, as if independent), then the 10th/90th percentile of the
  negative binomial with that mean and variance (Poisson when the variance is not above the mean). **Approximate**:
  s is shared by every cell of a region, so area ranges added in quadrature understate its part. In `B` months: a
  placeholder, negative binomial with mean `m` and size 5 (the model describes VIIRS, not Terra alone). In `O` months
  `p10 = p90 = m`.
- `bg` is optional for readers: if absent, treat it as zero.

Sizes (31 Oct 2026): Portugal 1.03 MB (185 cells), Lebanon 0.16 MB (28 cells).
`monthly_bd.json` has the same layout and cells, in burning days, plus `"unit": "burning days"` (2 Nov 2026: Portugal
1.03 MB, Lebanon 0.16 MB).

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
  "predicted_modis": [...],                   // MODIS predicted by the model (weights + background) from each covering VIIRS
                                              // satellite, averaged when both cover the month (as the estimated record), 2 decimals
  "trailing12_ratio": [null × 11, ...],       // Σ observed / Σ predicted over the 12 months ending here
  "band": {"what": "…", "range": [lo, hi], "fitted": ["2012-02", "2019-12"]},  // min–max of the trailing ratio, windows ending in 2012-02..2019-12
  "predicted_from": "the model, from Suomi NPP and NOAA-20 (weights + background), combined as the estimated record",
  "model": "A2 + NOAA-20 via Suomi NPP (round-2 choice, frozen)",
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

## The burning-day view

### The unit

A **burning day** is the tournament's unit (`pipeline/tournament/data.py`, `docs/TOURNAMENT_RESULTS.md` deviation 11),
built from the same filtered detections as the hotspot view:

- Each detection's **square** is the 0.01° cell `fx = floor(longitude / 0.01)`, `fy = floor(latitude / 0.01)` of its
  FIRMS coordinates as written in the file (not the 5-decimal rounding stored in `hotspots/`).
- A burning day is one **family × 0.25° cell × square × date (`acq_date`, UTC) × day/night** with at least one
  detection. Families: **MODIS** (Terra and Aqua together), **Suomi NPP**, **NOAA-20**. So a square seen by Terra and
  Aqua on the same date and time of day is one MODIS burning day; seen by Suomi NPP too, it is also one Suomi NPP
  burning day.
- Its **FRP class** is the class of its largest-FRP detection: `f0` FRP ≤ 0 (or missing), `f1` 0 < FRP < 5,
  `f2` 5 ≤ FRP < 20, `f3` FRP ≥ 20 MW. D-a reads the class of VIIRS burning days only; MODIS burning days carry one too,
  for information.
- No square straddles two 0.25° cells: the export checks `floor(fx / 25) = ix` and `floor(fy / 25) = iy` for every
  burning day and stops otherwise, so a burning day's 0.25° cell is found from its square by integer division.
- The export also checks that, inside 2012-02..2019-12, its burning days counted per 0.25° cell × month × day/night and
  by family and FRP class equal the table D-a was fitted on (`regions.json` `burning_days.model_detail.check
  .fit_table_burning_days_matched` is that total: Portugal 56,912, Lebanon 4,223).

### Source policy (the same months and flags as the hotspot view)

| Flag | Months | Harmonized estimate, in burning days |
|---|---|---|
| `B` bridged | 2000-12 .. 2002-06 | MODIS burning days (Terra alone flew; the export checks no Aqua detection) ÷ Terra's share for that calendar month |
| `O` observed | 2002-07 .. 2021-12 | MODIS burning days (Terra and Aqua together) |
| `E` / `N` / `J` | 2022-01 .. | from VIIRS burning days by D-a, the two satellites averaged or whichever covers, exactly as the hotspot view |

- **Terra share in burning days:** for calendar month m, from 2003–2011, `s_m = (T_m + 20 · s_pool) / (N_m + 20)`,
  where `T_m` = Terra's own burning days (its detections alone, the same key) and `N_m` = MODIS burning days (Terra
  and Aqua together) that month, `s_pool` = ΣT / ΣN over all months. The same shrink rule as the hotspot view.
  `regions.json` `burning_days.terra_share` holds the values and their basis.
- **Naive record:** MODIS burning days up to 2011-12, raw Suomi NPP burning days from 2012-01.
- **Which satellite covers a month, outages, record start and end:** the hotspot view's, shared (they are decided on
  detections).

### Model: D-a + NOAA-20 via Suomi NPP (round-3 confirmed)

`pipeline/weights_bd.py` refits, on each product region's own rows, exactly what the round-3 exam refitted, through the
same code: `pipeline.round3.data.rows` / `burning_days` (round 2's rows in the tournament's unit),
`pipeline.round3.model.fit_frozen` (the tournament's `C3` with the frozen a = 10), `pipeline.round2.models.fit_s`.
It reads a only from `data/processed/tournament/frozen_round3.json` and stops unless that file's SHA-256 is
`f3130df9ed80894e0176866cd3c8e51a3c4a7233c3cb40dd1c7b93651d4357a2` (`pipeline.round3.data.load_frozen`).

- **Frozen by construction:** only detections dated 2012-02..2019-12 are passed to the fit; the rows are the cells with
  a MODIS, Suomi NPP or NOAA-20 detection in that window. A cell outside that footprint gets D-a's region-level ratio
  r0_k for its slot and class, and its background is region-level.
- **D-a:** per 0.25° cell × calendar month × day/night × FRP class k, posterior MODIS burning days per Suomi NPP
  burning day `r_k = (a + SY_k) / (a / r0_k + SV_k)`, sums over training rows with Suomi NPP > 0, MODIS split over the
  classes at the fitted fixed point; 0 where r0_k = 0. Rows where Suomi NPP saw nothing predict Poisson(b), b = mean
  MODIS burning days in such training rows.
- **NOAA-20 (J-S):** s = ΣSuomi NPP / ΣNOAA-20 burning days per day/night over 2018-04..2019-12, month-block bootstrap
  for Var(s) (200 resamples, seeded with the label ("product", region, "J-S", "burning days")); a NOAA-20 burning day
  is multiplied by s and goes through D-a.
- **Weights `w`** (per burning day; `share` = the satellite's share of the month × day/night, ½ or 1, by the
  combination rule):

| Burning day | `B` | `O` | `E` / `N` / `J` |
|---|---|---|---|
| MODIS | 1 / s_m | 1 | 0 |
| Suomi NPP, class k | 0 | 0 | share · r_k |
| NOAA-20, class k | 0 | 0 | share · s · r_k |

  D-a's predictive mean is linear in the class counts, so for every cell-month the weights plus the background are
  its mean; `regions.json` `burning_days.model_detail.check.max_gap_between_model_predictive_mean_and_m` is the
  largest difference, rounding only (Portugal 0.0126, Lebanon 0.0050).
- **Combination rule:** the hotspot view's, with "ratio above 0" read as "some FRP class has r0_k > 0 in the slot (and
  s > 0 for NOAA-20)". In both product regions every slot has one, so both satellites always share a month they both
  cover and no slot note is written (`burning_days.combination`). A class whose r0_k is 0 weighs 0 (Portugal's and
  Lebanon's `f0` in every slot, Portugal's `f3` in January nights, and Lebanon's `f1`–`f3` in several slots, mostly
  winter and spring: `burning_days.model_detail.satellites.snpp.prior_ratio_r0`, one list of four classes per slot).
- **Background, `p10`/`p90`:** as the hotspot view, from D-a's predictive: the class negative binomials summed and
  moment-matched per cell × month × day/night (Poisson(b) where V = 0), plus (mean / s)² · Var(s) for NOAA-20, day and
  night added, the satellites combined with their shares. Bridged months keep the placeholder (negative binomial, mean
  `m`, size 5). Approximate in the same ways.

### `<region>/burning/<year>.json` — every burning day, columnar

```jsonc
{
  "region": "portugal", "year": 2017, "n": 14022,
  "x0": -950, "y0": 3702,                    // the region's smallest fx and fy (the same in every year's file)
  "cols": {
    "x": [...], "y": [...],                  // fx - x0, fy - y0: the 0.01 deg square is fx = x0 + x, fy = y0 + y
    "doy": [...],                            // day of year of acq_date (1 = 1 Jan)
    "dn": [...],                             // 0 = day, 1 = night
    "fam": [...],                            // 0 = MODIS (Terra + Aqua), 1 = Suomi NPP, 2 = NOAA-20
    "k": [...],                              // FRP class of the largest-FRP detection, 0..3 (f0..f3)
    "nd": [...],                             // detections in it
    "frp": [...],                            // its largest FRP, MW, 2 decimals (null if every FRP is missing)
    "w": [...]                               // contribution to the harmonized estimate, 4 decimals (table above)
  }
}
```

Rows are sorted by date, day/night, family, fy, fx. Only months inside the record are written. Sizes (2 Nov 2026):
Portugal 135,574 burning days, 3.99 MB over 25 files (largest 2025, 0.45 MB); Lebanon 12,285, 0.35 MB.

### `<region>/drift_bd.json`

The layout of `drift.json`, plus `"unit": "burning days"`: observed MODIS burning days against MODIS burning days
predicted by D-a from Suomi NPP and NOAA-20 burning days (weights + background), combined as the estimated record.

### `regions.json` `burning_days`

```jsonc
"burning_days": {
  "unit": "MODIS-equivalent burning days: …", "definition": "…",
  "files": {"monthly": "monthly_bd.json", "drift": "drift_bd.json", "records": "burning/<year>.json"},
  "fine_cell_deg": 0.01, "origin": {"x0": -950, "y0": 3702},
  "model": "D-a + NOAA-20 via Suomi NPP (burning days, round-3 confirmed)",
  "model_detail": {                          // from weights_bd.describe()
    "name": "…", "badge": "D-a · ROUND 3 CONFIRMED", "a": 10, "unit": "burning days",
    "frozen": {"file": "data/processed/tournament/frozen_round3.json", "sha256": "f3130df9…", "commit": "80e297f",
               "confirmation": "docs/ROUND3_CONFIRMATION.md"},
    "classes": "f0 FRP <= 0, …",
    "satellites": {
      "snpp":   {"train": ["2012-02", "2019-12"], "method": "…", "prior_ratio_r0": {"01D": [r0_f0, r0_f1, r0_f2, r0_f3], …},
                 "background_b": {"01D": …, …}, "train_burning_days": {"modis": …, "snpp": …}},
      "noaa20": {"train": ["2018-04", "2019-12"], "method": "…", "s": {"D": …, "N": …}, "s_sd": {"D": …, "N": …},
                 "train_burning_days": {"snpp": …, "noaa20": …}}
    },
    "fit_cells": …, "cells_outside_fit_region_level": …, "em": {"iterations": …, "delta": …, "converged": true},
    "method": "…", "interval": "…", "evidence": ["docs/ROUND3_CONFIRMATION.md", "docs/TOURNAMENT_RESULTS.md"],
    "check": {"max_gap_between_model_predictive_mean_and_m": …, "background_total": …, "fit_table_burning_days_matched": …}
  },
  "combination": {"rule": "…", "slots_when_both_cover": {"01D": ["snpp", "noaa20"], …}},
  "terra_share": {"years": [2003, 2011], "by_month": {"01": …}, "pooled": …, "prior_burning_days": 20, "basis": {…}},
  "years": [2001, …, 2025],                  // years with a burning/<year>.json
  "records": {"modis": …, "snpp": …, "noaa20": …}
}
```

### How the website turns burning days into an area's calendar (exact)

- **Whole region:** the sum of the cells of `monthly_bd.json`, as the hotspot view.
- **Drawn shape or circle:** a burning day is **inside** the shape when the **centre of its square**,
  `((x0 + x + 0.5) × 0.01, (y0 + y + 0.5) × 0.01)` in IEEE double arithmetic, is inside the shape (the same
  ray-casting test as for hotspots). The area's harmonized estimate for a month is Σ `w` of the burning days inside,
  plus `bg` of each touched 0.25° cell times the share of the cell inside the shape (as the hotspot view). The naive
  record counts the naive-record burning days inside. One rule decides membership, and every burning day has exactly
  one point, so the same burning days make the calendar, the season dates and the burning-day CSV; shapes that tile an
  area add up to it. A detection inside the shape whose square's centre is outside is not counted in this view (it is
  in the hotspot view), and the other way round.
- **Burning-day CSV:** every burning day inside the exact area for the chosen years, one row each:
  `latitude, longitude` (the square's centre, 3 decimals), `cell_x, cell_y` (fx, fy), `acq_date, daynight, family,
  detections, max_frp, frp_class, source_flag, w`. For any area, **Σ monthly `harmonized_estimate` = Σ CSV `w` +
  Σ monthly `background`** up to the 4-decimal rounding of the monthly CSV (the calendar adds the same 4-decimal
  weights). `tools/probe_site.py` checks this for both regions as a whole, circles from 1 km to 25 km, a rectangle
  and a polygon, and recomputes the inside set in Python from the files.
- **Monthly CSV in burning days:** the hotspot view's columns, with the unit named in the `#` methods line and in the
  file name (`…_monthly_burning_days.csv`; the hotspot view's is `…_monthly_hotspots.csv`).

## The model interface

`export_v2.py` talks to the model only through `pipeline/weights_r2.py` (the same functions as `weights_a.py`):

```python
model = fit(det, region)                     # det: filtered detections (columns month, moy, dn, fam, …); fits never see 2020+
w = hotspot_weights(model, rows)             # full weight of each Suomi NPP or NOAA-20 row; the export applies the ½ share
bg = cell_month_background(model, grid)      # grid: one row per cell-month: ci, moy, m, share_N, share_J1, V_N_D, V_N_N, V_J1_D, V_J1_N
p10, p90 = cell_month_interval(model, grid)  # same grid rows (estimated months)
describe(model)                              # dict stored as regions.json model_detail
```

A replacement module with the same functions and a different `NAME` changes `"model"` in `regions.json`
and nothing else in the contract.

The burning-day view talks to `pipeline/weights_bd.py` the same way, in burning days:

```python
model = weights_bd.fit(det, region)                  # only 2012-02..2019-12 detections reach the fit
w = weights_bd.burning_day_weights(model, rows)      # rows: burning days (ci, moy, dn, fam, k); full weight, share applied by the export
bg = weights_bd.cell_month_background(model, grid)   # grid also has V_<s>_<dn>_f0..f3, burning days by FRP class
p10, p90 = weights_bd.cell_month_interval(model, grid)
weights_bd.describe(model)                           # regions.json burning_days.model_detail
```
