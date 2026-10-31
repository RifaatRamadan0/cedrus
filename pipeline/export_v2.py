"""Static data for the v2 website: harmonized monthly record per 0.25 deg cell, hotspots with weights, drift.

    python pipeline/export_v2.py                 # every product region with raw files present
    python pipeline/export_v2.py --region lebanon

Reads data/raw/<region>/*.csv with the filters of 02_aggregate.py, on the global grid of regions.py.
Writes web/data/regions.json and web/data/<region>/{monthly.json, drift.json, hotspots/<year>.json}.
The file layout is documented in docs/DATA_CONTRACT.md.

Source policy for the harmonized record (team lead's ruling):
  2000-11..2002-06  bridged    Terra only, divided by Terra's share of Terra+Aqua for that calendar month (2003-2011)
  2002-07..2021-12  observed   MODIS Terra + Aqua, nominal orbits
  2022-01..         estimated  Suomi NPP VIIRS converted to MODIS-equivalent by the weight model (MODIS drifted)
The record ends at Suomi NPP's last complete month; detections after it are not exported.
The naive record is MODIS up to 2011 and raw Suomi NPP counts from 2012: the false jump, kept for the toggle.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import weights_interim as model_impl
from regions import CELL, REGIONS, assert_not_sealed, regions_with

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "data"

FIRST = "2000-11"          # Terra's first full month
BRIDGE_END = "2002-06"     # Aqua's first month is 2002-07
OBSERVED_END = "2021-12"   # MODIS drifted from its nominal orbits after this
NAIVE_SWITCH = "2012-01"   # the naive record switches to raw Suomi NPP here
SHARE_YEARS = (2003, 2011)
SHARE_PRIOR = 20           # MODIS pseudo-detections pulling a calendar month's Terra share toward the pooled share
MIN_DAYS = 20              # a sensor file's final month counts only with detections on this many distinct days
DRIFT_FROM = model_impl.TRAIN[0]
SENSORS = ["T", "A", "N", "J1"]
FAMILY = {"T": "modis", "A": "modis", "N": "snpp", "J1": "noaa20"}
SENSOR_OF_FILE = {"viirs-snpp": "N", "viirs-jpss1": "J1"}


def load(path, box):
    """One raw FIRMS file, filtered exactly as 02_aggregate.py, keeping every original field."""
    df = pd.read_csv(path, low_memory=False, dtype={"acq_time": str})
    if df.empty:
        return df
    stem = path.name.split("_")[0]
    lon0, lat0, lon1, lat1 = box
    df = df[(df.longitude >= lon0) & (df.longitude < lon1) & (df.latitude >= lat0) & (df.latitude < lat1)]
    if "type" in df.columns:
        df = df[df["type"] == 0]  # presumed vegetation fire
    if stem == "modis":
        df = df[pd.to_numeric(df.confidence, errors="coerce") >= 30]
        sensor = df.satellite.astype(str).str.lower().str[0].map({"t": "T", "a": "A"})
        df = df.rename(columns={"brightness": "bright", "bright_t31": "bright2"})
        conf = pd.to_numeric(df.confidence).astype(int).astype(object)
    else:
        df = df[df.confidence.astype(str).str.lower().str[0].isin(["n", "h"])]
        sensor = pd.Series(SENSOR_OF_FILE[stem], index=df.index)
        df = df.rename(columns={"bright_ti4": "bright", "bright_ti5": "bright2"})
        conf = df.confidence.astype(str).str.lower().str[0]
    return df.assign(sensor=sensor, conf=conf, file=path.name)


def month_index(first, last):
    return [str(p) for p in pd.period_range(first, last, freq="M")]


def flag_of(month):
    return "B" if month <= BRIDGE_END else "O" if month <= OBSERVED_END else "E"


def round_list(a, nd):
    return [round(float(x), nd) if nd else int(round(float(x))) for x in a]


def complete_through(rows):
    """Last complete month of one sensor family: its file's final month counts only with MIN_DAYS distinct days."""
    last_date = rows.acq_date.max()
    last = last_date[:7]
    days = rows[rows.month == last].acq_date.nunique()
    return (last if days >= MIN_DAYS else month_before(last)), last_date, days


