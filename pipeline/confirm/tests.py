"""Test 1, Test 2 and the two report-only checks of docs/CONFIRMATION_PLAN.md, for one region.

Model A is the bake-off's own code (pipeline.bakeoff.models.fit_A / predict_A), a = 30, nothing tuned.
Each region is fitted on its own rows only.
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

from pipeline.bakeoff.models import add_groups, fit_A, predict_A
from pipeline.bakeoff.validate import score_rows, weights

A = 30
Z80 = float(norm.ppf(0.9))  # central 80% interval from a summed variance: mean +/- 1.2816 sd
TEST1_YEARS = [2020, 2021]
TEST2_YEARS = list(range(2020, 2026))
DRIFT_YEARS = [2022, 2023, 2024, 2025]
N20_FIT = ("2018-04", "2019-12")
MIN_TOTAL = 10


def moments(kind, a, b):
    """Predictive mean and variance of A's forecasts (0 = all mass at 0, 1 = Poisson, 2 = NB)."""
    kind, a, b = np.asarray(kind), np.asarray(a, float), np.asarray(b, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        nb_mean, nb_var = a * (1 - b) / b, a * (1 - b) / b ** 2
    mean = np.where(kind == 1, a, np.where(kind == 2, nb_mean, 0.0))
    var = np.where(kind == 1, a, np.where(kind == 2, nb_var, 0.0))
    return mean, var


def prepare(R):
    R = R.reset_index(drop=True).copy()
    R["rid"] = 0
    R["cid"] = pd.factorize(R.cell)[0]
    R["dnN"] = (R.dn == "N").astype(int)
    return add_groups(R, 1)


def test1(R, bad_months):
    """Fit on 2012-02..2019-12, score 2020-2021 rows (months with an outage day left out)."""
    tr = (R.ym <= "2019-12").to_numpy()
    fA = fit_A(R, tr)
    rows = np.flatnonzero(R.year.isin(TEST1_YEARS).to_numpy() & ~R.ym.isin(bad_months).to_numpy())
    y = R.Y.to_numpy()[rows]
    k, a, b = predict_A(R, rows, fA, A)
    s = score_rows(k, a, b, y)
    mean, var = moments(k, a, b)
    assert np.allclose(mean, s["mean"]), "predictive mean disagrees with scores.score"
    V = R.V.to_numpy()
    sy = np.bincount(R.dnN.to_numpy()[tr], R.Y.to_numpy()[tr], 2)
    sv = np.bincount(R.dnN.to_numpy()[tr], V[tr], 2)
    ratio = np.where(sv > 0, sy / np.where(sv > 0, sv, 1), 0.0)  # F1: one ratio per day/night
    out = R.iloc[rows][["region", "cell", "ym", "year", "dn"]].reset_index(drop=True)
    out["Y"], out["V"] = y, V[rows]
    out["w"] = weights(R, tr)[R.cid.to_numpy()[rows]]
    out["crps"], out["covered"], out["mean_A"], out["var_A"] = s["crps"], s["covered"], mean, var
    out["mean_F0"] = V[rows].astype(float)
    out["mean_F1"] = V[rows] * ratio[R.dnN.to_numpy()[rows]]
    out["active"] = (out.Y > 0) | (out.V > 0)
    info = {"a": A, "F1_ratio": {"D": float(ratio[0]), "N": float(ratio[1])},
            "rows_r0_zero": int(np.sum((out.V > 0) & (fA["r0"][R.rmd.to_numpy()[rows]] == 0)))}
    return out, fA, info


def test2(R, bad_months):
    """Suomi NPP fit (2012-02..2019-12) and NOAA-20 fit (2018-04..2019-12); region-month totals 2020-2025."""
    trS = (R.ym <= "2019-12").to_numpy()
    R20 = R.copy()
    R20["V"] = R.V20
    trN = ((R.ym >= N20_FIT[0]) & (R.ym <= N20_FIT[1])).to_numpy()
    fS, fN = fit_A(R, trS), fit_A(R20, trN)
    rows = np.flatnonzero(R.year.isin(TEST2_YEARS).to_numpy() & ~R.ym.isin(bad_months).to_numpy())
    mS, vS = moments(*predict_A(R, rows, fS, A))
    mN, vN = moments(*predict_A(R20, rows, fN, A))
    d = pd.DataFrame({"ym": R.ym.to_numpy()[rows], "tot_S": mS, "var_S": vS, "tot_N": mN, "var_N": vN,
                      "V": R.V.to_numpy()[rows], "V20": R.V20.to_numpy()[rows]})
    g = d.groupby("ym").sum().reset_index()
    for m in ("S", "N"):
        sd = np.sqrt(g[f"var_{m}"])
        g[f"lo_{m}"], g[f"hi_{m}"] = g[f"tot_{m}"] - Z80 * sd, g[f"tot_{m}"] + Z80 * sd
    g["counted"] = (g.tot_S >= MIN_TOTAL) & (g.tot_N >= MIN_TOTAL)
    g["agree"] = (g.lo_S <= g.hi_N) & (g.lo_N <= g.hi_S)
    g.insert(0, "region", R.region.iloc[0])
    return g


def seam(t1):
    """Harmonized / observed MODIS annual totals, 2020 and 2021, with the 80% interval."""
    g = t1.groupby(["region", "year"])[["mean_A", "var_A", "Y"]].sum().reset_index()
    sd = np.sqrt(g.var_A)
    g["lo"], g["hi"] = g.mean_A - Z80 * sd, g.mean_A + Z80 * sd
    return g


def drift(R, fA, bad_months):
    """Monthly observed MODIS / A-predicted, 2022-2025, against the band of the same ratio in 2012-2019.

    The 2012-2019 ratios are leave-one-year-out (A refitted without that year), so both sides are out of sample.
    Only months whose predicted total is >= 10 are used; months with an outage day are left out.
    """
    ok = ~R.ym.isin(bad_months).to_numpy()
    parts = []
    for y in range(2012, 2020):
        tr = (R.ym <= "2019-12").to_numpy() & (R.year.to_numpy() != y)
        rows = np.flatnonzero((R.year.to_numpy() == y) & ok)
        m, _ = moments(*predict_A(R, rows, fit_A(R, tr), A))
        parts.append(pd.DataFrame({"ym": R.ym.to_numpy()[rows], "pred": m, "Y": R.Y.to_numpy()[rows]}))
    rows = np.flatnonzero(R.year.isin(DRIFT_YEARS).to_numpy() & ok)
    m, _ = moments(*predict_A(R, rows, fA, A))
    parts.append(pd.DataFrame({"ym": R.ym.to_numpy()[rows], "pred": m, "Y": R.Y.to_numpy()[rows]}))
    g = pd.concat(parts).groupby("ym").sum().reset_index()
    g = g[g.pred >= MIN_TOTAL].copy()
    g["ratio"] = g.Y / g.pred
    g["year"] = g.ym.str[:4].astype(int)
    g.insert(0, "region", R.region.iloc[0])
    return g
