"""Folds, inner leave-one-year-out tuning, the summary scores, the bootstrap and the decision rule."""
import time

import numpy as np
import pandas as pd

from .models import A_GRID, B_GRID, exposure, fit_A, fit_B, fit_g, predict_A, predict_B
from .scores import score

BOOT = 2000
SEED = 20261031


def score_rows(kind, a, b, y):
    """scores.score on the distinct (forecast, y) combinations only, expanded back to rows."""
    key = np.c_[kind, a, b, y]
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    s = score(uniq[:, 0].astype(int), uniq[:, 1], uniq[:, 2], uniq[:, 3])
    inv = inv.ravel()
    y = np.asarray(y)
    return {"crps": s["crps"][inv], "covered": (s["q10"][inv] <= y) & (y <= s["q90"][inv]), "mean": s["mean"][inv]}


def weights(R, train):
    """w = 1 + the cell's mean Y over its training rows."""
    cid, Y = R.cid.to_numpy(), R.Y.to_numpy().astype(float)
    n = int(cid.max()) + 1
    tot, cnt = np.bincount(cid[train], Y[train], n), np.bincount(cid[train], minlength=n)
    return 1.0 + tot / np.maximum(cnt, 1)


def masks(R, U, years):
    return R.year.isin(years).to_numpy(), U.year.isin(years).to_numpy()


def inner_loyo(R, U, scored, years):
    """Choose a (A) and b (B) by leave-one-year-out inside `years`; criterion = weighted mean CRPS."""
    tabA = {a: [0.0, 0.0] for a in A_GRID}
    tabB = {b: [0.0, 0.0] for b in B_GRID}
    for i in years:
        rest = [y for y in years if y != i]
        tr, tru = masks(R, U, rest)
        rows = np.flatnonzero((R.year.to_numpy() == i) & scored)
        w = weights(R, tr)[R.cid.to_numpy()[rows]]
        y = R.Y.to_numpy()[rows]
        fA = fit_A(R, tr)
        for a in A_GRID:
            s = score_rows(*predict_A(R, rows, fA, a), y)
            tabA[a][0] += np.sum(w * s["crps"])
            tabA[a][1] += np.sum(w)
        E = exposure(R, U, fit_g(U, tru))
        for b in B_GRID:
            fB = fit_B(R, tr, E, b)
            s = score_rows(*predict_B(R, rows, E, fB), y)
            tabB[b][0] += np.sum(w * s["crps"])
            tabB[b][1] += np.sum(w)
    tabA = {a: v[0] / v[1] for a, v in tabA.items()}
    tabB = {b: v[0] / v[1] for b, v in tabB.items()}
    return min(tabA, key=tabA.get), tabA, min(tabB, key=tabB.get), tabB


def run_fold(R, U, scored, train_years, score_years, label):
    t0 = time.time()
    a, tabA, b, tabB = inner_loyo(R, U, scored, train_years)
    tr, tru = masks(R, U, train_years)
    rows = np.flatnonzero(R.year.isin(score_years).to_numpy() & scored)
    y = R.Y.to_numpy()[rows]
    fA = fit_A(R, tr)
    sA = score_rows(*predict_A(R, rows, fA, a), y)
    rmd, pos = R.rmd.to_numpy()[rows], R.V.to_numpy()[rows] > 0
    gfit = fit_g(U, tru)
    E = exposure(R, U, gfit)
    fB = fit_B(R, tr, E, b)
    sB = score_rows(*predict_B(R, rows, E, fB), y)
    out = pd.DataFrame({"row": rows, "fold": label, "w": weights(R, tr)[R.cid.to_numpy()[rows]], "Y": y,
                        "crps_A": sA["crps"], "cov_A": sA["covered"], "mean_A": sA["mean"],
                        "crps_B": sB["crps"], "cov_B": sB["covered"], "mean_B": sB["mean"]})
    info = {"fold": label, "train_years": list(train_years), "score_years": list(score_years), "a": a, "b": b,
            "inner_A": tabA, "inner_B": tabB, "alpha": fB["alpha"], "nb_converged": fB["fit"]["converged"],
            "nb_max_abs_grad": fB["fit"]["max_abs_grad"], "nb_unique_rows": fB["n_unique"],
            "tau2": {"DN"[d]: fB["eb"][d]["tau2"] for d in (0, 1)},
            "A_rows_r0_fallback": int(np.sum(pos & (fA["r0_level"][rmd] > 0))),
            "A_rows_r0_zero": int(np.sum(pos & (fA["r0"][rmd] == 0))),
            "A_rows_bA_fallback": int(np.sum(~pos & fA["bA_fallback"][rmd])),
            "seconds": round(time.time() - t0, 1)}
    return out, info


def summary(df, R):
    """All plan scores for one set of scored rows (df from run_fold, joined to the row table)."""
    out = {"rows": len(df), "Y": int(df.Y.sum())}
    keys = R.loc[df.row, ["region", "cid", "ym"]].reset_index(drop=True)
    d = pd.concat([df.reset_index(drop=True), keys], axis=1)
    active = (d.Y > 0) | (R.V.to_numpy()[d.row] > 0)
    for m in ("A", "B"):
        out[f"wcrps_{m}"] = float(np.sum(d.w * d[f"crps_{m}"]) / np.sum(d.w))
        out[f"crps_{m}"] = float(d[f"crps_{m}"].mean())
        out[f"cov_{m}"] = float(d[f"cov_{m}"].mean())
        out[f"cov_active_{m}"] = float(d.loc[active, f"cov_{m}"].mean()) if active.any() else float("nan")
        ytot = d.Y.sum()
        cm = d.groupby(["cid", "ym"])[[f"mean_{m}", "Y"]].sum()
        nm = d.groupby(["region", "ym"])[[f"mean_{m}", "Y"]].sum()
        out[f"wape_cm_{m}"] = float(np.abs(cm[f"mean_{m}"] - cm.Y).sum() / ytot) if ytot else float("nan")
        out[f"wape_row_{m}"] = float(np.abs(d[f"mean_{m}"] - d.Y).sum() / ytot) if ytot else float("nan")
        out[f"wape_nm_{m}"] = float(np.abs(nm[f"mean_{m}"] - nm.Y).sum() / ytot) if ytot else float("nan")
    out["ratio"] = out["wcrps_B"] / out["wcrps_A"]
    return out


def bootstrap(df, R):
    """Paired block bootstrap of the weighted-CRPS ratio B/A, held-out years as blocks."""
    yr = R.year.to_numpy()[df.row]
    years = sorted(set(yr))
    SA = np.array([np.sum((df.w * df.crps_A)[yr == y]) for y in years])
    SB = np.array([np.sum((df.w * df.crps_B)[yr == y]) for y in years])
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(years), (BOOT, len(years)))
    ratios = SB[idx].sum(1) / SA[idx].sum(1)
    lo, hi = np.percentile(ratios, [5, 95])
    return {"lo": float(lo), "hi": float(hi), "resamples": BOOT, "seed": SEED, "blocks": [int(y) for y in years]}


def decide(overall, boot):
    c1 = overall["ratio"] <= 0.95
    c2 = boot["hi"] < 1.00
    c3 = 0.75 <= overall["cov_B"] <= 0.85
    winner = "B" if (c1 and c2 and c3) else "A"
    return {"i_ratio_le_0.95": bool(c1), "ii_boot_upper_lt_1": bool(c2), "iii_B_coverage_0.75_0.85": bool(c3),
            "winner": winner, "coverage_miss_only": bool(c1 and c2 and not c3)}
