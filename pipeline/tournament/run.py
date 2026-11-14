"""The model tournament on development regions only, exactly as docs/TOURNAMENT_PLAN.md (pre-registered at fa2c956).

    python -m pipeline.tournament.run              # the tournament: 17 development regions, both units
    python -m pipeline.tournament.run --jobs 3     # fewer worker processes

C0-C8 in the pixel unit: outer leave-one-year-out 2012-2019 plus the forward check (fit 2012-2016, score
2017-2019), every fitted quantity inside the folds and tuning nested inside them; swap stability on 2020-01..2021-12
from a fit on 2012-02..2019-12 (no MODIS). The best two and R1 are refitted in the burning-day unit (D-a, D-b, D-R1).
Writes docs/TOURNAMENT_RESULTS.md and data/processed/tournament/ (per-row scores, results.json, champion.json).
No sealed region is opened: every file access goes through pipeline.round2.data.guard.
"""
import argparse
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.bakeoff.data import outages as bakeoff_outages
from pipeline.round2 import data as r2
from pipeline.round2.models import A2_GRID, BOOT, SEED, fit_s, rng_for

from . import data
from .candidates import (A2_FROZEN, C5_GRID, CANDIDATES, EM_ITERS, EM_TOL, GBM, GBM_FEATURES, NAMES, SIMPLICITY,
                         gbm_backend, neighbours)
from .report import write_results
from .validate import (BD_COVERAGE, BD_SKILL_GAIN, STOP_HEADROOM, WITHIN, best_two, decide_unit, headroom, run_job,
                       select_pixel, skill, summary, swap_stability)

YEARS = list(range(2012, 2020))
FORWARD = (list(range(2012, 2017)), [2017, 2018, 2019])
SWAP = ("2020-01", "2021-12")
ROUND2_13 = ["portugal", "lebanon", "cyprus", "jordan", "israel", "palestine", "greece", "syria", "turkey", "morocco",
             "tunisia", "central_chile", "western_cape"]
ROUND2_A2_LOYO = 0.2492  # docs/ROUND2_SELECTION.md, Decision 1
CACHE = data.OUT / "cache"
CODE = ["data.py", "candidates.py", "nbreg.py", "validate.py"]
HEAVY = ["C7", "C6", "C5", "C3", "C4", "C2", "C1", "C0", "C8"]  # job order, slowest first

_W = {}


