"""Detections 2012-2025 (MODIS, Suomi NPP, NOAA-20), the row table and the outage days.

Filters are the bake-off's own (pipeline.bakeoff.data._read). A region's raw folder is
data/raw/<FIRMS country, lower case>, e.g. data/raw/chile for central_chile.
"""
import json

import numpy as np
import pandas as pd

from pipeline.bakeoff.data import RAW, ROOT, _read
from pipeline.regions import CELL, REGIONS, assert_not_sealed

OUT = ROOT / "data" / "processed" / "confirm"
YEARS = list(range(2012, 2026))
N20_YEARS = list(range(2018, 2026))
FIRST_MONTH, LAST_MONTH = "2012-02", "2025-12"
FIT_LAST = "2019-12"
MONTHS = [str(p) for p in pd.period_range(FIRST_MONTH, LAST_MONTH, freq="M")]
SENSOR_OF_FILE = {"modis": None, "viirs-snpp": "snpp", "viirs-jpss1": "noaa20"}
CACHE_VERSION = 1


def folder(region):
    return RAW / REGIONS[region]["country"].lower()


def files_needed(region):
    c = REGIONS[region]["country"]
    return ([f"modis_{y}_{c}.csv" for y in YEARS] + [f"viirs-snpp_{y}_{c}.csv" for y in YEARS]
            + [f"viirs-jpss1_{y}_{c}.csv" for y in N20_YEARS])


def readiness(region):
    """(ready, missing file names) from the manifest only; no detection file is opened."""
    assert_not_sealed(region)
    man = folder(region) / "manifest.json"
    done = json.loads(man.read_text()) if man.exists() else {}
    missing = [f for f in files_needed(region) if f not in done or not (folder(region) / f).exists()]
    return not missing, missing


def pixels(region):
    """Every kept detection 2012-01-01..2025-12-31, cached per region (keyed on the files' SHA-256)."""
    assert_not_sealed(region)
    out = OUT / region
    out.mkdir(parents=True, exist_ok=True)
    man = json.loads((folder(region) / "manifest.json").read_text())
    sig = {"version": CACHE_VERSION, "files": {f: man[f]["sha256"] for f in files_needed(region)}}
    cache, meta = out / "pixels.pkl", out / "pixels.json"
    if cache.exists() and meta.exists() and json.loads(meta.read_text()) == sig:
        return pd.read_pickle(cache)
    box = REGIONS[region]["box"]
    parts = []
    for name in files_needed(region):
        stem, year = name.split("_")[0], int(name.split("_")[1])
        df = _read(folder(region) / name, stem, box)
        if len(df):
            assert df.date.str[:4].astype(int).eq(year).all(), f"{name}: rows outside {year}"
            if SENSOR_OF_FILE[stem]:
                df["sensor"] = SENSOR_OF_FILE[stem]
            parts.append(df)
    px = pd.concat(parts, ignore_index=True)
    px = px[px.sensor.notna() & px.dn.isin(["D", "N"])].reset_index(drop=True)
    px["cell"] = (np.floor(px.lon / CELL).astype(int).astype(str) + "_"
                  + np.floor(px.lat / CELL).astype(int).astype(str))
    px["ym"] = px.date.str[:7]
    px["region"] = region
    px.to_pickle(cache)
    meta.write_text(json.dumps(sig, indent=1))
    return px


def rows(region, px):
    """cell x month x day/night, 2012-02..2025-12, for every cell with a MODIS or VIIRS detection in
    2012-02..2019-12. Y = Terra + Aqua, V = Suomi NPP, V20 = NOAA-20."""
    w = px[(px.ym >= FIRST_MONTH) & (px.ym <= LAST_MONTH)]
    fit_cells = sorted(w[w.ym <= FIT_LAST].cell.unique())
    grid = pd.MultiIndex.from_product([fit_cells, MONTHS, ["D", "N"]], names=["cell", "ym", "dn"])
    cnt = w.groupby(["cell", "ym", "dn", "sensor"]).size().unstack("sensor", fill_value=0)
    cnt = cnt.reindex(grid, fill_value=0)
    for s in ("terra", "aqua", "snpp", "noaa20"):
        if s not in cnt:
            cnt[s] = 0
    r = cnt[["terra", "aqua", "snpp", "noaa20"]].reset_index()
    r.columns.name = None
    r["Y"] = r.terra + r.aqua
    r["V"] = r.snpp
    r["V20"] = r.noaa20
    r["year"] = r.ym.str[:4].astype(int)
    r["moy"] = r.ym.str[5:7].astype(int)
    r.insert(0, "region", region)
    # detections that fall in cells outside the row table (first seen after 2019): counted, not scored
    late = w[(w.ym > FIT_LAST) & ~w.cell.isin(fit_cells)]
    outside = late.groupby("sensor").size().to_dict()
    inside = w[(w.ym > FIT_LAST) & w.cell.isin(fit_cells)].groupby("sensor").size().to_dict()
    return r.drop(columns=["terra", "aqua", "snpp", "noaa20"]), {"outside": outside, "inside": inside,
                                                                    "cells": len(fit_cells)}


def outages(all_px):
    """Outage days over all included regions combined (bake-off rule, applied per family).

    MODIS outage: MODIS 0 while Suomi NPP >= 50.  Suomi NPP outage: Suomi NPP 0 while MODIS >= 50.
    NOAA-20 outage (used by Test 2 only): NOAA-20 0 while MODIS >= 50, from 2018-04 on.
    """
    w = all_px[(all_px.ym >= FIRST_MONTH) & (all_px.ym <= LAST_MONTH)]
    days = pd.date_range(f"{FIRST_MONTH}-01", "2025-12-31").strftime("%Y-%m-%d")
    fam = w.sensor.map({"terra": "modis", "aqua": "modis", "snpp": "snpp", "noaa20": "noaa20"})
    d = w.assign(fam=fam).groupby(["date", "fam"]).size().unstack(fill_value=0)
    d = d.reindex(days, fill_value=0).reindex(columns=["modis", "snpp", "noaa20"], fill_value=0)
    out = {
        "modis": d.index[(d.modis == 0) & (d.snpp >= 50)].tolist(),
        "snpp": d.index[(d.snpp == 0) & (d.modis >= 50)].tolist(),
        "noaa20": d.index[(d.noaa20 == 0) & (d.modis >= 50) & (d.index >= "2018-04-01")].tolist(),
    }
    out["months_modis_snpp"] = sorted({x[:7] for x in out["modis"] + out["snpp"]})  # Test 1, seam, drift
    out["months_snpp_noaa20"] = sorted({x[:7] for x in out["snpp"] + out["noaa20"]})  # Test 2
    return out
