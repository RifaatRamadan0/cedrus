"""Filter raw FIRMS detections and count them per grid cell per day.

    python pipeline/02_aggregate.py

Reads data/raw/<country>/*.csv, applies the filters fixed in docs/TEST_PLAN.md,
writes data/processed/<country>/daily_cells.csv with columns
    date, sensor, cell, count
sensor is one of: terra, aqua, snpp, noaa20, noaa21.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from common import BOX, CELL, ROOT, cell_of

SENSOR_OF_FILE = {"viirs-snpp": "snpp", "viirs-jpss1": "noaa20", "viirs-jpss2": "noaa21"}


def load(path):
    df = pd.read_csv(path, low_memory=False)
    if df.empty:
        return df
    stem = path.name.split("_")[0]
    lon0, lat0, lon1, lat1 = BOX
    df = df[(df.longitude >= lon0) & (df.longitude < lon1) & (df.latitude >= lat0) & (df.latitude < lat1)]
    if "type" in df.columns:
        df = df[df["type"] == 0]  # presumed vegetation fire
    if stem == "modis":
        df = df[pd.to_numeric(df.confidence, errors="coerce") >= 30]
        sat = df.satellite.astype(str).str.lower().str[0]
        df = df.assign(sensor=sat.map({"t": "terra", "a": "aqua"}))
    else:
        df = df[df.confidence.astype(str).str.lower().str[0].isin(["n", "h"])]
        df = df.assign(sensor=SENSOR_OF_FILE[stem])
    return df.assign(cell=cell_of(df.longitude, df.latitude), date=df.acq_date)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", default="Portugal")
    args = ap.parse_args()
    raw = ROOT / "data" / "raw" / args.country.lower()
    out = ROOT / "data" / "processed" / args.country.lower()
    out.mkdir(parents=True, exist_ok=True)

    parts, kept = [], {}
    for path in sorted(raw.glob("*.csv")):
        df = load(path)
        if df.empty:
            continue
        kept[path.name] = int(len(df))
        parts.append(df.groupby(["date", "sensor", "cell"]).size().rename("count").reset_index())
    daily = pd.concat(parts).groupby(["date", "sensor", "cell"], as_index=False)["count"].sum()
    daily.sort_values(["date", "sensor", "cell"]).to_csv(out / "daily_cells.csv", index=False)
    (out / "filter_report.json").write_text(json.dumps(
        {"box": BOX, "cell_deg": CELL, "kept_detections_per_file": kept}, indent=1))
    print(daily.groupby("sensor")["count"].sum().to_string())
    print(f"-> {out / 'daily_cells.csv'} ({len(daily)} rows)")


if __name__ == "__main__":
    main()
