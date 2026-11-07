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
]

REGIONS = {
    # role: "dev" = bake-off development, "product" = shown in the app, "sealed" = never opened before freeze,
    # "confirm" = formerly sealed, opened once for docs/CONFIRMATION_PLAN.md after the model was frozen
    "portugal": {"country": "Portugal", "box": (-9.6, 36.9, -6.1, 42.2), "roles": {"dev", "product"}},
    "lebanon": {"country": "Lebanon", "box": (35.10, 33.05, 36.65, 34.70), "roles": {"dev", "product"}},
    "cyprus": {"country": "Cyprus", "box": (32.1, 34.4, 34.8, 35.8), "roles": {"dev", "product"}},
    "jordan": {"country": "Jordan", "box": (34.8, 29.0, 39.5, 33.5), "roles": {"dev", "product"}},
    "israel": {"country": "Israel", "box": (34.2, 29.4, 35.95, 33.4), "roles": {"dev"}},
    "palestine": {"country": "Palestine", "box": (34.1, 31.1, 35.7, 32.7), "roles": {"dev"}},
    "greece": {"country": "Greece", "box": None, "roles": {"dev"}},
    "syria": {"country": "Syria", "box": (35.5, 32.2, 42.5, 37.5), "roles": {"dev", "product"}},
    "la_rioja": {"country": "Argentina", "name": "La Rioja area, Argentina",
                 "box": (-69.7, -32.8, -65.4, -27.7), "roles": {"product"},
                 "notes": ["Regional monthly summaries were tested against MODIS in 2020–2021. Local grid-cell errors remain substantial, around 60%. Accuracy for 2022–2025 has not been directly established. This region is outside the climates used in the earlier Mediterranean validation.",
                           "Annual totals in the 2020-2021 test were above the 80% range.",
                           "This is a rectangular area including neighboring provincial land, not the exact La Rioja province."]},
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
