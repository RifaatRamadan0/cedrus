"""Folds, scores, swap stability, the headroom floor and the selection rules of docs/TOURNAMENT_PLAN.md."""
import time

import numpy as np
import pandas as pd
from scipy.stats import poisson

from pipeline.bakeoff.validate import score_rows, weights

from .candidates import SIMPLICITY, fit, forecast, mean_of
from .data import swap_view

WITHIN = 0.02  # "within 2% of the best"
BD_SKILL_GAIN = 0.10  # burning days: best skill at least 10% above the pixel champion's, in relative terms
BD_COVERAGE = (0.70, 0.90)
STOP_HEADROOM = 0.15
MIN_TOTAL = 10  # round 2's counting rule, shown for information next to the plan's median |log|


def run_job(T, scored, cand, train_years, score_years, label, sfit=None, swap_rows=None, nb=None):
    """Fit one candidate on train_years (tuning nested inside them), score score_years' rows in scored months.
    The final fit (score_years empty) instead returns the swap totals: the same fit applied to Suomi NPP and to
    s x NOAA-20 (J-S), per region-month."""
    t0 = time.time()
    yr = T.year.to_numpy()
    tr = np.isin(yr, train_years)
    m = fit(cand, T, tr, scored, list(train_years), label, nb=nb)
    info = {"cand": cand, "fold": label, "train_years": list(train_years), "score_years": list(score_years),
            "setting": m.get("setting"), "inner": m.get("inner"), "detail": describe(m)}
    out = None
    if len(score_years):
        rows = np.flatnonzero(np.isin(yr, score_years) & scored)
        y = T.Y.to_numpy()[rows]
        fc = forecast(m, T, rows)
        s = score_rows(*fc, y)
        mean = mean_of(fc)
        assert np.allclose(s["mean"], mean), f"{cand}: predictive mean disagrees with scores.score"
        out = pd.DataFrame({"row": rows, "fold": label, "w": weights(T, tr)[T.cid.to_numpy()[rows]], "Y": y,
                            "crps": s["crps"], "cov": s["covered"], "mean": mean})
    else:
        S = swap_view(T, sfit)
        mS, mN = mean_of(forecast(m, T, swap_rows)), mean_of(forecast(m, S, swap_rows))
        key = pd.DataFrame({"region": T.region.to_numpy()[swap_rows], "ym": T.ym.to_numpy()[swap_rows],
                            "tot_S": mS, "tot_N": mN, "V": T.V.to_numpy()[swap_rows].astype(float),
                            "V20": T.V20.to_numpy()[swap_rows].astype(float)})
        out = key.groupby(["region", "ym"], as_index=False).sum()
    info["seconds"] = round(time.time() - t0, 1)
    return out, info


def describe(m):
    """The fitted numbers that fit in a JSON file (for results.json and champion.json)."""
    n, d = m["name"], {}
    if n == "C0":
        d["a"] = m["r2"]["a"]
    elif n in ("C1", "C2"):
        r = m["r2"]
        d["alpha_fallback_groups"] = int(r["alpha_fallback"].sum())
        d["rows_note"] = "ratio, b and alpha per group as pipeline.round2.models.fit_ratio"
    elif n in ("C3", "C4"):
        f = m["fit"]
        d.update(a=f["a"], cols=f["cols"], em_iterations=f["em_iterations"], em_delta=f["em_delta"],
                 em_converged=f["em_converged"],
                 r0_groups_on_fallback=int((f["r0_level"] > 0).sum()))
    elif n == "C5":
        d["a"], d["a_n"] = m["setting"]
        d["mean_neighbours"] = float(np.mean(m["fit"]["n_neighbours"]))
    elif n == "C6":
        f = m["fit"]
        d.update(beta=dict(zip(f["cols"], map(float, f["beta"]))), alpha=f["alpha"], converged=f["converged"],
                 max_abs_grad=f["max_abs_grad"], iterations=f["iterations"], unique_rows=f["n_unique"],
                 region_raw=list(map(float, f["region_raw"])), region_shrunk=list(map(float, f["region_shrunk"])),
                 tau2=f["eb"]["tau2"], gamma_md=list(map(float, f["gamma"])))
    elif n == "C7":
        f = m["fit"]
        d.update(backend=f["backend"], alpha=list(map(float, f["alpha"])),
                 alpha_fallback=int(f["alpha_fallback"].sum()), inner_years=f["inner_years"])
    elif n == "C8":
        f = m["fit"]
        d.update(alpha=list(map(float, f["alpha"])), alpha_fallback=int(f["alpha_fallback"].sum()),
                 map_sizes=[len(v[0]) for v in f["maps"].values()],
                 groups_from_all_regions=sum(v != "region" for v in f["source"].values()))
    return d


