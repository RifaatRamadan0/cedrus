"""Read-only type audit and record reconciliation against committed exports."""
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis/tier1"
TYPES = ["0", "1", "2", "3", "missing", "unexpected"]


def committed(path):
    return json.loads(subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=ROOT))


def normalized(value):
    return None if pd.isna(value) else value


def main():
    index = committed("web/data/regions.json")
    detail, results = [], {}
    for meta in index["regions"]:
        rid = meta["id"]
        if rid not in ("portugal", "lebanon"):
            continue
        first, last = meta["months"]["first"], meta["months"]["last"]
        x0, y0, x1, y1 = meta["bbox"]
        eligible, nonzero = Counter(), Counter()
        burning = []
        all_types, removed = Counter(), Counter()
        for source in meta["provenance"]["files"]:
            path = ROOT / "data/raw" / rid / source["name"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"], path.name
            d = pd.read_csv(path, dtype={"acq_time": str, "version": str}, low_memory=False)
            kind = pd.to_numeric(d.get("type", pd.Series(index=d.index, dtype=float)), errors="coerce")
            labels = kind.map({0: "0", 1: "1", 2: "2", 3: "3"}).fillna("unexpected")
            labels.loc[d.get("type", pd.Series(index=d.index, dtype=float)).isna()] = "missing"
            family, year = path.name.split("_")[:2]
            modis = family == "modis"
            sensor = d.satellite.astype(str).str.lower().str[0].map({"t": "Terra", "a": "Aqua"}) if modis else pd.Series("Suomi NPP" if family == "viirs-snpp" else "NOAA-20", index=d.index)
            assert not sensor.isna().any(), path.name
            box = d.longitude.ge(x0) & d.longitude.lt(x1) & d.latitude.ge(y0) & d.latitude.lt(y1)
            confidence = pd.to_numeric(d.confidence, errors="coerce").ge(30) if modis else d.confidence.astype(str).str.lower().str[0].isin(["n", "h"])
            window = d.acq_date.str[:7].between(first, last)
            for s in sensor.unique():
                for t in TYPES:
                    sel = sensor.eq(s) & labels.eq(t)
                    detail.append(dict(region=rid, file=path.name, archive_family=family, sensor=s, year=int(year), type=t,
                                       raw_rows=int(sel.sum()), after_box=int((sel & box).sum()),
                                       after_box_confidence=int((sel & box & confidence).sum()),
                                       in_export_window=int((sel & box & confidence & window).sum())))
                    all_types[t] += int(sel.sum())
                    if t != "0":
                        removed[t] += int((sel & box & confidence).sum())
            q = d[box & confidence & window].copy()
            q["type_label"] = labels.loc[q.index]
            q["sensor_code"] = sensor.loc[q.index].map({"Terra": 0, "Aqua": 1, "Suomi NPP": 2, "NOAA-20": 3})
            q["doy"] = pd.to_datetime(q.acq_date).dt.dayofyear
            q["dn"] = q.daynight.str.upper().str[0].eq("N").astype(int)
            q["version_code"] = q.version.map({v: i for i, v in enumerate(meta["versions"])})
            q["conf"] = pd.to_numeric(q.confidence) if modis else q.confidence.astype(str).str.lower().str[0]
            q = q.rename(columns={"brightness": "bright", "bright_t31": "bright2"} if modis else {"bright_ti4": "bright", "bright_ti5": "bright2"})
            for column, places in (("latitude", 5), ("longitude", 5), ("frp", 2), ("bright", 2), ("bright2", 2), ("scan", 2), ("track", 2)):
                q[column] = q[column].round(places)
            for row in q.itertuples():
                key = tuple(normalized(v) for v in (int(year), row.latitude, row.longitude, row.doy, int(row.acq_time), row.sensor_code, row.dn, row.frp, row.conf, row.bright, row.bright2, row.scan, row.track, row.version_code))
                (eligible if row.type_label == "0" else nonzero)[key] += 1
            b = d[box & confidence & window & labels.eq("0")].copy()
            b["fx"] = np.floor(b.longitude / .01).astype(int)
            b["fy"] = np.floor(b.latitude / .01).astype(int)
            b["fam"] = 0 if modis else 1 if family == "viirs-snpp" else 2
            b["dn"] = b.daynight.str.upper().str[0].eq("N").astype(int)
            burning.append(b)
        actual = Counter()
        for year in meta["hotspot_years"]:
            obj = committed(f"web/data/{rid}/hotspots/{year}.json")
            c = obj["cols"]
            for i in range(obj["n"]):
                actual[tuple([year] + [c[k][i] for k in ("lat", "lon", "doy", "time", "sensor", "dn", "frp", "conf", "bright", "bright2", "scan", "track", "version")])] += 1
        b = pd.concat(burning, ignore_index=True)
        groups = b.groupby(["fx", "fy", "fam", "acq_date", "dn"]).agg(nd=("frp", "size"), frp=("frp", "max"))
        expected_bd = Counter()
        for (fx, fy, fam, date, dn), row in groups.iterrows():
            frp = float(row.frp)
            k = 0 if not np.isfinite(frp) or frp <= 0 else 1 if frp < 5 else 2 if frp < 20 else 3
            expected_bd[(fx, fy, fam, date, dn, int(row.nd), normalized(round(frp, 2)), k)] += 1
        actual_bd = Counter()
        for year in meta["burning_days"]["years"]:
            obj = committed(f"web/data/{rid}/burning/{year}.json")
            c = obj["cols"]
            for i in range(obj["n"]):
                date = (pd.Timestamp(year, 1, 1) + pd.Timedelta(days=c["doy"][i] - 1)).strftime("%Y-%m-%d")
                actual_bd[(obj["x0"]+c["x"][i], obj["y0"]+c["y"][i], c["fam"][i], date, c["dn"][i], c["nd"][i], c["frp"][i], c["k"][i])] += 1
        results[rid] = dict(raw_types=dict(all_types), excluded_by_type_after_box_confidence=dict(removed),
                            committed_hotspots=sum(actual.values()), type0_expected_hotspots=sum(eligible.values()),
                            unexpected_hotspots=sum((actual-eligible).values()), missing_hotspots=sum((eligible-actual).values()),
                            non_type0_fingerprint_matches=sum((actual & nonzero).values()),
                            committed_burning_days=sum(actual_bd.values()),
                            unexpected_burning_days=sum((actual_bd-expected_bd).values()), missing_burning_days=sum((expected_bd-actual_bd).values()))
        print(rid, json.dumps(results[rid]), flush=True)
    with (OUT / "existing_type_counts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(detail[0])); writer.writeheader(); writer.writerows(detail)
    (OUT / "existing_type_impact.json").write_text(json.dumps(results, indent=2)+"\n", encoding="utf-8")
    assert all(not r[k] for r in results.values() for k in ("unexpected_hotspots", "missing_hotspots", "non_type0_fingerprint_matches", "unexpected_burning_days", "missing_burning_days"))


if __name__ == "__main__":
    main()
