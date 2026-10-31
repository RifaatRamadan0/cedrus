"""Static data for the v2 website: harmonized monthly record per 0.25 deg cell, hotspots with weights, drift.

    python pipeline/export_v2.py                 # every product region with raw files present
    python pipeline/export_v2.py --region lebanon

Reads data/raw/<region>/*.csv with the filters of 02_aggregate.py, on the global grid of regions.py.
Writes web/data/regions.json and web/data/<region>/{monthly.json, drift.json, hotspots/<year>.json}.
The file layout is documented in docs/DATA_CONTRACT.md.

Source policy for the harmonized record (team lead's ruling):
  2000-11..2002-06  bridged    Terra only, divided by Terra's share of Terra+Aqua for that calendar month (2003-2011)
  2002-07..2021-12  observed   MODIS Terra + Aqua, nominal orbits
  2022-01..         estimated  VIIRS converted to MODIS-equivalent by model A, the bake-off winner (MODIS drifted):
                               the average of the Suomi NPP and NOAA-20 estimates in months both cover,
                               whichever covers otherwise (so the record survives Suomi NPP's end)
A sensor's final month counts only if its file has a detection in the month's last EDGE_DAYS days.
The record ends at the last month a VIIRS satellite covers; detections after it are not exported.
The naive record is MODIS up to 2011 and raw Suomi NPP counts from 2012: the false jump, kept for the toggle.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import weights_a as model_impl                 # the bake-off winner; weights_interim.py is kept for reference only
from weights_interim import nb_quantiles         # bridged months keep the placeholder range (A says nothing about Terra)
from regions import CELL, REGIONS, assert_not_sealed, regions_with

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "data"

FIRST = "2000-11"          # Terra's first full month
BRIDGE_END = "2002-06"     # Aqua's first month is 2002-07
OBSERVED_END = "2021-12"   # MODIS drifted from its nominal orbits after this
NAIVE_SWITCH = "2012-01"   # the naive record switches to raw Suomi NPP here
SHARE_YEARS = (2003, 2011)
SHARE_PRIOR = 20           # MODIS pseudo-detections pulling a calendar month's Terra share toward the pooled share
EDGE_DAYS = 3              # a file's final (first) month counts if it has a detection in its last (first) 3 days
OUTAGE_OTHER = 20          # a VIIRS satellite with 0 detections in a month while the other has >= this is "no data"
DRIFT_FROM = model_impl.TRAIN["snpp"][0]
FLAG_CODES = {"B": "bridged", "O": "observed", "E": "estimated (S-NPP+NOAA-20)", "N": "estimated (S-NPP only)",
              "J": "estimated (NOAA-20 only)", "X": "no data"}
VIIRS = {"N": "snpp", "J1": "noaa20"}
SENSORS = ["T", "A", "N", "J1"]
FAMILY = {"T": "modis", "A": "modis", "N": "snpp", "J1": "noaa20"}
SENSOR_OF_FILE = {"viirs-snpp": "N", "viirs-jpss1": "J1"}


def load(path, box):
    """One raw FIRMS file, filtered exactly as 02_aggregate.py, keeping every original field."""
    df = pd.read_csv(path, low_memory=False, dtype={"acq_time": str, "version": str})  # version kept exactly as written
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


def era_of(month):
    return "B" if month <= BRIDGE_END else "O" if month <= OBSERVED_END else "E"


def round_list(a, nd):
    return [round(float(x), nd) if nd else int(round(float(x))) for x in a]


def coverage(rows):
    """First and last complete month of one sensor's files. The final month counts if the file has a detection
    in its last EDGE_DAYS days; the first month if it has one in its first EDGE_DAYS days."""
    first_date, last_date = rows.acq_date.min(), rows.acq_date.max()
    first = first_date[:7] if int(first_date[8:10]) <= EDGE_DAYS else month_after(first_date[:7])
    dim = pd.Period(last_date[:7], freq="M").days_in_month
    last = last_date[:7] if int(last_date[8:10]) > dim - EDGE_DAYS else month_before(last_date[:7])
    return {"first": first, "last": last, "first_detection": first_date, "last_detection": last_date}


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
    cov = {s: coverage(det[det.sensor == s]) for s in VIIRS}
    cov_modis = coverage(det[det.fam == "modis"])
    modis_end = cov_modis["last"]
    last = max(c["last"] for c in cov.values())
    dropped = int((det.month > last).sum())
    det = det[det.month <= last].sort_values(["acq_date", "acq_time", "sensor"]).reset_index(drop=True)
    months = month_index(FIRST, last)

    # Which VIIRS satellite covers each month: inside its complete span, and not an outage month
    # (zero detections in the region while the other satellite has OUTAGE_OTHER or more).
    per_month = det[det.sensor.isin(list(VIIRS))].groupby(["month", "sensor"]).size().unstack(fill_value=0)

    def covers(s, m):
        if not (cov[s]["first"] <= m <= cov[s]["last"]):
            return False
        other = "J1" if s == "N" else "N"
        n_s = int(per_month.loc[m, s]) if m in per_month.index and s in per_month else 0
        n_o = int(per_month.loc[m, other]) if m in per_month.index and other in per_month else 0
        return not (n_s == 0 and n_o >= OUTAGE_OTHER)
    covering = {m: [s for s in VIIRS if covers(s, m)] for m in month_index(DRIFT_FROM, last)}
    outages = [(m, s) for m in covering for s in VIIRS if cov[s]["first"] <= m <= cov[s]["last"] and s not in covering[m]]

    def flag_of(m):
        era = era_of(m)
        if era != "E":
            return era
        c = covering[m]
        return "E" if len(c) == 2 else "N" if c == ["N"] else "J" if c == ["J1"] else "X"
    flags = "".join(flag_of(m) for m in months)

    # ---- cells (model A is fitted per cell), then weights: each row's contribution to its month
    det["mi"] = det.month.map({m: i for i, m in enumerate(months)})
    cells = det.groupby(["ix", "iy"]).size().reset_index()[["ix", "iy"]].sort_values(["iy", "ix"]).reset_index(drop=True)
    cell_index = {(r.ix, r.iy): i for i, r in enumerate(cells.itertuples())}
    det["ci"] = [cell_index[k] for k in zip(det.ix, det.iy)]
    shape = (len(cells), len(months))
    model = model_impl.fit(det, region)
    # Combination rule (lead's ruling, 31 Oct 2026, after observing NOAA-20's short 21-month fit window): in each
    # region x calendar month x day/night slot, a satellite enters the average only if A's prior ratio r0 > 0 there.
    # One qualifying satellite carries the whole slot; none qualifying keeps A's literal behaviour (weight 0,
    # background as fitted) for the satellites that cover the month. A itself is not changed.
    positive = model_impl.prior_ratio_positive(model)

    def slot_share(m, sat, moy, dn):
        cov = covering[m]
        md = (moy - 1) * 2 + (dn == "N")
        q = [s for s in cov if positive[VIIRS[s]][md]]
        use = q if q else cov
        return 1.0 / len(use) if sat in use else 0.0
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

    month_flag = dict(zip(months, flags))
    flag = det.month.map(month_flag)
    w = np.zeros(len(det))
    obs = (flag == "O") & (det.fam == "modis")
    w[obs.to_numpy()] = 1.0
    br = ((flag == "B") & (det.sensor == "T")).to_numpy()
    w[br] = 1.0 / det.moy[br].map(terra_share).to_numpy()
    # Estimated months: each VIIRS row carries its satellite's ratio times that satellite's share of the month
    # (1/2 when both cover it, 1 when only it does, 0 when it does not).
    share = np.array([slot_share(m, s, moy, dn) if f in "ENJ" and s in VIIRS else 0.0
                      for m, s, f, moy, dn in zip(det.month, det.sensor, flag, det.moy, det.dn)])
    est = share > 0
    w[est] = share[est] * model_impl.hotspot_weights(model, det[est])
    det["w"] = np.round(w, 4)

    # ---- cell x month tables
    w_arr = np.zeros(shape)
    np.add.at(w_arr, (det.ci.to_numpy(), det.mi.to_numpy()), det.w.to_numpy())
    grid = cell_month_grid(det, months, shape, slot_share, flags)
    grid["w"] = w_arr.ravel()
    bg = np.round(np.asarray(model_impl.cell_month_background(model, grid), float).reshape(shape), 2)
    m_arr = w_arr + bg  # harmonized estimate (expected value) = sum of hotspot weights + background term
    grid["m"] = m_arr.ravel()
    naive_rows = det[((det.month < NAIVE_SWITCH) & (det.fam == "modis")) | ((det.month >= NAIVE_SWITCH) & (det.sensor == "N"))]
    naive = np.zeros(shape)
    np.add.at(naive, (naive_rows.ci.to_numpy(), naive_rows.mi.to_numpy()), 1)

    # interval: observed months carry none; estimated months get model A's predictive (approximate);
    # bridged months keep the placeholder (negative binomial, mean m, size 5): A models VIIRS, not Terra alone.
    m_round = np.round(m_arr, 2)
    p10, p90 = m_round.copy(), m_round.copy()
    e_cols = np.array([f in "ENJ" for f in flags])
    e_rows = np.tile(e_cols, shape[0])
    lo, hi = model_impl.cell_month_interval(model, grid[e_rows])
    mean_a, _ = model_impl.cell_month_moments(model, grid[e_rows])
    mean_gap = float(np.abs(mean_a - grid.m.to_numpy()[e_rows]).max()) if e_rows.any() else 0.0
    p10[:, e_cols] = np.asarray(lo).reshape(shape[0], -1)
    p90[:, e_cols] = np.asarray(hi).reshape(shape[0], -1)
    b_cols = np.array([f == "B" for f in flags])
    b_vals = m_arr[:, b_cols]
    blo, bhi = nb_quantiles(b_vals.ravel(), 5, (0.1, 0.9))
    p10[:, b_cols] = blo.reshape(b_vals.shape)
    p90[:, b_cols] = bhi.reshape(b_vals.shape)

    names = {"N": "S-NPP", "J1": "NOAA-20"}
    slot_notes = {}
    for m, f in zip(months, flags):
        if f not in "ENJ":
            continue
        parts = []
        for dn, word in (("D", "day"), ("N", "night")):
            moy = int(m[5:7])
            used = [s for s in covering[m] if slot_share(m, s, moy, dn) > 0]
            md = (moy - 1) * 2 + (dn == "N")
            if not any(positive[VIIRS[s]][md] for s in covering[m]):
                parts.append(f"{word}: no MODIS in either fit, detections weigh 0 (background only)")
            elif len(used) < len(covering[m]):
                parts.append(f"{word}: {' + '.join(names[s] for s in used)} only")
        if parts:
            slot_notes[m] = "; ".join(parts)

    out = OUT / region
    (out / "hotspots").mkdir(parents=True, exist_ok=True)
    for old in (out / "hotspots").glob("*.json"):  # a year that drops out must not linger
        old.unlink()
    monthly = {
        "region": region, "cell_deg": CELL, "months": {"first": months[0], "last": months[-1], "n": len(months)},
        "flags": flags, "flag_codes": FLAG_CODES,
        "slot_notes": slot_notes,  # month -> which satellites the combination rule used, where not all that cover it
        "cells": {"ix": cells.ix.tolist(), "iy": cells.iy.tolist()},
        "m": [round_list(r, 2) for r in m_round],
        "bg": [round_list(r, 2) for r in bg],
        "p10": [round_list(r, 2) for r in p10],
        "p90": [round_list(r, 2) for r in p90],
        "naive": [round_list(r, 0) for r in naive],
    }
    write_json(out / "monthly.json", monthly)

    # ---- hotspots, one file per year, columnar
    versions = sorted(det.version.unique())
    hot_years = []
    for year, g in det.groupby("year"):
        cols = {
            "lat": g.latitude.round(5).tolist(), "lon": g.longitude.round(5).tolist(),
            "doy": pd.to_datetime(g.acq_date).dt.dayofyear.tolist(), "time": g.acq_time.astype(int).tolist(),
            "sensor": g.sensor.map(SENSORS.index).tolist(), "dn": (g.dn == "N").astype(int).tolist(),
            "frp": g.frp.round(2).tolist(), "conf": g.conf.tolist(), "w": g.w.tolist(),
            "bright": g.bright.round(2).tolist(), "bright2": g.bright2.round(2).tolist(),
            "scan": g.scan.round(2).tolist(), "track": g.track.round(2).tolist(),
            "version": g.version.map(versions.index).tolist(),
        }
        write_json(out / "hotspots" / f"{year}.json", {"region": region, "year": int(year), "n": len(g), "cols": cols})
        hot_years.append(int(year))

    # ---- drift: observed MODIS vs MODIS predicted from VIIRS by model A (weights + background, averaged over the
    # satellites that cover the month, as in the estimated record), region total
    d_months = month_index(DRIFT_FROM, modis_end)
    viirs = det[det.sensor.isin(list(VIIRS))]
    full = pd.Series(model_impl.hotspot_weights(model, viirs), index=viirs.index).groupby([viirs.month, viirs.sensor, viirs.dn]).sum()
    d_idx = [months.index(m) for m in d_months]
    bg_sat = {}
    for sat in VIIRS:
        for dn in ("D", "N"):
            g = grid.copy()
            for other in VIIRS:
                for d2 in ("D", "N"):
                    g[f"share_{other}_{d2}"] = 1.0 if (other == sat and d2 == dn) else 0.0
            bg_sat[(sat, dn)] = np.asarray(model_impl.cell_month_background(model, g)).reshape(shape)[:, d_idx].sum(axis=0)
    obs_m = det[det.fam == "modis"].groupby("month").size()
    observed = [int(obs_m.get(m, 0)) for m in d_months]
    predicted = [round(float(sum(slot_share(m, s, int(m[5:7]), dn) * (full.get((m, s, dn), 0.0) + bg_sat[(s, dn)][k])
                                 for s in covering[m] for dn in ("D", "N"))), 2) if covering[m] else 0.0
                 for k, m in enumerate(d_months)]
    trailing = []
    for i in range(len(d_months)):
        if i < 11:
            trailing.append(None)
            continue
        o, p = sum(observed[i - 11:i + 1]), sum(predicted[i - 11:i + 1])
        trailing.append(round(o / p, 4) if p > 0 else None)
    band_vals = [t for m, t in zip(d_months, trailing) if t is not None and m <= model_impl.TRAIN["snpp"][1]]
    drift = {
        "region": region, "months": {"first": d_months[0], "last": d_months[-1], "n": len(d_months)},
        "observed_modis": observed, "predicted_modis": predicted, "trailing12_ratio": trailing,
        "band": {"what": "min-max of the trailing 12-month ratio over windows ending inside the fitting years",
                 "range": [round(min(band_vals), 4), round(max(band_vals), 4)] if band_vals else None,
                 "fitted": list(model_impl.TRAIN["snpp"])},
        "predicted_from": "model A from Suomi NPP and NOAA-20 (weights + background), combined as the estimated record",
        "model": model_impl.NAME,
        "modis_archive_ends": cov_modis["last_detection"],
        "complete_rule": f"a file's final month counts if it has a detection in that month's last {EDGE_DAYS} days",
    }
    write_json(out / "drift.json", drift)

    lon0, lat0, lon1, lat1 = box
    meta = {
        "id": region, "name": cfg["country"], "bbox": [lon0, lat0, lon1, lat1],
        "months": {"first": months[0], "last": months[-1]},
        "record_end": {"suomi_npp": cov["N"], "noaa20": cov["J1"], "modis": cov_modis,
                       "detections_after_record_dropped": dropped,
                       "viirs_outage_months": [f"{m} {'Suomi NPP' if s == 'N' else 'NOAA-20'}" for m, s in outages],
                       "rule": f"a file's final month counts if it has a detection in that month's last {EDGE_DAYS} days; "
                               f"a VIIRS satellite with 0 detections in a month while the other has >= {OUTAGE_OTHER} "
                               "does not cover that month",
                       "after": "2026 to the present needs NASA's FIRMS near-real-time API key (pending)"},
        "default_view": {"bounds": [[lon0, lat0], [lon1, lat1]]},
        "model": model_impl.NAME,
        "model_detail": model_impl.describe(model),
        "combination": {
            "rule": "in each region x calendar month x day/night slot, a satellite enters the average only if model A's "
                    "prior ratio r0 > 0 there; one qualifying satellite carries the slot alone; none qualifying keeps A's "
                    "literal behaviour (weight 0, background as fitted). Decided 31 Oct 2026 after observing NOAA-20's "
                    "short 21-month fit window. Model A itself is unchanged.",
            "slots_when_both_cover": {f"{md // 2 + 1:02d}{'DN'[md % 2]}": [f for f in ("snpp", "noaa20") if positive[f][md]]
                                      for md in range(24)},
        },
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
    meta["model_detail"]["check"] = {"max_gap_between_A_predictive_mean_and_m": round(mean_gap, 4),
                                     "background_total": round(float(bg.sum()), 2)}
    sizes = {p.relative_to(OUT).as_posix(): p.stat().st_size for p in sorted(out.rglob("*.json"))}
    print(f"{region}: {len(det)} detections, {len(cells)} cells, months {months[0]}..{months[-1]}, "
          f"monthly.json {sizes[f'{region}/monthly.json'] / 1e6:.2f} MB, "
          f"hotspots {sum(v for k, v in sizes.items() if '/hotspots/' in k) / 1e6:.2f} MB in {len(hot_years)} files; "
          f"model {model_impl.NAME}: background total {bg.sum():.2f}, max |A mean - m| {mean_gap:.4f}")
    return meta


def cell_month_grid(det, months, shape, slot_share, flags):
    """One row per cell-month: each VIIRS satellite's detections and its share of the month, by day and night."""
    n_cells, n_months = shape
    g = pd.DataFrame({"ci": np.repeat(np.arange(n_cells), n_months), "mi": np.tile(np.arange(n_months), n_cells),
                      "month": np.tile(months, n_cells)})
    g["moy"] = g.month.str[5:7].astype(int)
    v = det[det.sensor.isin(list(VIIRS))]
    for sat in VIIRS:
        for dn in ("D", "N"):
            arr = np.zeros(shape)
            sel = v[(v.sensor == sat) & (v.dn == dn)]
            np.add.at(arr, (sel.ci.to_numpy(), sel.mi.to_numpy()), 1)
            g[f"V_{sat}_{dn}"] = arr.ravel()
        for dn in ("D", "N"):
            share = np.array([slot_share(m, sat, int(m[5:7]), dn) if f in "ENJ" else 0.0 for m, f in zip(months, flags)])
            g[f"share_{sat}_{dn}"] = np.tile(share, n_cells)
    return g


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
