"""Which published boundary reproduces FIRMS's country assignment for Lebanon?

    python analysis/obs2026/validate_lebanon_boundaries.py select
    python analysis/obs2026/validate_lebanon_boundaries.py test

Rules: docs/OBS2026_VALIDATION_PLAN.md, addendum "other boundary datasets for Lebanon" (written before any
candidate was downloaded).

`select` scores every candidate on 2000-2022 country-file detections only and writes the choice to
results_lebanon_boundaries.json. `test` reads that choice back, without changing it, and runs the unchanged
clipping test (C1, C2, C3) on 2023, 2024 and 2025 area-API data. Reads only; no export, model or catalog file is
touched.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "pipeline"))
import validate_processing as v  # noqa: E402
from outline import edge_km, inside, load_countries  # noqa: E402
from regions import REGIONS  # noqa: E402

CAND = ROOT / "data/raw/boundaries/candidates"
OUT = HERE / "results_lebanon_boundaries.json"
BOX = REGIONS["lebanon"]["box"]
SELECT_YEARS = range(2000, 2023)
TEST_YEARS = (2023, 2024, 2025)
FILES = {"lebanon": "Lebanon", "syria": "Syria", "israel": "Israel"}   # Lebanon and its two land neighbours
STEMS = ("modis", "viirs-snpp", "viirs-jpss1")
SENSORS = ("modis", "snpp", "noaa20")


# ---------- candidates: each loader returns a list of parts; a point is Lebanon's if it is inside any part ----------
def rings_of(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [np.asarray(ring, float)[:, :2] for poly in polys for ring in poly]


def geojson_parts(path, match):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [rings_of(f["geometry"]) for f in data["features"] if match(f["properties"])]


def shp_parts(stem, match):
    """Polygons from an extracted shapefile (path without extension) whose attributes match."""
    import shapefile  # pyshp
    r = shapefile.Reader(str(stem), encoding="utf-8", encodingErrors="replace")
    fields = [f[0] for f in r.fields[1:]]
    parts = []
    for i, rec in enumerate(r.iterRecords()):
        if match(dict(zip(fields, rec))):
            shape = r.shape(i)
            pts = np.asarray(shape.points, float)
            cuts = list(shape.parts) + [len(pts)]
            parts.append([pts[a:b] for a, b in zip(cuts[:-1], cuts[1:])])
    return parts


def ne(scale):
    return lambda: geojson_parts(ROOT / "data/raw/boundaries" / "ne_10m_admin_0_countries.geojson" if scale == "10m"
                                 else CAND / f"ne_{scale}_admin_0_countries.geojson",
                                 lambda p: p.get("ADM0_A3") == "LBN")


CANDIDATES = {
    "Natural Earth 1:10m": ne("10m"),
    "Natural Earth 1:50m": ne("50m"),
    "Natural Earth 1:110m": ne("110m"),
    "GADM 4.1 level 0": lambda: geojson_parts(CAND / "gadm41_LBN_0.json", lambda p: p.get("GID_0") == "LBN"),
    "geoBoundaries gbOpen ADM0": lambda: geojson_parts(CAND / "gbOpen-LBN-ADM0.geojson", lambda p: True),
    "geoBoundaries gbHumanitarian ADM0": lambda: geojson_parts(CAND / "gbHumanitarian-LBN-ADM0.geojson", lambda p: True),
    # The same layer as the 401 MB GeoJSON, in its 104 MB shapefile form (slow link).
    "geoBoundaries CGAZ ADM0": lambda: shp_parts(CAND / "cgaz/geoBoundariesCGAZ_ADM0",
                                                 lambda p: p.get("shapeGroup") == "LBN"),
    "FAO GAUL 2024 (level 1 units of Lebanon, merged)": lambda: shp_parts(
        CAND / "gaul/GAUL_2024_L1", lambda p: p.get("gaul0_name") == "Lebanon"),
    "US State Dept LSIB v11.4": lambda: lsib_parts(),
}


def lsib_parts():
    """LSIB v11.4 is published as boundary lines only (POLYLINE, no coastline), so there is no Lebanon polygon to
    test. Building one from its lines plus another dataset's coast would be a new, untested boundary; the plan
    says such a candidate is left out, not substituted."""
    raise RuntimeError("LSIB v11.4 is lines only (POLYLINE shapefile, no coastline); no Lebanon polygon to test")


def in_parts(parts, lon, lat):
    hit = np.zeros(len(lon), dtype=bool)
    for rings in parts:
        hit |= inside(rings, lon, lat)
    return hit


# ---------- selection data: 2000-2022 country files ----------
def selection_points():
    lon0, lat0, lon1, lat1 = BOX
    rows = []
    for folder, country in FILES.items():
        for stem in STEMS:
            for year in SELECT_YEARS:
                path = ROOT / "data/raw" / folder / f"{stem}_{year}_{country}.csv"
                if not path.exists():
                    continue
                df = pd.read_csv(path, usecols=["latitude", "longitude", "acq_date"], low_memory=False)
                df = df[(df.longitude >= lon0) & (df.longitude < lon1) & (df.latitude >= lat0) & (df.latitude < lat1)]
                rows.append(df.assign(file=folder, stem=stem, year=year))
    df = pd.concat(rows, ignore_index=True)
    df["truth"] = df.file == "lebanon"
    return df


def stretch(lon, lat):
    """Coarse label for where a mismatch lies, for the report only."""
    if lat < 33.45:
        return "south (incl. Shebaa area)" if lon > 35.6 else "south"
    if lon < 35.75 and lat > 33.2:
        return "coast"
    return "east / north (Syria)"


def select():
    pts = selection_points()
    lon, lat = pts.longitude.to_numpy(), pts.latitude.to_numpy()
    ne10 = load_countries()["LBN"]["rings"]
    scores, skipped = {}, {}
    for name, load in CANDIDATES.items():
        try:
            parts = load()
            if not parts:
                raise RuntimeError("no Lebanon polygon found")
        except Exception as e:  # recorded, not substituted
            skipped[name] = f"{type(e).__name__}: {e}"
            print(f"skip {name}: {skipped[name]}", flush=True)
            continue
        pred = in_parts(parts, lon, lat)
        bad = pts[pred != pts.truth.to_numpy()]
        km = edge_km(ne10, bad.longitude.to_numpy(), bad.latitude.to_numpy()) if len(bad) else np.array([])
        scores[name] = {
            "mismatches": int(len(bad)),
            "lebanon_file_outside": int((bad.truth).sum()),
            "neighbour_file_inside": int((~bad.truth).sum()),
            "by_file": bad.file.value_counts().to_dict(),
            "by_stretch": pd.Series([stretch(a, b) for a, b in zip(bad.longitude, bad.latitude)], dtype=object).value_counts().to_dict(),
            "km_to_ne10m_edge_p50_p90_max": [round(float(x), 2) for x in np.percentile(km, [50, 90, 100])] if len(km) else [],
            "parts": len(parts), "vertices": int(sum(len(r) for p in parts for r in p)),
        }
        print(f"{name}: {len(bad)} mismatches", flush=True)
    order = list(CANDIDATES)
    chosen = min(scores, key=lambda n: (scores[n]["mismatches"], order.index(n)))
    out = {"plan": "docs/OBS2026_VALIDATION_PLAN.md (addendum: other boundary datasets for Lebanon)",
           "selection_years": [SELECT_YEARS.start, SELECT_YEARS.stop - 1],
           "selection_points": int(len(pts)), "lebanon_file_points": int(pts.truth.sum()),
           "points_in_two_files": int(pts.duplicated(["latitude", "longitude", "acq_date", "stem"], keep=False).sum()),
           "scores": scores, "skipped": skipped, "selected": chosen}
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"selected: {chosen}")


def test():
    out = json.loads(OUT.read_text(encoding="utf-8"))
    chosen = out["selected"]
    parts = CANDIDATES[chosen]()
    countries = load_countries()
    keep = lambda df: in_parts(parts, df.longitude.to_numpy(), df.latitude.to_numpy())  # noqa: E731
    res = {str(y): {s: v.clipping("lebanon", s, countries, year=y, keep=keep) for s in SENSORS} for y in TEST_YEARS}
    out["test"] = res
    out["test_pass"] = all(r["c1_pass"] and r["c2_pass"] and r["c3_pass"] for yr in res.values() for r in yr.values())
    OUT.write_text(json.dumps(out, indent=2, default=float) + "\n", encoding="utf-8", newline="\n")
    report(out)


def report(out):
    lines = ["# Lebanon: other boundary datasets", "",
             "Rules: [plan addendum](../../docs/OBS2026_VALIDATION_PLAN.md). Selection on 2000–2022 country files; "
             "independent test on 2023–2025 area-API data with the unchanged C1–C3 thresholds.", "",
             f"Selection points: {out['selection_points']:,} detections in Lebanon's box from Lebanon's and its two "
             f"neighbours' files ({out['lebanon_file_points']:,} in Lebanon's file).", "",
             "## Selection (2000–2022)", "",
             "| Candidate | Mismatches | Lebanon's, outside | Neighbour's, inside | Where |", "|---|---:|---:|---:|---|"]
    for name, s in sorted(out["scores"].items(), key=lambda kv: kv[1]["mismatches"]):
        where = ", ".join(f"{k} {n}" for k, n in s["by_stretch"].items())
        mark = " **(selected)**" if name == out["selected"] else ""
        lines.append(f"| {name}{mark} | {s['mismatches']:,} | {s['lebanon_file_outside']:,} | {s['neighbour_file_inside']:,} | {where} |")
    for name, why in out["skipped"].items():
        lines.append(f"| {name} | not scored | | | {why} |")
    if "test" in out:
        lines += ["", f"## Independent test: {out['selected']} — **{'PASS' if out['test_pass'] else 'FAIL'}**", "",
                  "| Year | Sensor | Country file | False incl. | False excl. | C1 | Worst month (C2) | C3 | Pass |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---|"]
        for y, yr in out["test"].items():
            for s, r in yr.items():
                ok = r["c1_pass"] and r["c2_pass"] and r["c3_pass"]
                lines.append(f"| {y} | {s} | {r['country_file']:,} | {r['false_inclusions']} | {r['false_exclusions']} | "
                             f"{v.pct(r['c1_share'])} | {v.pct(r['c2_worst_month'])} | {v.pct(r['c3_share'])} | {'yes' if ok else '**no**'} |")
    (HERE / "REPORT_lebanon_boundaries.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    {"select": select, "test": test}[sys.argv[1]]()
