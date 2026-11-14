"""Country outlines (Natural Earth 1:10m) for assigning area-API detections to a country.

FIRMS country files already assign each detection to a country; the area API (the only 2026 source) does not.
This module does that step, and is the code tested in analysis/obs2026/validate_processing.py against the 2025
country files (docs/OBS2026_VALIDATION_PLAN.md).
"""
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MplPath

ROOT = Path(__file__).resolve().parent.parent
BOUNDARIES = ROOT / "data/raw/boundaries/ne_10m_admin_0_countries.geojson"
BOUNDARIES_SHA256 = "239eec57ac17f100a11e2536cffc56752c318b50ae765b0918ff7aab4ce8f255"


def load_countries(path=BOUNDARIES):
    """{ADM0_A3: {"name", "rings"}} with every ring (outer rings and holes) as an (n, 2) lon/lat array."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for f in data["features"]:
        g, iso = f["geometry"], f["properties"]["ADM0_A3"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        out[iso] = {"name": f["properties"]["ADMIN"], "rings": [np.asarray(ring) for poly in polys for ring in poly]}
    return out


# Lebanon only: the 1:10m outline as of Natural Earth commit be165336bb (30 August 2021). Natural Earth's commit
# of 3 September 2021 moved part of Lebanon's southern line by about 1 km; FIRMS's Lebanon country files follow the
# earlier line. This outline matched every FIRMS assignment in 2000-2022 (selection) and 2023-2025 (independent
# test), see docs/OBS2026_VALIDATION_PLAN.md and analysis/obs2026/REPORT_lebanon_ne_versions.md. The current file
# above stays in use for every other country, and for the map.
LEBANON_2021 = {
    "commit": "be165336bbc6d3c28fb75348fa223339308b7742",
    "date": "2021-08-30",
    "url": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/be165336bbc6d3c28fb75348fa223339308b7742/"
           "10m_cultural/ne_10m_admin_0_countries.{ext}",
    "dir": ROOT / "data/raw/boundaries/ne10m_be165336bb",
    "sha256": {"shp": "7b306090a2114e460f2dbe3c86b3204a274bc64762fce55a7d181fe8fae249bc",
               "shx": "d12bed229116f995c705e7880dd7e44e3eb44190ed7af30414bcac4edbe6a8cb",
               "dbf": "79253ccd579d52b1071463fb090edc2312074e2eb7e72786b970c010b824d28b"},
    "git_blob_shp": "b59994c3c9029d03ac9932dd7adf79b3110dd644",
    "record": 12,  # 0-based; its ADM0_A3 is checked below
    "geometry_sha256": "fc650ad77adb60f55c099bc55de6615dfe5b87a74e637ba703e8d456a8b87cfc",
}


def _dbf_field(dbf, field, i):
    """Field `field` of record i of a dBASE file, located from the file's own header and field descriptors."""
    n, header, reclen = struct.unpack("<IHH", dbf[4:12])
    pos, off = 32, 1  # byte 0 of each record is the deletion flag
    while dbf[pos] != 0x0D:
        name, width = dbf[pos:pos + 11].split(b"\x00")[0].decode("ascii"), dbf[pos + 16]
        if name == field:
            rec = dbf[header + i * reclen:header + (i + 1) * reclen]
            return rec[off:off + width].decode("utf-8", "replace").strip()
        off, pos = off + width, pos + 32
    raise KeyError(field)


def load_lebanon_2021():
    """Lebanon's rings from the 2021-08-30 shapefile, refusing unless every file and the polygon match the test."""
    c = LEBANON_2021
    raw = {}
    for ext, want in c["sha256"].items():
        path = c["dir"] / f"ne_10m_admin_0_countries.{ext}"
        raw[ext] = path.read_bytes()
        if hashlib.sha256(raw[ext]).hexdigest() != want:
            raise SystemExit(f"{path.name} differs from the Natural Earth {c['commit'][:10]} file that was tested")
    i = c["record"]
    if _dbf_field(raw["dbf"], "ADM0_A3", i) != "LBN":
        raise SystemExit(f"record {i} of the {c['commit'][:10]} file is not Lebanon")
    off, words = struct.unpack(">ii", raw["shx"][100 + 8 * i:108 + 8 * i])
    content = raw["shp"][2 * off + 8:2 * off + 8 + 2 * words]
    stype, nparts, npts = struct.unpack("<i", content[:4])[0], *struct.unpack("<ii", content[36:44])
    if stype != 5:
        raise SystemExit(f"Lebanon's record has shape type {stype}, expected 5 (Polygon)")
    cuts = list(struct.unpack(f"<{nparts}i", content[44:44 + 4 * nparts])) + [npts]
    pts = np.frombuffer(content, "<f8", 2 * npts, 44 + 4 * nparts).reshape(-1, 2)
    rings = [pts[a:b].copy() for a, b in zip(cuts[:-1], cuts[1:])]
    if hashlib.sha256(b"".join(r.tobytes() for r in rings)).hexdigest() != c["geometry_sha256"]:
        raise SystemExit("Lebanon polygon differs from the one validated")
    return rings


def inside(rings, lon, lat):
    """Even-odd rule over every ring, so holes are handled."""
    pts = np.column_stack([np.asarray(lon, float), np.asarray(lat, float)])
    hit = np.zeros(len(pts), dtype=bool)
    for ring in rings:
        lo, hi = ring.min(axis=0), ring.max(axis=0)
        near = (pts[:, 0] >= lo[0]) & (pts[:, 0] <= hi[0]) & (pts[:, 1] >= lo[1]) & (pts[:, 1] <= hi[1])
        if near.any():
            hit[near] ^= MplPath(ring).contains_points(pts[near])
    return hit


def edge_km(rings, lon, lat):
    """Distance in km from each point to the nearest outline edge (local equirectangular approximation)."""
    segs = np.concatenate([np.stack([r[:-1], r[1:]], axis=1) for r in rings])
    out = np.empty(len(lon))
    for i, (x, y) in enumerate(zip(lon, lat)):
        k = math.cos(math.radians(y))
        near = segs[(np.abs(segs[:, :, 1] - y).min(axis=1) < 1) & (np.abs(segs[:, :, 0] - x).min(axis=1) < 1.5)]
        if not len(near):
            out[i] = np.inf
            continue
        a = (near[:, 0] - [x, y]) * [k * 111.32, 110.57]
        b = (near[:, 1] - [x, y]) * [k * 111.32, 110.57]
        d = b - a
        t = np.clip(-(a * d).sum(axis=1) / np.maximum((d * d).sum(axis=1), 1e-12), 0, 1)
        out[i] = np.sqrt(((a + t[:, None] * d) ** 2).sum(axis=1)).min()
    return out


def which_country(countries, lon, lat):
    names = np.array(["(none)"] * len(lon), dtype=object)
    for c in countries.values():
        names[inside(c["rings"], lon, lat) & (names == "(none)")] = c["name"]
    return names
