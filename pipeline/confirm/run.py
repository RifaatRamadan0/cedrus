"""The confirmation, run once on the four regions that were sealed (docs/CONFIRMATION_PLAN.md).

    python -m pipeline.confirm.run                              # the four confirmation regions
    python -m pipeline.confirm.run --regions portugal lebanon   # development regions, for debugging only

Writes data/processed/confirm/* and docs/CONFIRMATION_RESULTS.md. Every invocation is appended
to data/processed/confirm/runs.jsonl, and the report lists them, so a re-run cannot go unseen.
"""
import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from pipeline.regions import REGIONS, assert_not_sealed, regions_with

from . import data
from .report import write_report
from .tests import MIN_TOTAL, drift, prepare, seam, test1, test2

FROZEN_COMMIT = "f0823f9"


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=data.ROOT, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:  # git missing: say so in the report rather than fail
        return f"unavailable ({e})"


def provenance():
    files = ["models.py", "scores.py", "validate.py", "data.py"]
    return {
        "commit": git("rev-parse", "HEAD"),
        "uncommitted_in_pipeline": git("status", "--porcelain", "--", "pipeline"),
        "bakeoff_diff_vs_frozen": git("diff", "--stat", FROZEN_COMMIT, "--", "pipeline/bakeoff"),
        "bakeoff_sha256": {f: hashlib.sha256((data.ROOT / "pipeline" / "bakeoff" / f).read_bytes()).hexdigest()[:16]
                           for f in files},
    }


def wape(pred, truth):
    t = truth.sum()
    return float(np.abs(pred - truth).sum() / t) if t else float("nan")


def summary1(t1):
    out = {"rows": len(t1), "active_rows": int(t1.active.sum()), "Y": int(t1.Y.sum()), "V": int(t1.V.sum())}
    out["wcrps_A"] = float(np.sum(t1.w * t1.crps) / np.sum(t1.w))
    out["crps_A"] = float(t1.crps.mean())
    out["cov_active_A"] = float(t1.loc[t1.active, "covered"].mean()) if t1.active.any() else float("nan")
    out["cov_all_A"] = float(t1.covered.mean())
    cm = t1.groupby(["region", "cell", "ym"])[["mean_A", "mean_F0", "mean_F1", "Y"]].sum()
    nm = t1.groupby(["region", "ym"])[["mean_A", "mean_F0", "mean_F1", "Y"]].sum()
    for m in ("A", "F0", "F1"):
        out[f"wape_cm_{m}"] = wape(cm[f"mean_{m}"], cm.Y)
        out[f"wape_nm_{m}"] = wape(nm[f"mean_{m}"], nm.Y)
        out[f"total_{m}"] = float(t1[f"mean_{m}"].sum())
    return out


def verdict1(s):
    a = s["wape_cm_A"] < s["wape_cm_F1"] and s["wape_cm_A"] < s["wape_cm_F0"]
    b = 0.70 <= s["cov_active_A"] <= 0.90
    return {"a_wape_beats_floors": bool(a), "b_active_coverage_0.70_0.90": bool(b), "pass": bool(a and b)}


