"""Candidates A and B of docs/BAKEOFF_PLAN.md, fitted on a boolean mask of training rows.

Row table columns used: rid (region), cid (region x cell), moy, dnN (0 day, 1 night), Y, V, urow (units).
Group ids: md = month x day/night (24), rd = region x day/night, rmd = region x month x day/night.
Each predict_* returns forecasts in the form scores.score takes: (kind, a, b).
"""
import numpy as np

from .nb import fit_nb2, fit_poisson

A_GRID = [1, 3, 10, 30]
B_GRID = [0.01, 0.03, 0.1, 0.3]
G_FLOOR = 0.001


def add_groups(R, n_regions):
    R["md"] = (R.moy.to_numpy() - 1) * 2 + R.dnN.to_numpy()
    R["rd"] = R.rid.to_numpy() * 2 + R.dnN.to_numpy()
    R["rmd"] = R.rid.to_numpy() * 24 + R.md.to_numpy()
    R["cmd"] = R.cid.to_numpy() * 24 + R.md.to_numpy()
    R.attrs["n_regions"] = n_regions
    return R


def _sums(key, val, mask, n):
    return np.bincount(key[mask], val[mask], n)


# ---------------------------------------------------------------- A: Poisson-gamma shrinkage ratio
def fit_A(R, train):
    """Everything A needs except `a`: prior ratios r0, cell sums, b_A."""
    nr = R.attrs["n_regions"]
    rmd, rd, dn, cmd = (R[c].to_numpy() for c in ("rmd", "rd", "dnN", "cmd"))
    Y, V = R.Y.to_numpy().astype(float), R.V.to_numpy().astype(float)
    sy, sv = _sums(rmd, Y, train, nr * 24), _sums(rmd, V, train, nr * 24)
    sy_rd, sv_rd = _sums(rd, Y, train, nr * 2), _sums(rd, V, train, nr * 2)
    sy_d, sv_d = _sums(dn, Y, train, 2), _sums(dn, V, train, 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        r0 = sy / sv
        # fallbacks, used only where a region x month x day/night has no Suomi NPP detection in training
        g_rd = np.repeat(np.arange(nr), 24) * 2 + np.tile(np.arange(24) % 2, nr)
        fb1 = sy_rd[g_rd] / sv_rd[g_rd]
        fb2 = (sy_d / sv_d)[np.tile(np.arange(24) % 2, nr)]
    level = np.where(sv > 0, 0, np.where(sv_rd[g_rd] > 0, 1, 2))
    r0 = np.where(level == 0, r0, np.where(level == 1, fb1, fb2))
    zero_v = train & (V == 0)
    n0, y0 = np.bincount(rmd[zero_v], minlength=nr * 24), _sums(rmd, Y, zero_v, nr * 24)
    n0_rd, y0_rd = np.bincount(rd[zero_v], minlength=nr * 2), _sums(rd, Y, zero_v, nr * 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        bA = np.where(n0 > 0, y0 / n0, y0_rd[g_rd] / np.maximum(n0_rd[g_rd], 1))
    nc = int(R.cmd.max()) + 1
    return {"r0": r0, "r0_level": level, "bA": bA, "bA_fallback": n0 == 0,
            "SY": _sums(cmd, Y, train, nc), "SV": _sums(cmd, V, train, nc)}


def predict_A(R, rows, fitA, a):
    rmd, cmd = R.rmd.to_numpy()[rows], R.cmd.to_numpy()[rows]
    V = R.V.to_numpy()[rows].astype(float)
    r0 = fitA["r0"][rmd]
    shape = a + fitA["SY"][cmd]
    with np.errstate(divide="ignore"):
        rate = a / r0 + fitA["SV"][cmd]  # r0 = 0 -> infinite rate -> all mass at 0
    lam = fitA["bA"][rmd]
    pos = V > 0
    kind = np.where(pos, np.where(np.isinf(rate), 0, 2), np.where(lam > 0, 1, 0))
    fa = np.where(pos, shape, lam)
    with np.errstate(invalid="ignore"):
        fb = np.where(pos & ~np.isinf(rate), rate / (rate + V), 0.0)
    return kind, np.where(kind == 0, 0.0, fa), fb


# ---------------------------------------------------------------- B: learned detection response + NB
def unit_design(frp):
    pos = frp > 0
    return np.c_[np.ones(len(frp)), np.where(pos, np.log(np.where(pos, frp, 1.0)), 0.0), (~pos).astype(float)]


def fit_g(U, train_units):
    """Two Poisson GLMs per day/night: matched count m and chance count c on log FRP + 1[FRP <= 0]."""
    out = {}
    for dn in ("D", "N"):
        sel = train_units & (U.dn.to_numpy() == dn)
        X = unit_design(U.frp.to_numpy()[sel])
        out[dn] = {"match": fit_poisson(X, U.m.to_numpy()[sel]), "chance": fit_poisson(X, U.c.to_numpy()[sel]),
                   "units": int(sel.sum())}
    return out


def g_of(gfit, frp, dn):
    g = np.zeros(len(frp))
    for d in ("D", "N"):
        sel = dn == d
        X = unit_design(frp[sel])
        g[sel] = np.maximum(np.exp(X @ gfit[d]["match"]) - np.exp(X @ gfit[d]["chance"]), G_FLOOR)
    return g


def exposure(R, U, gfit):
    g = g_of(gfit, U.frp.to_numpy(), U.dn.to_numpy())
    return np.bincount(U.urow.to_numpy(), g, len(R))


def fit_B(R, train, E, b):
    """NB2 with offset log(E + b), month x day/night and region x day/night effects; region effects shrunk."""
    nr = R.attrs["n_regions"]
    md, rid, dn = R.md.to_numpy(), R.rid.to_numpy(), R.dnN.to_numpy()
    f2 = np.where(rid == 0, -1, (rid - 1) * 2 + dn)  # region 0 is the reference while fitting
    off = np.log(E + b)
    y = R.Y.to_numpy().astype(float)
    # collapse identical training rows into frequency weights
    key = np.c_[y[train], off[train], md[train], f2[train]]
    uniq, w = np.unique(key, axis=0, return_counts=True)
    n2 = 2 * (nr - 1)
    fit = fit_nb2(uniq[:, 0], uniq[:, 1], uniq[:, 2].astype(int), uniq[:, 3].astype(int), 24, n2, w)
    # region x day/night effects, centred per day/night (mean moved into the month terms), then shrunk
    full = np.zeros((nr, 2))
    cov_free = fit["cov"][24:, 24:]
    beta_md = fit["beta1"].copy()
    shrunk = np.zeros((nr, 2))
    eb = {}
    for d in (0, 1):
        M = np.zeros((nr, nr - 1))  # free params of this day/night -> all regions' effects
        cols = [(r - 1) * 2 + d for r in range(1, nr)]
        M[1:, :] = np.eye(nr - 1)
        C = (np.eye(nr) - 1.0 / nr) @ M
        free = fit["beta2"][cols] if nr > 1 else np.zeros(0)
        cov = C @ cov_free[np.ix_(cols, cols)] @ C.T if nr > 1 else np.zeros((1, 1))
        raw = M @ free
        centred = C @ free
        se2 = np.clip(np.diag(cov), 0, None)
        tau2 = max(0.0, float(np.var(centred) - np.mean(se2)))
        with np.errstate(invalid="ignore", divide="ignore"):
            factor = np.where(tau2 + se2 > 0, tau2 / (tau2 + se2), 0.0)
        shrunk[:, d] = centred * factor
        full[:, d] = centred
        beta_md[d::2] += raw.mean()
        eb[d] = {"tau2": tau2, "se": np.sqrt(se2), "factor": factor}
    return {"b": b, "alpha": fit["alpha"], "beta_md": beta_md, "region_raw": full, "region_shrunk": shrunk,
            "eb": eb, "fit": fit, "n_unique": len(w)}


def mu_B(R, rows, E, fitB, shrunk=True):
    eff = fitB["region_shrunk"] if shrunk else fitB["region_raw"]
    md, rid, dn = R.md.to_numpy()[rows], R.rid.to_numpy()[rows], R.dnN.to_numpy()[rows]
    return np.exp(np.log(E[rows] + fitB["b"]) + fitB["beta_md"][md] + eff[rid, dn])


def predict_B(R, rows, E, fitB):
    mu = mu_B(R, rows, E, fitB)
    th = 1.0 / fitB["alpha"]
    return np.full(len(mu), 2), np.full(len(mu), th), th / (th + mu)
