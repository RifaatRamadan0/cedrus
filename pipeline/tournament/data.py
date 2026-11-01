"""Detections with fire power and pixel size, the row table in both units, and the outage days (docs/TOURNAMENT_PLAN.md).

Filters, box clip, rows and outage rule are round 2's (pipeline.round2.data, which uses the bake-off's _read).
Round 2's own pixel cache keeps no FRP or scan, so the tournament reads the same files again and keeps them, in
data/processed/tournament/<region>/pixels.pkl. Every file access goes through pipeline.round2.data.guard, which
refuses sealed regions.

Units, on the same rows (cell x month x day/night):
- pixels: Y = Terra + Aqua detections, V = Suomi NPP, V20 = NOAA-20 (round 2's rows, unchanged);
- burning days: a 0.01 degree cell counts once per day if it has any detection of that family; the cell-day counts
  are summed per 0.25 degree cell x month x day/night. MODIS (Terra and Aqua together) in the same unit.
Class counts (Suomi NPP and NOAA-20): FRP class f0 FRP <= 0, f1 0 < FRP < 5, f2 5 <= FRP < 20, f3 FRP >= 20 MW;
scan class s0 scan < 0.5, s1 0.5 <= scan <= 0.65, s2 scan > 0.65 km. A burning day takes the classes of its
detection with the largest FRP, so its class counts still add up to its total.
"""
import json

import numpy as np
import pandas as pd

from pipeline.bakeoff.data import _read
from pipeline.round2 import data as r2

ROOT = r2.ROOT
OUT = ROOT / "data" / "processed" / "tournament"
LAST_YEAR = 2021
LAST_MONTH = "2021-12"
FIT_LAST = r2.FIT_LAST
N20_FIRST = r2.N20_FIRST
FINE = 0.01  # burning-day cell, degrees
FRP_EDGES = (5.0, 20.0)
SCAN_EDGES = (0.5, 0.65)
NF, NS = 4, 3
CACHE_VERSION = 1
SAT = ("V", "V20")  # Suomi NPP, NOAA-20 column stems


def frp_class(frp):
    frp = np.asarray(frp, float)
    return np.where(~(frp > 0), 0, np.where(frp < FRP_EDGES[0], 1, np.where(frp < FRP_EDGES[1], 2, 3)))


def scan_class(scan):
    scan = np.asarray(scan, float)
    return np.where(scan < SCAN_EDGES[0], 0, np.where(scan <= SCAN_EDGES[1], 1, 2))


def class_cols(stem):
    return [f"{stem}f{k}" for k in range(NF)] + [f"{stem}s{k}" for k in range(NS)]


def pixels(region):
    """Every kept detection 2012-01-01..2021-12-31 of a development region, with FRP and scan, cached per region."""
    r2.guard(region)
    avail = r2.availability(region, LAST_YEAR)
    names = {k: f for k, f in r2.files_wanted(region, LAST_YEAR).items() if avail[k]}
    man = json.loads((r2.folder(region) / "manifest.json").read_text())
    sig = {"version": CACHE_VERSION, "last_year": LAST_YEAR, "files": {f: man[f]["sha256"] for f in names.values()}}
    out = OUT / region
    out.mkdir(parents=True, exist_ok=True)
    cache, meta = out / "pixels.pkl", out / "pixels.json"
    if cache.exists() and meta.exists() and json.loads(meta.read_text()) == sig:
        return pd.read_pickle(cache)
    box = r2.REGIONS[region]["box"]
    parts = []
    for (sensor, year), name in names.items():
        df = _read(r2.folder(region) / name, "modis" if sensor == "modis" else "viirs", box)
        if len(df):
            assert df.date.str[:4].astype(int).eq(year).all(), f"{name}: rows outside {year}"
            if sensor != "modis":
                df["sensor"] = sensor
            parts.append(df[["sensor", "lat", "lon", "date", "dn", "frp", "scan"]])
    px = pd.concat(parts, ignore_index=True)
    px = px[px.sensor.notna() & px.dn.isin(["D", "N"])].reset_index(drop=True)
    px["cell"] = (np.floor(px.lon / r2.CELL).astype(int).astype(str) + "_"
                  + np.floor(px.lat / r2.CELL).astype(int).astype(str))
    px["fx"] = np.floor(px.lon / FINE).astype(np.int32)
    px["fy"] = np.floor(px.lat / FINE).astype(np.int32)
    px["ym"] = px.date.str[:7]
    px["region"] = region
    px.to_pickle(cache)
    meta.write_text(json.dumps(sig, indent=1))
    return px


