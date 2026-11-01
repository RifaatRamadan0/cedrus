"""Round-2 selection on development regions only, exactly as docs/ROUND2_PLAN.md ("Selection").

    python -m pipeline.round2.select                      # every development region whose files are in
    python -m pipeline.round2.select --regions portugal   # a subset, for development only (not the selection)

Stage 1 scores R1, Rm and A2 (outer leave-one-year-out 2012-2019 plus the forward check) and keeps the simplest within
2% of the best pooled weighted CRPS. Stage 2 compares J-M and J-S by the Suomi NPP / NOAA-20 swap on 2020-01..2021-12.
Writes data/processed/round2/* and, for the full run only, docs/ROUND2_SELECTION.md and data/processed/round2/frozen.json.
No sealed region is opened: every file access goes through data.guard.
"""
import argparse
import json
import os
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from pipeline.bakeoff.data import outages as bakeoff_outages

from . import data
from .models import A2_GRID, BOOT, MODELS, SEED
from .report import write_selection
from .validate import (MIN_TOTAL, WITHIN, Z80, choose_n20, fit_n20, run_fold, select, summary, swap_summary,
                       swap_table)

YEARS = list(range(2012, 2020))
FORWARD = (list(range(2012, 2017)), [2017, 2018, 2019])
SWAP = ("2020-01", "2021-12")
LAST_YEAR = 2021

_W = {}


def _init(path):
    _W.update(pd.read_pickle(path))


def _fold(args):
    return run_fold(_W["R"], _W["scored"], *args)


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=data.ROOT, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:
        return f"unavailable ({e})"