def export(region):
    assert_not_sealed(region)
    cfg = REGIONS[region]
    raw = ROOT / "data" / "raw" / region
    box = cfg["box"]
    if box is None:
        raise SystemExit(f"{region}: product regions need a box")
    manifest = json.loads((raw / "manifest.json").read_text())

    parts = [load(p, box) for p in sorted(raw.glob("*.csv"))]
    det = pd.concat([p for p in parts if not p.empty], ignore_index=True)
    det["acq_time"] = det.acq_time.str.zfill(4)
    det["month"] = det.acq_date.str[:7]
    det["moy"] = det.month.str[5:7].astype(int)
    det["year"] = det.month.str[:4].astype(int)
    det["dn"] = det.daynight.astype(str).str.upper().str[0]
    det["fam"] = det.sensor.map(FAMILY)
    det["ix"] = np.floor(det.longitude / CELL).astype(int)
    det["iy"] = np.floor(det.latitude / CELL).astype(int)
    det = det[det.month >= FIRST]
    last, snpp_last_date, snpp_last_days = complete_through(det[det.sensor == "N"])
    modis_end, modis_last_date, modis_last_days = complete_through(det[det.fam == "modis"])
    dropped = int((det.month > last).sum())
    det = det[det.month <= last].sort_values(["acq_date", "acq_time", "sensor"]).reset_index(drop=True)
    months = month_index(FIRST, last)
    flags = "".join(flag_of(m) for m in months)

    # ---- weights: each row's contribution to the harmonized record for its month
    model = model_impl.fit(det, region)
    share_rows = det[(det.year >= SHARE_YEARS[0]) & (det.year <= SHARE_YEARS[1]) & (det.fam == "modis")]
    st = share_rows.groupby(["moy", "sensor"]).size().unstack(fill_value=0)
    pooled_share = float(st["T"].sum() / (st["T"].sum() + st["A"].sum()))
    # Lead's ruling: every calendar month's share is shrunk toward the pooled share, so a month with
    # few (or no) Terra detections in 2003-2011 cannot produce a share of 0 or 1.
    terra_share, share_basis = {}, {}
    for m in range(1, 13):
        t_, a_ = (int(st.loc[m, s]) if m in st.index else 0 for s in ("T", "A"))
        terra_share[m] = (t_ + SHARE_PRIOR * pooled_share) / (t_ + a_ + SHARE_PRIOR)
        share_basis[m] = f"({t_} Terra + {SHARE_PRIOR} x {pooled_share:.4f}) / ({t_ + a_} MODIS + {SHARE_PRIOR})"

    flag = det.month.map(flag_of)
    w = np.zeros(len(det))
    obs = (flag == "O") & (det.fam == "modis")
    w[obs.to_numpy()] = 1.0
    br = ((flag == "B") & (det.sensor == "T")).to_numpy()
    w[br] = 1.0 / det.moy[br].map(terra_share).to_numpy()
    est = ((flag == "E") & (det.sensor == "N")).to_numpy()
    w[est] = model_impl.hotspot_weights(model, det[est])
    det["w"] = np.round(w, 4)

    # ---- cell x month tables
    det["mi"] = det.month.map({m: i for i, m in enumerate(months)})
    cells = det.groupby(["ix", "iy"]).size().reset_index()[["ix", "iy"]].sort_values(["iy", "ix"]).reset_index(drop=True)
    cell_index = {(r.ix, r.iy): i for i, r in enumerate(cells.itertuples())}
    det["ci"] = [cell_index[k] for k in zip(det.ix, det.iy)]
    shape = (len(cells), len(months))

    w_arr = np.zeros(shape)
    np.add.at(w_arr, (det.ci.to_numpy(), det.mi.to_numpy()), det.w.to_numpy())
    grid = pd.DataFrame({"ci": np.repeat(np.arange(shape[0]), shape[1]), "mi": np.tile(np.arange(shape[1]), shape[0]),
                         "month": np.tile(months, shape[0]), "w": w_arr.ravel()})
    bg = np.round(np.asarray(model_impl.cell_month_background(model, grid), float).reshape(shape), 2)
    m_arr = w_arr + bg  # harmonized estimate (expected value) = sum of hotspot weights + background term
    naive_rows = det[((det.month < NAIVE_SWITCH) & (det.fam == "modis")) | ((det.month >= NAIVE_SWITCH) & (det.sensor == "N"))]
    naive = np.zeros(shape)
    np.add.at(naive, (naive_rows.ci.to_numpy(), naive_rows.mi.to_numpy()), 1)

    # interval: observed months carry none; estimated and bridged months get the model's (interim placeholder)
    m_round = np.round(m_arr, 2)
    p10, p90 = m_round.copy(), m_round.copy()
    e_cols = np.array([f in "EB" for f in flags])
    e_vals = m_arr[:, e_cols]
    lo, hi = model_impl.cell_month_interval(model, pd.DataFrame({"m": e_vals.ravel()}))
    p10[:, e_cols] = lo.reshape(e_vals.shape)
    p90[:, e_cols] = hi.reshape(e_vals.shape)

    out = OUT / region
    (out / "hotspots").mkdir(parents=True, exist_ok=True)
    for old in (out / "hotspots").glob("*.json"):  # a year that drops out must not linger
        old.unlink()
    monthly = {
        "region": region, "cell_deg": CELL, "months": {"first": months[0], "last": months[-1], "n": len(months)},
        "flags": flags, "flag_codes": {"B": "bridged", "O": "observed", "E": "estimated"},
        "cells": {"ix": cells.ix.tolist(), "iy": cells.iy.tolist()},
        "m": [round_list(r, 2) for r in m_round],
        "bg": [round_list(r, 2) for r in bg],
        "p10": [round_list(r, 2) for r in p10],
        "p90": [round_list(r, 2) for r in p90],
        "naive": [round_list(r, 0) for r in naive],
    }
    write_json(out / "monthly.json", monthly)

    # ---- hotspots, one file per year, columnar
    versions = sorted(det.version.astype(str).unique())
    hot_years = []
    for year, g in det.groupby("year"):
        cols = {
            "lat": g.latitude.round(5).tolist(), "lon": g.longitude.round(5).tolist(),
            "doy": pd.to_datetime(g.acq_date).dt.dayofyear.tolist(), "time": g.acq_time.astype(int).tolist(),
            "sensor": g.sensor.map(SENSORS.index).tolist(), "dn": (g.dn == "N").astype(int).tolist(),
            "frp": g.frp.round(2).tolist(), "conf": g.conf.tolist(), "w": g.w.tolist(),
            "bright": g.bright.round(2).tolist(), "bright2": g.bright2.round(2).tolist(),
            "scan": g.scan.round(2).tolist(), "track": g.track.round(2).tolist(),
            "version": g.version.astype(str).map(versions.index).tolist(),
        }
        write_json(out / "hotspots" / f"{year}.json", {"region": region, "year": int(year), "n": len(g), "cols": cols})
        hot_years.append(int(year))

    # ---- drift: observed MODIS vs Suomi NPP converted to MODIS-equivalent, region total by month
    d_months = month_index(DRIFT_FROM, modis_end)
    snpp = det[det.sensor == "N"]
    pred = pd.Series(model_impl.hotspot_weights(model, snpp), index=snpp.index).groupby(snpp.month).sum()
    obs_m = det[det.fam == "modis"].groupby("month").size()
    observed = [int(obs_m.get(m, 0)) for m in d_months]
    predicted = [round(float(pred.get(m, 0.0)), 2) for m in d_months]
    trailing = []
    for i in range(len(d_months)):
        if i < 11:
            trailing.append(None)
            continue
        o, p = sum(observed[i - 11:i + 1]), sum(predicted[i - 11:i + 1])
        trailing.append(round(o / p, 4) if p > 0 else None)
    band_vals = [t for m, t in zip(d_months, trailing) if t is not None and m <= model_impl.TRAIN[1]]
    drift = {
        "region": region, "months": {"first": d_months[0], "last": d_months[-1], "n": len(d_months)},
        "observed_modis": observed, "predicted_modis": predicted, "trailing12_ratio": trailing,
        "band": {"what": "min-max of the trailing 12-month ratio over windows ending inside the fitting years",
                 "range": [round(min(band_vals), 4), round(max(band_vals), 4)] if band_vals else None,
                 "fitted": list(model_impl.TRAIN)},
        "modis_archive_ends": modis_last_date,
        "complete_rule": f"a sensor file's final month counts only with detections on >= {MIN_DAYS} distinct days",
    }
    write_json(out / "drift.json", drift)

    lon0, lat0, lon1, lat1 = box
    meta = {
        "id": region, "name": cfg["country"], "bbox": [lon0, lat0, lon1, lat1],
        "months": {"first": months[0], "last": months[-1]},
        "record_end": {"suomi_npp_last_detection": snpp_last_date, "final_month_days": snpp_last_days,
                       "modis_last_detection": modis_last_date, "modis_final_month_days": modis_last_days,
                       "modis_complete_through": modis_end, "detections_after_record_dropped": dropped,
                       "rule": f"a sensor file's final month counts only with detections on >= {MIN_DAYS} distinct days"},
        "default_view": {"bounds": [[lon0, lat0], [lon1, lat1]]},
        "model": "interim",
        "model_detail": model_impl.describe(model),
        "terra_share": {"years": list(SHARE_YEARS), "by_month": {f"{m:02d}": round(v, 4) for m, v in terra_share.items()},
                        "pooled": round(pooled_share, 4), "prior_detections": SHARE_PRIOR,
                        "basis": {f"{m:02d}": b for m, b in share_basis.items()}},
        "policy": {"bridged": [FIRST, BRIDGE_END], "observed": [month_after(BRIDGE_END), OBSERVED_END],
                   "estimated": [month_after(OBSERVED_END), months[-1]], "naive_switch": NAIVE_SWITCH},
        "cells": len(cells),
        "hotspot_years": hot_years,
        "sensors": {"T": "Terra MODIS", "A": "Aqua MODIS", "N": "Suomi NPP VIIRS", "J1": "NOAA-20 VIIRS"},
        "satellite_field": {s: str(v) for s, v in det.groupby("sensor").satellite.first().items()},
        "instrument_field": {s: str(v) for s, v in det.groupby("sensor").instrument.first().items()},
        "versions": versions,
        "detections": {s: int(n) for s, n in det.sensor.value_counts().items()},
        "provenance": {
            "source": "NASA FIRMS country archive (standard products)",
            "filters": f"box lon {lon0}..{lon1}, lat {lat0}..{lat1}; vegetation fires only (type 0); "
                       "MODIS confidence >= 30; VIIRS confidence nominal or high",
            "unit": "fire detections (satellite pixels flagged as burning), not burned area",
            "files": [{"name": n, **{k: m[k] for k in ("url", "sensor", "rows", "sha256", "retrieved")},
                       "sha256_ok": sha256(raw / n) == m["sha256"]} for n, m in sorted(manifest.items())],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    sizes = {p.relative_to(OUT).as_posix(): p.stat().st_size for p in sorted(out.rglob("*.json"))}
    print(f"{region}: {len(det)} detections, {len(cells)} cells, months {months[0]}..{months[-1]}, "
          f"monthly.json {sizes[f'{region}/monthly.json'] / 1e6:.2f} MB, "
          f"hotspots {sum(v for k, v in sizes.items() if '/hotspots/' in k) / 1e6:.2f} MB in {len(hot_years)} files")
    return meta


def month_after(m):
    return str(pd.Period(m, freq="M") + 1)


def month_before(m):
    return str(pd.Period(m, freq="M") - 1)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, separators=(",", ":"), allow_nan=False), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", choices=regions_with("product"))
    args = ap.parse_args()
    wanted = [args.region] if args.region else regions_with("product")
    index_path = OUT / "regions.json"
    existing = json.loads(index_path.read_text()) if index_path.exists() else {"regions": []}
    by_id = {r["id"]: r for r in existing["regions"]}
    for region in wanted:
        if not (ROOT / "data" / "raw" / region / "manifest.json").exists():
            print(f"{region}: no raw files yet, skipped")
            continue
        by_id[region] = export(region)
    order = regions_with("product")
    index = {"contract": "docs/DATA_CONTRACT.md", "version": 2,
             "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "regions": [by_id[r] for r in order if r in by_id]}
    index_path.write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"-> {index_path}")


if __name__ == "__main__":
    main()
