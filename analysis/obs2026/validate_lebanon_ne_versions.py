"""Does an older version of Natural Earth 1:10m reproduce FIRMS's country assignment for Lebanon?

    python analysis/obs2026/validate_lebanon_ne_versions.py fetch
    python analysis/obs2026/validate_lebanon_ne_versions.py select
    python analysis/obs2026/validate_lebanon_ne_versions.py test

Rules: docs/OBS2026_VALIDATION_PLAN.md, addendum "older Natural Earth 1:10m versions for Lebanon" (written before
any version was downloaded).

`fetch` reads, for each of the 23 commits that changed the 1:10m countries file, that commit's .shx and .dbf and
only Lebanon's record from the .shp (an HTTP Range request), and saves Lebanon's rings. `select` scores the distinct
Lebanon polygons on 2000-2022 country-file detections. `test` runs the unchanged clipping test (C1, C2, C3) on
2023-2025 with the selected polygon. Reads only; no export, model or catalog file is touched.
"""
import hashlib
import json
import struct
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate_lebanon_boundaries as b  # noqa: E402  (selection data, point-in-polygon, report helpers)

v, ROOT = b.v, b.ROOT
DIR = ROOT / "data/raw/boundaries/candidates/ne10m_history"
OUT = HERE / "results_lebanon_ne_versions.json"
RAW = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{sha}/10m_cultural/ne_10m_admin_0_countries.{ext}"

# Every commit that changed 10m_cultural/ne_10m_admin_0_countries.shp, newest first (GitHub commit history for that
# path, read 12 November 2026). The first is the file in releases 5.1.0-5.1.2 and in use now.
COMMITS = [
    ("5faefd9a6cd52490b56e04087862326ab21040af", "2022-04-22"),
    ("a7c8ff86de88b1c3c979ff62557de1e6c86cfac7", "2022-03-17"),
    ("dfa866485b6eb1bac8dafe088944ac3b4c719d11", "2021-12-07"),
    ("402b35abd07ef4edb6b5da1699a63dfbc99effdd", "2021-11-14"),
    ("3aa16bdc7acfa611d5196d5aa0ba10d51db762bb", "2021-11-09"),
    ("6bd810ae44a701eecc2ba46a65ea530e9f9019c7", "2021-09-03"),
    ("be165336bbc6d3c28fb75348fa223339308b7742", "2021-08-30"),
    ("de9e8d074120163b1cc02a83a828829a1e93202e", "2021-08-01"),
    ("0edfe737ffc3a3e3f167ede3ffcb5ed54a28fa04", "2021-05-29"),
    ("c034dccd73b13a4a2a8e4f0187562bcd7ee1b347", "2021-02-14"),
    ("0eca99ed93f932774ef8119de41e600e6eab675f", "2021-01-20"),
    ("709ffdf7e55f73a0d81dd1adcb4a1032a38e3730", "2021-01-06"),
    ("e5f6e02319764c8a4e9f181163c7cd0300e3266b", "2020-12-13"),
    ("a632044a316fff77916ea3822126544a8cf4eedd", "2018-05-15"),
    ("f1cf55a25f779aadc9b73fef7c725e13cf1fe397", "2017-10-05"),
    ("8dc5287cad537edfcd0f3ccc2cab99da8335b87a", "2017-08-14"),
    ("4db6e25860af9d144092467afdaae71af3404651", "2014-12-31"),
    ("68f72292bd4c623a6484e27fdbd964b4580a7ba1", "2013-06-02"),
    ("d19dfc7f9ab3969ea1dbcece85b864916336a4f9", "2012-11-05"),
    ("58b6cdc00a7f7d9d5dde6c0e06a0d65a94cbd4bc", "2012-11-04"),
    ("04b377f5cc81315ab1bcf2d27b21dfec8cb3fed5", "2012-11-04"),
    ("71967a117ed15640e5fb90236f49fa2628c558a1", "2012-08-19"),
    ("3564a7c7bb38d18d9059f49036f7b5bbc6852380", "2012-01-22"),
]
CURRENT = COMMITS[0][0]


def get(url, rng=None):
    headers = {"User-Agent": "cedrus-validation/1"}
    if rng:
        headers["Range"] = f"bytes={rng[0]}-{rng[1]}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=600) as r:
        return r.read()


def is_lebanon(rec):
    for key in ("ADM0_A3", "adm0_a3", "ISO_A3", "iso_a3"):
        if key in rec:
            return rec[key] == "LBN"
    return any(rec.get(k) == "Lebanon" for k in ("ADMIN", "admin", "NAME", "name"))


