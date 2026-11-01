"""Candidates R1, Rm and A2 of docs/ROUND2_PLAN.md, the NOAA-20 ratio s, and their predictive moments.

Row table columns used: rid, cid, moy, dnN, Y, V (Suomi NPP), V20 (NOAA-20), ym, year; group ids from
pipeline.bakeoff.models.add_groups (rd = region x day/night, rmd = region x calendar month x day/night).
Every fit takes a boolean mask of training rows and refuses any row after 2019-12.

R1 / Rm: r = sum Y / sum V over training rows with V > 0 (per rd, or per rmd for Rm); rows with V = 0 predict b, the
mean Y of training rows with V = 0 (same grouping). alpha by maximum likelihood per rd with the means held fixed.
Var(r) from a year-block bootstrap of r inside the training rows. A row's predictive variance is
NB variance + V^2 Var(r); its predictive distribution is the negative binomial with that mean and variance.
A2: A of the bake-off with the ratio sums (prior r0 and the cell sums) taken over rows with V > 0 only.
"""
import zlib

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import gammaln

from pipeline.bakeoff.models import fit_A, predict_A
from pipeline.confirm.tests import moments as a_moments

from .data import FIT_LAST

BOOT = 200
SEED = 20261101
A2_GRID = [10, 30, 100, 300, 1000]
LOG_ALPHA_BOUNDS = (-20.0, 6.0)  # as pipeline/bakeoff/nb.py
MODELS = ["R1", "Rm", "A2"]  # simplicity order


def refuse_late(R, train):
    """No fit may see a row after 2019-12 (the swap window is scored, never fitted)."""
    late = np.asarray(train, bool) & (R.ym.to_numpy() > FIT_LAST)
    if late.any():
        raise ValueError(f"fit refused: {int(late.sum())} training rows after {FIT_LAST}")


def rng_for(*key):
    """A reproducible generator per fit: the seed plus a key such as ("fold", "2014", "R1")."""
    return np.random.default_rng([SEED] + [zlib.crc32(str(k).encode()) for k in key])