def _counts(w, sensor_sets, stem):
    """Per (cell, ym, dn): total and class counts of one family, as detections (pixels) and as burning days."""
    d = w[w.sensor.isin(sensor_sets)]
    f, s = frp_class(d.frp.to_numpy()), scan_class(d.scan.to_numpy())
    d = d.assign(fc=f, sc=s)
    key = ["cell", "ym", "dn"]
    px_tot = d.groupby(key).size().rename(stem)
    parts = [px_tot]
    if stem != "Y":
        parts += [d[d.fc == k].groupby(key).size().rename(f"{stem}f{k}") for k in range(NF)]
        parts += [d[d.sc == k].groupby(key).size().rename(f"{stem}s{k}") for k in range(NS)]
    # burning days: one per 0.01 degree cell x date x day/night, classed by its largest-FRP detection
    frp = np.where(np.isfinite(d.frp.to_numpy()), d.frp.to_numpy(), -np.inf)
    d = d.assign(frpk=frp).sort_values(["cell", "fx", "fy", "date", "dn", "frpk"], ascending=[1, 1, 1, 1, 1, 0],
                                       kind="mergesort")
    b = d.drop_duplicates(["cell", "fx", "fy", "date", "dn"], keep="first")
    stem_b = stem + "b"
    parts.append(b.groupby(key).size().rename(stem_b))
    if stem != "Y":
        parts += [b[b.fc == k].groupby(key).size().rename(f"{stem_b}f{k}") for k in range(NF)]
        parts += [b[b.sc == k].groupby(key).size().rename(f"{stem_b}s{k}") for k in range(NS)]
    return pd.concat(parts, axis=1)


def rows(region, px):
    """Round 2's rows (pipeline.round2.data.rows, 2012-02..2021-12) with class counts and the burning-day unit added.
    The pixel counts Y, V, V20 are round 2's own; the added totals are checked against them."""
    base, cover = r2.rows(region, px, LAST_MONTH)
    w = px[(px.ym >= r2.FIRST_MONTH) & (px.ym <= LAST_MONTH)]
    extra = pd.concat([_counts(w, ["terra", "aqua"], "Y"), _counts(w, ["snpp"], "V"), _counts(w, ["noaa20"], "V20")],
                      axis=1)
    extra = extra.drop(columns=["Y", "V", "V20"]).fillna(0).astype(np.int32)
    R = base.merge(extra.reset_index(), on=["cell", "ym", "dn"], how="left")
    cols = [c for c in extra.columns]
    R[cols] = R[cols].fillna(0).astype(np.int32)
    for c in ("Y", "V", "V20"):
        R[c] = R[c].astype(np.int32)
    for stem in SAT:
        for u in ("", "b"):
            s = stem + u
            fsum = R[[f"{s}f{k}" for k in range(NF)]].sum(axis=1)
            ssum = R[[f"{s}s{k}" for k in range(NS)]].sum(axis=1)
            assert (fsum == R[s]).all() and (ssum == R[s]).all(), f"{region}: {s} classes do not add up"
    for s in ("Y", "V", "V20"):
        assert (R[s + "b"] <= R[s]).all(), f"{region}: more burning days than detections in {s}"
    ij = R.cell.str.split("_", expand=True).astype(int)
    R["ix"], R["iy"] = ij[0].to_numpy(np.int32), ij[1].to_numpy(np.int32)
    return R, cover


def unit_table(R, unit):
    """The row table in one unit, with the column names every candidate reads: Y, V, V20 and their classes.
    unit "px" = pixels (round 2's), "bd" = burning days."""
    keep = ["region", "cell", "ym", "dn", "year", "moy", "rid", "cid", "dnN", "md", "rd", "rmd", "cmd", "ix", "iy"]
    T = R[keep].copy()
    sfx = "" if unit == "px" else "b"
    T["Y"] = R["Y" + sfx].to_numpy()
    for stem in SAT:
        T[stem] = R[stem + sfx].to_numpy()
        for c, src in zip(class_cols(stem), class_cols(stem + sfx)):
            T[c] = R[src].to_numpy()
    T.attrs.update(R.attrs)
    T.attrs["unit"] = unit
    return T


def swap_view(T, sfit):
    """The same table with every Suomi NPP column replaced by s x the NOAA-20 column (J-S), s per region x day/night.
    The candidate fitted on Suomi NPP is applied to this view; its fitted sums are untouched."""
    S = T.copy()
    s_row = sfit["s"][T.rd.to_numpy()]
    S["V"] = s_row * T.V20.to_numpy()
    for c, c20 in zip(class_cols("V"), class_cols("V20")):
        S[c] = s_row * T[c20].to_numpy()
    S.attrs.update(T.attrs)
    return S
