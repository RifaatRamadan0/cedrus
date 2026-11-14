"""Scores of a count forecast: exact CRPS by summation, the central 80% interval, the predictive mean.

A forecast is (kind, a, b): kind 0 = all mass at 0; 1 = Poisson(a); 2 = negative binomial with
size a and probability b (scipy's nbinom: mean a (1 - b) / b).
CRPS = sum over k = 0..K of (F(k) - 1[y <= k])^2, K = max(0.9999 quantile, y + 50).
"""
import numpy as np
from scipy.stats import nbinom, poisson

CHUNK = 4_000_000  # grid points per batch


def _dist(kind, a, b):
    return poisson(a) if kind == 1 else nbinom(a, b)


def score(kind, a, b, y):
    """Arrays in, dict of arrays out: crps, q10, q90, mean (one per forecast)."""
    kind, a, b, y = (np.asarray(v) for v in (kind, a, b, y))
    n = len(y)
    out = {"crps": np.zeros(n), "q10": np.zeros(n), "q90": np.zeros(n), "mean": np.zeros(n)}
    zero = kind == 0
    out["crps"][zero] = y[zero]  # F(k) = 1 for all k >= 0
    for k_ in (1, 2):
        sel = np.flatnonzero(kind == k_)
        if not len(sel):
            continue
        A, B, Ys = a[sel], b[sel], y[sel].astype(float)
        d = _dist(k_, A, B)
        out["q10"][sel] = d.ppf(0.1)
        out["q90"][sel] = d.ppf(0.9)
        out["mean"][sel] = d.mean()
        K = np.maximum(d.ppf(0.9999), Ys + 50).astype(np.int64)
        L = K + 1
        start = 0
        while start < len(sel):
            stop = start + max(1, int(np.searchsorted(np.cumsum(L[start:]), CHUNK)))
            idx = np.repeat(np.arange(start, stop), L[start:stop])
            kk = np.arange(len(idx)) - np.repeat(np.cumsum(L[start:stop]) - L[start:stop], L[start:stop])
            F = _dist(k_, A[idx], B[idx]).cdf(kk)
            out["crps"][sel[start:stop]] = np.bincount(idx - start, (F - (kk >= Ys[idx])) ** 2, stop - start)
            start = stop
    return out
