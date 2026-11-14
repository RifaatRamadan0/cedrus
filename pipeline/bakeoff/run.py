"""The bake-off, end to end, exactly as docs/BAKEOFF_PLAN.md.

    python -m pipeline.bakeoff.run                      # every development region whose 2012-2019 files are in
    python -m pipeline.bakeoff.run --regions portugal   # a subset, for development only

Writes data/processed/bakeoff/* (intermediate) and docs/BAKEOFF_RESULTS.md.
"""
import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import data
from .models import A_GRID, B_GRID, add_groups, exposure, fit_A, fit_B, fit_g, g_of, unit_design
from .report import write_report
from .units import units_with_matches
from .validate import bootstrap, decide, inner_loyo, masks, run_fold, summary

YEARS = data.YEARS
FORWARD = (list(range(2012, 2017)), [2017, 2018, 2019])
FRP_BINS = [0, 1, 2, 5, 10, 20, 50, 100, 500, np.inf]


def region_tables(region):
    """(pixels, rows, units, unit info) for one region; rows and units cached next to the pixels."""
    px = data.pixels(region)
    folder = data.OUT / region
    sig = json.loads((folder / "pixels.json").read_text())
    meta = folder / "tables.json"
    if meta.exists() and json.loads(meta.read_text()).get("sig") == sig:
        return px, pd.read_pickle(folder / "rows.pkl"), pd.read_pickle(folder / "units.pkl"), \
            json.loads(meta.read_text())["units_info"]
    rows = data.rows(region, px)
    units, info = units_with_matches(px)
    rows.to_pickle(folder / "rows.pkl")
    units.to_pickle(folder / "units.pkl")
    meta.write_text(json.dumps({"sig": sig, "units_info": info}, indent=1))
    return px, rows, units, info


def build(regions):
    pxs, Rs, Us, infos = [], [], [], {}
    for reg in regions:
        t = time.time()
        px, r, u, info = region_tables(reg)
        pxs.append(px[["region", "sensor", "date", "ym"]])
        Rs.append(r)
        Us.append(u)
        infos[reg] = info
        print(f"  {reg}: {len(px):,} detections, {r.cell.nunique()} cells, {len(r):,} rows, {len(u):,} units "
              f"({time.time() - t:.1f}s)")
    R = pd.concat(Rs, ignore_index=True)
    R["rid"] = R.region.map({r: i for i, r in enumerate(regions)})
    R["cid"] = pd.factorize(R.region + ":" + R.cell)[0]
    R["dnN"] = (R.dn == "N").astype(int)
    R = add_groups(R, len(regions))
    U = pd.concat(Us, ignore_index=True)
    key = R.reset_index()[["region", "cell", "ym", "dn", "index"]].rename(columns={"index": "urow"})
    U = U.merge(key, on=["region", "cell", "ym", "dn"], how="left", validate="many_to_one")
    assert U.urow.notna().all(), "a unit has no row"
    U["urow"] = U.urow.astype(int)
    return pd.concat(pxs, ignore_index=True), R, U, infos


# worker processes read the tables once, from the cache written by the parent
_W = {}


def _init(path):
    _W.update(pd.read_pickle(path))


def _fold(args):
    train, score, label = args
    return run_fold(_W["R"], _W["U"], _W["scored"], train, score, label)


def g_table(U, gfit):
    """Mean matched and chance counts per unit by FRP bin, next to the fitted response."""
    out = []
    frp, dn = U.frp.to_numpy(), U.dn.to_numpy()
    g = g_of(gfit, frp, dn)
    X = unit_design(frp)
    for d in ("D", "N"):
        gm = np.exp(X @ gfit[d]["match"])
        gc = np.exp(X @ gfit[d]["chance"])
        for lo, hi in zip([-np.inf] + FRP_BINS[:-1], FRP_BINS):
            sel = (dn == d) & (frp > lo) & (frp <= hi)
            if not sel.any():
                continue
            label = "FRP <= 0" if lo == -np.inf else f"{lo:g}-{hi:g}" if np.isfinite(hi) else f"> {lo:g}"
            out.append({"dn": d, "bin": label, "units": int(sel.sum()), "median_frp": float(np.median(frp[sel])),
                        "m_mean": float(U.m.to_numpy()[sel].mean()), "c_mean": float(U.c.to_numpy()[sel].mean()),
                        "g_match": float(gm[sel].mean()), "g_chance": float(gc[sel].mean()),
                        "g": float(g[sel].mean())})
    return out


