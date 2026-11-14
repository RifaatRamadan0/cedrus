"""Border correction: near a country's edge, follow FIRMS's own historical country assignment.

Natural Earth's outline and the boundary FIRMS uses for its country files can differ by about a kilometre
(Lebanon's southern line in the 2025 test). For an area-API detection within EDGE_KM of the outline edge, every
historical FIRMS country-file detection within RADIUS_KM is looked up, from the region's own files and from its
neighbours' files; if most come from a neighbour, the detection is not the region's. With no historical detection
nearby, or a tie, the outline decides. Rule and test: docs/OBS2026_VALIDATION_PLAN.md (addendum, 11 Nov 2026).
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from outline import edge_km, inside  # noqa: E402
from regions import REGIONS  # noqa: E402

EDGE_KM, RADIUS_KM = 3.0, 1.0
# region -> (its raw folder and FIRMS country name, then each neighbour's)
NEIGHBOURS = {"lebanon": [("lebanon", "Lebanon"), ("syria", "Syria"), ("israel", "Israel")]}
STEMS = ("modis", "viirs-snpp", "viirs-jpss1")


def reference(region, years, pad=0.1):
    """Historical country-file detections near the region's box: lon, lat, and whether the file is the region's."""
    lon0, lat0, lon1, lat1 = REGIONS[region]["box"]
    parts = []
    for k, (folder, country) in enumerate(NEIGHBOURS[region]):
        for stem in STEMS:
            for year in years:
                path = ROOT / "data/raw" / folder / f"{stem}_{year}_{country}.csv"
                if not path.exists():
                    continue
                df = pd.read_csv(path, usecols=["longitude", "latitude"])
                df = df[(df.longitude >= lon0 - pad) & (df.longitude < lon1 + pad)
                        & (df.latitude >= lat0 - pad) & (df.latitude < lat1 + pad)]
                parts.append(df.assign(own=(k == 0)))
    return pd.concat(parts, ignore_index=True)


def _xy(lon, lat, lat0):
    return np.column_stack([np.asarray(lon) * math.cos(math.radians(lat0)) * 111.32, np.asarray(lat) * 110.57])


def keep(region, rings, ref, lon, lat):
    """Boolean array: which detections are the region's, after the border correction."""
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    kept = inside(rings, lon, lat)
    if not len(lon):
        return kept
    near = np.zeros(len(lon), dtype=bool)
    # Only detections near the edge can change; measure distance only for those within ~5 km of any ring vertex.
    pts = np.column_stack([lon, lat])
    verts = np.concatenate(rings)
    lat0 = float(np.mean(lat))
    tree_v = cKDTree(_xy(verts[:, 0], verts[:, 1], lat0))
    close = tree_v.query(_xy(lon, lat, lat0), distance_upper_bound=EDGE_KM + 5)[0] < np.inf
    if close.any():
        idx = np.flatnonzero(close)
        near[idx] = edge_km(rings, pts[idx, 0], pts[idx, 1]) <= EDGE_KM
    if not near.any():
        return kept
    tree = cKDTree(_xy(ref.longitude, ref.latitude, lat0))
    own = ref.own.to_numpy()
    for i in np.flatnonzero(near):
        hits = tree.query_ball_point(_xy([lon[i]], [lat[i]], lat0)[0], RADIUS_KM)
        if not hits:
            continue
        n_own = int(own[hits].sum())
        n_other = len(hits) - n_own
        if n_own != n_other:
            kept[i] = n_own > n_other
    return kept
