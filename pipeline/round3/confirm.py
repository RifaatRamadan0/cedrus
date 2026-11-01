"""The round-3 confirmation of D-a on the four round-3 sealed regions (docs/TOURNAMENT_PLAN.md, "Round 3 sealed exam"
and the ruling added 1 Nov 2026), run once.

    python -m pipeline.round3.confirm --i-am-the-lead-running-it-once      # the confirmation (the four sealed regions)
    python -m pipeline.round3.confirm --regions central_spain portugal     # development regions, for debugging only

D-a (data/processed/tournament/frozen_round3.json, refused unless its SHA-256 is the one recorded at the freeze) is
refitted on each region's own 2012-02..2019-12 rows in the burning-day unit (NOAA-20 by J-S, s fitted on
2018-04..2019-12 in the same unit). Nothing is tuned. Tests and pass rules are round 2's (pipeline.round2.confirm),
applied in burning days; F0 and F1 are in burning days too. Without the flag, a sealed region is refused before any of
its files is opened. A debugging run writes data/processed/round3/confirm_dev_report.md; only the confirmation writes
docs/ROUND3_CONFIRMATION.md. Every invocation is appended to data/processed/round3/confirm_runs.jsonl.
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from pipeline.bakeoff.validate import score_rows, weights
from pipeline.round2 import data as r2
from pipeline.round2.confirm import verdict1, wape
from pipeline.round2.models import fit_ratio, fit_s, ratio_parts, rng_for, totals
from pipeline.round2.validate import MIN_TOTAL, Z80, region_month_units, swap_summary
from pipeline.regions import REGIONS, regions_with
from pipeline.tournament.run import code_hash

from . import data
from .model import fit_frozen, forecast, frozen_a, js_parts, parts
from .report import write_confirmation

FLAG = "--i-am-the-lead-running-it-once"
LAST_YEAR = data.LAST_YEAR
TEST1_YEARS = [2020, 2021]
TEST2 = ("2020-01", "2025-12")
DRIFT_YEARS = [2022, 2023, 2024, 2025]
F0_SHARE = 0.25  # the recorded f0 tail risk: region-months where the FRP <= 0 class is more than this of the total
SWAP_Q = 0.90


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=data.ROOT, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:
        return f"unavailable ({e})"


def have(T, avail, sensors):
    """Rows whose year has a file for every one of `sensors` (a missing file is not a zero)."""
    ok = {y for y in range(2012, LAST_YEAR + 1) if all(avail.get((s, y), False) for s in sensors)}
    return T.year.isin(ok).to_numpy()


def test1(fz, T, avail, bad):
    """Fit on 2012-02..2019-12, score 2020-2021 against MODIS burning days. F0 = raw Suomi NPP burning days,
    F1 = R1's point forecast fitted in burning days."""
    reg = T.region.iloc[0]
    tr = (T.ym <= data.FIT_LAST).to_numpy()
    m = fit_frozen(fz, T, tr, ("round3", reg, "S"))
    rows = np.flatnonzero(T.year.isin(TEST1_YEARS).to_numpy() & ~T.ym.isin(bad).to_numpy()
                          & have(T, avail, ("modis", "snpp")))
    y = T.Y.to_numpy()[rows]
    s = score_rows(*forecast(m, T, rows), y)
    p = parts(m, T, rows)
    assert np.allclose(s["mean"], p["mean"]), "predictive mean disagrees with scores.score"
    f1 = fit_ratio(T, tr, False, rng_for("round3", reg, "F1"))
    out = T.iloc[rows][["region", "cell", "ym", "year", "dn"]].reset_index(drop=True)
    out["Y"], out["V"] = y, T.V.to_numpy()[rows]
    out["Vf0"] = T.Vf0.to_numpy()[rows]
    out["w"] = weights(T, tr)[T.cid.to_numpy()[rows]]
    out["crps"], out["covered"], out["mean_M"] = s["crps"], s["covered"], p["mean"]
    out["f0_M"] = p["f0"]
    out["mean_F0"] = out.V.astype(float)
    out["mean_F1"] = ratio_parts(T, rows, f1)["mean"]
    out["active"] = (out.Y > 0) | (out.V > 0)
    yu, ylab = pd.factorize(out.year)
    tot, nbv, pv = totals(p, yu, len(ylab))
    seam = pd.DataFrame({"region": reg, "year": ylab, "Y": out.groupby(yu).Y.sum().to_numpy(), "pred": tot,
                         "sd": np.sqrt(nbv + pv)})
    seam["lo"], seam["hi"] = seam.pred - Z80 * seam.sd, seam.pred + Z80 * seam.sd
    f = m["fit"]
    info = {"a": f["a"], "em_iterations": f["em_iterations"], "em_delta": f["em_delta"],
            "em_converged": f["em_converged"], "r0_groups_on_fallback": int((f["r0_level"] > 0).sum()),
            "F1_r": {"D": float(f1["r"][0]), "N": float(f1["r"][1])},
            "F1_b": {"D": float(f1["b"][0]), "N": float(f1["b"][1])}}
    return out, m, seam, info


