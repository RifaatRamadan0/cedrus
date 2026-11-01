"""Detections, the row table and the outage days for round 2 (docs/ROUND2_PLAN.md).

Filters are the bake-off's own (pipeline.bakeoff.data._read). A region's raw folder is
data/raw/<FIRMS country, lower case>: data/raw/chile for central_chile, data/raw/australia_sw for sw_australia.
A sealed region is opened only by the confirmation, and only when the caller passes sealed_ok=True.
"""
import json

import numpy as np
import pandas as pd

from pipeline.bakeoff.data import RAW, ROOT, _read
from pipeline.regions import CELL, REGIONS, regions_with

OUT = ROOT / "data" / "processed" / "round2"
FIRST_MONTH, FIT_LAST = "2012-02", "2019-12"
N20_FIRST = "2018-04"
STEMS = {"modis": "modis", "snpp": "viirs-snpp", "noaa20": "viirs-jpss1"}
FIRST_YEAR = {"modis": 2012, "snpp": 2012, "noaa20": 2018}
CACHE_VERSION = 1


def guard(region, sealed_ok=False):
    """Every file access goes through here. Sealed regions only for the confirmation run."""
    if region not in REGIONS:
        raise SystemExit(f"{region} is not a region in pipeline/regions.py")
    if "sealed" in REGIONS[region]["roles"] and not sealed_ok:
        raise SystemExit(f"{region} is sealed until the round-2 model is frozen (docs/ROUND2_PLAN.md)")


def dev_regions():
    regs = regions_with("dev")
    for r in regs:
        guard(r)
    return regs


def folder(region):
    return RAW / REGIONS[region]["country"].lower()


def file_name(region, sensor, year):
    return f"{STEMS[sensor]}_{year}_{REGIONS[region]['country']}.csv"


def files_wanted(region, last_year):
    return {(s, y): file_name(region, s, y) for s in STEMS for y in range(FIRST_YEAR[s], last_year + 1)}


def availability(region, last_year, sealed_ok=False):
    """{(sensor, year): present} from the region's manifest.json; no detection file is opened."""
    guard(region, sealed_ok)
    man = folder(region) / "manifest.json"
    done = json.loads(man.read_text()) if man.exists() else {}
    return {k: (f in done and (folder(region) / f).exists()) for k, f in files_wanted(region, last_year).items()}


def fit_ready(avail):
    """A region can be fitted only with MODIS and Suomi NPP for 2012-2019 and NOAA-20 for 2018-2019."""
    need = [(s, y) for s in ("modis", "snpp") for y in range(2012, 2020)] + [("noaa20", 2018), ("noaa20", 2019)]
    return [k for k in need if not avail.get(k, False)]


def pixels(region, last_year, sealed_ok=False):
    """Every kept detection 2012-01-01..<last_year>-12-31 from the files that exist, cached per region."""
    guard(region, sealed_ok)
    avail = availability(region, last_year, sealed_ok)
    names = {k: f for k, f in files_wanted(region, last_year).items() if avail[k]}
    man = json.loads((folder(region) / "manifest.json").read_text())
    sig = {"version": CACHE_VERSION, "last_year": last_year, "files": {f: man[f]["sha256"] for f in names.values()}}
    out = OUT / region
    out.mkdir(parents=True, exist_ok=True)
    cache, meta = out / f"pixels_{last_year}.pkl", out / f"pixels_{last_year}.json"
    if cache.exists() and meta.exists() and json.loads(meta.read_text()) == sig:
        return pd.read_pickle(cache)
    box = REGIONS[region]["box"]
    parts = []
    for (sensor, year), name in names.items():
        df = _read(folder(region) / name, "modis" if sensor == "modis" else "viirs", box)
        if len(df):
            assert df.date.str[:4].astype(int).eq(year).all(), f"{name}: rows outside {year}"
            if sensor != "modis":
                df["sensor"] = sensor
            parts.append(df[["sensor", "lat", "lon", "date", "dn"]])
    px = pd.concat(parts, ignore_index=True)
    px = px[px.sensor.notna() & px.dn.isin(["D", "N"])].reset_index(drop=True)
    px["cell"] = (np.floor(px.lon / CELL).astype(int).astype(str) + "_"
                  + np.floor(px.lat / CELL).astype(int).astype(str))
    px["ym"] = px.date.str[:7]
    px["region"] = region
    px.to_pickle(cache)
    meta.write_text(json.dumps(sig, indent=1))
    return px


def rows(region, px, last_month):
    """cell x month x day/night, 2012-02..last_month, for every cell with a MODIS, Suomi NPP or NOAA-20 detection in
    2012-02..2019-12. Y = Terra + Aqua, V = Suomi NPP, V20 = NOAA-20."""
    w = px[(px.ym >= FIRST_MONTH) & (px.ym <= last_month)]
    cells = sorted(w[w.ym <= FIT_LAST].cell.unique())
    months = [str(p) for p in pd.period_range(FIRST_MONTH, last_month, freq="M")]
    grid = pd.MultiIndex.from_product([cells, months, ["D", "N"]], names=["cell", "ym", "dn"])
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
    late = w[w.ym > FIT_LAST]
    cover = {"cells": len(cells),
             "inside": late[late.cell.isin(cells)].groupby("sensor").size().to_dict(),
             "outside": late[~late.cell.isin(cells)].groupby("sensor").size().to_dict()}
    return r.drop(columns=["terra", "aqua", "snpp", "noaa20"]), cover


def outage_days(px, first_day, last_day, sensor, other, min_other=50, usable=None):
    """Days in [first_day, last_day] where `sensor` has zero detections over the regions combined while `other`
    has >= min_other (the bake-off's outage rule). Families: "modis" (Terra + Aqua), "snpp", "noaa20".

    usable: optional set of (region, year) whose files for both families exist; other pairs are left out of the
    count, so a missing file cannot look like an outage.
    """
    fam = px.sensor.map({"terra": "modis", "aqua": "modis", "snpp": "snpp", "noaa20": "noaa20"})
    w = px.assign(fam=fam)
    w = w[(w.date >= first_day) & (w.date <= last_day) & w.fam.isin([sensor, other])]
    if usable is not None:
        w = w[(w.region + ":" + w.date.str[:4]).isin({f"{r}:{y}" for r, y in usable})]
    days = pd.date_range(first_day, last_day).strftime("%Y-%m-%d")
    d = w.groupby(["date", "fam"]).size().unstack(fill_value=0).reindex(days, fill_value=0)
    d = d.reindex(columns=[sensor, other], fill_value=0)
    return d.index[(d[sensor] == 0) & (d[other] >= min_other)].tolist()


def build_table(Rs):
    """Concatenate per-region row tables into one table with region / cell ids and the bake-off's group ids."""
    from pipeline.bakeoff.models import add_groups

    regions = list(Rs)
    R = pd.concat([Rs[r] for r in regions], ignore_index=True)
    R["rid"] = R.region.map({r: i for i, r in enumerate(regions)}).astype(int)
    R["cid"] = pd.factorize(R.region + ":" + R.cell)[0]
    R["dnN"] = (R.dn == "N").astype(int)
    return add_groups(R, len(regions))