def summary2(t2):
    c = t2[t2.counted]
    return {"region_months": len(t2), "counted": len(c), "agree": int(c.agree.sum()),
            "share": float(c.agree.mean()) if len(c) else float("nan")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", nargs="*", help="development regions, for debugging the runner only")
    ap.add_argument("--report", default=str(data.ROOT / "docs" / "CONFIRMATION_RESULTS.md"))
    args = ap.parse_args()
    t_all = time.time()
    confirm = regions_with("confirm")
    wanted = args.regions or confirm
    for r in wanted:
        assert_not_sealed(r)
        assert r in REGIONS, r
    is_confirmation = sorted(wanted) == sorted(confirm) and bool(confirm)
    ready = {r: data.readiness(r) for r in wanted}
    regions = [r for r in wanted if ready[r][0]]
    left_out = {r: ready[r][1] for r in wanted if not ready[r][0]}
    print(f"regions: {regions}; incomplete: {sorted(left_out)}; confirmation run: {is_confirmation}")
    assert regions, "no region has complete files"

    data.OUT.mkdir(parents=True, exist_ok=True)
    log = data.OUT / "runs.jsonl"
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    prov = provenance()
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "start", "at": started, "regions": regions, "confirmation": is_confirmation,
                            "commit": prov["commit"]}) + "\n")

    T = {}
    t = time.time()
    pxs, Rs, cover = [], {}, {}
    for reg in regions:
        px = data.pixels(reg)
        r, cover[reg] = data.rows(reg, px)
        Rs[reg] = prepare(r)
        pxs.append(px[["region", "sensor", "date", "ym"]])
        print(f"  {reg}: {len(px):,} detections, {cover[reg]['cells']} cells, {len(r):,} rows")
    out = data.outages(pd.concat(pxs, ignore_index=True))
    del pxs
    T["data"] = time.time() - t

    t = time.time()
    T1, T2, SEAM, DRIFT, info1 = [], [], [], [], {}
    for reg in regions:
        R = Rs[reg]
        t1, fA, info1[reg] = test1(R, out["months_modis_snpp"])
        T1.append(t1)
        T2.append(test2(R, out["months_snpp_noaa20"]))
        SEAM.append(seam(t1))
        DRIFT.append(drift(R, fA, out["months_modis_snpp"]))
    T1, T2 = pd.concat(T1, ignore_index=True), pd.concat(T2, ignore_index=True)
    SEAM, DRIFT = pd.concat(SEAM, ignore_index=True), pd.concat(DRIFT, ignore_index=True)
    T["tests"] = time.time() - t
    for name, df in (("test1_rows", T1), ("test2_region_months", T2), ("seam", SEAM), ("drift", DRIFT)):
        df.to_pickle(data.OUT / f"{name}.pkl")

    s1 = summary1(T1)
    v1 = verdict1(s1)
    s2 = summary2(T2)
    v2 = {"pass": bool(s2["counted"] > 0 and s2["share"] >= 0.80)}
    overall = "CONFIRMED" if v1["pass"] and v2["pass"] else "NOT CONFIRMED"
    failing = [n for n, ok in (("Test 1 (a) cell-month WAPE vs floors", v1["a_wape_beats_floors"]),
                               ("Test 1 (b) active-row coverage", v1["b_active_coverage_0.70_0.90"]),
                               ("Test 2 swap agreement", v2["pass"])) if not ok]
    band = DRIFT[DRIFT.year <= 2019].groupby("region").ratio.quantile([0.1, 0.5, 0.9]).unstack()
    T["total"] = time.time() - t_all

    runs = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    res = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "started": started,
        "is_confirmation": is_confirmation, "regions": regions, "left_out": left_out, "provenance": prov,
        "cover": cover, "outages": out, "info1": info1,
        "test1": {"pooled": s1, "verdict": v1, "per_region": {r: summary1(T1[T1.region == r]) for r in regions}},
        "test2": {"pooled": s2, "verdict": v2, "per_region": {r: summary2(T2[T2.region == r]) for r in regions},
                  "months": T2.round(2).to_dict("records")},
        "seam": SEAM.to_dict("records"),
        "drift_band": {r: band.loc[r].to_dict() for r in band.index},
        "drift": DRIFT[DRIFT.year >= 2022].to_dict("records"),
        "overall": overall, "failing": failing, "timings_s": T, "min_total": MIN_TOTAL,
        "runs_logged": [x for x in runs if x.get("confirmation")],
    }
    (data.OUT / "results.json").write_text(json.dumps(res, indent=1, default=float))
    write_report(res, args.report)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "finish", "at": res["generated"], "regions": regions,
                            "confirmation": is_confirmation, "overall": overall}) + "\n")
    print(json.dumps({"test1": res["test1"]["pooled"], "v1": v1, "test2": s2, "overall": overall,
                      "failing": failing}, indent=1, default=float))
    print(f"total {T['total']:.0f}s -> {args.report}")


if __name__ == "__main__":
    main()
