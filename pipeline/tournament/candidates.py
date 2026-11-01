"""Candidates C0-C8 of docs/TOURNAMENT_PLAN.md: Suomi NPP -> MODIS-equivalent, fitted on a boolean mask of training rows.

Row table (pipeline.tournament.data.unit_table): rid, cid, moy, dnN, md, rd, rmd, cmd, ix, iy, Y, V, V20 and the
class counts Vf0..Vf3 (FRP) and Vs0..Vs2 (scan). Every fit refuses a training row after 2019-12
(pipeline.round2.models.refuse_late). forecast() returns (kind, a, b) as pipeline/bakeoff/scores.py takes it.

C0 A2 frozen (a = 30), C1 R1, C2 Rm: round 2's own code, unchanged.
C3 / C4: one A2-style Poisson-gamma ratio per class. MODIS is not split by class, so the class shares of each
    training row's Y are allocated in proportion to the current class means (an EM-style fixed point). Prior per
    region x calendar month x day/night x class, posterior per cell x calendar month x day/night x class.
C5: A2 with two levels: the cell shrinks toward its 3 x 3 neighbourhood's ratio, which shrinks toward the region's r0.
C6: NB2 regression on the seven class counts with month x day/night and region terms; region terms shrunk by
    empirical Bayes as the bake-off's B.
C7: LightGBM Poisson on the class counts, day/night, month, region and the cell's history ratio; NB dispersion from
    inner leave-one-year-out residuals.
C8: zero-aware monotone quantile mapping per region x day/night, NB dispersion by maximum likelihood.
"""
import numpy as np
from scipy import sparse

from pipeline.bakeoff.models import fit_A, predict_A
from pipeline.bakeoff.validate import score_rows, weights
from pipeline.confirm.tests import moments
from pipeline.round2.models import (A2_GRID, _chain, fit_alpha, fit_model, forecast as r2_forecast, nb_from_moments,
                                    refuse_late, rng_for)

from . import nbreg
from .data import NF, NS, class_cols

CANDIDATES = ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]
SIMPLICITY = ["C1", "C2", "C0", "C5", "C3", "C4", "C8", "C6", "C7"]  # the plan's order, simplest first
NAMES = {"C0": "A2, frozen round-2 settings (a = 30)", "C1": "R1 one ratio per region × day/night",
         "C2": "Rm one ratio per region × calendar month × day/night", "C3": "FRP-class A2 ratios",
         "C4": "pixel-size (scan) class A2 ratios", "C5": "A2 with 3×3 neighbour shrinkage",
         "C6": "NB regression on class counts, EB-shrunk region terms", "C7": "gradient-boosted Poisson trees",
         "C8": "zero-aware monotone quantile mapping"}
A2_FROZEN = 30
EM_ITERS, EM_TOL = 3000, 1e-7  # relative change of the class means between iterations
C5_GRID = [(a, an) for a in A2_GRID for an in A2_GRID]
GBM = {"objective": "poisson", "n_estimators": 300, "learning_rate": 0.05, "num_leaves": 31,
       "min_child_samples": 100, "subsample": 1.0, "colsample_bytree": 1.0, "reg_lambda": 0.0, "max_bin": 255,
       "random_state": 20261101, "deterministic": True, "force_row_wise": True, "n_jobs": 1, "verbose": -1}
GBM_FEATURES = class_cols("V") + ["dnN", "moy", "rid", "hist"]
FRP_COLS, SCAN_COLS = class_cols("V")[:NF], class_cols("V")[NF:]


