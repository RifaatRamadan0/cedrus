"""Region definitions shared by every pipeline step.

A region is one FIRMS country file, optionally clipped to a box (lon_min, lat_min, lon_max, lat_max).
Grid: global 0.25 degree cells, ix = floor(lon / 0.25), iy = floor(lat / 0.25).
"""
import numpy as np

CELL = 0.25

REGIONS = {
    # role: "dev" = bake-off development, "product" = shown in the app, "sealed" = never opened before freeze,
    # "confirm" = formerly sealed, opened once for docs/CONFIRMATION_PLAN.md after the model was frozen
    "portugal": {"country": "Portugal", "box": (-9.6, 36.9, -6.1, 42.2), "roles": {"dev", "product"}},
    "lebanon": {"country": "Lebanon", "box": (35.10, 33.05, 36.65, 34.70), "roles": {"dev", "product"}},
    "cyprus": {"country": "Cyprus", "box": None, "roles": {"dev"}},
    "jordan": {"country": "Jordan", "box": None, "roles": {"dev"}},
    "israel": {"country": "Israel", "box": None, "roles": {"dev"}},
    "palestine": {"country": "Palestine", "box": None, "roles": {"dev"}},
    "greece": {"country": "Greece", "box": None, "roles": {"dev"}},
    "syria": {"country": "Syria", "box": None, "roles": {"dev"}},
    "turkey": {"country": "Turkey", "box": None, "roles": {"dev"}},
    # Round 1 confirmation regions: opened once on 1 Nov 2026 (NOT CONFIRMED) -> spent; usable as development data only.
    "morocco": {"country": "Morocco", "box": None, "roles": {"dev", "spent"}},
    "tunisia": {"country": "Tunisia", "box": None, "roles": {"dev", "spent"}},
    "central_chile": {"country": "Chile", "box": (-73.0, -38.5, -70.0, -32.0), "roles": {"dev", "spent"}},
    "western_cape": {"country": "South_Africa", "box": (17.5, -35.0, 24.0, -31.0), "roles": {"dev", "spent"}},
    # Round 2 sealed regions (docs/ROUND2_PLAN.md): do NOT read until the round-2 model is frozen.
    "central_spain": {"country": "Spain", "box": (-6.0, 38.5, -2.0, 41.0), "roles": {"sealed"}},
    "southern_italy": {"country": "Italy", "box": (12.3, 36.6, 16.7, 39.0), "roles": {"sealed"}},
    "sw_australia": {"country": "Australia_SW", "box": (114.5, -35.5, 119.0, -30.5), "roles": {"sealed"}},
    "s_california": {"country": "USA_SoCal", "box": (-121.0, 32.5, -116.0, 35.5), "roles": {"sealed"}},
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