def summary(df, T, cands):
    """All reported scores for one set of scored rows (per-candidate columns crps_X, cov_X, mean_X)."""
    out = {"rows": len(df), "Y": float(df.Y.sum())}
    keys = T.loc[df.row, ["region", "cid", "ym"]].reset_index(drop=True)
    d = pd.concat([df.reset_index(drop=True), keys], axis=1)
    V = T.V.to_numpy()[d.row]
    active = ((d.Y > 0).to_numpy() | (V > 0))
    vpos, vzero = active & (V > 0), active & (V == 0)
    out.update(active_rows=int(active.sum()), active_vpos=int(vpos.sum()), active_vzero=int(vzero.sum()))
    ytot = d.Y.sum()
    for m in cands:
        cov = d[f"cov_{m}"].to_numpy()
        out[f"wcrps_{m}"] = float(np.sum(d.w * d[f"crps_{m}"]) / np.sum(d.w))
        out[f"crps_{m}"] = float(d[f"crps_{m}"].mean())
        out[f"cov_active_{m}"] = float(cov[active].mean()) if active.any() else float("nan")
        out[f"cov_vpos_{m}"] = float(cov[vpos].mean()) if vpos.any() else float("nan")
        out[f"cov_vzero_{m}"] = float(cov[vzero].mean()) if vzero.any() else float("nan")
        out[f"cov_all_{m}"] = float(cov.mean())
        cm = d.groupby(["cid", "ym"])[[f"mean_{m}", "Y"]].sum()
        nm = d.groupby(["region", "ym"])[[f"mean_{m}", "Y"]].sum()
        out[f"wape_cm_{m}"] = float(np.abs(cm[f"mean_{m}"] - cm.Y).sum() / ytot) if ytot else float("nan")
        out[f"wape_nm_{m}"] = float(np.abs(nm[f"mean_{m}"] - nm.Y).sum() / ytot) if ytot else float("nan")
        out[f"total_{m}"] = float(d[f"mean_{m}"].sum())
        out[f"bias_{m}"] = out[f"total_{m}"] / ytot - 1 if ytot else float("nan")
    return out


def swap_stability(g):
    """Median |log(NOAA-20-based total / Suomi NPP-based total)| over region-months where both totals are > 0
    (the plan's metric), and the same over region-months where both are >= 10 (round 2's counting rule, information)."""
    pos = (g.tot_S > 0) & (g.tot_N > 0)
    lg = np.abs(np.log(g.tot_N[pos] / g.tot_S[pos]))
    big = (g.tot_S >= MIN_TOTAL) & (g.tot_N >= MIN_TOTAL)
    lb = np.abs(np.log(g.tot_N[big] / g.tot_S[big]))
    return {"region_months": int(len(g)), "used": int(pos.sum()), "median_abs_log": float(np.median(lg)) if len(lg) else float("nan"),
            "used_ge10": int(big.sum()), "median_abs_log_ge10": float(np.median(lb)) if len(lb) else float("nan"),
            "sum_S": float(g.tot_S.sum()), "sum_N": float(g.tot_N.sum())}