def _rmd_maps(nr):
    i = np.arange(nr * 24)
    return (i // 24) * 2 + i % 2, i % 2


def _poisson_or_zero(lam):
    return np.where(lam > 0, 1, 0), np.where(lam > 0, lam, 0.0), np.zeros(len(lam))


# ---------------------------------------------------------------- C3 / C4: class A2 ratios
def fit_class_a2(T, train, cols, a):
    """Per class k: prior r0_k per region x calendar month x day/night (fallback region x day/night, then all
    regions x day/night), posterior shape a + SY_k, rate a / r0_k + SV_k per cell x calendar month x day/night.
    Sums over training rows with V > 0 (A2). SY_k comes from Y split over classes in proportion to V_k times the
    current class mean, iterated to a fixed point. With one class this is A2 exactly.

    The plain iteration converges linearly and slowly (over a thousand steps on the development table), so it is
    accelerated by SQUAREM (Varadhan and Roland 2008, scheme S3, step clamped at -1 and halved back toward -1 until
    the extrapolated means are not negative). The stopping rule is the plain one: one step of the map changes the
    class means by less than EM_TOL relative to the largest."""
    refuse_late(T, train)
    train = np.asarray(train, bool)
    nr, K = T.attrs["n_regions"], len(cols)
    rmd, cmd = T.rmd.to_numpy(), T.cmd.to_numpy()
    nc = (int(T.cid.max()) + 1) * 24
    Y, V = T.Y.to_numpy().astype(float), T.V.to_numpy().astype(float)
    Vk = T[cols].to_numpy().astype(float)
    pos = np.flatnonzero(train & (V > 0))
    y, vk, g, c = Y[pos], Vk[pos], rmd[pos], cmd[pos]
    g_rd, g_d = _rmd_maps(nr)
    rm = _cell_rmd(T, nc)
    kk = np.arange(K)
    key_c, key_g = (c[:, None] * K + kk).ravel(), (g[:, None] * K + kk).ravel()
    SV = np.bincount(key_c, vk.ravel(), nc * K).reshape(nc, K)
    den = np.bincount(key_g, vk.ravel(), nr * 24 * K).reshape(nr * 24, K)
    even = vk / vk.sum(1, keepdims=True)

    def step(lam):
        share = vk * lam[c]
        tot = share.sum(1, keepdims=True)
        share = np.where(tot > 0, share / np.where(tot > 0, tot, 1), even)
        yk = (y[:, None] * share).ravel()
        SY = np.bincount(key_c, yk, nc * K).reshape(nc, K)
        num = np.bincount(key_g, yk, nr * 24 * K).reshape(nr * 24, K)
        r0, level = _chain(num.T, den.T, g_rd, g_d)
        r0, level = r0.T, level.T
        with np.errstate(divide="ignore", invalid="ignore"):
            rate = a / r0[rm] + SV
            new = np.where(np.isinf(rate), 0.0, (a + SY) / rate)
        return new, (r0, level, SY)

    lam, it, evals, delta = np.ones((nc, K)), 0, 0, np.inf
    while evals < EM_ITERS:
        it += 1
        x1, parts = step(lam)
        evals += 1
        delta = np.max(np.abs(x1 - lam)) / max(np.max(x1), 1e-12)
        if delta < EM_TOL:
            lam = x1
            break
        x2, _ = step(x1)
        evals += 1
        r, v = x1 - lam, x2 - 2 * x1 + lam
        nv = np.sqrt(np.sum(v * v))
        alpha = min(-np.sqrt(np.sum(r * r)) / nv, -1.0) if nv > 0 else -1.0
        xp = lam - 2 * alpha * r + alpha ** 2 * v
        while alpha < -1.0 and (xp < 0).any():
            alpha = (alpha - 1.0) / 2 if alpha < -1.01 else -1.0
            xp = lam - 2 * alpha * r + alpha ** 2 * v
        lam, _ = step(np.maximum(xp, 0.0))
        evals += 1
    r0, level, SY = parts
    full = fit_A(T, train)
    return {"cols": list(cols), "a": a, "r0": r0, "r0_level": level, "SY": SY, "SV": SV, "bA": full["bA"],
            "em_iterations": evals, "em_delta": float(delta), "em_converged": bool(delta < EM_TOL)}


def _cell_rmd(T, nc):
    """rmd group of every cell x calendar month x day/night index (cmd = cid * 24 + md)."""
    cid_r = np.zeros(nc // 24, int)
    cid_r[T.cid.to_numpy()] = T.rid.to_numpy()
    return (cid_r[:, None] * 24 + np.arange(24)[None, :]).ravel()


def predict_class_a2(T, rows, f, a=None):
    """Sum over classes of NB(shape_k, rate_k / (rate_k + V_k)); moment-matched to one NB. V = 0 rows: Poisson(b_A)."""
    a = f["a"] if a is None else a
    rmd, cmd = T.rmd.to_numpy()[rows], T.cmd.to_numpy()[rows]
    V = T.V.to_numpy()[rows].astype(float)
    Vk = T[f["cols"]].to_numpy()[rows].astype(float)
    r0 = f["r0"][rmd]
    with np.errstate(divide="ignore", invalid="ignore"):
        rate = a / r0 + f["SV"][cmd]
        live = (Vk > 0) & ~np.isinf(rate)
        m_k = np.where(live, Vk * (a + f["SY"][cmd]) / np.where(live, rate, 1.0), 0.0)
        v_k = np.where(live, m_k * (1 + Vk / np.where(live, rate, 1.0)), 0.0)
    mean, var = m_k.sum(1), v_k.sum(1)
    k1, a1, b1 = nb_from_moments(mean, var)
    k0, a0, b0 = _poisson_or_zero(f["bA"][rmd])
    pos = V > 0
    return np.where(pos, k1, k0), np.where(pos, a1, a0), np.where(pos, b1, b0)


# ---------------------------------------------------------------- C5: neighbour shrinkage
def neighbours(T):
    """Sparse cid x cid matrix: 1 where two cells of the same region are within one cell east-west and north-south
    (the 3 x 3 block, the cell itself included)."""
    cid = T.cid.to_numpy()
    n = int(cid.max()) + 1
    first = np.unique(cid, return_index=True)[1]
    rid, ix, iy = (T[c].to_numpy()[first] for c in ("rid", "ix", "iy"))
    key = {(int(r), int(x), int(y)): i for i, (r, x, y) in enumerate(zip(rid, ix, iy))}
    I, J = [], []
    for i in range(n):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                j = key.get((int(rid[i]), int(ix[i]) + dx, int(iy[i]) + dy))
                if j is not None:
                    I.append(i)
                    J.append(j)
    return sparse.csr_matrix((np.ones(len(I)), (I, J)), shape=(n, n))


def fit_c5_sums(T, train, nb=None):
    """Everything C5 needs except (a, a_n): A2's r0 and b_A, the cell sums and the neighbourhood sums."""
    refuse_late(T, train)
    train = np.asarray(train, bool)
    V = T.V.to_numpy()
    Tpos = T.assign(Y=np.where(V > 0, T.Y.to_numpy(), 0))
    Tpos.attrs.update(T.attrs)
    f = fit_A(Tpos, train)
    f["bA"] = fit_A(T, train)["bA"]
    nb = neighbours(T) if nb is None else nb
    n = nb.shape[0]
    f["NY"] = np.asarray(nb @ f["SY"][:n * 24].reshape(n, 24)).ravel()
    f["NV"] = np.asarray(nb @ f["SV"][:n * 24].reshape(n, 24)).ravel()
    f["n_neighbours"] = np.asarray(nb.sum(1)).ravel()
    return f


def predict_c5(T, rows, f, a, an):
    rmd, cmd = T.rmd.to_numpy()[rows], T.cmd.to_numpy()[rows]
    V = T.V.to_numpy()[rows].astype(float)
    r0 = f["r0"][rmd]
    with np.errstate(divide="ignore", invalid="ignore"):
        r_nb = np.where(r0 > 0, (an + f["NY"][cmd]) / (an / r0 + f["NV"][cmd]), 0.0)
        rate = np.where(r_nb > 0, a / r_nb + f["SV"][cmd], np.inf)
    shape = a + f["SY"][cmd]
    lam = f["bA"][rmd]
    pos = V > 0
    kind = np.where(pos, np.where(np.isinf(rate), 0, 2), np.where(lam > 0, 1, 0))
    fa = np.where(pos, shape, lam)
    with np.errstate(invalid="ignore"):
        fb = np.where(pos & ~np.isinf(rate), rate / (rate + V), 0.0)
    return kind, np.where(kind == 0, 0.0, fa), fb


# ---------------------------------------------------------------- C6: NB regression on class counts
def fit_c6(T, train):
    refuse_late(T, train)
    train = np.asarray(train, bool)
    nr = T.attrs["n_regions"]
    cols = class_cols("V")
    X = T[cols].to_numpy()[train].astype(float)
    y = T.Y.to_numpy()[train].astype(float)
    md, rid = T.md.to_numpy()[train], T.rid.to_numpy()[train]
    key = np.c_[y, X, md, rid]
    uniq, w = np.unique(key, axis=0, return_counts=True)
    K = len(cols)
    fit = nbreg.fit(uniq[:, 0], uniq[:, 1:1 + K], uniq[:, 1 + K].astype(int), uniq[:, 2 + K].astype(int), 24,
                    nr - 1, w.astype(float))
    gamma = fit["gamma"].copy()
    eb = {"tau2": 0.0, "se": [0.0], "factor": [0.0]}
    shrunk = np.zeros(nr)
    raw = np.zeros(nr)
    if nr > 1:  # region effects, centred (mean moved into the month terms), then shrunk (as the bake-off's B)
        M = np.zeros((nr, nr - 1))
        M[1:, :] = np.eye(nr - 1)
        C = (np.eye(nr) - 1.0 / nr) @ M
        free = fit["delta"]
        cov = C @ fit["cov"][K + 24:, K + 24:] @ C.T
        centred = C @ free
        se2 = np.clip(np.diag(cov), 0, None)
        tau2 = max(0.0, float(np.var(centred) - np.mean(se2)))
        with np.errstate(invalid="ignore", divide="ignore"):
            factor = np.where(tau2 + se2 > 0, tau2 / (tau2 + se2), 0.0)
        shrunk, raw = centred * factor, centred
        gamma += (M @ free).mean()
        eb = {"tau2": tau2, "se": np.sqrt(se2).tolist(), "factor": factor.tolist()}
    return {"cols": cols, "beta": fit["beta"], "gamma": gamma, "region_raw": raw, "region_shrunk": shrunk,
            "alpha": fit["alpha"], "eb": eb, "converged": fit["converged"], "max_abs_grad": fit["max_abs_grad"],
            "iterations": fit["iterations"], "n_unique": len(w)}


def mu_c6(T, rows, f):
    X = T[f["cols"]].to_numpy()[rows].astype(float)
    md, rid = T.md.to_numpy()[rows], T.rid.to_numpy()[rows]
    return (X @ f["beta"] + 1.0) * np.exp(f["gamma"][md] + f["region_shrunk"][rid])


def predict_c6(T, rows, f):
    mu = mu_c6(T, rows, f)
    return nb_from_moments(mu, mu + f["alpha"] * mu ** 2)


# ---------------------------------------------------------------- C7: gradient-boosted Poisson trees
def gbm_backend():
    try:
        import lightgbm  # noqa: F401
        return "lightgbm"
    except ImportError:
        return "sklearn"


def history_ratio(T, train):
    """Per cell: sum Y / sum V over its training rows with V > 0 (NaN where the cell has no Suomi NPP detection)."""
    cid, V, Y = T.cid.to_numpy(), T.V.to_numpy().astype(float), T.Y.to_numpy().astype(float)
    n = int(cid.max()) + 1
    pos = np.asarray(train, bool) & (V > 0)
    sy, sv = np.bincount(cid[pos], Y[pos], n), np.bincount(cid[pos], V[pos], n)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(sv > 0, sy / sv, np.nan)


def _features(T, rows, hist):
    X = T[class_cols("V") + ["dnN", "moy", "rid"]].to_numpy()[rows].astype(float)
    return np.c_[X, hist[T.cid.to_numpy()[rows]]]


def _gbm_fit(T, train):
    rows = np.flatnonzero(train)
    hist = history_ratio(T, train)
    X, y = _features(T, rows, hist), T.Y.to_numpy()[rows].astype(float)
    cat = GBM_FEATURES.index("rid")
    if gbm_backend() == "lightgbm":
        import lightgbm as lgb
        model = lgb.LGBMRegressor(**GBM)
        model.fit(X, y, categorical_feature=[cat])
    else:
        from sklearn.ensemble import HistGradientBoostingRegressor
        model = HistGradientBoostingRegressor(loss="poisson", learning_rate=GBM["learning_rate"],
                                              max_iter=GBM["n_estimators"], max_leaf_nodes=GBM["num_leaves"],
                                              min_samples_leaf=GBM["min_child_samples"], l2_regularization=0.0,
                                              categorical_features=[cat], early_stopping=False,
                                              random_state=GBM["random_state"])
        model.fit(X, y)
    return {"model": model, "hist": hist}


def _gbm_mu(g, T, rows):
    return np.maximum(g["model"].predict(_features(T, rows, g["hist"])), 0.0)


def _alpha_rd(T, rows, y, mu):
    """alpha per region x day/night by maximum likelihood with the means held fixed; a region x day/night with no
    informative row takes the alpha of all regions' rows of that day/night."""
    nr = T.attrs["n_regions"]
    rd, dn = T.rd.to_numpy()[rows], T.dnN.to_numpy()[rows]
    alpha = np.full(nr * 2, np.nan)
    for k in range(nr * 2):
        sel = rd == k
        if sel.any():
            alpha[k] = fit_alpha(y[sel], mu[sel])
    fb = np.isnan(alpha)
    for d in (0, 1):
        if fb[d::2].any():
            sel = dn == d
            alpha[d::2] = np.where(fb[d::2], fit_alpha(y[sel], mu[sel]), alpha[d::2])
    return alpha, fb


def fit_c7(T, train, scored, years):
    """The trees on all training rows; alpha per region x day/night from the residuals of inner leave-one-year-out
    fits (each inner year predicted by trees fitted on the other training years, scored months only)."""
    refuse_late(T, train)
    train = np.asarray(train, bool)
    yr = T.year.to_numpy()
    ys, ms, rs = [], [], []
    for i in years:
        tr = train & (yr != i)
        rows = np.flatnonzero(train & (yr == i) & scored)
        if not len(rows) or not tr.any():
            continue
        g = _gbm_fit(T, tr)
        rs.append(rows)
        ms.append(_gbm_mu(g, T, rows))
        ys.append(T.Y.to_numpy()[rows].astype(float))
    rows, mu, y = np.concatenate(rs), np.concatenate(ms), np.concatenate(ys)
    alpha, fb = _alpha_rd(T, rows, y, mu)
    g = _gbm_fit(T, train)
    return {"gbm": g, "alpha": alpha, "alpha_fallback": fb, "backend": gbm_backend(), "inner_years": list(years)}


def predict_c7(T, rows, f):
    mu = _gbm_mu(f["gbm"], T, rows)
    al = f["alpha"][T.rd.to_numpy()[rows]]
    return nb_from_moments(mu, mu + al * mu ** 2)


# ---------------------------------------------------------------- C8: quantile mapping
def qm_table(v, y):
    """Distinct V values and their mapped means: each V value takes the mean of the observed Y over the same quantile
    band of the pooled distribution (rows sorted by V; Y sorted on its own). Monotone; zero-aware: V = 0 maps to the
    mean of the lowest P(V = 0) share of Y, which is 0 when MODIS has at least as many zero rows."""
    v, y = np.asarray(v, float), np.sort(np.asarray(y, float))
    vals, counts = np.unique(v, return_counts=True)
    cum_y = np.r_[0.0, np.cumsum(y)]
    hi = np.cumsum(counts)
    lo = hi - counts
    return vals, (cum_y[hi] - cum_y[lo]) / counts


def qm_apply(vals, means, v):
    """The frozen rules between and beyond the training values: linear between neighbouring values (from (0, 0) if
    0 was never seen); above the largest value, proportional: m(v) = m(v_max) * v / v_max."""
    v = np.asarray(v, float)
    if vals[0] > 0:
        vals, means = np.r_[0.0, vals], np.r_[0.0, means]
    out = np.interp(v, vals, means)
    top = v > vals[-1]
    if top.any():
        out[top] = means[-1] * v[top] / vals[-1] if vals[-1] > 0 else means[-1]
    return out


def fit_c8(T, train):
    refuse_late(T, train)
    train = np.asarray(train, bool)
    nr = T.attrs["n_regions"]
    rd, dn = T.rd.to_numpy(), T.dnN.to_numpy()
    V, Y = T.V.to_numpy().astype(float), T.Y.to_numpy().astype(float)
    maps, source = {}, {}
    for k in range(nr * 2):
        sel = train & (rd == k)
        if not sel.any():  # no training row in this region x day/night: all regions' rows of that day/night
            sel, source[k] = train & (dn == k % 2), "all regions"
        else:
            source[k] = "region"
        maps[k] = qm_table(V[sel], Y[sel])
    f = {"maps": maps, "source": source}
    rows = np.flatnonzero(train)
    mu = mu_c8(T, rows, f)
    f["alpha"], f["alpha_fallback"] = _alpha_rd(T, rows, Y[rows], mu)
    return f


def mu_c8(T, rows, f):
    rd, V = T.rd.to_numpy()[rows], T.V.to_numpy()[rows].astype(float)
    mu = np.zeros(len(rows))
    for k in np.unique(rd):
        sel = rd == k
        mu[sel] = qm_apply(*f["maps"][k], V[sel])
    return mu


def predict_c8(T, rows, f):
    mu = mu_c8(T, rows, f)
    al = f["alpha"][T.rd.to_numpy()[rows]]
    return nb_from_moments(mu, mu + al * mu ** 2)


# ---------------------------------------------------------------- inner tuning and one interface
def tune(T, base, scored, years, grid, prep, predict):
    """A setting from `grid` by leave-one-year-out inside `years` (rows of `base` only): weighted mean CRPS, weights
    from the inner training years, ties to the earlier (smaller) setting. prep(train) -> fit; predict(fit, rows, s)."""
    tab = {s: [0.0, 0.0] for s in grid}
    yr = T.year.to_numpy()
    for i in years:
        tr = np.asarray(base, bool) & np.isin(yr, [y for y in years if y != i])
        rows = np.flatnonzero(np.asarray(base, bool) & (yr == i) & scored)
        if not len(rows):
            continue
        w = weights(T, tr)[T.cid.to_numpy()[rows]]
        y = T.Y.to_numpy()[rows]
        f = prep(tr)
        for s in grid:
            sc = score_rows(*predict(f, rows, s), y)
            tab[s][0] += np.sum(w * sc["crps"])
            tab[s][1] += np.sum(w)
    tab = {s: v[0] / v[1] for s, v in tab.items()}
    return min(grid, key=lambda s: (tab[s], grid.index(s))), tab


def fit(name, T, train, scored, years, label, setting=None, nb=None):
    """Fit one candidate on the training mask. Tuned candidates (C3, C4, C5) choose their setting by inner
    leave-one-year-out over `years` unless `setting` is given (frozen)."""
    train = np.asarray(train, bool)
    refuse_late(T, train)
    m = {"name": name, "inner": None}
    if name == "C0":
        m["r2"] = fit_model("A2", T, train, rng_for("tournament", label, name), a=A2_FROZEN)
    elif name in ("C1", "C2"):
        m["r2"] = fit_model("R1" if name == "C1" else "Rm", T, train, rng_for("tournament", label, name))
    elif name in ("C3", "C4"):
        cols = FRP_COLS if name == "C3" else SCAN_COLS
        a = setting
        if a is None:
            a, m["inner"] = tune(T, train, scored, years, A2_GRID, lambda tr: tr,
                                 lambda tr, rows, a_: predict_class_a2(T, rows, fit_class_a2(T, tr, cols, a_)))
        m["fit"], m["setting"] = fit_class_a2(T, train, cols, a), a
    elif name == "C5":
        nb = neighbours(T) if nb is None else nb
        s = setting
        if s is None:
            s, m["inner"] = tune(T, train, scored, years, C5_GRID, lambda tr: fit_c5_sums(T, tr, nb),
                                 lambda f, rows, s_: predict_c5(T, rows, f, *s_))
        m["fit"], m["setting"] = fit_c5_sums(T, train, nb), tuple(s)
    elif name == "C6":
        m["fit"] = fit_c6(T, train)
    elif name == "C7":
        m["fit"] = fit_c7(T, train, scored, years)
    elif name == "C8":
        m["fit"] = fit_c8(T, train)
    else:
        raise ValueError(name)
    return m


def forecast(m, T, rows):
    """(kind, a, b) of each row; T may be a J-S view (pipeline.tournament.data.swap_view)."""
    n = m["name"]
    if n in ("C0", "C1", "C2"):
        return r2_forecast(m["r2"], T, rows)
    if n in ("C3", "C4"):
        return predict_class_a2(T, rows, m["fit"])
    if n == "C5":
        return predict_c5(T, rows, m["fit"], *m["setting"])
    if n == "C6":
        return predict_c6(T, rows, m["fit"])
    if n == "C7":
        return predict_c7(T, rows, m["fit"])
    if n == "C8":
        return predict_c8(T, rows, m["fit"])
    raise ValueError(n)


def mean_of(fc):
    return moments(*fc)[0]