def polygon_rings(content):
    """Rings of one shapefile Polygon record's content (type 5), as [N, 2] arrays."""
    stype, = struct.unpack("<i", content[:4])
    if stype != 5:
        raise ValueError(f"shape type {stype}, expected 5 (Polygon)")
    nparts, npts = struct.unpack("<ii", content[36:44])
    parts = list(struct.unpack(f"<{nparts}i", content[44:44 + 4 * nparts])) + [npts]
    pts = np.frombuffer(content, "<f8", 2 * npts, 44 + 4 * nparts).reshape(-1, 2)
    return [pts[a:c].copy() for a, c in zip(parts[:-1], parts[1:])]


def dbf_records(dbf, keys=("ADM0_A3", "adm0_a3", "ISO_A3", "iso_a3", "ADMIN", "admin", "NAME", "name")):
    """The few identifying fields of every record in a dBASE file, read from its own header. (pyshp rejects the
    2020-12-13 file, whose field list it misreads; the header and the field descriptors are consistent.)"""
    n, header, reclen = struct.unpack("<IHH", dbf[4:12])
    fields, pos, off = {}, 32, 1  # byte 0 of each record is the deletion flag
    while dbf[pos] != 0x0D:
        name, width = dbf[pos:pos + 11].split(b"\0")[0].decode("ascii"), dbf[pos + 16]
        if name in keys:
            fields[name] = (off, width)
        off, pos = off + width, pos + 32
    if off != reclen:
        raise ValueError(f"fields add up to {off} bytes, header says {reclen}")
    for i in range(n):
        rec = dbf[header + i * reclen:header + (i + 1) * reclen]
        yield {k: rec[o:o + w].decode("utf-8", "replace").strip() for k, (o, w) in fields.items()}


def cached(path, url, rng=None):
    if not path.exists():
        path.write_bytes(get(url, rng))
    return path.read_bytes()


def fetch():
    DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for sha, date in COMMITS:
        out = DIR / sha[:10]
        out.mkdir(exist_ok=True)
        try:
            shx, dbf = (cached(out / f"countries.{e}", RAW.format(sha=sha, ext=e)) for e in ("shx", "dbf"))
            hits = [i for i, rec in enumerate(dbf_records(dbf)) if is_lebanon(rec)]
            if len(hits) != 1:
                raise ValueError(f"{len(hits)} Lebanon records")
            i = hits[0]
            off, words = struct.unpack(">ii", shx[100 + 8 * i:108 + 8 * i])
            start, length = 2 * off, 8 + 2 * words
            record = cached(out / "lebanon_record.shp-part", RAW.format(sha=sha, ext="shp"), (start, start + length - 1))
            if len(record) != length or struct.unpack(">i", record[:4])[0] != i + 1:
                raise ValueError(f"range returned {len(record)} bytes (expected {length}) or the wrong record")
            rings = polygon_rings(record[8:])
            geom = hashlib.sha256(b"".join(r_.tobytes() for r_ in rings)).hexdigest()
            (out / "lebanon.json").write_text(json.dumps({"rings": [r_.tolist() for r_ in rings]}), encoding="utf-8")
            manifest[sha] = {"date": date, "record_index": i, "shp_bytes": [start, start + length - 1],
                             "sha256": {"shx": hashlib.sha256(shx).hexdigest(), "dbf": hashlib.sha256(dbf).hexdigest(),
                                        "lebanon_record": hashlib.sha256(record).hexdigest()},
                             "lebanon_geometry_sha256": geom, "rings": len(rings),
                             "vertices": int(sum(len(r_) for r_ in rings))}
            print(f"{sha[:10]} {date}: record {i}, {len(rings)} rings, {manifest[sha]['vertices']} vertices, "
                  f"geometry {geom[:12]}", flush=True)
        except Exception as e:  # recorded, not substituted
            manifest[sha] = {"date": date, "error": f"{type(e).__name__}: {e}"}
            print(f"{sha[:10]} {date}: ERROR {manifest[sha]['error']}", flush=True)
    meta = {"source": RAW, "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "license": "public domain (Natural Earth)", "versions": manifest}
    (DIR / "manifest.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")


def rings_of(sha):
    return [np.asarray(r_, float) for r_ in json.loads((DIR / sha[:10] / "lebanon.json").read_text("utf-8"))["rings"]]


def groups():
    """Distinct Lebanon polygons, newest first: [(geometry hash, [commits]), ...]."""
    man = json.loads((DIR / "manifest.json").read_text("utf-8"))["versions"]
    out = {}
    for sha, _ in COMMITS:
        if "error" not in man[sha]:
            out.setdefault(man[sha]["lebanon_geometry_sha256"], []).append(sha)
    return list(out.items()), {s: m["error"] for s, m in man.items() if "error" in m}


def select():
    pts = b.selection_points()
    lon, lat = pts.longitude.to_numpy(), pts.latitude.to_numpy()
    grp, skipped = groups()
    dates = dict(COMMITS)
    scores = []
    for geom, shas in grp:
        pred = b.inside(rings_of(shas[0]), lon, lat)
        bad = pts[pred != pts.truth.to_numpy()]
        scores.append({"geometry": geom, "commits": [f"{s[:10]} ({dates[s]})" for s in shas], "first_commit": shas[0],
                       "current": CURRENT in shas, "mismatches": int(len(bad)),
                       "lebanon_file_outside": int(bad.truth.sum()), "neighbour_file_inside": int((~bad.truth).sum()),
                       "by_stretch": {k: int(n) for k, n in
                                      b.pd.Series([b.stretch(a, c) for a, c in zip(bad.longitude, bad.latitude)],
                                                  dtype=object).value_counts().items()}})
        print(f"{shas[0][:10]} ({dates[shas[-1]]}..{dates[shas[0]]}, {len(shas)} commits): {len(bad)} mismatches",
              flush=True)
    chosen = min(range(len(scores)), key=lambda k: (scores[k]["mismatches"], k))  # ties: newer (earlier in list)
    out = {"plan": "docs/OBS2026_VALIDATION_PLAN.md (addendum: older Natural Earth 1:10m versions for Lebanon)",
           "selection_years": [b.SELECT_YEARS.start, b.SELECT_YEARS.stop - 1], "selection_points": int(len(pts)),
           "groups": scores, "skipped": skipped, "selected": scores[chosen]["first_commit"],
           "selected_is_current": scores[chosen]["current"]}
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"selected: {out['selected'][:10]}" + (" (the file in use now)" if out["selected_is_current"] else ""))


