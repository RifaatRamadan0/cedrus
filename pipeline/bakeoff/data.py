"""Filtered detections, the row table and the outage rule (docs/BAKEOFF_PLAN.md, "Data").

Reads only data/raw/<region>/{modis,viirs-snpp}_<year>_<Country>.csv for 2012..2019.
Rows run from Feb 2012 (Suomi NPP's first full month) to Dec 2019.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.regions import CELL, REGIONS, assert_not_sealed, regions_with

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "bakeoff"
YEARS = list(range(2012, 2020))
FIRST_MONTH, LAST_MONTH = "2012-02", "2019-12"
MONTHS = [str(p) for p in pd.period_range(FIRST_MONTH, LAST_MONTH, freq="M")]
FAMILY = {"terra": "modis", "aqua": "modis", "snpp": "viirs"}
CACHE_VERSION = 2


def files_needed(region):
    c = REGIONS[region]["country"]
    return [f"{s}_{y}_{c}.csv" for s in ("modis", "viirs-snpp") for y in YEARS]


def readiness(region):
    """(ready, missing file names) from the region's manifest.json."""
    assert_not_sealed(region)
    folder = RAW / region
    man = folder / "manifest.json"
    done = json.loads(man.read_text()) if man.exists() else {}
    missing = [f for f in files_needed(region) if f not in done or not (folder / f).exists()]
    return not missing, missing


def _signature(region):
    man = json.loads((RAW / region / "manifest.json").read_text())
    return {"version": CACHE_VERSION, "files": {f: man[f]["sha256"] for f in files_needed(region)}}


def _read(path, sensor_file, box):
    df = pd.read_csv(path, dtype={"acq_time": str}, low_memory=False)
    if df.empty:
        return df
    if box is not None:
        lon0, lat0, lon1, lat1 = box
        df = df[(df.longitude >= lon0) & (df.longitude < lon1) & (df.latitude >= lat0) & (df.latitude < lat1)]
    if "type" in df.columns:
        df = df[df["type"] == 0]
    if sensor_file == "modis":
        df = df[pd.to_numeric(df.confidence, errors="coerce") >= 30]
        sensor = df.satellite.astype(str).str.upper().str[0].map({"T": "terra", "A": "aqua"})
    else:
        df = df[df.confidence.astype(str).str.lower().str[0].isin(["n", "h"])]
        sensor = pd.Series("snpp", index=df.index)
    t = df.acq_time.str.zfill(4)
    return pd.DataFrame({
        "sensor": sensor.values,
        "lat": df.latitude.values, "lon": df.longitude.values,
        "date": df.acq_date.values,
        "tmin": (t.str[:2].astype(int) * 60 + t.str[2:].astype(int)).values,
        "dn": df.daynight.astype(str).str.upper().str[0].values,
        "frp": pd.to_numeric(df.frp, errors="coerce").values,
        "scan": df.scan.values, "track": df.track.values,
    })


def pixels(region):
    """Every kept detection of the region, 2012-01-01..2019-12-31, cached per region."""
    assert_not_sealed(region)
    folder = OUT / region
    folder.mkdir(parents=True, exist_ok=True)
    sig = _signature(region)
    cache, meta = folder / "pixels.pkl", folder / "pixels.json"
    if cache.exists() and meta.exists() and json.loads(meta.read_text()) == sig:
        return pd.read_pickle(cache)
    box = REGIONS[region]["box"]
    parts = []
    for name in files_needed(region):
        year = int(name.split("_")[1])
        assert 2012 <= year <= 2019, name
        df = _read(RAW / region / name, name.split("_")[0], box)
        if len(df):
            assert df.date.str[:4].astype(int).eq(year).all(), f"{name}: rows outside {year}"
            parts.append(df)
    px = pd.concat(parts, ignore_index=True)
    px = px[px.sensor.notna() & px.dn.isin(["D", "N"])].reset_index(drop=True)
    px["ix"] = np.floor(px.lon / CELL).astype(int)
    px["iy"] = np.floor(px.lat / CELL).astype(int)
    px["cell"] = px.ix.astype(str) + "_" + px.iy.astype(str)
    px["ym"] = px.date.str[:7]
    px["region"] = region
    px.to_pickle(cache)
    meta.write_text(json.dumps(sig, indent=1))
    return px


def in_window(px):
    return px[(px.ym >= FIRST_MONTH) & (px.ym <= LAST_MONTH)]


def rows(region, px):
    """cell x month x day/night for every cell with a detection in the window; Y = Terra + Aqua, V = Suomi NPP."""
    w = in_window(px)
    cells = sorted(w.cell.unique())
    grid = pd.MultiIndex.from_product([cells, MONTHS, ["D", "N"]], names=["cell", "ym", "dn"])
    cnt = w.groupby(["cell", "ym", "dn", "sensor"]).size().unstack("sensor", fill_value=0)
    cnt = cnt.reindex(grid, fill_value=0)
    for s in ("terra", "aqua", "snpp"):
        if s not in cnt:
            cnt[s] = 0
    r = cnt[["terra", "aqua", "snpp"]].reset_index()
    r.columns.name = None
    r["Y"] = r.terra + r.aqua
    r["V"] = r.snpp
    r["year"] = r.ym.str[:4].astype(int)
    r["moy"] = r.ym.str[5:7].astype(int)
    r.insert(0, "region", region)
    return r.drop(columns=["terra", "aqua", "snpp"])


def outages(all_px):
    """Outage days per family across all included regions, and the months they rule out of scoring.

    A family-day with zero detections while the other family has >= 50 is an outage.
    """
    w = in_window(all_px)
    days = pd.date_range(f"{FIRST_MONTH}-01", "2019-12-31").strftime("%Y-%m-%d")
    d = w.assign(fam=w.sensor.map(FAMILY)).groupby(["date", "fam"]).size().unstack(fill_value=0)
    d = d.reindex(days, fill_value=0).reindex(columns=["modis", "viirs"], fill_value=0)
    out_modis = d.index[(d.modis == 0) & (d.viirs >= 50)].tolist()
    out_viirs = d.index[(d.viirs == 0) & (d.modis >= 50)].tolist()
    # Not part of the rule: single-satellite gaps inside the MODIS family, reported only.
    s = w.groupby(["date", "sensor"]).size().unstack(fill_value=0).reindex(days, fill_value=0)
    s = s.reindex(columns=["terra", "aqua", "snpp"], fill_value=0)
    single = {sat: s.index[(s[sat] == 0) & (s.snpp >= 50)].tolist() for sat in ("terra", "aqua")}
    bad = sorted({x[:7] for x in out_modis + out_viirs})
    return {"modis_days": out_modis, "viirs_days": out_viirs, "excluded_months": bad,
            "single_satellite_zero_days": single}


def dev_regions():
    regs = regions_with("dev")
    for r in regs:
        assert_not_sealed(r)
    return regs