def swap_table(T, rows, m, sfit):
    """Region-month totals from Suomi NPP and from NOAA-20 by J-S, each with its 80% interval; counted if both
    totals >= 10; agree if the intervals overlap (round 2's pipeline.round2.validate.swap_table, for D-a)."""
    unit, g = region_month_units(T, rows)
    n = len(g)
    pS, pN = parts(m, T, rows), js_parts(m, T, rows, sfit)
    tS, nbS, pvS = totals(pS, unit, n)
    tN, nbN, pvN = totals(pN, unit, n, sfit["s_boot"])
    g["tot_S"], g["nbvar_S"], g["pvar_S"] = tS, nbS, pvS
    g["tot_N"], g["nbvar_N"], g["pvar_N"] = tN, nbN, pvN
    for k in ("S", "N"):
        sd = np.sqrt(g[f"nbvar_{k}"] + g[f"pvar_{k}"])
        g[f"lo_{k}"], g[f"hi_{k}"] = g[f"tot_{k}"] - Z80 * sd, g[f"tot_{k}"] + Z80 * sd
    g["f0_S"], g["f0_N"] = np.bincount(unit, pS["f0"], n), np.bincount(unit, pN["f0"], n)
    g["V"] = np.bincount(unit, T.V.to_numpy()[rows], n)
    g["V20"] = np.bincount(unit, T.V20.to_numpy()[rows], n)
    g["Vf0"] = np.bincount(unit, T.Vf0.to_numpy()[rows], n)
    g["V20f0"] = np.bincount(unit, T.V20f0.to_numpy()[rows], n)
    g["counted"] = (g.tot_S >= MIN_TOTAL) & (g.tot_N >= MIN_TOTAL)
    g["agree"] = (g.lo_S <= g.hi_N) & (g.lo_N <= g.hi_S)
    return g


def test2(T, avail, bad, mS):
    """Region-month totals 2020-01..2025-12 from Suomi NPP and from NOAA-20 by J-S (s on 2018-04..2019-12)."""
    reg = T.region.iloc[0]
    train_n = ((T.ym >= data.N20_FIRST) & (T.ym <= data.FIT_LAST)).to_numpy()
    rows = np.flatnonzero(((T.ym >= TEST2[0]) & (T.ym <= TEST2[1])).to_numpy() & ~T.ym.isin(bad).to_numpy()
                          & have(T, avail, ("snpp", "noaa20")))
    sfit = fit_s(T, train_n, rng_for("round3", reg, "J-S"))
    g = swap_table(T, rows, mS, sfit)
    info = {"s": {"D": float(sfit["s"][0]), "N": float(sfit["s"][1])},
            "sd_s": {"D": float(np.sqrt(sfit["var_s"][0])), "N": float(np.sqrt(sfit["var_s"][1]))}}
    return g, info