def poisson_floor(mu):
    """E_{y ~ Pois(mu)} CRPS(Pois(mu), y) = sum_k F(k) (1 - F(k)), summed to the 1 - 1e-12 quantile + 1.
    The CRPS is pipeline/bakeoff/scores.py's sum over k of (F(k) - 1[y <= k])^2."""
    mu = np.asarray(mu, float)
    u, inv = np.unique(mu, return_inverse=True)
    out = np.zeros(len(u))
    live = np.flatnonzero(u > 0)
    if len(live):
        K = poisson.ppf(1 - 1e-12, u[live]).astype(np.int64) + 1
        L = K + 1
        idx = np.repeat(np.arange(len(live)), L)
        kk = np.arange(len(idx)) - np.repeat(np.cumsum(L) - L, L)
        F = poisson.cdf(kk, u[live][idx])
        out[live] = np.bincount(idx, F * (1 - F), len(live))
    return out[inv.ravel()]


def headroom(df, mean_col, crps_col):
    """(champion weighted CRPS - Poisson floor) / champion weighted CRPS, weighted as the primary score."""
    fl = poisson_floor(df[mean_col].to_numpy())
    w = df.w.to_numpy()
    c = float(np.sum(w * df[crps_col]) / np.sum(w))
    f = float(np.sum(w * fl) / np.sum(w))
    return {"wcrps": c, "floor": f, "headroom": (c - f) / c if c else float("nan"), "below_stop": bool((c - f) / c < STOP_HEADROOM)}


def select_pixel(overall, cands):
    """The simplest candidate within 2% of the best pooled weighted CRPS, in the plan's simplicity order."""
    best = min(cands, key=lambda m: overall[f"wcrps_{m}"])
    bar = overall[f"wcrps_{best}"] * (1 + WITHIN)
    clauses = [{"model": m, "wcrps": overall[f"wcrps_{m}"], "ratio_to_best": overall[f"wcrps_{m}"] / overall[f"wcrps_{best}"],
                "within": bool(overall[f"wcrps_{m}"] <= bar)} for m in SIMPLICITY if m in cands]
    chosen = next(c["model"] for c in clauses if c["within"])
    return {"best": best, "bar": bar, "clauses": clauses, "chosen": chosen}


def best_two(overall, cands):
    """The two lowest pooled weighted CRPS among C0-C8 (ties to the simpler)."""
    return sorted(cands, key=lambda m: (overall[f"wcrps_{m}"], SIMPLICITY.index(m)))[:2]


def skill(wcrps, wcrps_r1):
    return 1 - wcrps / wcrps_r1


def decide_unit(px_skill, px_swap, bd):
    """Burning days are primary only if its best skill (i) beats the pixel champion's by >= 10% relative,
    (ii) its swap stability is at least as good (median |log| not larger), (iii) its active-row coverage is in
    0.70..0.90. bd: {name: {"skill", "swap", "cov_active"}} for D-a and D-b."""
    best = max(bd, key=lambda k: bd[k]["skill"])
    b = bd[best]
    c1 = b["skill"] >= px_skill * (1 + BD_SKILL_GAIN) if px_skill > 0 else b["skill"] > px_skill
    c2 = b["swap"] <= px_swap
    c3 = BD_COVERAGE[0] <= b["cov_active"] <= BD_COVERAGE[1]
    return {"best_bd": best, "bd_skill": b["skill"], "px_skill": px_skill, "needed_skill": px_skill * (1 + BD_SKILL_GAIN),
            "i_skill": bool(c1), "bd_swap": b["swap"], "px_swap": px_swap, "ii_swap": bool(c2),
            "bd_cov_active": b["cov_active"], "iii_coverage": bool(c3), "primary": "burning days" if (c1 and c2 and c3)
            else "hotspots (pixels)", "bd_secondary_view_allowed": not (c1 and c2 and c3)}
