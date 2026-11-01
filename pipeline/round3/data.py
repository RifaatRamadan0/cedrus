"""The frozen entrant, detections with FRP and scan for 2012-2025, and the one-region table in the burning-day unit
(docs/TOURNAMENT_PLAN.md, "Round 3 sealed exam", and the ruling added 1 Nov 2026).

Filters, box clip, rows and outage rule are round 2's (pipeline.round2.data, which uses the bake-off's _read). Class
counts and the burning-day unit are the tournament's (pipeline.tournament.data._counts and unit_table). The tournament
reads only 2012-2021 and refuses sealed regions, so this module reads the same files through 2025 and keeps FRP and
scan, in data/processed/round3/<region>/pixels.pkl. Every file access goes through pipeline.round2.data.guard; a
sealed region is opened only when the caller passes sealed_ok=True, which only the confirmation run does.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.bakeoff.data import _read
from pipeline.bakeoff.models import add_groups
from pipeline.round2 import data as r2
from pipeline.tournament import data as td

ROOT = r2.ROOT
OUT = ROOT / "data" / "processed" / "round3"
FROZEN = ROOT / "data" / "processed" / "tournament" / "frozen_round3.json"
FROZEN_SHA256 = "f3130df9ed80894e0176866cd3c8e51a3c4a7233c3cb40dd1c7b93651d4357a2"  # docs/TOURNAMENT_RESULTS.md, Freeze
LAST_YEAR = 2025
LAST_MONTH = "2025-12"
FIT_LAST = r2.FIT_LAST
N20_FIRST = r2.N20_FIRST
CACHE_VERSION = 1


def load_frozen(path=FROZEN):
    """frozen_round3.json, refused unless its bytes have the SHA-256 recorded at the freeze."""
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"refused: {path} missing (the round-3 entrant is frozen there)")
    raw = path.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != FROZEN_SHA256:
        raise SystemExit(f"refused: {path} has SHA-256 {got}, not the frozen {FROZEN_SHA256} "
                         "(docs/TOURNAMENT_RESULTS.md, Freeze)")
    fz = json.loads(raw)
    bd = fz["champion_json"]["burning_days_model"]
    if not (fz["entrant"] == "D-a" and bd["id"] == "D-a" and bd["candidate"] == "C3" and bd["unit"] == "burning days"):
        raise SystemExit(f"refused: {path} does not name D-a (C3 in burning days) as the entrant")
    return fz, got


def complete(avail):
    """Files the confirmation needs that are not in the manifest: MODIS and Suomi NPP 2012-2025, NOAA-20 2018-2025."""
    need = [(s, y) for s in r2.STEMS for y in range(r2.FIRST_YEAR[s], LAST_YEAR + 1)]
    return [k for k in need if not avail.get(k, False)]


def pixels(region, sealed_ok=False):
    """Every kept detection 2012-01-01..2025-12-31 from the files that exist, with FRP and scan, cached per region."""
    r2.guard(region, sealed_ok)
    avail = r2.availability(region, LAST_YEAR, sealed_ok)
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
    px["fx"] = np.floor(px.lon / td.FINE).astype(np.int32)
    px["fy"] = np.floor(px.lat / td.FINE).astype(np.int32)
    px["ym"] = px.date.str[:7]
    px["region"] = region
    px.to_pickle(cache)
    meta.write_text(json.dumps(sig, indent=1))
    return px


def rows(region, px):
    """pipeline.tournament.data.rows with the last month at 2025-12: round 2's rows (cells with a detection in
    2012-02..2019-12) with the class counts and the burning-day unit added, checked against the pixel totals."""
    base, cover = r2.rows(region, px, LAST_MONTH)
    w = px[(px.ym >= r2.FIRST_MONTH) & (px.ym <= LAST_MONTH)]
    extra = pd.concat([td._counts(w, ["terra", "aqua"], "Y"), td._counts(w, ["snpp"], "V"),
                       td._counts(w, ["noaa20"], "V20")], axis=1)
    extra = extra.drop(columns=["Y", "V", "V20"]).fillna(0).astype(np.int32)
    R = base.merge(extra.reset_index(), on=["cell", "ym", "dn"], how="left")
    cols = [c for c in extra.columns]
    R[cols] = R[cols].fillna(0).astype(np.int32)
    for c in ("Y", "V", "V20"):
        R[c] = R[c].astype(np.int32)
    for stem in td.SAT:
        for u in ("", "b"):
            s = stem + u
            fsum = R[[f"{s}f{k}" for k in range(td.NF)]].sum(axis=1)
            ssum = R[[f"{s}s{k}" for k in range(td.NS)]].sum(axis=1)
            assert (fsum == R[s]).all() and (ssum == R[s]).all(), f"{region}: {s} classes do not add up"
    for s in ("Y", "V", "V20"):
        assert (R[s + "b"] <= R[s]).all(), f"{region}: more burning days than detections in {s}"
    ij = R.cell.str.split("_", expand=True).astype(int)
    R["ix"], R["iy"] = ij[0].to_numpy(np.int32), ij[1].to_numpy(np.int32)
    return R, cover


def prepare(R):
    """A one-region table: the region's own rows only, so every fallback stays inside the region (round 2's
    confirmation does the same)."""
    R = R.reset_index(drop=True).copy()
    R["rid"] = 0
    R["cid"] = pd.factorize(R.cell)[0]
    R["dnN"] = (R.dn == "N").astype(int)
    return add_groups(R, 1)


def burning_days(R):
    """The one-region table in the burning-day unit: Y, V, V20 and the class columns are burning days."""
    return td.unit_table(prepare(R), "bd")
