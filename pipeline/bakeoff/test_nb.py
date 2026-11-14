"""Does the hand-written NB2 / Poisson maximum likelihood recover known parameters?

    python -m pipeline.bakeoff.test_nb
"""
import numpy as np
import pandas as pd
from scipy.optimize import approx_fprime

from .nb import fit_nb2, fit_poisson, nb2_negloglik


def simulate(rng, n=200_000, n1=24, n2=6, alpha=0.7):
    f1 = rng.integers(0, n1, n)
    f2 = rng.integers(-1, n2, n)  # -1 = reference level
    E = np.where(rng.random(n) < 0.6, 0.0, rng.gamma(0.5, 4.0, n))
    off = np.log(E + 0.1)
    b1 = rng.normal(-0.5, 0.8, n1)
    b2 = rng.normal(0.0, 0.5, n2)
    mu = np.exp(off + b1[f1] + np.where(f2 >= 0, b2[np.maximum(f2, 0)], 0.0))
    y = rng.poisson(mu * rng.gamma(1 / alpha, alpha, n))
    return y, off, f1, f2, n1, n2, b1, b2


def test_gradient(rng):
    y, off, f1, f2, n1, n2, *_ = simulate(rng, n=2000)
    x = np.r_[rng.normal(0, 0.3, n1 + n2), np.log(0.5)]
    w = rng.integers(1, 4, len(y)).astype(float)
    f = lambda p: nb2_negloglik(p, y, off, f1, f2, n1, n2, w)[0]
    num = approx_fprime(x, f, 1e-6)
    ana = nb2_negloglik(x, y, off, f1, f2, n1, n2, w)[1]
    err = np.max(np.abs(num - ana) / (1 + np.abs(num)))
    print(f"gradient: max relative difference analytic vs numeric = {err:.2e}")
    assert err < 1e-4


def test_recovery(rng):
    alpha = 0.7
    y, off, f1, f2, n1, n2, b1, b2 = simulate(rng, alpha=alpha)
    fit = fit_nb2(y, off, f1, f2, n1, n2)
    z1 = (fit["beta1"] - b1) / fit["se"][:n1]
    z2 = (fit["beta2"] - b2) / fit["se"][n1:]
    z = np.r_[z1, z2]
    print(f"NB2 recovery: converged={fit['converged']} alpha true {alpha} fit {fit['alpha']:.4f}; "
          f"max |beta error| {np.max(np.abs(np.r_[fit['beta1'] - b1, fit['beta2'] - b2])):.4f}; "
          f"z-scores mean {z.mean():+.2f} sd {z.std():.2f} max |z| {np.abs(z).max():.2f} (n params {len(z)})")
    assert fit["converged"]
    assert abs(fit["alpha"] - alpha) < 0.03
    assert np.abs(z).max() < 4.0
    assert 0.6 < z.std() < 1.5
    return y, off, f1, f2, n1, n2, fit


def test_weights_equal_rows(y, off, f1, f2, n1, n2, fit):
    # collapse rows by rounding the offset to a coarse grid: weighted fit must equal the row-by-row fit
    off_r = np.round(off, 1)
    full = fit_nb2(y, off_r, f1, f2, n1, n2)
    d = pd.DataFrame({"y": y, "o": off_r, "a": f1, "b": f2}).groupby(["y", "o", "a", "b"]).size().reset_index()
    comp = fit_nb2(d.y.to_numpy(), d.o.to_numpy(), d.a.to_numpy(), d.b.to_numpy(), n1, n2, d[0].to_numpy())
    diff = np.max(np.abs(np.r_[full["beta1"] - comp["beta1"], full["beta2"] - comp["beta2"],
                               full["alpha"] - comp["alpha"]]))
    print(f"weights: {len(y)} rows collapsed to {len(d)}; max parameter difference {diff:.2e}")
    assert diff < 1e-4


def test_poisson(rng):
    n = 100_000
    frp = np.where(rng.random(n) < 0.02, 0.0, rng.lognormal(1.0, 1.5, n))
    pos = frp > 0
    X = np.c_[np.ones(n), np.where(pos, np.log(np.where(pos, frp, 1)), 0), (~pos).astype(float)]
    b = np.array([-1.2, 0.45, -0.8])
    y = rng.poisson(np.exp(X @ b))
    bh = fit_poisson(X, y)
    yc = (rng.poisson(np.exp(X @ b)) + rng.poisson(np.exp(X @ b))) / 2.0  # non-integer, as the chance count
    bc = fit_poisson(X, yc)
    print(f"Poisson recovery: true {b}, fit {np.round(bh, 3)}, fit on half-integer averages {np.round(bc, 3)}")
    assert np.max(np.abs(bh - b)) < 0.1 and np.max(np.abs(bc - b)) < 0.1


if __name__ == "__main__":
    rng = np.random.default_rng(20261031)
    test_gradient(rng)
    args = test_recovery(rng)
    test_weights_equal_rows(*args)
    test_poisson(rng)
    print("ALL NB/Poisson TESTS PASSED")
