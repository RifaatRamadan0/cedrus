"""Region definitions shared by every pipeline step.

A region is one FIRMS country file, optionally clipped to a box (lon_min, lat_min, lon_max, lat_max).
Grid: global 0.25 degree cells, ix = floor(lon / 0.25), iy = floor(lat / 0.25).
"""
import numpy as np

CELL = 0.25

SHARED_NOTES = [
    "Counts all fires FIRMS detects, from any cause, including agricultural burning and conflict. "
    "Static heat sources (type 2) are excluded. Monthly completeness is unknown; known FIRMS data gaps are listed in the docs.",
    "Only type 0 (presumed vegetation fire) is eligible; volcano and offshore detections are also excluded. Fire causes are not classified.",
    "Accuracy is checked against MODIS only up to 2021. From 2022 the MODIS satellites drift in orbit, so 2022–2025 values "
    "are checked only by agreement between two VIIRS satellites, not against an independent record.",
    "2026 (January–July) comes from FIRMS standard data, assigned to each country with Natural Earth outlines; in a test "
    "this matched FIRMS's own 2025 country files exactly. Lebanon uses the outline as it was on 30 August 2021, which "
    "matched every FIRMS Lebanon assignment in 2000–2025; the current outline differs by about 1 km on the southern border. "
    "Later months are added when FIRMS releases standard data; near-real-time data is not used.",
    # Measured 13 Nov 2026 (docs/DATA_CONTRACT.md, p10/p90; docs/TIER1_IMPLEMENTATION_STATUS.md). Wording only.
    "The 80% ranges are too narrow: in a test on 2020–2021 they held the observed MODIS value about half the time. "
    "Read the trust check and the chance figure as optimistic.",
]

# Per-region forward tests (fit 2012-2019, score 2020-2021): analysis/tier1/region_evidence/<region>/REPORT.md
FORWARD = "Forward test against MODIS, 2020–2021 (fitted on 2012–2019): "

