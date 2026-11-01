"""Folds, scores and the two selection rules of docs/ROUND2_PLAN.md (selection on development regions only)."""
import time

import numpy as np
import pandas as pd
from scipy.stats import norm

from pipeline.bakeoff.validate import score_rows, weights

from .models import MODELS, fit_model, forecast, fit_s, js_parts, parts, rng_for, totals

Z80 = float(norm.ppf(0.9))  # central 80% interval of a total: mean +/- 1.2816 sd
MIN_TOTAL = 10
WITHIN = 0.02  # "within 2% of the best"


def run_fold(R, scored, train_years, score_years, label):
    """Fit R1, Rm and A2 on train_years (A2's a by inner leave-one-year-out inside them); score score_years."""
    t0 = time.time()
    yr = R.year.to_numpy()
    tr = np.isin(yr, train_years)
    rows = np.flatnonzero(np.isin(yr, score_years) & scored)
    y = R.Y.to_numpy()[rows]
    out = pd.DataFrame({"row": rows, "fold": label, "w": weights(R, tr)[R.cid.to_numpy()[rows]], "Y": y})
    info = {"fold": label, "train_years": list(train_years), "score_years": list(score_years)}
    for name in MODELS:
        m = fit_model(name, R, tr, rng_for("fold", label, name), inner_years=train_years, scored=scored)
        s = score_rows(*forecast(m, R, rows), y)
        p = parts(m, R, rows)
        assert np.allclose(s["mean"], p["mean"]), f"{name}: predictive mean disagrees with scores.score"
        out[f"crps_{name}"], out[f"cov_{name}"], out[f"mean_{name}"] = s["crps"], s["covered"], p["mean"]
        if name == "A2":
            info["a"], info["inner_A2"] = m["a"], m["inner"]
            rmd, pos = R.rmd.to_numpy()[rows], R.V.to_numpy()[rows] > 0
            info["A2_rows_r0_fallback"] = int(np.sum(pos & (m["fit"]["r0_level"][rmd] > 0)))
            info["A2_rows_r0_zero"] = int(np.sum(pos & (m["fit"]["r0"][rmd] == 0)))
        else:
            g = R.rmd.to_numpy()[rows] if m["per_month"] else R.rd.to_numpy()[rows]
            pos = R.V.to_numpy()[rows] > 0
            info[f"{name}_rows_r_fallback"] = int(np.sum(pos & (m["r_level"][g] > 0)))
            info[f"{name}_rows_b_fallback"] = int(np.sum(~pos & (m["b_level"][g] > 0)))
            info[f"{name}_alpha"] = [float(x) for x in m["alpha"]]
            info[f"{name}_alpha_fallback"] = int(m["alpha_fallback"].sum())
    info["seconds"] = round(time.time() - t0, 1)
    return out, info


def summary(df, R, models=MODELS):
    """All reported scores for one set of scored rows (df from run_fold, joined to the row table)."""
    out = {"rows": len(df), "Y": int(df.Y.sum())}
    keys = R.loc[df.row, ["region", "cid", "ym"]].reset_index(drop=True)
    d = pd.concat([df.reset_index(drop=True), keys], axis=1)
    active = ((d.Y > 0) | (R.V.to_numpy()[d.row] > 0)).to_numpy()
    out["active_rows"] = int(active.sum())
    ytot = d.Y.sum()
    for m in models:
        out[f"wcrps_{m}"] = float(np.sum(d.w * d[f"crps_{m}"]) / np.sum(d.w))
        out[f"crps_{m}"] = float(d[f"crps_{m}"].mean())
        out[f"cov_active_{m}"] = float(d.loc[active, f"cov_{m}"].mean()) if active.any() else float("nan")
        out[f"cov_all_{m}"] = float(d[f"cov_{m}"].mean())
        cm = d.groupby(["cid", "ym"])[[f"mean_{m}", "Y"]].sum()
        nm = d.groupby(["region", "ym"])[[f"mean_{m}", "Y"]].sum()
        out[f"wape_cm_{m}"] = float(np.abs(cm[f"mean_{m}"] - cm.Y).sum() / ytot) if ytot else float("nan")
        out[f"wape_nm_{m}"] = float(np.abs(nm[f"mean_{m}"] - nm.Y).sum() / ytot) if ytot else float("nan")
        out[f"total_{m}"] = float(d[f"mean_{m}"].sum())
        out[f"bias_{m}"] = out[f"total_{m}"] / ytot - 1 if ytot else float("nan")
    return out