def drift(fz, T, avail, bad, mS):
    """Monthly observed MODIS burning days / predicted, 2022-2025, against the band of the same ratio in 2012-2019,
    where each 2012-2019 year is predicted by D-a refitted without that year. Months with predicted >= 10 only."""
    reg = T.region.iloc[0]
    ok = ~T.ym.isin(bad).to_numpy() & have(T, avail, ("modis", "snpp"))
    parts_ = []
    for y in range(2012, 2020):
        tr = (T.ym <= data.FIT_LAST).to_numpy() & (T.year.to_numpy() != y)
        m = fit_frozen(fz, T, tr, ("round3", reg, "drift", y))
        rows = np.flatnonzero((T.year.to_numpy() == y) & ok)
        parts_.append(pd.DataFrame({"ym": T.ym.to_numpy()[rows], "pred": parts(m, T, rows)["mean"],
                                    "Y": T.Y.to_numpy()[rows]}))
    rows = np.flatnonzero(T.year.isin(DRIFT_YEARS).to_numpy() & ok)
    parts_.append(pd.DataFrame({"ym": T.ym.to_numpy()[rows], "pred": parts(mS, T, rows)["mean"],
                                "Y": T.Y.to_numpy()[rows]}))
    g = pd.concat(parts_).groupby("ym").sum().reset_index()
    g = g[g.pred >= MIN_TOTAL].copy()
    g["ratio"] = g.Y / g.pred
    g["year"] = g.ym.str[:4].astype(int)
    g.insert(0, "region", reg)
    return g


def summary1(t1):
    """Round 2's summary1 (pipeline.round2.confirm) plus coverage split by V > 0 / V = 0 among active rows."""
    out = {"rows": len(t1), "active_rows": int(t1.active.sum()), "Y": int(t1.Y.sum()), "V": int(t1.V.sum())}
    out["wcrps_M"] = float(np.sum(t1.w * t1.crps) / np.sum(t1.w)) if len(t1) else float("nan")
    out["cov_active_M"] = float(t1.loc[t1.active, "covered"].mean()) if t1.active.any() else float("nan")
    out["cov_all_M"] = float(t1.covered.mean()) if len(t1) else float("nan")
    vpos, vzero = t1.active & (t1.V > 0), t1.active & (t1.V == 0)
    out["active_vpos"], out["active_vzero"] = int(vpos.sum()), int(vzero.sum())
    out["cov_vpos_M"] = float(t1.loc[vpos, "covered"].mean()) if vpos.any() else float("nan")
    out["cov_vzero_M"] = float(t1.loc[vzero, "covered"].mean()) if vzero.any() else float("nan")
    cm = t1.groupby(["region", "cell", "ym"])[["mean_M", "mean_F0", "mean_F1", "Y"]].sum()
    nm = t1.groupby(["region", "ym"])[["mean_M", "mean_F0", "mean_F1", "Y"]].sum()
    for k in ("M", "F0", "F1"):
        out[f"wape_cm_{k}"] = wape(cm[f"mean_{k}"], cm.Y)
        out[f"wape_nm_{k}"] = wape(nm[f"mean_{k}"], nm.Y)
        out[f"total_{k}"] = float(t1[f"mean_{k}"].sum())
    out["total_ratio_M"] = out["total_M"] / out["Y"] if out["Y"] else float("nan")
    out["f0_M"] = float(t1.f0_M.sum())
    return out