REGIONS = {
    # role: "dev" = bake-off development, "product" = shown in the app, "sealed" = never opened before freeze,
    # "confirm" = formerly sealed, opened once for docs/CONFIRMATION_PLAN.md after the model was frozen
    "portugal": {"country": "Portugal", "box": (-9.6, 36.9, -6.1, 42.2), "roles": {"dev", "product"},
                 "notes": [FORWARD + "met every pass rule in both units, with regional monthly error 15.3% against 30.8% "
                           "for a simple conversion and the total 3.8–4.3% too high. This provides evidence for "
                           "regional-level performance in 2020–2021. It does not show accuracy after 2021 or for single "
                           "grid cells, where errors are 78–80%."]},
    "lebanon": {"country": "Lebanon", "box": (35.10, 33.05, 36.65, 34.70), "roles": {"dev", "product"},
                "notes": [FORWARD + "failed the check that the total is within 10%, underestimating by 16% in burning days "
                          "and 21% in hotspots. It still beat a simple conversion by a wide margin (regional monthly error "
                          "28.3% against 58.0%). Lebanon has few fires (245 MODIS burning days in the two years), so one "
                          "large fire moves the total; grid-cell errors are 78–82%.",
                          "11 of Lebanon's 28 grid cells lie on the border and also cover land in Syria; they hold 23% of "
                          "Lebanon's estimated values. Each cell counts only Lebanon's records; Syria's fires in the same "
                          "cell are in the Syria view.",
                          "One 2026 Suomi NPP detection (24 June, 0.1 km inside the eastern border) fell in a grid cell "
                          "with no earlier Lebanon fires and is left out, so the 2000–2025 grid and its values stay "
                          "exactly as published."]},
    # Cyprus and Jordan were removed from the app on 10 Nov 2026 (no "product" role): their forward tests had too few
    # fires to measure (139 and 81 MODIS burning days in 2020-2021) and grid-cell errors of about 100% and 163%.
    # Results and rule: analysis/tier1/region_evidence/README.md.
    "cyprus": {"country": "Cyprus", "box": (32.1, 34.4, 34.8, 35.8), "roles": {"dev"}},
    "jordan": {"country": "Jordan", "box": (34.8, 29.0, 39.5, 33.5), "roles": {"dev"}},
    "israel": {"country": "Israel", "box": (34.2, 29.4, 35.95, 33.4), "roles": {"dev"}},
    "palestine": {"country": "Palestine", "box": (34.1, 31.1, 35.7, 32.7), "roles": {"dev"}},
    "greece": {"country": "Greece", "box": None, "roles": {"dev"}},
    "syria": {"country": "Syria", "box": (35.5, 32.2, 42.5, 37.5), "roles": {"dev", "product"},
              "notes": [FORWARD + "burning days passed every check, with regional monthly error 19.5% against 27.0% for a "
                        "simple conversion. Hotspots failed one check: regional monthly error 27.5%, slightly worse than the "
                        "simple conversion's 24.4%. 2021 was overestimated (662 predicted against 490 observed burning days). "
                        "Local grid-cell errors are 69–77%. August and September 2020 were left out of the test by the "
                        "sensor-outage rule.",
                        "Cells on Syria's borders also cover land in neighbouring countries, but count only Syria's records. "
                        "11 of them are shared with Lebanon, whose fires are in the Lebanon view; fires in Turkey, Iraq and "
                        "Jordan are not shown anywhere."]},
    "la_rioja": {"country": "Argentina", "name": "La Rioja area, Argentina",
                 "box": (-69.7, -32.8, -65.4, -27.7), "roles": {"product"},
                 "notes": ["Regional monthly summaries were tested against MODIS in 2020–2021. Local grid-cell errors remain substantial, around 60%. This region is outside the climates used in the earlier Mediterranean validation.",
                           "Annual totals in the 2020-2021 test were above the 80% range.",
                           "This is a rectangular area including neighboring provincial land, not the exact La Rioja province.",
                           "One 2026 NOAA-20 detection fell in a grid cell with no earlier fires and is left out, so the "
                           "2000–2025 grid and its values stay exactly as published."]},
    "turkey": {"country": "Turkey", "box": None, "roles": {"dev"}},
    # Round 1 confirmation regions: opened once on 1 Nov 2026 (NOT CONFIRMED) -> spent; usable as development data only.
    "morocco": {"country": "Morocco", "box": None, "roles": {"dev", "spent"}},
    "tunisia": {"country": "Tunisia", "box": None, "roles": {"dev", "spent"}},
    "central_chile": {"country": "Chile", "box": (-73.0, -38.5, -70.0, -32.0), "roles": {"dev", "spent"}},
    "western_cape": {"country": "South_Africa", "box": (17.5, -35.0, 24.0, -31.0), "roles": {"dev", "spent"}},
    # Round 2 confirmation regions: opened once on 1 Nov 2026 (CONFIRMED) -> spent; usable as development data only.
    "central_spain": {"country": "Spain", "box": (-6.0, 38.5, -2.0, 41.0), "roles": {"dev", "spent"}},
    "southern_italy": {"country": "Italy", "box": (12.3, 36.6, 16.7, 39.0), "roles": {"dev", "spent"}},
    "sw_australia": {"country": "Australia_SW", "box": (114.5, -35.5, 119.0, -30.5), "roles": {"dev", "spent"}},
    "s_california": {"country": "USA_SoCal", "box": (-121.0, 32.5, -116.0, 35.5), "roles": {"dev", "spent"}},
    # Round 3 sealed regions (docs/TOURNAMENT_PLAN.md): do NOT download or read until the tournament champion is frozen.
    "northern_algeria": {"country": "Algeria", "box": (-1.0, 34.5, 8.5, 37.1), "roles": {"sealed"}},
    "southern_france": {"country": "France", "box": (3.0, 42.5, 7.7, 44.5), "roles": {"sealed"}},
    "south_australia": {"country": "Australia_SA", "box": (136.5, -36.5, 141.0, -33.0), "roles": {"sealed"}},
    "n_california": {"country": "USA_NorCal", "box": (-123.5, 37.5, -120.5, 40.5), "roles": {"sealed"}},
}


def regions_with(role):
    return [k for k, v in REGIONS.items() if role in v["roles"]]


def cell_ids(lon, lat):
    """Global 0.25 deg cell id as 'ix_iy' strings."""
    ix = np.floor(np.asarray(lon, float) / CELL).astype(int)
    iy = np.floor(np.asarray(lat, float) / CELL).astype(int)
    return np.char.add(np.char.add(ix.astype(str), "_"), iy.astype(str))


def cell_bounds(cell_id):
    ix, iy = (int(v) for v in cell_id.split("_"))
    return ix * CELL, iy * CELL, (ix + 1) * CELL, (iy + 1) * CELL


def assert_not_sealed(region):
    if "sealed" in REGIONS[region]["roles"]:
        raise SystemExit(f"{region} is sealed until the model is frozen (docs/BAKEOFF_PLAN.md)")