def test():
    out = json.loads(OUT.read_text(encoding="utf-8"))
    if out["selected_is_current"]:
        raise SystemExit("selected polygon is the one in use now; its test result is already recorded (FAIL)")
    rings = rings_of(out["selected"])
    countries = b.load_countries()
    keep = lambda df: b.inside(rings, df.longitude.to_numpy(), df.latitude.to_numpy())  # noqa: E731
    res = {str(y): {s: v.clipping("lebanon", s, countries, year=y, keep=keep) for s in b.SENSORS} for y in b.TEST_YEARS}
    out["test"] = res
    out["test_pass"] = all(r["c1_pass"] and r["c2_pass"] and r["c3_pass"] for yr in res.values() for r in yr.values())
    OUT.write_text(json.dumps(out, indent=2, default=float) + "\n", encoding="utf-8", newline="\n")
    report(out)


def report(out):
    lines = ["# Lebanon: older Natural Earth 1:10m versions", "",
             "Rules: [plan addendum](../../docs/OBS2026_VALIDATION_PLAN.md). Selection on 2000–2022 country files; "
             "test on 2023–2025 area-API data with the unchanged C1–C3 thresholds.", "",
             f"Selection points: {out['selection_points']:,}. Versions with an identical Lebanon polygon are one row.", "",
             "## Selection (2000–2022)", "", "| Commits (newest first) | Mismatches | Lebanon's, outside | "
             "Neighbour's, inside | Where |", "|---|---:|---:|---:|---|"]
    for g in out["groups"]:
        mark = " **(selected)**" if g["first_commit"] == out["selected"] else ""
        now = " — in use now" if g["current"] else ""
        where = ", ".join(f"{k} {n}" for k, n in g["by_stretch"].items())
        lines.append(f"| {', '.join(g['commits'])}{now}{mark} | {g['mismatches']:,} | {g['lebanon_file_outside']:,} | "
                     f"{g['neighbour_file_inside']:,} | {where} |")
    for sha, why in out["skipped"].items():
        lines.append(f"| {sha[:10]} | not scored | | | {why} |")
    if "test" in out:
        lines += ["", f"## Independent test — **{'PASS' if out['test_pass'] else 'FAIL'}**", "",
                  "| Year | Sensor | Country file | False incl. | False excl. | C1 | Worst month (C2) | C3 | Pass |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---|"]
        for y, yr in out["test"].items():
            for s, r in yr.items():
                ok = r["c1_pass"] and r["c2_pass"] and r["c3_pass"]
                lines.append(f"| {y} | {s} | {r['country_file']:,} | {r['false_inclusions']} | {r['false_exclusions']} | "
                             f"{v.pct(r['c1_share'])} | {v.pct(r['c2_worst_month'])} | {v.pct(r['c3_share'])} | "
                             f"{'yes' if ok else '**no**'} |")
    (HERE / "REPORT_lebanon_ne_versions.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    {"fetch": fetch, "select": select, "test": test}[sys.argv[1]]()
