# Test plan — the MODIS retirement test

Written **before** any model was fitted or any held-out number was looked at.
The git history shows this file was committed before `pipeline/03_harmonize.py`
first ran. If we change the plan later, we add a dated section below — we never
edit the original rules after seeing results.

## The question

MODIS (on Terra and Aqua) is being retired. VIIRS (Suomi NPP, NOAA-20, NOAA-21)
takes over. VIIRS sees more small fires, so a record that simply switches from
MODIS to VIIRS jumps upward — a jump that is the instrument, not the fires.

**If MODIS had stopped at the end of 2019, how well could we rebuild what MODIS
would have seen in 2020–2025, using VIIRS alone?** We can check, because MODIS
did keep running. That comparison is the score.

## Data

- NASA FIRMS country archive, Portugal, standard (archive) products.
  - MODIS Collection 6.1, Terra + Aqua, 2000–2025.
  - VIIRS 375 m Suomi NPP (`viirs-snpp`), 2012–2025.
  - VIIRS 375 m NOAA-20 (`viirs-jpss1`), whatever years the archive holds — secondary check only.
- Area: mainland Portugal box, lon −9.6 to −6.1, lat 36.9 to 42.2 (drops Azores and Madeira).
- Kept detections:
  - `type == 0` (presumed vegetation fire) where the column exists;
  - MODIS `confidence >= 30`; VIIRS `confidence` in {nominal, high} (drop `low`);
  - day and night both kept.
- Unit: **detection count per grid cell per calendar month.** Grid: 0.25° squares.
- MODIS series = Terra + Aqua added together.

## Split

- Training: Suomi NPP's first full month (Feb 2012) to Dec 2019.
- Held out: Jan 2020 to Dec 2025. Nothing from these years is used to fit or tune anything.
- Tuning (choosing `k` below) uses leave-one-year-out inside 2012–2019 only.

## Models compared

| Name | What it says |
|---|---|
| **F0 — joined record** (floor) | MODIS-equivalent = the VIIRS count, unchanged. This is what a naive merge does. |
| **F1 — one ratio** (floor) | MODIS-equivalent = r × VIIRS, one ratio r for all of Portugal, fitted on training. |
| **M1 — CEDRUS** | MODIS-equivalent = r(cell, month) × VIIRS. r(cell, month) = (ΣMODIS + k·r(month)) / (ΣVIIRS + k), sums over training years for that cell and calendar month; r(month) is the all-Portugal ratio for that calendar month. `k` (a pull towards the national value where a cell has few fires) is chosen from {10, 30, 100, 300} by leave-one-year-out on training years. |

## Scores (all on held-out years 2020–2025)

1. **Primary — cell-month error (WAPE):** Σ |predicted − MODIS| ÷ Σ MODIS over all cell-months. Lower is better.
2. Yearly national total: % error per year.
3. National monthly WAPE.
4. Fire-season dates per year (start = day 10% of the year's detections are reached, middle = 50%, end = 90%): mean absolute difference in days between the dates from the predicted record and from real MODIS. For this score, daily national VIIRS counts are scaled by r(month).

## Pass rule

M1 **passes** if its primary score is lower than both F0 and F1. It **fails** otherwise.
Either way the result goes in `docs/RESULTS.md` and on the website, with the per-year breakdown.

## Known things that could make it fail (written down in advance)

- **Terra and Aqua have been drifting since about 2020–2022**, so their overpass times changed. The thing we are trying to predict (MODIS) changes during the held-out years. We report Terra and Aqua separately so this is visible.
- 2017 (the Pedrógão and October fires) dominates the training years. A ratio learned mostly from extreme days may not hold in quiet years.
- Cells with almost no fires get the national ratio; their errors are large in % terms but tiny in counts. The primary score is count-weighted for that reason.

## Secondary check — the satellite handover

Suomi NPP stopped delivering data products on 1 Nov 2026. Fit M1 on Suomi NPP, apply it unchanged to NOAA-20 for the years where both exist, and report the same scores. If NOAA-20 needs its own ratio, we say so.

## Note added 23 Oct 2026, after downloading and before any model was fitted

Found while checking the downloaded files (no scores had been computed yet):

- **The MODIS files are not one product version.** The `version` column reads 6.2 for 2000–2017,
  6.03 for 2018–2022 and 61.03 for 2023–2025. A processing change inside the training years (2018)
  and inside the held-out years (2023) could move MODIS counts for reasons that are neither fires
  nor VIIRS. The rules above are unchanged. RESULTS.md reports the yearly errors, so a step at 2018
  or 2023 would show up there.
- **The NOAA-20 archive covers 2018–2025**, not only 2024–2025, so the handover check runs on all
  held-out years.
