"""The round-2 confirmation on the four new sealed regions (docs/ROUND2_PLAN.md, "Confirmation"), run once.

    python -m pipeline.round2.confirm --i-am-the-lead-running-it-once     # the confirmation (the four sealed regions)
    python -m pipeline.round2.confirm --regions portugal lebanon          # development regions, for debugging only

The frozen pair (data/processed/round2/frozen.json, from pipeline.round2.select) is refitted on each region's own
2012-02..2019-12 rows (NOAA-20: 2018-04..2019-12). Nothing is tuned. Without the flag, a sealed region is refused
before any of its files is opened. A debugging run writes data/processed/round2/confirm_dev_report.md; only the
confirmation writes docs/ROUND2_CONFIRMATION.md. Every invocation is appended to data/processed/round2/confirm_runs.jsonl.
"""
import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.bakeoff.models import add_groups
from pipeline.bakeoff.validate import score_rows, weights
from pipeline.regions import REGIONS, regions_with

from . import data
from .models import fit_model, fit_ratio, fit_s, forecast, parts, ratio_parts, rng_for, totals
from .report import write_confirmation
from .validate import MIN_TOTAL, Z80, swap_summary, swap_table

FLAG = "--i-am-the-lead-running-it-once"
LAST_YEAR = 2025
TEST1_YEARS = [2020, 2021]
TEST2 = ("2020-01", "2025-12")
DRIFT_YEARS = [2022, 2023, 2024, 2025]


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=data.ROOT, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:
        return f"unavailable ({e})"


def prepare(R):
    """A one-region table: the region's own rows only, so every fallback stays inside the region."""
    R = R.reset_index(drop=True).copy()
    R["rid"] = 0
    R["cid"] = pd.factorize(R.cell)[0]
    R["dnN"] = (R.dn == "N").astype(int)
    return add_groups(R, 1)


def have(R, avail, sensors):
    """Rows whose year has a file for every one of `sensors` (a missing file is not a zero)."""
    ok = {y for y in range(2012, LAST_YEAR + 1) if all(avail.get((s, y), False) for s in sensors)}
    return R.year.isin(ok).to_numpy()


def fit_frozen(fz, R, train, label, vcol="V", which="a"):
    s = fz["settings"]
    return fit_model(s["suomi_npp_model"], R, train, rng_for("confirm", label), vcol=vcol, a=s.get(which))


def test1(fz, R, avail, bad):
    """Fit on 2012-02..2019-12, score 2020-2021 against MODIS. F0 = raw Suomi NPP, F1 = R1's point forecast."""
    reg = R.region.iloc[0]
    tr = (R.ym <= data.FIT_LAST).to_numpy()
    m = fit_frozen(fz, R, tr, (reg, "S"))
    rows = np.flatnonzero(R.year.isin(TEST1_YEARS).to_numpy() & ~R.ym.isin(bad).to_numpy()
                          & have(R, avail, ("modis", "snpp")))
    y = R.Y.to_numpy()[rows]
    s = score_rows(*forecast(m, R, rows), y)
    p = parts(m, R, rows)
    assert np.allclose(s["mean"], p["mean"]), "predictive mean disagrees with scores.score"
    f1 = fit_ratio(R, tr, False, rng_for("confirm", reg, "F1"))
    out = R.iloc[rows][["region", "cell", "ym", "year", "dn"]].reset_index(drop=True)
    out["Y"], out["V"] = y, R.V.to_numpy()[rows]
    out["w"] = weights(R, tr)[R.cid.to_numpy()[rows]]
    out["crps"], out["covered"], out["mean_M"] = s["crps"], s["covered"], p["mean"]
    out["mean_F0"] = out.V.astype(float)
    out["mean_F1"] = ratio_parts(R, rows, f1)["mean"]
    out["active"] = (out.Y > 0) | (out.V > 0)
    yu, ylab = pd.factorize(out.year)
    tot, nbv, pv = totals(p, yu, len(ylab))
    seam = pd.DataFrame({"region": reg, "year": ylab, "Y": out.groupby(yu).Y.sum().to_numpy(), "pred": tot,
                         "sd": np.sqrt(nbv + pv)})
    seam["lo"], seam["hi"] = seam.pred - Z80 * seam.sd, seam.pred + Z80 * seam.sd
    info = {"F1_r": {"D": float(f1["r"][0]), "N": float(f1["r"][1])}, "F1_b": {"D": float(f1["b"][0]), "N": float(f1["b"][1])}}
    if m["model"] == "A2":
        info["a"] = m["a"]
    else:
        info["r"] = {"D": float(m["r"][0]), "N": float(m["r"][1])} if not m["per_month"] else None
        info["alpha"] = {"D": float(m["alpha"][0]), "N": float(m["alpha"][1])}
    return out, m, seam, info