def model_params(m, regions):
    """The fitted numbers of one model, per region (for the report and frozen.json)."""
    if m["model"] == "A2":
        f = m["fit"]
        return {"a": m["a"], "inner_loyo_weighted_crps": m["inner"],
                "r0": [{"region": regions[i // 24], "moy": (i % 24) // 2 + 1, "dn": "DN"[i % 2], "r0": float(f["r0"][i]),
                        "b": float(f["bA"][i])} for i in range(len(regions) * 24)]}
    out = []
    ng = len(m["r"])
    for i in range(ng):
        reg = regions[i // 24] if m["per_month"] else regions[i // 2]
        row = {"region": reg, "dn": "DN"[i % 2], "r": float(m["r"][i]), "sd_r": float(np.sqrt(m["var_r"][i])),
               "r_source": ["group", "region", "all regions", "none"][int(m["r_level"][i])],
               "b": float(m["b"][i]), "b_source": ["group", "region", "all regions", "none"][int(m["b_level"][i])]}
        if m["per_month"]:
            row["moy"] = (i % 24) // 2 + 1
        out.append(row)
    alpha = [{"region": regions[k // 2], "dn": "DN"[k % 2], "alpha": float(m["alpha"][k]),
              "from_all_regions": bool(m["alpha_fallback"][k])} for k in range(len(regions) * 2)]
    return {"groups": out, "alpha": alpha, "bootstrap_blocks": m["boot_blocks"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", nargs="*", help="development subset, for development only")
    ap.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1))
    args = ap.parse_args()
    T = {}
    t_all = time.time()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    dev = data.dev_regions()
    wanted = args.regions or dev
    for r in wanted:
        data.guard(r)
        assert r in dev, f"{r} is not a development region"
    full_run = sorted(wanted) == sorted(dev)
    avail = {r: data.availability(r, LAST_YEAR) for r in wanted}
    missing_fit = {r: data.fit_ready(avail[r]) for r in wanted}
    regions = [r for r in wanted if not missing_fit[r]]
    left_out = {r: [data.file_name(r, s, y) for s, y in v] for r, v in missing_fit.items() if v}
    missing_swap = {r: [data.file_name(r, s, y) for (s, y), ok in avail[r].items() if not ok and y >= 2020
                        and s in ("snpp", "noaa20")] for r in regions}
    missing_swap = {r: v for r, v in missing_swap.items() if v}
    print(f"regions: {regions}; left out: {sorted(left_out)}; swap files missing: {missing_swap}")
    assert regions, "no development region has its files"

    t = time.time()
    Rs, pxs, cover = {}, [], {}
    for reg in regions:
        px = data.pixels(reg, LAST_YEAR)
        Rs[reg], cover[reg] = data.rows(reg, px, f"{LAST_YEAR}-12")
        pxs.append(px[["region", "sensor", "date", "ym"]])
        print(f"  {reg}: {len(px):,} detections, {cover[reg]['cells']} cells, {len(Rs[reg]):,} rows")
    px_all = pd.concat(pxs, ignore_index=True)
    del pxs
    R = data.build_table(Rs)
    del Rs
    out = bakeoff_outages(px_all)  # the bake-off's own rule, 2012-02..2019-12, all included regions combined
    scored = ~R.ym.isin(out["excluded_months"]).to_numpy()
    usable = {(r, y) for r in regions for y in (2020, 2021)
              if avail[r].get(("snpp", y)) and avail[r].get(("noaa20", y))}
    swap_out = {"snpp": data.outage_days(px_all, "2020-01-01", "2021-12-31", "snpp", "noaa20", usable=usable),
                "noaa20": data.outage_days(px_all, "2020-01-01", "2021-12-31", "noaa20", "snpp", usable=usable)}
    swap_out["excluded_months"] = sorted({d[:7] for d in swap_out["snpp"] + swap_out["noaa20"]})
    del px_all
    T["data"] = time.time() - t
    fit_rows = (R.ym <= data.FIT_LAST).to_numpy()
    print(f"rows {len(R):,} ({fit_rows.sum():,} in 2012-02..2019-12, {scored[fit_rows].mean():.1%} of them in scored "
          f"months); excluded months {out['excluded_months']}; swap outage months {swap_out['excluded_months']}")

    # ---------------------------------------------------------------- stage 1: Suomi NPP candidates
    data.OUT.mkdir(parents=True, exist_ok=True)
    jobs = [([y for y in YEARS if y != h], [h], str(h)) for h in YEARS] + [(FORWARD[0], FORWARD[1], "forward")]
    t = time.time()
    if args.jobs > 1:
        cache = data.OUT / "_tables.pkl"
        pd.to_pickle({"R": R, "scored": scored}, cache)
        with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(str(cache),)) as ex:
            res = list(ex.map(_fold, jobs))
        cache.unlink()
    else:
        res = [run_fold(R, scored, *j) for j in jobs]
    T["outer folds and forward check"] = time.time() - t
    for _, info in res:
        print(f"  fold {info['fold']}: a={info['a']} ({info['seconds']}s)")
    loyo = pd.concat([r for r, i in res if i["fold"] != "forward"], ignore_index=True)
    fwd = next(r for r, i in res if i["fold"] == "forward")
    folds = [i for _, i in res]
    tag = "" if full_run else "_subset"
    loyo.to_pickle(data.OUT / f"loyo_rows{tag}.pkl")
    fwd.to_pickle(data.OUT / f"forward_rows{tag}.pkl")

    t = time.time()
    region_of, year_of = R.region.to_numpy(), R.year.to_numpy()
    overall = summary(loyo, R)
    per_region = {r: summary(loyo[region_of[loyo.row] == r], R) for r in regions}
    per_year = {int(y): summary(loyo[year_of[loyo.row] == y], R) for y in YEARS}
    forward = summary(fwd, R)
    forward_region = {r: summary(fwd[region_of[fwd.row] == r], R) for r in regions}
    decision = select(overall)
    T["scores"] = time.time() - t
    print(json.dumps({"overall": overall, "decision": decision}, indent=1, default=float))

    # ---------------------------------------------------------------- stage 2: NOAA-20 method
    t = time.time()
    chosen = decision["chosen"]
    train_s = fit_rows
    train_n = ((R.ym >= data.N20_FIRST) & (R.ym <= data.FIT_LAST)).to_numpy()
    mS, mN, sfit = fit_n20(chosen, R, train_s, train_n, scored, "dev-n20")
    ok_ry = (R.region + ":" + R.year.astype(str)).isin({f"{r}:{y}" for r, y in usable}).to_numpy()
    rows = np.flatnonzero(((R.ym >= SWAP[0]) & (R.ym <= SWAP[1])).to_numpy() & ok_ry
                          & ~R.ym.isin(swap_out["excluded_months"]).to_numpy())
    jm = swap_table(R, rows, mS, mN)
    js = swap_table(R, rows, mS, None, sfit)
    sum_jm, sum_js = swap_summary(jm), swap_summary(js)
    n20 = choose_n20(sum_js, sum_jm)
    swap_region = {r: {"J-M": swap_summary(jm[jm.region == r]), "J-S": swap_summary(js[js.region == r])}
                   for r in regions}
    jm.to_pickle(data.OUT / f"swap_jm{tag}.pkl")
    js.to_pickle(data.OUT / f"swap_js{tag}.pkl")
    T["NOAA-20 stage"] = time.time() - t
    print(json.dumps({"J-M": sum_jm, "J-S": sum_js, "n20": n20}, indent=1, default=float))
    T["total"] = time.time() - t_all

    s_tab = [{"region": regions[k // 2], "dn": "DN"[k % 2], "s": float(sfit["s"][k]), "sd_s": float(np.sqrt(sfit["var_s"][k])),
              "s_source": ["region", "region", "all regions", "none"][int(sfit["s_level"][k])]}
             for k in range(len(regions) * 2)]
    settings = {
        "suomi_npp_model": chosen, "noaa20_method": n20["chosen"],
        "a": mS.get("a") if chosen == "A2" else None,
        "a_jm": mN.get("a") if chosen == "A2" else None,
        "a_note": ("a frozen at the value chosen by leave-one-year-out over 2012-2019 on the development regions, "
                   "a_jm at the value chosen over 2018/2019 for J-M; the confirmation refits A2 with these and tunes "
                   "nothing") if chosen == "A2" else None,
        "fit_window_suomi_npp": [data.FIRST_MONTH, data.FIT_LAST], "fit_window_noaa20": [data.N20_FIRST, data.FIT_LAST],
        "bootstrap_resamples": BOOT, "bootstrap_seed": SEED,
        "bootstrap_r": "year blocks over the training years of the fit, resampled with replacement",
        "bootstrap_s": "month blocks over 2018-04..2019-12, resampled with replacement",
        "ratio_fallback": "group -> region x day/night -> all regions x day/night (a one-region table: the region)",
        "alpha": "NB2 maximum likelihood per region x day/night, means held at the fitted r*V and b, log alpha in [-20, 6]",
        "predictive_distribution": ("R1/Rm: negative binomial moment-matched to mean and NB variance + V^2 Var(r); "
                                    "A2: A's Poisson-gamma (NB for V > 0, Poisson(b) for V = 0)"),
        "interval_of_a_total": f"mean +/- {Z80:.4f} sd; sd^2 = summed NB variances + bootstrap variance of the total",
        "count_rule_min_total": MIN_TOTAL, "a2_grid": A2_GRID, "within": WITHIN,
        "rows": "cell x month x day/night from 2012-02 for every cell with a MODIS, Suomi NPP or NOAA-20 detection in "
                "2012-02..2019-12; region box from pipeline/regions.py; bake-off filters",
        "outage_rule_test1": "MODIS 0 while Suomi NPP >= 50, or Suomi NPP 0 while MODIS >= 50 (regions combined)",
        "outage_rule_swap": "Suomi NPP 0 while NOAA-20 >= 50, or NOAA-20 0 while Suomi NPP >= 50 (regions combined)",
    }
    results = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "started": started,
        "commit": git("rev-parse", "HEAD"), "uncommitted_round2": git("status", "--porcelain", "--", "pipeline/round2"),
        "full_run": full_run, "regions": regions, "left_out": left_out, "missing_swap": missing_swap,
        "cover": cover, "outages": out, "swap_outages": swap_out,
        "n_rows_fit": int(fit_rows.sum()), "n_scored_fit": int((fit_rows & scored).sum()),
        "rows_per_region": R[fit_rows].groupby("region").size().to_dict(),
        "Y_per_region": R[fit_rows].groupby("region").Y.sum().to_dict(),
        "V_per_region": R[fit_rows].groupby("region").V.sum().to_dict(),
        "V20_per_region_fit": R[train_n].groupby("region").V20.sum().to_dict(),
        "folds": folds, "overall": overall, "per_region": per_region, "per_year": per_year,
        "forward": forward, "forward_region": forward_region, "decision": decision,
        "n20": n20, "swap": {"J-M": sum_jm, "J-S": sum_js, "per_region": swap_region,
                             "jm_months": jm.round(3).to_dict("records"), "js_months": js.round(3).to_dict("records")},
        "s": s_tab, "snpp_params": model_params(mS, regions), "jm_params": model_params(mN, regions),
        "settings": settings, "timings_s": T, "jobs": args.jobs,
    }
    (data.OUT / f"selection{tag}.json").write_text(json.dumps(results, indent=1, default=float))
    report = data.ROOT / "docs" / "ROUND2_SELECTION.md" if full_run else data.OUT / "selection_subset.md"
    write_selection(results, report)
    if full_run:
        frozen = {"plan": "docs/ROUND2_PLAN.md", "selection_report": "docs/ROUND2_SELECTION.md",
                  "generated": results["generated"], "commit_at_run": results["commit"],
                  "uncommitted_round2_at_run": results["uncommitted_round2"],
                  "development_regions": regions, "settings": settings,
                  "dev_fit_for_information": {"suomi_npp": results["snpp_params"], "noaa20_jm": results["jm_params"],
                                              "s": s_tab}}
        (data.OUT / "frozen.json").write_text(json.dumps(frozen, indent=1, default=float))
    print(f"chosen {chosen} + {n20['chosen']}; total {T['total']:.0f}s -> {report}")


if __name__ == "__main__":
    main()