def jsonable(x):
    """C5's inner-tuning table is keyed by (a, a_n) pairs; JSON keys must be strings."""
    if isinstance(x, dict):
        return {(", ".join(map(str, k)) if isinstance(k, tuple) else k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    return x


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=data.ROOT, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:
        return f"unavailable ({e})"


def code_hash():
    h = hashlib.sha256()
    for f in CODE:
        h.update((Path(__file__).parent / f).read_bytes())
    for f in ("pipeline/round2/models.py", "pipeline/bakeoff/models.py", "pipeline/bakeoff/scores.py"):
        h.update((data.ROOT / f).read_bytes())
    h.update(gbm_backend().encode())
    return h.hexdigest()[:16]


# ---------------------------------------------------------------- the table
def _region(reg):
    px = data.pixels(reg)
    R, cover = data.rows(reg, px)
    return reg, R, cover, px[["region", "sensor", "date", "ym"]]


def build(regions, jobs):
    sigs = {r: json.loads((data.OUT / r / "pixels.json").read_text()) if (data.OUT / r / "pixels.json").exists()
            else None for r in regions}
    cache, meta = data.OUT / "table.pkl", data.OUT / "table.json"
    sig = {"version": data.CACHE_VERSION, "regions": regions, "pixels": sigs}
    if None not in sigs.values() and cache.exists() and meta.exists() and json.loads(meta.read_text()) == sig:
        return pd.read_pickle(cache)
    with ProcessPoolExecutor(min(jobs, len(regions))) as ex:
        res = {reg: (R, cover, px) for reg, R, cover, px in ex.map(_region, regions)}
    R = r2.build_table({reg: res[reg][0] for reg in regions})
    cover = {reg: res[reg][1] for reg in regions}
    px_all = pd.concat([res[reg][2] for reg in regions], ignore_index=True)
    out = bakeoff_outages(px_all)  # the bake-off's own rule, 2012-02..2019-12, all included regions combined
    avail = {r: r2.availability(r, data.LAST_YEAR) for r in regions}
    usable = sorted((r, y) for r in regions for y in (2020, 2021)
                    if avail[r].get(("snpp", y)) and avail[r].get(("noaa20", y)))
    swap_out = {"snpp": r2.outage_days(px_all, "2020-01-01", "2021-12-31", "snpp", "noaa20", usable=set(usable)),
                "noaa20": r2.outage_days(px_all, "2020-01-01", "2021-12-31", "noaa20", "snpp", usable=set(usable))}
    swap_out["excluded_months"] = sorted({d[:7] for d in swap_out["snpp"] + swap_out["noaa20"]})
    missing = {r: [r2.file_name(r, s, y) for (s, y), ok in avail[r].items() if not ok] for r in regions}
    tab = {"R": R, "cover": cover, "outages": out, "swap_outages": swap_out, "usable": usable,
           "missing": {r: v for r, v in missing.items() if v}}
    sig["pixels"] = {r: json.loads((data.OUT / r / "pixels.json").read_text()) for r in regions}
    pd.to_pickle(tab, cache)
    meta.write_text(json.dumps(sig, indent=1))
    return tab


# ---------------------------------------------------------------- the jobs
def _init(paths):
    _W["paths"] = paths


def _unit(u):
    if u not in _W:
        _W[u] = pd.read_pickle(_W["paths"][u])
    return _W[u]


def _job(j):
    unit, cand, label, train_years, score_years, path, sig = j
    U = _unit(unit)
    out, info = run_job(U["T"], U["scored"], cand, train_years, score_years, f"{unit}:{label}", sfit=U["sfit"],
                        swap_rows=U["swap_rows"], nb=U["nb"])
    info["unit"] = unit
    with open(path, "wb") as fh:
        pickle.dump({"sig": sig, "out": out, "info": info}, fh)
    return path


def run_jobs(specs, paths, sig, jobs):
    """specs: (unit, cand, label, train_years, score_years); each result cached in data/processed/tournament/cache."""
    CACHE.mkdir(parents=True, exist_ok=True)
    todo, done = [], {}
    for unit, cand, label, tr, sc in specs:
        path = CACHE / f"{unit}_{cand}_{label}.pkl"
        if path.exists():
            with open(path, "rb") as fh:
                got = pickle.load(fh)
            if got["sig"] == sig:
                done[(unit, cand, label)] = got
                continue
        todo.append((unit, cand, label, tr, sc, str(path), sig))
    todo.sort(key=lambda j: (HEAVY.index(j[1]), j[2]))
    print(f"  {len(done)} job results from cache, {len(todo)} to run")
    if todo:
        with ProcessPoolExecutor(jobs, initializer=_init, initargs=(paths,)) as ex:
            for p in ex.map(_job, todo):
                with open(p, "rb") as fh:
                    got = pickle.load(fh)
                i = got["info"]
                done[(i["unit"], i["cand"], i["fold"].split(":", 1)[1])] = got
                print(f"    {i['unit']} {i['cand']} {i['fold'].split(':', 1)[1]}: {i['seconds']}s "
                      f"setting {i['setting']}", flush=True)
    return done, len(todo)


def folds():
    return ([(str(h), [y for y in YEARS if y != h], [h]) for h in YEARS] + [("forward", *FORWARD)]
            + [("final", YEARS, [])])


def pool(done, unit, cands, kind):
    """Per-row scores of the leave-one-year-out pool ("loyo") or the forward check, one column set per candidate."""
    labels = [str(h) for h in YEARS] if kind == "loyo" else ["forward"]
    base = None
    for c in cands:
        df = pd.concat([done[(unit, c, l)]["out"] for l in labels], ignore_index=True)
        if base is None:
            base = df[["row", "fold", "w", "Y"]].copy()
        else:
            assert (base.row.to_numpy() == df.row.to_numpy()).all() and np.allclose(base.w, df.w)
        base[f"crps_{c}"], base[f"cov_{c}"], base[f"mean_{c}"] = (df["crps"].to_numpy(), df["cov"].to_numpy(),
                                                                  df["mean"].to_numpy())
    return base


def unit_results(done, unit, cands, T, regions):
    loyo, fwd = pool(done, unit, cands, "loyo"), pool(done, unit, cands, "forward")
    region_of, year_of = T.region.to_numpy(), T.year.to_numpy()
    res = {"overall": summary(loyo, T, cands), "forward": summary(fwd, T, cands),
           "per_region": {r: summary(loyo[region_of[loyo.row] == r], T, cands) for r in regions},
           "per_year": {int(y): summary(loyo[year_of[loyo.row] == y], T, cands) for y in YEARS},
           "swap": {c: swap_stability(done[(unit, c, "final")]["out"]) for c in cands},
           "swap_region": {c: {r: swap_stability(g) for r, g in done[(unit, c, "final")]["out"].groupby("region")}
                           for c in cands},
           "folds": {c: [done[(unit, c, l)]["info"] for l, _, _ in folds()] for c in cands}}
    for c in cands:
        V = T.V.to_numpy()[loyo.row]
        res["overall"][f"headroom_{c}"] = headroom(loyo, f"mean_{c}", f"crps_{c}")
        res["overall"][f"headroom_{c}"]["floor_vpos"] = headroom(loyo[V > 0], f"mean_{c}", f"crps_{c}")["floor"]
    return res, loyo, fwd


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=min(6, os.cpu_count() or 1))
    args = ap.parse_args()
    jobs = max(1, min(args.jobs, 6))
    T_ = {}
    t_all = time.time()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    regions = r2.dev_regions()  # guarded: refuses any sealed region
    for r in regions:
        r2.guard(r)
        miss = r2.fit_ready(r2.availability(r, data.LAST_YEAR))
        assert not miss, f"{r}: fitting files missing {miss}"
    print(f"development regions ({len(regions)}): {regions}; GBM backend {gbm_backend()}")

    t = time.time()
    tab = build(regions, jobs)
    R = tab["R"]
    excluded = tab["outages"]["excluded_months"]
    scored = ~R.ym.isin(excluded).to_numpy()
    usable = {f"{r}:{y}" for r, y in tab["usable"]}
    ok_ry = (R.region + ":" + R.year.astype(str)).isin(usable).to_numpy()
    swap_rows = np.flatnonzero(((R.ym >= SWAP[0]) & (R.ym <= SWAP[1])).to_numpy() & ok_ry
                               & ~R.ym.isin(tab["swap_outages"]["excluded_months"]).to_numpy())
    train_n = ((R.ym >= data.N20_FIRST) & (R.ym <= data.FIT_LAST)).to_numpy()
    nb = neighbours(R)
    units, paths, sfits = {}, {}, {}
    for u in ("px", "bd"):
        T = data.unit_table(R, u)
        sfits[u] = fit_s(T, train_n, rng_for("tournament", u, "J-S"))
        units[u] = T
        paths[u] = str(data.OUT / f"_unit_{u}.pkl")
        pd.to_pickle({"T": T, "scored": scored, "sfit": sfits[u], "swap_rows": swap_rows, "nb": nb}, paths[u])
    fit_rows = (R.ym <= data.FIT_LAST).to_numpy()
    T_["data"] = time.time() - t
    print(f"rows {len(R):,} ({fit_rows.sum():,} in 2012-02..2019-12, {(fit_rows & scored).sum():,} in scored months); "
          f"excluded months {excluded}; swap rows {len(swap_rows):,}, swap outage months "
          f"{tab['swap_outages']['excluded_months']}; missing files {tab['missing']}")

    sig = {"code": code_hash(), "rows": int(len(R)), "regions": regions, "excluded": excluded,
           "swap_rows": int(len(swap_rows))}

    # ---------------------------------------------------------------- pixel unit: C0-C8
    t = time.time()
    done, n_fit_px = run_jobs([("px", c, l, tr, sc) for c in CANDIDATES for l, tr, sc in folds()], paths, sig, jobs)
    T_["pixel unit folds"] = time.time() - t
    px, loyo_px, fwd_px = unit_results(done, "px", CANDIDATES, units["px"], regions)
    decision = select_pixel(px["overall"], CANDIDATES)
    champ = decision["chosen"]
    for c in CANDIDATES:
        px["overall"][f"skill_{c}"] = skill(px["overall"][f"wcrps_{c}"], px["overall"]["wcrps_C1"])
        px["forward"][f"skill_{c}"] = skill(px["forward"][f"wcrps_{c}"], px["forward"]["wcrps_C1"])
    two = best_two(px["overall"], CANDIDATES)
    print(f"pixel champion {champ}; best two {two}")

    # spot check: C0 on round 2's 13 regions reproduces A2's pooled leave-one-year-out weighted CRPS
    in13 = np.isin(units["px"].region.to_numpy()[loyo_px.row], ROUND2_13)
    sub = loyo_px[in13]
    spot = {"rows": int(len(sub)), "wcrps_C0": float(np.sum(sub.w * sub.crps_C0) / np.sum(sub.w)),
            "round2": ROUND2_A2_LOYO, "round2_rows": 680184}
    spot["matches"] = bool(round(spot["wcrps_C0"], 4) == ROUND2_A2_LOYO)
    print(f"spot check C0 on round 2's 13 regions: {spot}")

    # ---------------------------------------------------------------- burning-day unit: D-a, D-b, D-R1
    t = time.time()
    bd_cands = list(dict.fromkeys(two + ["C1"]))
    done_bd, n_fit_bd = run_jobs([("bd", c, l, tr, sc) for c in bd_cands for l, tr, sc in folds()], paths, sig, jobs)
    T_["burning-day unit folds"] = time.time() - t
    bd, loyo_bd, fwd_bd = unit_results(done_bd, "bd", bd_cands, units["bd"], regions)
    for c in bd_cands:
        bd["overall"][f"skill_{c}"] = skill(bd["overall"][f"wcrps_{c}"], bd["overall"]["wcrps_C1"])
        bd["forward"][f"skill_{c}"] = skill(bd["forward"][f"wcrps_{c}"], bd["forward"]["wcrps_C1"])
    d_names = {two[0]: "D-a", two[1]: "D-b", "C1": "D-R1"}
    unit_dec = decide_unit(px["overall"][f"skill_{champ}"], px["swap"][champ]["median_abs_log"],
                           {d_names[c]: {"skill": bd["overall"][f"skill_{c}"], "swap": bd["swap"][c]["median_abs_log"],
                                         "cov_active": bd["overall"][f"cov_active_{c}"], "cand": c} for c in two})
    hr = px["overall"][f"headroom_{champ}"]
    T_["total"] = time.time() - t_all
    job_s = {u: float(sum(g["info"]["seconds"] for k, g in dd.items() if k[0] == u))
             for u, dd in (("px", done), ("bd", done_bd))}

    # ---------------------------------------------------------------- outputs
    loyo_px.to_pickle(data.OUT / "rows_px_loyo.pkl")
    fwd_px.to_pickle(data.OUT / "rows_px_forward.pkl")
    loyo_bd.to_pickle(data.OUT / "rows_bd_loyo.pkl")
    fwd_bd.to_pickle(data.OUT / "rows_bd_forward.pkl")
    pd.concat([done[("px", c, "final")]["out"].assign(cand=c) for c in CANDIDATES]).to_pickle(data.OUT / "swap_px.pkl")
    pd.concat([done_bd[("bd", c, "final")]["out"].assign(cand=c) for c in bd_cands]).to_pickle(data.OUT / "swap_bd.pkl")
    s_tab = {u: [{"region": regions[k // 2], "dn": "DN"[k % 2], "s": float(sfits[u]["s"][k]),
                  "sd_s": float(np.sqrt(sfits[u]["var_s"][k]))} for k in range(len(regions) * 2)] for u in sfits}
    Rf = R[fit_rows]
    data_tab = {r: {"cells": tab["cover"][r]["cells"], "rows": int((Rf.region == r).sum()),
                    **{c: int(Rf.loc[Rf.region == r, c].sum()) for c in ("Y", "V", "V20", "Yb", "Vb", "V20b")}}
                for r in regions}
    results = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "started": started,
        "commit": git("rev-parse", "HEAD"), "uncommitted": git("status", "--porcelain", "--", "pipeline/tournament"),
        "regions": regions, "missing_files": tab["missing"], "usable_swap": tab["usable"],
        "outages": tab["outages"], "swap_outages": tab["swap_outages"], "n_rows": int(len(R)),
        "n_rows_fit": int(fit_rows.sum()), "n_scored_fit": int((fit_rows & scored).sum()), "n_swap_rows": int(len(swap_rows)),
        "data": data_tab, "gbm_backend": gbm_backend(), "code_hash": sig["code"], "jobs": jobs,
        "px": px, "bd": bd, "decision": decision, "best_two": two, "bd_names": d_names, "unit_decision": unit_dec,
        "headroom": hr, "stop": {"threshold": STOP_HEADROOM, "headroom": hr["headroom"], "stop_now": hr["below_stop"]},
        "spot_check": spot, "s": s_tab, "timings_s": T_, "job_seconds": job_s,
        "jobs_fitted_now": {"px": n_fit_px, "bd": n_fit_bd},
        "rules": {"within": WITHIN, "simplicity": SIMPLICITY, "bd_skill_gain": BD_SKILL_GAIN, "bd_coverage": BD_COVERAGE},
    }
    (data.OUT / "results.json").write_text(json.dumps(jsonable(results), indent=1, default=float))
    final = done[("px", champ, "final")]["info"]
    bd_c = {v: k for k, v in d_names.items()}[unit_dec["best_bd"]]
    bd_final = done_bd[("bd", bd_c, "final")]["info"]
    champion = {
        "plan": "docs/TOURNAMENT_PLAN.md (pre-registered at fa2c956)", "results": "docs/TOURNAMENT_RESULTS.md",
        "generated": results["generated"], "commit_at_run": results["commit"], "uncommitted_at_run": results["uncommitted"],
        "code_hash": sig["code"], "champion": champ, "name": NAMES[champ], "unit": "hotspots (pixel counts)",
        "selected_by": "rule 1: the simplest candidate within 2% of the best pooled weighted CRPS (pixel unit)",
        "frozen_setting": final["setting"] if champ in ("C3", "C4", "C5") else (A2_FROZEN if champ == "C0" else None),
        "frozen_setting_note": "chosen by inner leave-one-year-out over 2012-2019 on the 17 development regions in the "
                               "final fit; a new region is refitted on its own 2012-02..2019-12 rows with this setting "
                               "and nothing is tuned",
        "refit": {
            "code": f"pipeline.tournament.candidates.fit('{champ}', T, train, scored, years, label, setting=<frozen_setting>)"
                    " on a one-region table built by pipeline.tournament.data.rows + pipeline.round2.data.build_table",
            "rows": "cell x month x day/night from 2012-02 for every cell with a MODIS, Suomi NPP or NOAA-20 detection "
                    "in 2012-02..2019-12; FIRMS standard; type 0; MODIS confidence >= 30; VIIRS confidence n/h; "
                    "region box from pipeline/regions.py; Y = Terra + Aqua",
            "fit_window_suomi_npp": [r2.FIRST_MONTH, data.FIT_LAST],
            "classes": {"frp": "f0 FRP <= 0, f1 0 < FRP < 5, f2 5 <= FRP < 20, f3 FRP >= 20 MW",
                        "scan": "s0 scan < 0.5, s1 0.5 <= scan <= 0.65, s2 scan > 0.65 km"},
            "a2_frozen_a": A2_FROZEN, "a2_grid": A2_GRID, "c5_grid": C5_GRID, "em": {"max_iterations": EM_ITERS,
                                                                                     "relative_tolerance": EM_TOL},
            "gbm": {"backend": gbm_backend(), "params": GBM, "features": GBM_FEATURES},
            "noaa20": {"method": "J-S", "window": [data.N20_FIRST, data.FIT_LAST],
                       "s": "sum V_SNPP / sum V_N20 per region x day/night; month-block bootstrap",
                       "bootstrap_resamples": BOOT, "bootstrap_seed": SEED},
            "outage_rule": "bake-off rule (pipeline.bakeoff.data.outages) over the included regions combined",
        },
        "dev_fit_for_information": final["detail"],
        "scores_dev_loyo": {"wcrps": px["overall"][f"wcrps_{champ}"], "skill_vs_R1": px["overall"][f"skill_{champ}"],
                            "cov_active": px["overall"][f"cov_active_{champ}"], "swap_median_abs_log":
                                px["swap"][champ]["median_abs_log"], "headroom": hr},
        "primary_unit": unit_dec["primary"], "unit_rule": unit_dec,
        "burning_days_model": {
            "id": unit_dec["best_bd"], "candidate": bd_c, "name": NAMES[bd_c], "unit": "burning days",
            "frozen_setting": bd_final["setting"] if bd_c in ("C3", "C4", "C5") else (A2_FROZEN if bd_c == "C0" else None),
            "unit_definition": "a 0.01 degree cell (floor(lon/0.01), floor(lat/0.01)) counts once per date and "
                               "day/night if it has any detection of the family (MODIS = Terra + Aqua); cell-day "
                               "counts summed per 0.25 degree cell x month x day/night; a burning day takes the FRP "
                               "and scan classes of its largest-FRP detection",
            "dev_fit_for_information": bd_final["detail"],
            "scores_dev_loyo": {"wcrps": bd["overall"][f"wcrps_{bd_c}"], "skill_vs_D_R1": bd["overall"][f"skill_{bd_c}"],
                                "cov_active": bd["overall"][f"cov_active_{bd_c}"],
                                "swap_median_abs_log": bd["swap"][bd_c]["median_abs_log"]}},
        "open_question": ("The plan does not say which model sits the round-3 exam when burning days are adopted as "
                          "the primary unit: the pixel champion of rule 1 or the burning-days model whose skill passed "
                          "rule 2. Both are recorded here; neither is chosen by this run.")
        if unit_dec["primary"] == "burning days" else None,
    }
    (data.OUT / "champion.json").write_text(json.dumps(jsonable(champion), indent=1, default=float))
    write_results(results, data.ROOT / "docs" / "TOURNAMENT_RESULTS.md")
    for u in paths.values():
        Path(u).unlink()
    print(f"pixel champion {champ}; unit {unit_dec['primary']}; headroom {hr['headroom']:.3f}; "
          f"total {T_['total']:.0f}s -> docs/TOURNAMENT_RESULTS.md")


if __name__ == "__main__":
    main()