def swap_metrics(g):
    """|log(NOAA-20-based total / Suomi NPP-based total)| per region-month: median and 90th percentile over
    region-months where both totals are > 0 (the tournament's population), and the same where both are >= 10."""
    out = {"region_months": int(len(g))}
    for key, sel in (("pos", (g.tot_S > 0) & (g.tot_N > 0)), ("ge10", (g.tot_S >= MIN_TOTAL) & (g.tot_N >= MIN_TOTAL))):
        lg = np.abs(np.log(g.tot_N[sel] / g.tot_S[sel])).to_numpy()
        out[f"used_{key}"] = int(sel.sum())
        out[f"median_{key}"] = float(np.median(lg)) if len(lg) else float("nan")
        out[f"p90_{key}"] = float(np.quantile(lg, SWAP_Q)) if len(lg) else float("nan")
        out[f"max_{key}"] = float(lg.max()) if len(lg) else float("nan")
    return out


def f0_tail(t1, t2):
    """Region-months where the f0 (FRP <= 0) class is more than 25% of the predicted total: Test 1 rows (Suomi NPP,
    with observed MODIS burning days) and Test 2 rows (Suomi NPP-based and NOAA-20-based)."""
    a = t1.groupby(["region", "ym"], as_index=False)[["mean_M", "f0_M", "Y", "V", "Vf0"]].sum()
    a = a.rename(columns={"mean_M": "pred", "f0_M": "f0", "Vf0": "class_f0"}).assign(source="Test 1, Suomi NPP")
    parts_ = [a]
    for k, lab, v, vf in (("S", "Test 2, Suomi NPP-based", "V", "Vf0"), ("N", "Test 2, NOAA-20-based (J-S)", "V20", "V20f0")):
        b = t2[["region", "ym", f"tot_{k}", f"f0_{k}", v, vf]].rename(
            columns={f"tot_{k}": "pred", f"f0_{k}": "f0", v: "V", vf: "class_f0"})
        parts_.append(b.assign(source=lab, Y=np.nan))
    d = pd.concat(parts_, ignore_index=True)
    d["share"] = np.where(d.pred > 0, d.f0 / d.pred.where(d.pred > 0, 1.0), 0.0)
    flagged = d[(d.pred > 0) & (d.share > F0_SHARE)].sort_values(["source", "region", "ym"])
    counts = d[d.pred > 0].groupby("source").size().to_dict()
    return flagged, counts


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", nargs="*", help="development regions, for debugging the runner only")
    ap.add_argument(FLAG, dest="lead", action="store_true", help="the one confirmation run, by the lead")
    ap.add_argument("--frozen", default=str(data.FROZEN))
    args = ap.parse_args()
    t_all = time.time()
    sealed = regions_with("sealed")
    wanted = args.regions or sealed
    for r in wanted:
        if r not in REGIONS:
            raise SystemExit(f"{r} is not a region in pipeline/regions.py")
    touches_sealed = [r for r in wanted if "sealed" in REGIONS[r]["roles"]]
    if touches_sealed and not args.lead:
        raise SystemExit(f"refused: {', '.join(touches_sealed)} sealed. The round-3 confirmation runs once, by the "
                         f"lead: python -m pipeline.round3.confirm {FLAG}")
    if args.lead and sorted(wanted) != sorted(sealed):
        raise SystemExit(f"{FLAG} runs exactly the four sealed regions ({', '.join(sealed)}), nothing else")
    is_confirmation = bool(args.lead)
    fz, fz_sha = data.load_frozen(args.frozen)
    a = frozen_a(fz)
    hash_now, hash_frozen = code_hash(), fz["champion_json"]["code_hash"]

    avail = {r: r2.availability(r, LAST_YEAR, sealed_ok=is_confirmation) for r in wanted}
    missing = {r: [r2.file_name(r, s, y) for (s, y) in data.complete(v)] for r, v in avail.items()}
    missing = {r: v for r, v in missing.items() if v}
    if is_confirmation and missing:
        raise SystemExit("refused: the sealed regions' files are not complete, and the confirmation runs once: "
                         + "; ".join(f"{r}: {len(v)} missing ({', '.join(v[:4])}{' ...' if len(v) > 4 else ''})"
                                     for r, v in missing.items()))
    regions = [r for r in wanted if not r2.fit_ready(avail[r])]
    left_out = {r: missing[r] for r in wanted if r not in regions}
    print(f"regions: {regions}; left out: {sorted(left_out)}; confirmation run: {is_confirmation}; frozen D-a "
          f"(C3 in burning days, a = {a}) + J-S; frozen_round3.json SHA-256 ok; code hash {hash_now} "
          f"(frozen {hash_frozen})")
    assert regions, "no region has its 2012-2019 files"

    data.OUT.mkdir(parents=True, exist_ok=True)
    log = data.OUT / "confirm_runs.jsonl"
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    prov = {"commit": git("rev-parse", "HEAD"),
            "uncommitted": git("status", "--porcelain", "--", "pipeline/round3", "pipeline/tournament",
                               "pipeline/round2", "pipeline/bakeoff"),
            "frozen_path": str(args.frozen), "frozen_sha256": fz_sha, "frozen_generated": fz["champion_json"]["generated"],
            "frozen_commit_at_run": fz["champion_json"]["commit_at_run"], "code_hash_now": hash_now,
            "code_hash_frozen": hash_frozen}
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "start", "at": started, "regions": regions, "confirmation": is_confirmation,
                            "commit": prov["commit"]}) + "\n")

    T_ = {}
    t = time.time()
    Ts, pxs, cover, bd_cover = {}, [], {}, {}
    for reg in regions:
        px = data.pixels(reg, sealed_ok=is_confirmation)
        R, cover[reg] = data.rows(reg, px)
        Ts[reg] = data.burning_days(R)
        late = R[R.ym > data.FIT_LAST]
        bd_cover[reg] = {c: int(late[c].sum()) for c in ("Yb", "Vb", "V20b")}
        pxs.append(px[["region", "sensor", "date", "ym"]])
        print(f"  {reg}: {len(px):,} detections, {cover[reg]['cells']} cells, {len(R):,} rows")
    px_all = pd.concat(pxs, ignore_index=True)
    del pxs
    use_ms = {(r, y) for r in regions for y in range(2012, LAST_YEAR + 1)
              if avail[r].get(("modis", y)) and avail[r].get(("snpp", y))}
    use_sn = {(r, y) for r in regions for y in range(2018, LAST_YEAR + 1)
              if avail[r].get(("snpp", y)) and avail[r].get(("noaa20", y))}
    out = {"modis": r2.outage_days(px_all, "2012-02-01", f"{LAST_YEAR}-12-31", "modis", "snpp", usable=use_ms),
           "snpp": r2.outage_days(px_all, "2012-02-01", f"{LAST_YEAR}-12-31", "snpp", "modis", usable=use_ms),
           "snpp_vs_noaa20": r2.outage_days(px_all, "2020-01-01", f"{LAST_YEAR}-12-31", "snpp", "noaa20", usable=use_sn),
           "noaa20": r2.outage_days(px_all, "2020-01-01", f"{LAST_YEAR}-12-31", "noaa20", "snpp", usable=use_sn)}
    out["months_modis_snpp"] = sorted({x[:7] for x in out["modis"] + out["snpp"]})
    out["months_swap"] = sorted({x[:7] for x in out["snpp_vs_noaa20"] + out["noaa20"]})
    del px_all
    T_["data"] = time.time() - t

    t = time.time()
    T1, T2, SEAM, DRIFT, info = [], [], [], [], {}
    for reg in regions:
        T = Ts[reg]
        t1, mS, seam, info[reg] = test1(fz, T, avail[reg], out["months_modis_snpp"])
        g2, info2 = test2(T, avail[reg], out["months_swap"], mS)
        info[reg].update(info2)
        T1.append(t1)
        T2.append(g2)
        SEAM.append(seam)
        DRIFT.append(drift(fz, T, avail[reg], out["months_modis_snpp"], mS))
        print(f"  {reg}: tests done ({time.time() - t:.0f}s)", flush=True)
    T1, T2 = pd.concat(T1, ignore_index=True), pd.concat(T2, ignore_index=True)
    SEAM, DRIFT = pd.concat(SEAM, ignore_index=True), pd.concat(DRIFT, ignore_index=True)
    T_["tests"] = time.time() - t
    tag = "confirm" if is_confirmation else "confirm_dev"
    for name, df in (("test1_rows", T1), ("test2_region_months", T2), ("seam", SEAM), ("drift", DRIFT)):
        df.to_pickle(data.OUT / f"{tag}_{name}.pkl")

    s1 = summary1(T1)
    v1 = verdict1(s1, "D-a")
    s2 = swap_summary(T2)
    v2 = {"pass": bool(s2["counted"] > 0 and s2["share"] >= 0.80)}
    overall = "CONFIRMED" if v1["pass"] and v2["pass"] else "NOT CONFIRMED"
    failing = [n for n, ok in (("Test 1 (a) cell-month WAPE", v1["a"]), ("Test 1 (b) active-row coverage", v1["b"]),
                               ("Test 1 (c) pooled total", v1["c"]), ("Test 1 (d) national-month WAPE", v1["d"]),
                               ("Test 2 swap agreement", v2["pass"])) if not ok]
    band = DRIFT[DRIFT.year <= 2019].groupby("region").ratio.quantile([0.1, 0.5, 0.9]).unstack() if len(DRIFT) else None
    early = T2[T2.ym <= "2021-12"]
    swap_m = {"all": swap_metrics(T2), "2020-2021": swap_metrics(early),
              "per_region": {r: swap_metrics(T2[T2.region == r]) for r in regions}}
    flagged, f0_counts = f0_tail(T1, T2)
    T_["total"] = time.time() - t_all

    runs = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    res = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "started": started,
        "is_confirmation": is_confirmation, "regions": regions, "left_out": left_out, "missing": missing,
        "provenance": prov, "frozen_a": a, "cover": cover, "bd_cover": bd_cover, "outages": out, "info": info,
        "test1": {"pooled": s1, "verdict": v1, "per_region": {r: summary1(T1[T1.region == r]) for r in regions}},
        "test2": {"pooled": s2, "verdict": v2, "per_region": {r: swap_summary(T2[T2.region == r]) for r in regions},
                  "months": T2.round(3).to_dict("records")},
        "swap_metrics": swap_m,
        "f0": {"threshold": F0_SHARE, "flagged": flagged.round(3).to_dict("records"), "region_months": f0_counts,
               "test1_share": s1["f0_M"] / s1["total_M"] if s1["total_M"] else float("nan")},
        "seam": SEAM.to_dict("records"),
        "drift_band": {} if band is None else {r: band.loc[r].to_dict() for r in band.index},
        "drift": DRIFT[DRIFT.year >= 2022].to_dict("records") if len(DRIFT) else [],
        "overall": overall, "failing": failing, "timings_s": T_, "min_total": MIN_TOTAL,
        "runs_logged": [x for x in runs if x.get("confirmation") == is_confirmation],
    }
    (data.OUT / f"{tag}_results.json").write_text(json.dumps(res, indent=1, default=float))
    report = data.ROOT / "docs" / "ROUND3_CONFIRMATION.md" if is_confirmation else data.OUT / "confirm_dev_report.md"
    write_confirmation(res, report)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "finish", "at": res["generated"], "regions": regions,
                            "confirmation": is_confirmation, "overall": overall}) + "\n")
    print(json.dumps({"test1": s1, "v1": v1, "test2": s2, "swap_metrics": swap_m["all"], "f0_flagged": len(flagged),
                      "overall": overall, "failing": failing}, indent=1, default=float))
    print(f"total {T_['total']:.0f}s -> {report}")


if __name__ == "__main__":
    main()
