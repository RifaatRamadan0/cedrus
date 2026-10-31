"""Region definitions shared by every pipeline step.

A region is one FIRMS country file, optionally clipped to a box (lon_min, lat_min, lon_max, lat_max).
Grid: global 0.25 degree cells, ix = floor(lon / 0.25), iy = floor(lat / 0.25).
"""
import numpy as np

CELL = 0.25

REGIONS = {
    # role: "dev" = bake-off development, "product" = shown in the app, "sealed" = never opened before freeze
    "portugal": {"country": "Portugal", "box": (-9.6, 36.9, -6.1, 42.2), "roles": {"dev", "product"}},
    "lebanon": {"country": "Lebanon", "box": (35.10, 33.05, 36.65, 34.70), "roles": {"dev", "product"}},
    "cyprus": {"country": "Cyprus", "box": None, "roles": {"dev"}},
    "jordan": {"country": "Jordan", "box": None, "roles": {"dev"}},
    "israel": {"country": "Israel", "box": None, "roles": {"dev"}},
    "palestine": {"country": "Palestine", "box": None, "roles": {"dev"}},
    "greece": {"country": "Greece", "box": None, "roles": {"dev"}},
    "syria": {"country": "Syria", "box": None, "roles": {"dev"}},
    "turkey": {"country": "Turkey", "box": None, "roles": {"dev"}},
    # Sealed: do NOT download or read until the model is frozen (docs/BAKEOFF_PLAN.md).
    "morocco": {"country": "Morocco", "box": None, "roles": {"sealed"}},
    "tunisia": {"country": "Tunisia", "box": None, "roles": {"sealed"}},
    "central_chile": {"country": "Chile", "box": (-73.0, -38.5, -70.0, -32.0), "roles": {"sealed"}},
    "western_cape": {"country": "South_Africa", "box": (17.5, -35.0, 24.0, -31.0), "roles": {"sealed"}},
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
