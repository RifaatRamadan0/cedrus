"""The frozen entrant D-a and its predictive pieces (docs/TOURNAMENT_PLAN.md, ruling added 1 Nov 2026).

D-a is the tournament's C3 (FRP-class A2-style ratios) in the burning-day unit, refitted on one region's own rows with
the frozen a from frozen_round3.json: pipeline.tournament.candidates.fit("C3", ..., setting=a). Nothing is tuned.
Every fit refuses a training row after 2019-12 (pipeline.round2.models.refuse_late, inside fit).

parts() gives what round 2's totals() takes: the row means, the row predictive variances, no parameter term of its
own (as A2 in round 2), and k, a row's mean per unit of s, so the J-S totals can carry s's bootstrap. It also gives
the f0 part of each mean: the FRP <= 0 class's own term of the class sum.
"""
import numpy as np

from pipeline.confirm.tests import moments
from pipeline.tournament.candidates import FRP_COLS, fit, forecast as c_forecast
from pipeline.tournament.data import swap_view

ENTRANT = "C3"


def frozen_a(fz):
    return fz["champion_json"]["burning_days_model"]["frozen_setting"]


def fit_frozen(fz, T, train, label):
    """D-a on the training mask with the frozen a."""
    m = fit(ENTRANT, T, train, None, None, label, setting=frozen_a(fz))
    assert m["fit"]["cols"] == FRP_COLS, m["fit"]["cols"]
    return m


def forecast(m, T, rows):
    return c_forecast(m, T, rows)


def class_means(T, rows, f):
    """Per row and FRP class, the class term m_k = V_k (a + SY_k) / (a / r0_k + SV_k) that
    pipeline.tournament.candidates.predict_class_a2 sums into the mean. V = 0 rows predict b_A and have no class
    term (all 0 here)."""
    a = f["a"]
    rmd, cmd = T.rmd.to_numpy()[rows], T.cmd.to_numpy()[rows]
    Vk = T[f["cols"]].to_numpy()[rows].astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        rate = a / f["r0"][rmd] + f["SV"][cmd]
        live = (Vk > 0) & ~np.isinf(rate)
        m_k = np.where(live, Vk * (a + f["SY"][cmd]) / np.where(live, rate, 1.0), 0.0)
    pos = T.V.to_numpy()[rows] > 0
    return np.where(pos[:, None], m_k, 0.0)


def parts(m, T, rows):
    """Row mean, NB variance, parameter variance (0), k = mean on V > 0 rows (linear in V), and the f0 part."""
    fc = forecast(m, T, rows)
    mean, var = moments(*fc)
    pos = T.V.to_numpy()[rows] > 0
    f0 = class_means(T, rows, m["fit"])[:, 0]
    return {"mean": mean, "nbvar": var, "pvar": np.zeros(len(mean)), "k": np.where(pos, mean, 0.0),
            "g": np.zeros(len(mean), int), "r_boot": None, "f0": f0, "forecast": fc}


def js_parts(m, T, rows, sfit):
    """J-S: D-a applied to the swap view (every Suomi NPP column replaced by s x the NOAA-20 column, s per
    region x day/night). k is re-expressed per unit of s, so round 2's totals() can draw s from its bootstrap."""
    S = swap_view(T, sfit)
    h = T.rd.to_numpy()[rows]
    s_row = sfit["s"][h]
    p = parts(m, S, rows)
    p["k"] = np.where(s_row > 0, p["k"] / np.where(s_row > 0, s_row, 1.0), 0.0)
    p["h"] = h
    return p
