"""Does the summed CRPS agree with closed forms and with an independent definition?

    python -m pipeline.bakeoff.test_crps
"""
import numpy as np
from scipy.special import ive
from scipy.stats import nbinom, poisson

from .scores import score


def crps_poisson_closed(y, lam):
    """Wei & Held (2014): (y - l)(2F(y) - 1) + 2 l f(y) - l e^{-2l} (I0(2l) + I1(2l))."""
    return ((y - lam) * (2 * poisson.cdf(y, lam) - 1) + 2 * lam * poisson.pmf(y, lam)
            - lam * (ive(0, 2 * lam) + ive(1, 2 * lam)))


def crps_kernel(pmf, y):
    """E|X - y| - 1/2 E|X - X'| on a finite support 0..len(pmf)-1."""
    k = np.arange(len(pmf))
    return np.sum(pmf * np.abs(k - y)) - 0.5 * np.sum(np.outer(pmf, pmf) * np.abs(k[:, None] - k[None, :]))


def main():
    lam = np.array([0.01, 0.3, 1.0, 4.0, 25.0, 300.0, 0.3, 4.0, 25.0, 2.0])
    y = np.array([0, 0, 3, 2, 40, 260, 7, 0, 0, 2])
    got = score(np.ones(len(y), int), lam, np.zeros(len(y)), y)["crps"]
    ref = crps_poisson_closed(y, lam)
    err = np.max(np.abs(got - ref))
    print("Poisson CRPS, summed vs closed form:")
    for a, b, c, d in zip(lam, y, got, ref):
        print(f"  lambda {a:7.2f} y {b:4d}: summed {c:.8f} closed {d:.8f}")
    print(f"  max abs difference {err:.2e}")
    assert err < 1e-6

    size = np.array([0.5, 2.0, 10.0, 1.3])
    p = np.array([0.4, 0.05, 0.9, 0.2])
    yy = np.array([0, 30, 1, 9])
    got = score(np.full(4, 2), size, p, yy)["crps"]
    ref = np.array([crps_kernel(nbinom.pmf(np.arange(3000), s, q), t) for s, q, t in zip(size, p, yy)])
    err = np.max(np.abs(got - ref))
    print(f"Negative binomial CRPS, summed vs E|X-y| - E|X-X'|/2: max abs difference {err:.2e}")
    assert err < 1e-6

    # NB2 with alpha -> 0 tends to Poisson
    mu, alpha = 5.0, 1e-7
    th = 1 / alpha
    nbv = score([2], [th], [th / (th + mu)], [8])["crps"][0]
    pov = crps_poisson_closed(8, mu)
    print(f"NB2(mu=5, alpha=1e-7) vs Poisson(5) at y=8: {nbv:.8f} vs {pov:.8f}")
    assert abs(nbv - pov) < 1e-5

    pm = score([0, 0], [0, 0], [0, 0], [0, 4])
    assert pm["crps"].tolist() == [0.0, 4.0] and pm["q90"].tolist() == [0.0, 0.0]
    s = score([1], [3.0], [0.0], [3])
    assert s["q10"][0] == poisson.ppf(0.1, 3.0) == 1 and s["q90"][0] == poisson.ppf(0.9, 3.0) == 5
    print("point mass and 10th/90th percentiles: ok")
    print("ALL CRPS TESTS PASSED")


if __name__ == "__main__":
    main()