def test2(fz, R, avail, bad, mS):
    """Region-month totals 2020-01..2025-12 from Suomi NPP and from NOAA-20 by the frozen method."""
    reg = R.region.iloc[0]
    train_n = ((R.ym >= data.N20_FIRST) & (R.ym <= data.FIT_LAST)).to_numpy()
    rows = np.flatnonzero(((R.ym >= TEST2[0]) & (R.ym <= TEST2[1])).to_numpy() & ~R.ym.isin(bad).to_numpy()
                          & have(R, avail, ("snpp", "noaa20")))
    if fz["settings"]["noaa20_method"] == "J-S":
        sfit = fit_s(R, train_n, rng_for("confirm", reg, "J-S"))
        g = swap_table(R, rows, mS, None, sfit)
        info = {"s": {"D": float(sfit["s"][0]), "N": float(sfit["s"][1])},
                "sd_s": {"D": float(np.sqrt(sfit["var_s"][0])), "N": float(np.sqrt(sfit["var_s"][1]))}}
    else:
        mN = fit_frozen(fz, R, train_n, (reg, "J-M"), vcol="V20", which="a_jm")
        g = swap_table(R, rows, mS, mN)
        info = {}
    return g, info


def drift(fz, R, avail, bad, mS):
    """Monthly observed MODIS / predicted, 2022-2025, against the band of the same ratio in 2012-2019, where each
    2012-2019 year is predicted by the frozen model refitted without that year. Months with predicted >= 10 only."""
    reg = R.region.iloc[0]
    ok = ~R.ym.isin(bad).to_numpy() & have(R, avail, ("modis", "snpp"))
    parts_ = []
    for y in range(2012, 2020):
        tr = (R.ym <= data.FIT_LAST).to_numpy() & (R.year.to_numpy() != y)
        m = fit_frozen(fz, R, tr, (reg, "drift", y))
        rows = np.flatnonzero((R.year.to_numpy() == y) & ok)
        parts_.append(pd.DataFrame({"ym": R.ym.to_numpy()[rows], "pred": parts(m, R, rows)["mean"],
                                    "Y": R.Y.to_numpy()[rows]}))
    rows = np.flatnonzero(R.year.isin(DRIFT_YEARS).to_numpy() & ok)
    parts_.append(pd.DataFrame({"ym": R.ym.to_numpy()[rows], "pred": parts(mS, R, rows)["mean"], "Y": R.Y.to_numpy()[rows]}))
    g = pd.concat(parts_).groupby("ym").sum().reset_index()
    g = g[g.pred >= MIN_TOTAL].copy()
    g["ratio"] = g.Y / g.pred
    g["year"] = g.ym.str[:4].astype(int)
    g.insert(0, "region", reg)
    return g


def wape(pred, truth):
    t = truth.sum()
    return float(np.abs(pred - truth).sum() / t) if t else float("nan")


def summary1(t1):
    out = {"rows": len(t1), "active_rows": int(t1.active.sum()), "Y": int(t1.Y.sum()), "V": int(t1.V.sum())}
    out["wcrps_M"] = float(np.sum(t1.w * t1.crps) / np.sum(t1.w)) if len(t1) else float("nan")
    out["cov_active_M"] = float(t1.loc[t1.active, "covered"].mean()) if t1.active.any() else float("nan")
    out["cov_all_M"] = float(t1.covered.mean()) if len(t1) else float("nan")
    cm = t1.groupby(["region", "cell", "ym"])[["mean_M", "mean_F0", "mean_F1", "Y"]].sum()
    nm = t1.groupby(["region", "ym"])[["mean_M", "mean_F0", "mean_F1", "Y"]].sum()
    for k in ("M", "F0", "F1"):
        out[f"wape_cm_{k}"] = wape(cm[f"mean_{k}"], cm.Y)
        out[f"wape_nm_{k}"] = wape(nm[f"mean_{k}"], nm.Y)
        out[f"total_{k}"] = float(t1[f"mean_{k}"].sum())
    out["total_ratio_M"] = out["total_M"] / out["Y"] if out["Y"] else float("nan")
    return out