def nb_from_moments(mean, var):
    """(kind, a, b) for scores.score: the negative binomial with this mean and variance.
    mean 0 -> all mass at 0; variance not above the mean -> Poisson(mean)."""
    mean, var = np.asarray(mean, float), np.asarray(var, float)
    nb = (mean > 0) & (var > mean * (1 + 1e-9))
    kind = np.where(mean > 0, np.where(nb, 2, 1), 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        size = np.where(nb, mean ** 2 / (var - mean), 0.0)
        p = np.where(nb, mean / var, 0.0)
    return kind, np.where(kind == 2, size, np.where(kind == 1, mean, 0.0)), p


# ---------------------------------------------------------------- the dispersion, means held fixed
def nb_negloglik_alpha(log_alpha, y, mu, w):
    th = np.exp(-log_alpha)
    ll = (gammaln(y + th) - gammaln(th) - gammaln(y + 1) + th * np.log(th / (th + mu))
          + y * np.log(mu / (th + mu)))
    return -np.sum(w * ll)


def fit_alpha(y, mu):
    """Maximum-likelihood alpha of NB2 (var = mu + alpha mu^2) with every mean fixed. Rows with mu = 0 carry no
    information (in sample they all have y = 0) and are dropped. Identical (y, mu) rows are collapsed."""
    keep = mu > 0
    if not keep.any():
        return float("nan")
    u, w = np.unique(np.c_[y[keep], mu[keep]], axis=0, return_counts=True)
    res = minimize_scalar(nb_negloglik_alpha, bounds=LOG_ALPHA_BOUNDS, method="bounded",
                          args=(u[:, 0], u[:, 1], w.astype(float)), options={"xatol": 1e-6})
    return float(np.exp(res.x))


# ---------------------------------------------------------------- ratio models R1 and Rm
def _groups(R, per_month):
    """Row -> group id, number of groups, group -> region x day/night, group -> day/night."""
    nr = R.attrs["n_regions"]
    if per_month:
        g, ng = R.rmd.to_numpy(), nr * 24
        g_rd = (np.arange(ng) // 24) * 2 + np.arange(ng) % 2
    else:
        g, ng = R.rd.to_numpy(), nr * 2
        g_rd = np.arange(ng)
    return g, ng, g_rd, np.arange(ng) % 2


def _chain(num, den, g_rd, g_d):
    """num/den per group, falling back to region x day/night, then all regions x day/night.
    Works on (groups,) or (resamples, groups). Returns (value, level); level 3 = nothing to fall back on (value 0)."""
    nrd = int(g_rd.max()) + 1
    M_rd = np.zeros((len(g_rd), nrd))
    M_rd[np.arange(len(g_rd)), g_rd] = 1
    M_d = np.zeros((len(g_rd), 2))
    M_d[np.arange(len(g_rd)), g_d] = 1
    num_rd, den_rd = (num @ M_rd)[..., g_rd], (den @ M_rd)[..., g_rd]
    num_d, den_d = (num @ M_d)[..., g_d], (den @ M_d)[..., g_d]
    level = np.where(den > 0, 0, np.where(den_rd > 0, 1, np.where(den_d > 0, 2, 3)))
    with np.errstate(divide="ignore", invalid="ignore"):
        val = np.where(level == 0, num / den, np.where(level == 1, num_rd / den_rd,
                                                       np.where(level == 2, num_d / den_d, 0.0)))
    return val, level


def _block_sums(block, g, ng, vals, mask):
    """Per (block, group) sums of each array in vals over mask rows; blocks = sorted unique block labels."""
    labels, b = np.unique(block[mask], return_inverse=True)
    key = b * ng + g[mask]
    return labels, [np.bincount(key, v[mask], len(labels) * ng).reshape(len(labels), ng) for v in vals]


def _resample(rng, n_blocks, n_boot):
    """Block counts of n_boot resamples with replacement: (n_boot, n_blocks)."""
    idx = rng.integers(0, n_blocks, (n_boot, n_blocks))
    counts = np.zeros((n_boot, n_blocks))
    np.add.at(counts, (np.repeat(np.arange(n_boot), n_blocks), idx.ravel()), 1)
    return counts


def fit_ratio(R, train, per_month, rng, vcol="V", n_boot=BOOT):
    """R1 (per_month False) or Rm (True), against MODIS, with V taken from column vcol."""
    refuse_late(R, train)
    train = np.asarray(train, bool)
    g, ng, g_rd, g_d = _groups(R, per_month)
    Y, V = R.Y.to_numpy().astype(float), R[vcol].to_numpy().astype(float)
    pos, zero = train & (V > 0), train & (V == 0)
    sy, sv = np.bincount(g[pos], Y[pos], ng), np.bincount(g[pos], V[pos], ng)
    r, r_level = _chain(sy, sv, g_rd, g_d)
    by, bn = np.bincount(g[zero], Y[zero], ng), np.bincount(g[zero], minlength=ng).astype(float)
    b, b_level = _chain(by, bn, g_rd, g_d)
    # year-block bootstrap of r over the training years
    years, (SYb, SVb) = _block_sums(R.year.to_numpy(), g, ng, (Y, V), pos)
    counts = _resample(rng, len(years), n_boot)
    r_boot, _ = _chain(counts @ SYb, counts @ SVb, g_rd, g_d)
    var_r = r_boot.var(axis=0, ddof=1)
    # alpha per region x day/night, means held at their fitted values
    mu = np.where(V > 0, r[g] * V, b[g])
    rd = R.rd.to_numpy()
    nrd = R.attrs["n_regions"] * 2
    alpha = np.full(nrd, np.nan)
    for k in range(nrd):
        sel = train & (rd == k)
        if sel.any():
            alpha[k] = fit_alpha(Y[sel], mu[sel])
    alpha_fallback = np.isnan(alpha)
    for d in (0, 1):  # a region x day/night with no informative row takes the alpha of all regions' rows
        if alpha_fallback[d::2].any():
            sel = train & (R.dnN.to_numpy() == d)
            alpha[d::2] = np.where(alpha_fallback[d::2], fit_alpha(Y[sel], mu[sel]), alpha[d::2])
    return {"model": "Rm" if per_month else "R1", "vcol": vcol, "per_month": per_month,
            "r": r, "r_level": r_level, "r_boot": r_boot, "var_r": var_r, "b": b, "b_level": b_level,
            "alpha": alpha, "alpha_fallback": alpha_fallback, "boot_blocks": [int(y) for y in years],
            "n_boot": n_boot}


def ratio_parts(R, rows, fit, V=None):
    """Per-row predictive parts of R1 / Rm. V defaults to the fit's own column (s * V20 is passed for J-S).
    Returns mean, NB variance, parameter variance V^2 Var(r), and the pieces the totals' bootstrap needs:
    k (the row's mean per unit of r) and g (its r group); rows with V = 0 have k = 0 and a fixed mean b."""
    g_all, _, _, _ = _groups(R, fit["per_month"])
    g = g_all[rows]
    V = R[fit["vcol"]].to_numpy()[rows].astype(float) if V is None else np.asarray(V, float)
    pos = V > 0
    mean = np.where(pos, fit["r"][g] * V, fit["b"][g])
    al = fit["alpha"][R.rd.to_numpy()[rows]]
    return {"mean": mean, "nbvar": mean + al * mean ** 2, "pvar": np.where(pos, V ** 2 * fit["var_r"][g], 0.0),
            "k": np.where(pos, V, 0.0), "g": g, "r_boot": fit["r_boot"]}


# ---------------------------------------------------------------- A2
def _with_v(R, vcol, V=None):
    if vcol == "V" and V is None:
        return R
    Rv = R.assign(V=R[vcol].to_numpy() if V is None else V)
    Rv.attrs.update(R.attrs)
    return Rv


def fit_A2(R, train, vcol="V"):
    """A's sums over rows with V > 0 only; b (V = 0 rows) exactly as A's b_A."""
    refuse_late(R, train)
    Rv = _with_v(R, vcol)
    Rpos = Rv.assign(Y=np.where(Rv.V.to_numpy() > 0, Rv.Y.to_numpy(), 0))
    Rpos.attrs.update(R.attrs)
    f = fit_A(Rpos, train)
    full = fit_A(Rv, train)
    f["bA"], f["bA_fallback"] = full["bA"], full["bA_fallback"]
    f["vcol"] = vcol
    return f


def predict_A2(R, rows, f, a, V=None):
    """A's forecast (kind, a, b) on V from the fit's column, or on the V given for every row (J-S passes s * V20)."""
    if V is None:
        return predict_A(_with_v(R, f["vcol"]), rows, f, a)
    full = np.zeros(len(R))
    full[rows] = V
    return predict_A(_with_v(R, f["vcol"], full), rows, f, a)


def a2_parts(R, rows, f, a, V=None):
    k_, a_, b_ = predict_A2(R, rows, f, a, V)
    mean, var = a_moments(k_, a_, b_)
    Vr = R[f["vcol"]].to_numpy()[rows].astype(float) if V is None else np.asarray(V, float)
    pos = (Vr > 0) & (k_ == 2)
    return {"mean": mean, "nbvar": var, "pvar": np.zeros(len(mean)), "k": np.where(pos, mean, 0.0),
            "g": np.zeros(len(mean), int), "r_boot": None, "forecast": (k_, a_, b_)}


# ---------------------------------------------------------------- NOAA-20 to Suomi NPP: s
def fit_s(R, train, rng, n_boot=BOOT):
    """s = sum V_SNPP / sum V_N20 per region x day/night over the training rows; month-block bootstrap."""
    refuse_late(R, train)
    train = np.asarray(train, bool)
    g, ng, g_rd, g_d = _groups(R, False)
    V, V20 = R.V.to_numpy().astype(float), R.V20.to_numpy().astype(float)
    s, level = _chain(np.bincount(g[train], V[train], ng), np.bincount(g[train], V20[train], ng), g_rd, g_d)
    months, (SV, SV20) = _block_sums(R.ym.to_numpy(), g, ng, (V, V20), train)
    counts = _resample(rng, len(months), n_boot)
    s_boot, _ = _chain(counts @ SV, counts @ SV20, g_rd, g_d)
    return {"s": s, "s_level": level, "s_boot": s_boot, "var_s": s_boot.var(axis=0, ddof=1),
            "boot_blocks": list(months), "n_boot": n_boot}


# ---------------------------------------------------------------- one interface for the chosen model
def fit_model(name, R, train, rng, vcol="V", a=None, inner_years=None, scored=None):
    """Fit R1, Rm or A2. A2 takes `a` if given, otherwise chooses it by leave-one-year-out over inner_years."""
    if name in ("R1", "Rm"):
        return fit_ratio(R, train, name == "Rm", rng, vcol)
    tab = None
    if a is None:
        a, tab = tune_a2(R, scored, inner_years, vcol, base=train)
    return {"model": "A2", "vcol": vcol, "fit": fit_A2(R, train, vcol), "a": a, "inner": tab}


def parts(m, R, rows, V=None):
    if m["model"] == "A2":
        return a2_parts(R, rows, m["fit"], m["a"], V)
    return ratio_parts(R, rows, m, V)


def forecast(m, R, rows):
    """(kind, a, b) predictive distribution of each row, for CRPS and coverage."""
    if m["model"] == "A2":
        return predict_A2(R, rows, m["fit"], m["a"])
    p = ratio_parts(R, rows, m)
    return nb_from_moments(p["mean"], p["nbvar"] + p["pvar"])


def tune_a2(R, scored, years, vcol="V", base=None):
    """a from A2_GRID by leave-one-year-out inside `years` (rows of `base` only): weighted mean CRPS,
    ties to the smaller a."""
    from pipeline.bakeoff.validate import score_rows, weights

    tab = {a: [0.0, 0.0] for a in A2_GRID}
    yr = R.year.to_numpy()
    for i in years:
        inside = np.ones(len(R), bool) if base is None else np.asarray(base, bool)
        tr = inside & np.isin(yr, [y for y in years if y != i])
        rows = np.flatnonzero(inside & (yr == i) & scored)
        if not len(rows):
            continue
        w = weights(R, tr)[R.cid.to_numpy()[rows]]
        y = R.Y.to_numpy()[rows]
        f = fit_A2(R, tr, vcol)
        for a in A2_GRID:
            s = score_rows(*predict_A2(R, rows, f, a), y)
            tab[a][0] += np.sum(w * s["crps"])
            tab[a][1] += np.sum(w)
    tab = {a: v[0] / v[1] for a, v in tab.items()}
    return min(A2_GRID, key=lambda a: (tab[a], a)), tab


def js_parts(m, R, rows, sfit):
    """J-S: the Suomi NPP model applied to s * V20, s per region x day/night. k is re-expressed per unit of
    r * s, so the totals' bootstrap can draw r and s together."""
    h = R.rd.to_numpy()[rows]
    s_row = sfit["s"][h]
    p = parts(m, R, rows, s_row * R.V20.to_numpy()[rows].astype(float))
    p["k"] = np.where(s_row > 0, p["k"] / np.where(s_row > 0, s_row, 1.0), 0.0)
    p["h"] = h
    return p


def totals(p, unit, n_units, s_boot=None):
    """Sum of row means per unit (e.g. region-month) and its variance: the summed NB variances plus the
    parameter variance of the sum over the bootstrap replicates (r for R1 / Rm, s for J-S, drawn with the same
    replicate index). Rows that share a parameter move together, so this is the variance of the sum itself.
    A row's mean is const + k * r[g] * s[h]; its replicate mean is const + k * r*[g] * s*[h]."""
    mean = np.bincount(unit, p["mean"], n_units)
    nbvar = np.bincount(unit, p["nbvar"], n_units)
    rb = p["r_boot"]
    live = np.flatnonzero(p["k"] > 0)
    if (rb is None and s_boot is None) or not len(live):
        return mean, nbvar, np.zeros(n_units)
    g = p["g"][live] if rb is not None else np.zeros(len(live), int)
    h = p["h"][live] if s_boot is not None else np.zeros(len(live), int)
    ent, inv = np.unique(np.c_[unit[live], g, h], axis=0, return_inverse=True)
    K = np.bincount(inv.ravel(), p["k"][live], len(ent))
    theta = 1.0
    if rb is not None:
        theta = theta * rb[:, ent[:, 1]]
    if s_boot is not None:
        theta = theta * s_boot[:, ent[:, 2]]
    M = np.zeros((len(ent), n_units))
    M[np.arange(len(ent)), ent[:, 0]] = 1
    reps = (theta * K) @ M
    return mean, nbvar, reps.var(axis=0, ddof=1)