def frozen(R, U, scored, winner):
    """Winner refit on all of 2012-2019, its tuning parameter chosen by leave-one-year-out over all eight years."""
    a, tabA, b, tabB = inner_loyo(R, U, scored, YEARS)
    tr, tru = masks(R, U, YEARS)
    regions = list(R.groupby("rid").region.first())
    out = {"model": winner, "plan": "docs/BAKEOFF_PLAN.md", "fitted_on": f"{data.FIRST_MONTH}..{data.LAST_MONTH}",
           "regions": regions, "generated": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if winner == "A":
        f = fit_A(R, tr)
        nr = len(regions)
        grp = [{"region": regions[i // 24], "moy": (i % 24) // 2 + 1, "dn": "DN"[i % 2],
                "r0": float(f["r0"][i]), "r0_source": ["region-month", "region", "all regions"][int(f["r0_level"][i])],
                "b_A": float(f["bA"][i]), "b_A_from_region_fallback": bool(f["bA_fallback"][i])}
               for i in range(nr * 24)]
        cells = R.groupby("cid")[["region", "cell"]].first()
        cmd = np.flatnonzero((f["SY"] > 0) | (f["SV"] > 0))
        cellsums = [{"region": cells.region.iat[i // 24], "cell": cells.cell.iat[i // 24], "moy": (i % 24) // 2 + 1,
                     "dn": "DN"[i % 2], "sum_Y": int(f["SY"][i]), "sum_V": int(f["SV"][i])} for i in cmd]
        out.update({"a": a, "inner_loyo_weighted_crps": tabA, "groups": grp,
                    "cell_sums": cellsums,
                    "cell_sums_note": "cell x calendar month x day/night with any training detection; all others are 0"})
    else:
        gfit = fit_g(U, tru)
        E = exposure(R, U, gfit)
        f = fit_B(R, tr, E, b)
        out.update({
            "b": b, "inner_loyo_weighted_crps": tabB, "alpha": f["alpha"],
            "g": {d: {"match": gfit[d]["match"].tolist(), "chance": gfit[d]["chance"].tolist(),
                      "design": ["intercept", "log(FRP) if FRP > 0 else 0", "1[FRP <= 0]"],
                      "floor": 0.001, "units": gfit[d]["units"]} for d in ("D", "N")},
            "beta_month_dn": [{"moy": i // 2 + 1, "dn": "DN"[i % 2], "beta": float(f["beta_md"][i])} for i in range(24)],
            "region_dn": [{"region": regions[r], "dn": "DN"[d], "beta_raw_centred": float(f["region_raw"][r, d]),
                           "se": float(f["eb"][d]["se"][r]), "shrink_factor": float(f["eb"][d]["factor"][r]),
                           "beta_shrunk": float(f["region_shrunk"][r, d])} for r in range(len(regions)) for d in (0, 1)],
            "tau2": {"D": f["eb"][0]["tau2"], "N": f["eb"][1]["tau2"]},
            "nb_converged": f["fit"]["converged"], "nb_max_abs_grad": f["fit"]["max_abs_grad"]})
    for old in data.OUT.glob("frozen_*.json"):  # a stale file from an earlier run must not survive
        old.unlink()
    path = data.OUT / f"frozen_{winner}.json"
    path.write_text(json.dumps(out, indent=1, default=float))
    return path, {"a": a, "inner_A": tabA, "b": b, "inner_B": tabB}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", nargs="*", help="development subset (default: every ready development region)")
    ap.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--report", default=str(data.ROOT / "docs" / "BAKEOFF_RESULTS.md"))
    args = ap.parse_args()
    T = {}
    t_all = time.time()

    dev = data.dev_regions()
    ready = {r: data.readiness(r) for r in dev}
    wanted = args.regions or dev
    for r in wanted:
        data.assert_not_sealed(r)
        assert r in dev, f"{r} is not a development region"
    regions = [r for r in wanted if ready[r][0]]
    left_out = {r: ready[r][1] for r in wanted if not ready[r][0]}
    not_requested = [r for r in dev if r not in wanted]
    print(f"regions: {regions}; files incomplete: {sorted(left_out)}; not requested: {not_requested}")

    t = time.time()
    px, R, U, unit_info = build(regions)
    out = data.outages(px)
    del px
    scored = ~R.ym.isin(out["excluded_months"]).to_numpy()
    T["data, units and matching"] = time.time() - t
    print(f"rows {len(R):,} ({scored.mean():.1%} in scored months), units {len(U):,}; "
          f"excluded months {out['excluded_months']}")

    cache = data.OUT / "_tables.pkl"
    pd.to_pickle({"R": R, "U": U, "scored": scored}, cache)
    jobs = [([y for y in YEARS if y != h], [h], str(h)) for h in YEARS] + [(FORWARD[0], FORWARD[1], "forward")]
    t = time.time()
    if args.jobs > 1:
        with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(str(cache),)) as ex:
            res = list(ex.map(_fold, jobs))
    else:
        res = [run_fold(R, U, scored, *j) for j in jobs]
    T["outer folds and forward check (inner tuning included)"] = time.time() - t
    for _, info in res:
        print(f"  fold {info['fold']}: a={info['a']} b={info['b']} ({info['seconds']}s)")
    loyo = pd.concat([r for r, i in res if i["fold"] != "forward"], ignore_index=True)
    fwd = next(r for r, i in res if i["fold"] == "forward")
    folds = [i for _, i in res]
    loyo.to_pickle(data.OUT / "loyo_rows.pkl")
    fwd.to_pickle(data.OUT / "forward_rows.pkl")

    t = time.time()
    overall = summary(loyo, R)
    boot = bootstrap(loyo, R)
    decision = decide(overall, boot)
    region_of = R.region.to_numpy()
    year_of = R.year.to_numpy()
    per_region = {r: summary(loyo[region_of[loyo.row] == r], R) for r in regions}
    per_year = {int(y): summary(loyo[year_of[loyo.row] == y], R) for y in YEARS}
    forward = summary(fwd, R)
    forward_region = {r: summary(fwd[region_of[fwd.row] == r], R) for r in regions}
    T["scores and bootstrap"] = time.time() - t
    print(json.dumps({"overall": overall, "bootstrap": boot, "decision": decision}, indent=1))

    t = time.time()
    tr, tru = masks(R, U, YEARS)
    gfit = fit_g(U, tru)
    gtab = g_table(U, gfit)
    T["response table"] = time.time() - t
    t = time.time()
    frozen_path, frozen_tuning = frozen(R, U, scored, decision["winner"])
    T["frozen refit of the winner"] = time.time() - t
    T["total"] = time.time() - t_all

    results = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "regions": regions, "left_out": left_out, "not_requested": not_requested, "unit_info": unit_info, "outages": out,
        "n_rows": int(len(R)), "n_scored_rows": int(scored.sum()), "n_units": int(len(U)),
        "rows_per_region": R.groupby("region").size().to_dict(),
        "cells_per_region": R.groupby("region").cell.nunique().to_dict(),
        "units_per_region": U.groupby("region").size().to_dict(),
        "Y_per_region": R.groupby("region").Y.sum().to_dict(), "V_per_region": R.groupby("region").V.sum().to_dict(),
        "folds": folds, "overall": overall, "bootstrap": boot, "decision": decision,
        "per_region": per_region, "per_year": per_year, "forward": forward, "forward_region": forward_region,
        "g_fit": {d: {"match": gfit[d]["match"].tolist(), "chance": gfit[d]["chance"].tolist(),
                      "units": gfit[d]["units"]} for d in ("D", "N")},
        "cross_midnight": {k: {"N_same_date": float(g.m.mean()), "N_cross": float(g.m_cross_midnight.mean())}
                           for k, g in U[U.dn == "N"].groupby("region")},
        "g_table": gtab, "frozen": str(frozen_path.relative_to(data.ROOT)).replace("\\", "/"),
        "frozen_tuning": frozen_tuning, "grids": {"a": A_GRID, "b": B_GRID}, "timings_s": T,
        "jobs": args.jobs,
    }
    (data.OUT / "results.json").write_text(json.dumps(results, indent=1, default=float))
    write_report(results, args.report)
    print(f"winner {decision['winner']}; total {T['total']:.0f}s -> {args.report}")


if __name__ == "__main__":
    main()