def verdict1(s, chosen):
    a = s["wape_cm_M"] <= s["wape_cm_F1"] + 0.01 and s["wape_cm_M"] < s["wape_cm_F0"]
    b = 0.70 <= s["cov_active_M"] <= 0.90
    c = abs(s["total_ratio_M"] - 1) <= 0.10
    d = s["wape_nm_M"] <= s["wape_nm_F1"] + 0.01
    return {"a": bool(a), "b": bool(b), "c": bool(c), "d": bool(d), "pass": bool(a and b and c and d),
            "by_construction": chosen == "R1"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", nargs="*", help="development regions, for debugging the runner only")
    ap.add_argument(FLAG, dest="lead", action="store_true", help="the one confirmation run, by the lead")
    ap.add_argument("--frozen", default=str(data.OUT / "frozen.json"))
    args = ap.parse_args()
    t_all = time.time()
    sealed = regions_with("sealed")
    wanted = args.regions or sealed
    for r in wanted:
        if r not in REGIONS:
            raise SystemExit(f"{r} is not a region in pipeline/regions.py")
    touches_sealed = [r for r in wanted if "sealed" in REGIONS[r]["roles"]]
    if touches_sealed and not args.lead:
        raise SystemExit(f"refused: {', '.join(touches_sealed)} sealed. The confirmation runs once, by the lead, "
                         f"after the frozen selection is reviewed and committed: python -m pipeline.round2.confirm {FLAG}")
    if args.lead and sorted(wanted) != sorted(sealed):
        raise SystemExit(f"{FLAG} runs exactly the four sealed regions ({', '.join(sealed)}), nothing else")
    is_confirmation = bool(args.lead)
    fz_path = Path(args.frozen)
    if not fz_path.exists():
        raise SystemExit(f"{fz_path} missing: run python -m pipeline.round2.select first")
    fz = json.loads(fz_path.read_text())
    chosen = fz["settings"]["suomi_npp_model"]

    avail = {r: data.availability(r, LAST_YEAR, sealed_ok=is_confirmation) for r in wanted}
    missing = {r: [data.file_name(r, s, y) for (s, y), ok in v.items() if not ok] for r, v in avail.items()}
    missing = {r: v for r, v in missing.items() if v}
    if is_confirmation and missing:
        raise SystemExit("refused: the sealed regions' files are not complete, and the confirmation runs once: "
                         + "; ".join(f"{r}: {len(v)} missing ({', '.join(v[:4])}{' ...' if len(v) > 4 else ''})"
                                     for r, v in missing.items()))
    regions = [r for r in wanted if not data.fit_ready(avail[r])]
    left_out = {r: missing[r] for r in wanted if r not in regions}
    print(f"regions: {regions}; left out: {sorted(left_out)}; confirmation run: {is_confirmation}; frozen {chosen} + "
          f"{fz['settings']['noaa20_method']}")
    assert regions, "no region has its 2012-2019 files"

    data.OUT.mkdir(parents=True, exist_ok=True)
    log = data.OUT / "confirm_runs.jsonl"
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    prov = {"commit": git("rev-parse", "HEAD"), "uncommitted_round2": git("status", "--porcelain", "--", "pipeline/round2"),
            "frozen_generated": fz["generated"], "frozen_commit_at_run": fz["commit_at_run"]}
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "start", "at": started, "regions": regions, "confirmation": is_confirmation,
                            "commit": prov["commit"]}) + "\n")

    T = {}
    t = time.time()
    Rs, pxs, cover = {}, [], {}
    for reg in regions:
        px = data.pixels(reg, LAST_YEAR, sealed_ok=is_confirmation)
        r, cover[reg] = data.rows(reg, px, f"{LAST_YEAR}-12")
        Rs[reg] = prepare(r)
        pxs.append(px[["region", "sensor", "date", "ym"]])
        print(f"  {reg}: {len(px):,} detections, {cover[reg]['cells']} cells, {len(r):,} rows")
    px_all = pd.concat(pxs, ignore_index=True)
    del pxs
    use_ms = {(r, y) for r in regions for y in range(2012, LAST_YEAR + 1)
              if avail[r].get(("modis", y)) and avail[r].get(("snpp", y))}
    use_sn = {(r, y) for r in regions for y in range(2018, LAST_YEAR + 1)
              if avail[r].get(("snpp", y)) and avail[r].get(("noaa20", y))}
    out = {"modis": data.outage_days(px_all, "2012-02-01", f"{LAST_YEAR}-12-31", "modis", "snpp", usable=use_ms),
           "snpp": data.outage_days(px_all, "2012-02-01", f"{LAST_YEAR}-12-31", "snpp", "modis", usable=use_ms),
           "snpp_vs_noaa20": data.outage_days(px_all, "2020-01-01", f"{LAST_YEAR}-12-31", "snpp", "noaa20", usable=use_sn),
           "noaa20": data.outage_days(px_all, "2020-01-01", f"{LAST_YEAR}-12-31", "noaa20", "snpp", usable=use_sn)}
    out["months_modis_snpp"] = sorted({x[:7] for x in out["modis"] + out["snpp"]})
    out["months_swap"] = sorted({x[:7] for x in out["snpp_vs_noaa20"] + out["noaa20"]})
    del px_all
    T["data"] = time.time() - t

    t = time.time()
    T1, T2, SEAM, DRIFT, info = [], [], [], [], {}
    for reg in regions:
        R = Rs[reg]
        t1, mS, seam, info[reg] = test1(fz, R, avail[reg], out["months_modis_snpp"])
        g2, info2 = test2(fz, R, avail[reg], out["months_swap"], mS)
        info[reg].update(info2)
        T1.append(t1)
        T2.append(g2)
        SEAM.append(seam)
        DRIFT.append(drift(fz, R, avail[reg], out["months_modis_snpp"], mS))
    T1, T2 = pd.concat(T1, ignore_index=True), pd.concat(T2, ignore_index=True)
    SEAM, DRIFT = pd.concat(SEAM, ignore_index=True), pd.concat(DRIFT, ignore_index=True)
    T["tests"] = time.time() - t
    tag = "confirm" if is_confirmation else "confirm_dev"
    for name, df in (("test1_rows", T1), ("test2_region_months", T2), ("seam", SEAM), ("drift", DRIFT)):
        df.to_pickle(data.OUT / f"{tag}_{name}.pkl")

    s1 = summary1(T1)
    v1 = verdict1(s1, chosen)
    s2 = swap_summary(T2)
    v2 = {"pass": bool(s2["counted"] > 0 and s2["share"] >= 0.80)}
    overall = "CONFIRMED" if v1["pass"] and v2["pass"] else "NOT CONFIRMED"
    failing = [n for n, ok in (("Test 1 (a) cell-month WAPE", v1["a"]), ("Test 1 (b) active-row coverage", v1["b"]),
                               ("Test 1 (c) pooled total", v1["c"]), ("Test 1 (d) national-month WAPE", v1["d"]),
                               ("Test 2 swap agreement", v2["pass"])) if not ok]
    band = DRIFT[DRIFT.year <= 2019].groupby("region").ratio.quantile([0.1, 0.5, 0.9]).unstack() if len(DRIFT) else None
    T["total"] = time.time() - t_all

    runs = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    res = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "started": started,
        "is_confirmation": is_confirmation, "regions": regions, "left_out": left_out, "missing": missing,
        "provenance": prov, "frozen": fz["settings"], "cover": cover, "outages": out, "info": info,
        "test1": {"pooled": s1, "verdict": v1, "per_region": {r: summary1(T1[T1.region == r]) for r in regions}},
        "test2": {"pooled": s2, "verdict": v2, "per_region": {r: swap_summary(T2[T2.region == r]) for r in regions},
                  "months": T2.round(3).to_dict("records")},
        "seam": SEAM.to_dict("records"),
        "drift_band": {} if band is None else {r: band.loc[r].to_dict() for r in band.index},
        "drift": DRIFT[DRIFT.year >= 2022].to_dict("records") if len(DRIFT) else [],
        "overall": overall, "failing": failing, "timings_s": T, "min_total": MIN_TOTAL,
        "runs_logged": [x for x in runs if x.get("confirmation") == is_confirmation],
    }
    (data.OUT / f"{tag}_results.json").write_text(json.dumps(res, indent=1, default=float))
    report = data.ROOT / "docs" / "ROUND2_CONFIRMATION.md" if is_confirmation else data.OUT / "confirm_dev_report.md"
    write_confirmation(res, report)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "finish", "at": res["generated"], "regions": regions,
                            "confirmation": is_confirmation, "overall": overall}) + "\n")
    print(json.dumps({"test1": s1, "v1": v1, "test2": s2, "overall": overall, "failing": failing}, indent=1, default=float))
    print(f"total {T['total']:.0f}s -> {report}")


if __name__ == "__main__":
    main()