def select(overall):
    """The simplest candidate whose pooled weighted CRPS is within 2% of the best (order R1 < Rm < A2)."""
    best = min(MODELS, key=lambda m: overall[f"wcrps_{m}"])
    bar = overall[f"wcrps_{best}"] * (1 + WITHIN)
    clauses = [{"model": m, "wcrps": overall[f"wcrps_{m}"], "ratio_to_best": overall[f"wcrps_{m}"] / overall[f"wcrps_{best}"],
                "within": bool(overall[f"wcrps_{m}"] <= bar)} for m in MODELS]
    chosen = next(c["model"] for c in clauses if c["within"])
    return {"best": best, "bar": bar, "clauses": clauses, "chosen": chosen}


def region_month_units(R, rows):
    """Region-month index of each row, and the (region, ym) table of the units."""
    key = R.region.to_numpy()[rows].astype(object) + "|" + R.ym.to_numpy()[rows].astype(object)
    unit, labels = pd.factorize(key)
    lab = pd.Series(labels).str.split("|", expand=True)
    return unit, pd.DataFrame({"region": lab[0], "ym": lab[1]})


def swap_table(R, rows, mS, mN, sfit=None):
    """Region-month totals from Suomi NPP (model mS) and from NOAA-20 (J-M: mN fitted on V20; J-S: mS on s * V20),
    each with its 80% interval; counted if both totals >= 10; agree if the intervals overlap."""
    unit, g = region_month_units(R, rows)
    n = len(g)
    pS = parts(mS, R, rows)
    tS, nbS, pvS = totals(pS, unit, n)
    if sfit is None:
        pN = parts(mN, R, rows)
        tN, nbN, pvN = totals(pN, unit, n)
    else:
        pN = js_parts(mS, R, rows, sfit)
        tN, nbN, pvN = totals(pN, unit, n, sfit["s_boot"])
    g["tot_S"], g["nbvar_S"], g["pvar_S"] = tS, nbS, pvS
    g["tot_N"], g["nbvar_N"], g["pvar_N"] = tN, nbN, pvN
    for m in ("S", "N"):
        sd = np.sqrt(g[f"nbvar_{m}"] + g[f"pvar_{m}"])
        g[f"lo_{m}"], g[f"hi_{m}"] = g[f"tot_{m}"] - Z80 * sd, g[f"tot_{m}"] + Z80 * sd
    g["V"] = np.bincount(unit, R.V.to_numpy()[rows], n)
    g["V20"] = np.bincount(unit, R.V20.to_numpy()[rows], n)
    g["counted"] = (g.tot_S >= MIN_TOTAL) & (g.tot_N >= MIN_TOTAL)
    g["agree"] = (g.lo_S <= g.hi_N) & (g.lo_N <= g.hi_S)
    return g


def swap_summary(g):
    c = g[g.counted]
    return {"region_months": len(g), "counted": len(c), "agree": int(c.agree.sum()),
            "share": float(c.agree.mean()) if len(c) else float("nan")}


def choose_n20(js, jm):
    """J-S if its agreement is greater than or equal to J-M's; otherwise J-M."""
    a, b = js["share"], jm["share"]
    return {"J-S": a, "J-M": b, "js_ge_jm": bool(a >= b), "chosen": "J-S" if a >= b else "J-M"}


def fit_n20(name, R, train_s, train_n, scored, label, a=None):
    """The chosen Suomi NPP model on train_s, J-M (same method on NOAA-20) and s for J-S on train_n."""
    yrs_s = sorted(set(R.year.to_numpy()[train_s]))
    yrs_n = sorted(set(R.year.to_numpy()[train_n]))
    mS = fit_model(name, R, train_s, rng_for(label, "S", name), a=a, inner_years=yrs_s, scored=scored)
    mN = fit_model(name, R, train_n, rng_for(label, "J-M", name), vcol="V20", inner_years=yrs_n, scored=scored)
    sfit = fit_s(R, train_n, rng_for(label, "J-S"))
    return mS, mN, sfit
