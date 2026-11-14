"""Maximum likelihood for the two GLMs the plan needs, written out (no statsmodels).

NB2:     y ~ NB(mu, alpha), var = mu + alpha mu^2,
         log mu = offset + beta1[f1] + beta2[f2]      (f2 = -1 marks the reference level, effect 0)
Poisson: y ~ Poisson(exp(X b)); y may be non-integer (the chance count is an average of two).
Both take frequency weights, so identical rows can be collapsed before fitting.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.special import digamma, gammaln

LOG_ALPHA_BOUNDS = (-20.0, 6.0)


def _nb_parts(params, y, off, f1, f2, n1):
    b1, b2, s = params[:n1], params[n1:-1], params[-1]
    eta = off + b1[f1] + np.where(f2 >= 0, b2[np.maximum(f2, 0)], 0.0)
    return eta, np.exp(eta), np.exp(-s)


def nb2_negloglik(params, y, off, f1, f2, n1, n2, w):
    eta, mu, th = _nb_parts(params, y, off, f1, f2, n1)
    ll = (gammaln(y + th) - gammaln(th) - gammaln(y + 1) + th * np.log(th / (th + mu))
          + y * (eta - np.log(th + mu)))
    # gradient: d ll / d eta and d ll / d log(alpha)
    d_eta = th * (y - mu) / (th + mu)
    d_th = digamma(y + th) - digamma(th) + np.log(th / (th + mu)) + 1 - (y + th) / (th + mu)
    d_s = -th * d_th
    g1 = np.bincount(f1, w * d_eta, n1)
    has2 = f2 >= 0
    g2 = np.bincount(f2[has2], (w * d_eta)[has2], n2)
    grad = np.r_[g1, g2, np.sum(w * d_s)]
    return -np.sum(w * ll), -grad


def nb2_information(params, off, f1, f2, n1, n2, w):
    """Expected Fisher information for (beta1, beta2); orthogonal to alpha for NB2."""
    _, mu, th = _nb_parts(params, None, off, f1, f2, n1)
    W = w * th * mu / (th + mu)
    P = n1 + n2
    info = np.zeros((P, P))
    info[np.arange(n1), np.arange(n1)] = np.bincount(f1, W, n1)
    has2 = f2 >= 0
    d2 = np.bincount(f2[has2], W[has2], n2)
    info[n1 + np.arange(n2), n1 + np.arange(n2)] = d2
    cross = np.bincount(f1[has2] * n2 + f2[has2], W[has2], n1 * n2).reshape(n1, n2)
    info[:n1, n1:] = cross
    info[n1:, :n1] = cross.T
    return info


def fit_nb2(y, off, f1, f2, n1, n2, w=None):
    """MLE of beta1 (n1), beta2 (n2, reference level excluded) and alpha. Returns a dict with se."""
    y = np.asarray(y, float)
    w = np.ones_like(y) if w is None else np.asarray(w, float)
    f1, f2 = np.asarray(f1, int), np.asarray(f2, int)
    # start: Poisson-like group means for beta1, zero for beta2, alpha = 1
    num = np.bincount(f1, w * y, n1)
    den = np.bincount(f1, w * np.exp(off), n1)
    b1 = np.log(np.maximum(num, 0.5) / np.maximum(den, 1e-12))
    x0 = np.r_[b1, np.zeros(n2), 0.0]
    bounds = [(None, None)] * (n1 + n2) + [LOG_ALPHA_BOUNDS]
    res = minimize(nb2_negloglik, x0, args=(y, off, f1, f2, n1, n2, w), jac=True, method="L-BFGS-B",
                   bounds=bounds, options={"maxiter": 5000, "maxfun": 10000, "ftol": 1e-13, "gtol": 1e-7})
    p = res.x
    info = nb2_information(p, off, f1, f2, n1, n2, w)
    cov = np.linalg.pinv(info)
    return {"beta1": p[:n1], "beta2": p[n1:-1], "alpha": float(np.exp(p[-1])), "cov": cov,
            "se": np.sqrt(np.clip(np.diag(cov), 0, None)), "converged": bool(res.success),
            "message": str(res.message), "nll": float(res.fun), "iterations": int(res.nit),
            "max_abs_grad": float(np.max(np.abs(res.jac)))}


def fit_poisson(X, y, w=None, iters=100, tol=1e-10):
    """Poisson GLM, log link, by Newton-Raphson. Columns of X that are all zero get coefficient 0."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    w = np.ones_like(y) if w is None else np.asarray(w, float)
    live = np.any(X != 0, axis=0)
    Xl = X[:, live]
    b = np.zeros(Xl.shape[1])
    b[0] = np.log(max(np.sum(w * y) / np.sum(w), 1e-8))  # column 0 is the intercept
    for _ in range(iters):
        mu = np.exp(Xl @ b)
        grad = Xl.T @ (w * (y - mu))
        H = (Xl * (w * mu)[:, None]).T @ Xl
        step = np.linalg.solve(H, grad)
        b += step
        if np.max(np.abs(step)) < tol:
            break
    out = np.zeros(X.shape[1])
    out[live] = b
    return out
