"""Daily NOAA-20 burning days per region, 2019-2025: the "normal" that the live last-days count is compared with.

    python tools/nrt_normal.py               # every product region whose raw country files are on this machine

The live FIRMS feed (near real time) has no `type` field, so it cannot drop gas flares and factories the way the
record does. To compare like with like, both sides here are built the same way:
  * NOAA-20 VIIRS only (the satellite in the live feed whose archive covers 2019-2025 in full),
  * confidence nominal or high, every `type`,
  * a burning day = one 0.01-degree square on one date and one time of day (day/night), as in the record,
  * squares that were ever flagged as a static or offshore heat source (type 2 or 3) in the VIIRS country files on
    this machine (2012 up to their last year, at most 2025) are dropped from both sides (data/nrt/<region>_static.json, also used by tools/nrt_snapshot.py),
  * inside the region's box and its country outline (pipeline/outline.py; Lebanon's 2021 line), as the 2026 builder.

Writes data/nrt/<region>_daily.json: {"years": [...], "days": {"2019": [366 counts by day of year], ...}}.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from outline import inside, load_countries, load_lebanon_2021  # noqa: E402
from regions import REGIONS  # noqa: E402

OUT = ROOT / "data" / "nrt"
YEARS = range(2019, 2026)
FINE = 0.01
ISO = {"Portugal": "PRT", "Lebanon": "LBN", "Syria": "SYR", "Argentina": "ARG"}


def rings_for(region):
    meta = REGIONS[region]
    if region == "lebanon":
        return load_lebanon_2021()
    return load_countries()[ISO[meta["country"]]]["rings"]


def raw_files(region, stem):
    meta = REGIONS[region]
    folder = ROOT / "data" / "raw" / meta.get("raw_dir", region)
    return sorted(folder.glob(f"{stem}_*_{meta['country']}.csv"))


def clip(df, region, rings):
    x0, y0, x1, y1 = REGIONS[region]["box"]
    df = df[(df.longitude >= x0) & (df.longitude < x1) & (df.latitude >= y0) & (df.latitude < y1)]
    return df[inside(rings, df.longitude.values, df.latitude.values)]


def squares(df):
    return np.floor(df.longitude.values / FINE).astype(int), np.floor(df.latitude.values / FINE).astype(int)


def static_squares(region, rings):
    """Every 0.01-degree square with a type 2 or 3 detection by any VIIRS satellite, 2012-2025."""
    keep = set()
    for stem in ("viirs-snpp", "viirs-jpss1"):
        for f in raw_files(region, stem):
            df = pd.read_csv(f, usecols=["latitude", "longitude", "type"])
            df = clip(df[df["type"].isin([2, 3])], region, rings)
            keep.update(zip(*squares(df)))
    return keep


def daily(region, rings, static):
    days = {}
    for f in raw_files(region, "viirs-jpss1"):
        year = int(f.name.split("_")[1])
        if year not in YEARS:
            continue
        df = pd.read_csv(f, usecols=["latitude", "longitude", "acq_date", "confidence", "daynight"])
        df = clip(df[df.confidence.astype(str).str.lower().isin(["n", "h", "nominal", "high"])], region, rings)
        sx, sy = squares(df)
        df = df.assign(sx=sx, sy=sy)
        df = df[[(a, b) not in static for a, b in zip(sx, sy)]]
        bd = df.drop_duplicates(["sx", "sy", "acq_date", "daynight"])
        doy = pd.to_datetime(bd.acq_date).dt.dayofyear.values
        days[str(year)] = np.bincount(doy, minlength=367)[1:].tolist()
    return days


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for region, meta in REGIONS.items():
        if "product" not in meta["roles"]:
            continue
        if not raw_files(region, "viirs-jpss1"):
            print(f"{region}: no NOAA-20 country files on this machine, skipped")
            continue
        rings = rings_for(region)
        static = static_squares(region, rings)
        days = daily(region, rings, static)
        missing = [y for y in YEARS if str(y) not in days]
        (OUT / f"{region}_static.json").write_text(json.dumps(sorted([int(a), int(b)] for a, b in static)), encoding="utf-8")
        (OUT / f"{region}_daily.json").write_text(json.dumps({"region": region, "years": sorted(map(int, days)), "days": days}), encoding="utf-8")
        tot = {y: sum(v) for y, v in days.items()}
        print(f"{region}: {len(static)} static squares; NOAA-20 burning days per year {tot}" + (f"; missing {missing}" if missing else ""))


if __name__ == "__main__":
    main()
