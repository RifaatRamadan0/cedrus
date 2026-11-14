"""C6's negative-binomial regression, written out (no statsmodels), in the style of pipeline/bakeoff/nb.py.

    y ~ NB2(mu, alpha), var = mu + alpha mu^2,
    log mu = log(sum_k beta_k X_k + 1) + gamma[f1] + delta[f2]      (f2 = 0 is the reference region, delta 0)

beta_k = exp(theta_k) >= 0. The baseline inside the log is fixed at 1: with the gamma terms free, a free b would only
rescale (beta, b) against gamma, so b = 1 is a normalisation, not a restriction (b of the plan = 1 / beta scale).
Frequency weights let identical rows be collapsed before fitting.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.special import digamma, gammaln

from pipeline.bakeoff.nb import LOG_ALPHA_BOUNDS

THETA_BOUNDS = (-20.0, 20.0)


def _eta(params, X, f1, f2, n1, n2):
    K = X.shape[1]
    th, g, d = params[:K], params[K:K + n1], params[K + n1:K + n1 + n2]
    beta = np.exp(th)
    lin = X @ beta + 1.0
    d_full = np.r_[0.0, d]
    return np.log(lin) + g[f1] + d_full[f2], beta, lin


def negloglik(params, y, X, f1, f2, n1, n2, w):
    K = X.shape[1]
    eta, beta, lin = _eta(params, X, f1, f2, n1, n2)
    mu, tha = np.exp(eta), np.exp(-params[-1])
    ll = (gammaln(y + tha) - gammaln(tha) - gammaln(y + 1) + tha * np.log(tha / (tha + mu))
          + y * (eta - np.log(tha + mu)))
    d_eta = w * tha * (y - mu) / (tha + mu)
    g_th = (X * beta).T @ (d_eta / lin)
    g_g = np.bincount(f1, d_eta, n1)
    g_d = np.bincount(f2, d_eta, n2 + 1)[1:]
    d_tha = digamma(y + tha) - digamma(tha) + np.log(tha / (tha + mu)) + 1 - (y + tha) / (tha + mu)
    g_s = np.sum(w * -tha * d_tha)
    return -np.sum(w * ll), -np.r_[g_th, g_g, g_d, g_s]


def information(params, X, f1, f2, n1, n2, w):
    """Expected Fisher information for (theta, gamma, delta); orthogonal to alpha for NB2."""
    K = X.shape[1]
    eta, beta, lin = _eta(params, X, f1, f2, n1, n2)
    mu, tha = np.exp(eta), np.exp(-params[-1])
    W = w * tha * mu / (tha + mu)
    J = np.zeros((len(eta), K + n1 + n2))
    J[:, :K] = X * beta / lin[:, None]
    J[np.arange(len(eta)), K + f1] = 1.0
    has = f2 > 0
    J[np.flatnonzero(has), K + n1 + f2[has] - 1] = 1.0
    return (J * W[:, None]).T @ J


def fit(y, X, f1, f2, n1, n2, w=None):
    """Maximum likelihood of theta (K), gamma (n1), delta (n2 free; level 0 is the reference) and alpha."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    w = np.ones_like(y) if w is None else np.asarray(w, float)
    f1, f2 = np.asarray(f1, int), np.asarray(f2, int)
    K = X.shape[1]
    tot = X.sum(axis=1)
    zero = tot == 0
    # start: gamma from the mean y of rows without detections, one common beta from the overall ratio
    num0, den0 = np.bincount(f1[zero], (w * y)[zero], n1), np.bincount(f1[zero], w[zero], n1)
    g0 = np.log(np.maximum(num0, 0.5) / np.maximum(den0, 1.0))
    ratio = max(np.sum((w * y)[~zero]), 0.5) / max(np.sum((w * tot)[~zero]), 1.0)
    th0 = np.full(K, np.clip(np.log(ratio) - np.mean(g0), *THETA_BOUNDS))
    x0 = np.r_[th0, g0, np.zeros(n2), 0.0]
    bounds = [THETA_BOUNDS] * K + [(None, None)] * (n1 + n2) + [LOG_ALPHA_BOUNDS]
    res = minimize(negloglik, x0, args=(y, X, f1, f2, n1, n2, w), jac=True, method="L-BFGS-B", bounds=bounds,
                   options={"maxiter": 20000, "maxfun": 40000, "ftol": 1e-14, "gtol": 1e-7})
    p = res.x
    cov = np.linalg.pinv(information(p, X, f1, f2, n1, n2, w))
    return {"theta": p[:K], "beta": np.exp(p[:K]), "gamma": p[K:K + n1], "delta": p[K + n1:K + n1 + n2],
            "alpha": float(np.exp(p[-1])), "cov": cov, "converged": bool(res.success), "message": str(res.message),
            "nll": float(res.fun), "iterations": int(res.nit), "max_abs_grad": float(np.max(np.abs(res.jac)))}
