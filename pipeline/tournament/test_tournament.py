"""Hand checks of the tournament candidates on toy tables.

    python -m pipeline.tournament.test_tournament
    python -m pipeline.round2.test_round2      # R1 / Rm / A2 (C1, C2, C0) and the swap pieces, unchanged
    python -m pipeline.bakeoff.test_crps       # the exact CRPS every score uses

C3 / C4 means against hand sums (one class = A2 exactly; classes that never share a row = one A2 per class; mixed
rows = the allocation's fixed point); C5 against explicit neighbourhood sums; C6's gradient, recovery and mean;
C7's history ratio and dispersion; C8's band means, tail rule and total; the Poisson floor; every fit refuses rows
after 2019-12.
"""
import sys

import numpy as np
import pandas as pd
from scipy.optimize import approx_fprime
from scipy.stats import poisson

from pipeline.bakeoff.models import add_groups
from pipeline.bakeoff.scores import score
from pipeline.round2.models import fit_A2, predict_A2, rng_for

from . import nbreg
from .candidates import (CANDIDATES, EM_ITERS, fit, fit_c5_sums, fit_c6, fit_c7, fit_c8, fit_class_a2, forecast,
                         history_ratio, mean_of, mu_c6, neighbours, predict_c5, predict_class_a2, qm_apply, qm_table)
from .data import class_cols, frp_class, scan_class, swap_view
from .validate import poisson_floor


def toy(last="2020-12", n_cells=4, n_regions=1, seed=7, mixed=True):
    """Cells in a row east-west, every month 2012-02..last, day and night; class counts made up so that their
    FRP and scan classes each add up to V."""
    rng = np.random.default_rng(seed)
    months = [str(p) for p in pd.period_range("2012-02", last, freq="M")]
    cells = [f"{i}_0" for i in range(n_cells)]
    parts = []
    for r in range(n_regions):
        idx = pd.MultiIndex.from_product([cells, months, ["D", "N"]], names=["cell", "ym", "dn"])
        P = idx.to_frame(index=False)
        P.insert(0, "region", f"toy{r}")
        parts.append(P)
    R = pd.concat(parts, ignore_index=True)
    n = len(R)
    for stem in ("V", "V20"):
        f = np.where(rng.random((n, 4)) < 0.55, 0, rng.integers(1, 5, (n, 4)))
        f[:, 0] = np.where(rng.random(n) < 0.9, 0, f[:, 0])
        if not mixed:  # one FRP class per row at most
            keep = rng.integers(0, 4, n)
            f = np.where(np.arange(4)[None, :] == keep[:, None], f, 0)
        tot = f.sum(1)
        s0 = np.minimum(rng.integers(0, 3, n), tot)
        s1 = np.minimum(rng.integers(0, 3, n), tot - s0)
        s = np.c_[s0, s1, tot - s0 - s1]
        for k in range(4):
            R[f"{stem}f{k}"] = f[:, k]
        for k in range(3):
            R[f"{stem}s{k}"] = s[:, k]
        R[stem] = tot
    R.loc[R.ym < "2018-04", class_cols("V20") + ["V20"]] = 0
    lam = 0.1 * R.Vf1 + 0.3 * R.Vf2 + 0.9 * R.Vf3 + 0.2 * R.Vf0 + 0.05
    R["Y"] = rng.poisson(lam * np.where(R.dn == "N", 0.6, 1.0))
    R["year"] = R.ym.str[:4].astype(int)
    R["moy"] = R.ym.str[5:7].astype(int)
    R["rid"] = R.region.str[3:].astype(int)
    R["cid"] = pd.factorize(R.region + ":" + R.cell)[0]
    R["dnN"] = (R.dn == "N").astype(int)
    R["ix"] = R.cell.str.split("_").str[0].astype(int)
    R["iy"] = 0
    return add_groups(R, n_regions)


def fit_mask(R):
    return (R.ym <= "2019-12").to_numpy()


def test_classes():
    frp = np.array([-1.0, 0.0, 0.01, 4.99, 5.0, 19.99, 20.0, 300.0, np.nan])
    assert frp_class(frp).tolist() == [0, 0, 1, 1, 2, 2, 3, 3, 0]
    scan = np.array([0.32, 0.49, 0.5, 0.6, 0.65, 0.66, 0.8])
    assert scan_class(scan).tolist() == [0, 0, 1, 1, 1, 2, 2]
    print("FRP classes (<= 0 | 0-5 | 5-20 | >= 20 MW) and scan classes (< 0.5 | 0.5-0.65 | > 0.65 km): ok")


def test_class_a2_one_class_is_a2():
    R = toy()
    tr = fit_mask(R)
    rows = np.flatnonzero(~tr)
    for a in (10, 30, 1000):
        f = fit_class_a2(R, tr, ["V"], a)
        got = predict_class_a2(R, rows, f)
        want = predict_A2(R, rows, fit_A2(R, tr), a)
        assert all(np.allclose(g, w) for g, w in zip(got, want)), a
    print("C3/C4 with a single class = A2 (kind, size, p identical), a in 10/30/1000: ok")


def test_class_a2_hand():
    """Rows never mix FRP classes: the allocation is exact, so each class is an A2 on its own rows, by hand."""
    R = toy(mixed=False)
    tr = fit_mask(R)
    rows = np.flatnonzero(~tr)
    cols = class_cols("V")[:4]
    a = 30
    f = fit_class_a2(R, tr, cols, a)
    k_, a_, b_ = predict_class_a2(R, rows, f)
    got = mean_of((k_, a_, b_))
    want = np.zeros(len(rows))
    pos = tr & (R.V > 0).to_numpy()
    for j, i in enumerate(rows):
        x = R.iloc[i]
        same_g = tr & (R.moy == x.moy).to_numpy() & (R.dn == x.dn).to_numpy()
        if x.V == 0:
            want[j] = R.Y[same_g & (R.V == 0).to_numpy()].mean()
            continue
        k = int(np.argmax([x[c] for c in cols]))
        own = pos & (R[cols[k]] > 0).to_numpy()
        sv_g = R[cols[k]][same_g].sum()
        if sv_g > 0:
            r0 = R.Y[same_g & own].sum() / sv_g
        else:
            same_d = tr & (R.dn == x.dn).to_numpy()
            r0 = R.Y[same_d & own].sum() / R[cols[k]][same_d].sum()
        cell = same_g & (R.cid == x.cid).to_numpy()
        sy, sv = R.Y[cell & own].sum(), R[cols[k]][cell].sum()
        want[j] = x[cols[k]] * (a + sy) / (a / r0 + sv) if r0 > 0 else 0.0
    err = np.max(np.abs(got - want))
    print(f"C3 on rows of one class each: mean vs hand A2 per class over {len(rows)} rows, max abs diff {err:.2e}")
    assert err < 1e-9


def test_class_a2_fixed_point():
    R = toy()
    tr = fit_mask(R)
    for name, cols in (("C3", class_cols("V")[:4]), ("C4", class_cols("V")[4:])):
        f = fit_class_a2(R, tr, cols, 30)
        # at the fixed point the allocated class sums add back to each cell's Y on V > 0 rows ...
        cmd = R.cmd.to_numpy()
        pos = tr & (R.V > 0).to_numpy()
        sy_cell = np.bincount(cmd[pos], R.Y.to_numpy()[pos].astype(float), len(f["SY"]))
        assert np.allclose(f["SY"].sum(1), sy_cell)
        # ... and every row's share is proportional to V_k times the class's posterior mean
        Vk = R[cols].to_numpy().astype(float)
        rm = np.arange(len(f["SY"])) % 24  # one region: rmd = calendar month x day/night
        with np.errstate(divide="ignore", invalid="ignore"):
            rate = 30 / f["r0"][rm] + f["SV"]
            post = np.where(np.isinf(rate), 0, (30 + f["SY"]) / rate)
        share = Vk[pos] * post[cmd[pos]]
        tot = share.sum(1, keepdims=True)
        share = np.where(tot > 0, share / np.where(tot > 0, tot, 1), Vk[pos] / Vk[pos].sum(1, keepdims=True))
        sy_again = np.stack([np.bincount(cmd[pos], R.Y.to_numpy()[pos] * share[:, k], len(f["SY"]))
                             for k in range(len(cols))], 1)
        err = np.max(np.abs(sy_again - f["SY"])) / np.max(f["SY"])
        assert f["em_iterations"] < EM_ITERS and err < 1e-4, (f["em_iterations"], err)
        print(f"{name}: allocation at its fixed point after {f['em_iterations']} iterations (max abs diff / max class "
              f"sum {err:.1e}); class sums add up to Y: ok")


def test_c5_hand():
    R = toy(n_cells=5)
    tr = fit_mask(R)
    rows = np.flatnonzero(~tr)
    nb = neighbours(R)
    assert nb.sum() == 5 + 2 * 4  # a row of five cells: each has itself and its east / west neighbours
    f = fit_c5_sums(R, tr, nb)
    a, an = 30, 100
    got = mean_of(predict_c5(R, rows, f, a, an))
    want = np.zeros(len(rows))
    for j, i in enumerate(rows):
        x = R.iloc[i]
        g = tr & (R.moy == x.moy).to_numpy() & (R.dn == x.dn).to_numpy()
        if x.V == 0:
            want[j] = R.Y[g & (R.V == 0).to_numpy()].mean()
            continue
        posg = g & (R.V > 0).to_numpy()
        r0 = R.Y[posg].sum() / R.V[g].sum()
        near = g & (np.abs(R.ix - x.ix) <= 1).to_numpy()
        r_nb = (an + R.Y[near & (R.V > 0).to_numpy()].sum()) / (an / r0 + R.V[near].sum())
        cell = g & (R.cid == x.cid).to_numpy()
        want[j] = x.V * (a + R.Y[cell & (R.V > 0).to_numpy()].sum()) / (a / r_nb + R.V[cell].sum())
    err = np.max(np.abs(got - want))
    print(f"C5 mean vs explicit 3x3 neighbourhood sums over {len(rows)} rows: max abs diff {err:.2e}")
    assert err < 1e-9
    # a very strong neighbourhood prior gives back A2
    k1, a1, b1 = predict_c5(R, rows, f, 30, 1e12)
    k2, a2, b2 = predict_A2(R, rows, fit_A2(R, tr), 30)
    assert (k1 == k2).all() and np.allclose(a1, a2) and np.allclose(b1, b2, rtol=1e-6)
    print("C5 with a_n -> infinity = A2: ok")


def test_c6():
    rng = np.random.default_rng(3)
    n = 60_000
    X = np.where(rng.random((n, 3)) < 0.7, 0, rng.integers(1, 6, (n, 3))).astype(float)
    f1, f2 = rng.integers(0, 4, n), rng.integers(0, 3, n)
    beta, g, d, alpha = np.array([2.0, 5.0, 12.0]), np.array([-3.0, -2.5, -2.0, -3.5]), np.array([0.0, 0.4, -0.3]), 0.8
    mu = (X @ beta + 1) * np.exp(g[f1] + d[f2])
    y = rng.poisson(mu * rng.gamma(1 / alpha, alpha, n)).astype(float)
    p = np.r_[np.log(beta), g, d[1:], np.log(alpha)] + rng.normal(0, 0.1, 3 + 4 + 2 + 1)
    w = np.ones(n)
    num = approx_fprime(p, lambda q: nbreg.negloglik(q, y, X, f1, f2, 4, 2, w)[0], 1e-6)
    ana = nbreg.negloglik(p, y, X, f1, f2, 4, 2, w)[1]
    assert np.max(np.abs(num - ana)) < 1e-2 * max(1, np.max(np.abs(ana))), (num, ana)
    fit_ = nbreg.fit(y, X, f1, f2, 4, 2)
    print(f"C6 NB regression: gradient = numerical; beta {np.round(fit_['beta'], 2)} (true {beta}), "
          f"delta {np.round(fit_['delta'], 2)} (true {d[1:]}), alpha {fit_['alpha']:.3f} (true {alpha})")
    assert np.allclose(fit_["beta"], beta, rtol=0.15) and np.allclose(fit_["delta"], d[1:], atol=0.08)
    assert abs(fit_["alpha"] - alpha) < 0.1
    # the candidate's mean is (sum beta_k V_k + 1) exp(gamma[md] + shrunk region effect), by hand
    R = toy(n_regions=3)
    tr = fit_mask(R)
    f = fit_c6(R, tr)
    rows = np.flatnonzero(~tr)
    x = R.iloc[rows]
    want = (x[class_cols("V")].to_numpy() @ f["beta"] + 1) * np.exp(f["gamma"][x.md] + f["region_shrunk"][x.rid])
    assert np.allclose(mu_c6(R, rows, f), want) and np.allclose(mean_of(forecast({"name": "C6", "fit": f}, R, rows)),
                                                                 want)
    assert abs(f["region_raw"].sum()) < 1e-9 and np.all(np.abs(f["region_shrunk"]) <= np.abs(f["region_raw"]) + 1e-12)
    print(f"C6 on a three-region toy: mean = (X beta + 1) exp(gamma + shrunk region effect); region effects centred "
          f"and shrunk (tau2 {f['eb']['tau2']:.4f}): ok")


def test_c7():
    R = toy(n_regions=2)
    tr = fit_mask(R)
    h = history_ratio(R, tr)
    cid = 3
    sel = tr & (R.cid == cid).to_numpy() & (R.V > 0).to_numpy()
    assert abs(h[cid] - R.Y[sel].sum() / R.V[sel].sum()) < 1e-12
    scored = np.ones(len(R), bool)
    f = fit_c7(R, tr, scored, list(range(2012, 2020)))
    rows = np.flatnonzero(~tr)
    m = mean_of(forecast({"name": "C7", "fit": f}, R, rows))
    assert np.all(m > 0) and np.all(np.isfinite(f["alpha"]))
    print(f"C7 ({f['backend']}): history ratio by hand ok; means > 0; alpha per region x day/night from inner "
          f"residuals {np.round(f['alpha'], 3)}")


def test_c8():
    v = np.array([0, 0, 0, 0, 1, 1, 2, 5])
    y = np.array([0, 0, 0, 1, 0, 2, 3, 9])
    vals, means = qm_table(v, y)
    # sorted y: 0 0 0 0 1 2 3 9 ; V = 0 takes ranks 0-3, V = 1 ranks 4-5, V = 2 rank 6, V = 5 rank 7
    assert vals.tolist() == [0, 1, 2, 5] and np.allclose(means, [0, 1.5, 3, 9])
    got = qm_apply(vals, means, np.array([0, 0.5, 1, 3.5, 5, 10]))
    assert np.allclose(got, [0, 0.75, 1.5, 6, 9, 18])
    R = toy()
    tr = fit_mask(R)
    f = fit_c8(R, tr)
    rows = np.flatnonzero(tr)
    m = mean_of(forecast({"name": "C8", "fit": f}, R, rows))
    for k in (0, 1):
        sel = R.rd.to_numpy()[rows] == k
        assert abs(m[sel].sum() - R.Y.to_numpy()[rows][sel].sum()) < 1e-6  # band means keep the training total
    vv = np.linspace(0, 40, 400)
    assert np.all(np.diff(qm_apply(*f["maps"][0], vv)) >= -1e-12)
    print("C8: band means by hand; linear between values; proportional above the largest; monotone; training total "
          "kept per region x day/night: ok")


def test_floor():
    mu = np.array([0.0, 0.05, 0.7, 3.0, 40.0])
    got = poisson_floor(mu)
    for m, g in zip(mu, got):
        if m == 0:
            assert g == 0
            continue
        ys = np.arange(int(poisson.ppf(1 - 1e-12, m)) + 2)
        pm = poisson.pmf(ys, m)
        cr = score(np.ones(len(ys), int), np.full(len(ys), m), np.zeros(len(ys)), ys)["crps"]
        assert abs(np.sum(pm * cr) - g) < 1e-8, (m, g, np.sum(pm * cr))
    print(f"Poisson floor = E over y ~ Pois(mu) of the summed CRPS, for mu {mu.tolist()}: {np.round(got, 4).tolist()}: ok")


def test_swap_view():
    R = toy()
    sfit = {"s": np.array([0.9, 1.2])}
    S = swap_view(R, sfit)
    s_row = np.where(R.dnN == 1, 1.2, 0.9)
    assert np.allclose(S.V, s_row * R.V20) and np.allclose(S.Vf2, s_row * R.V20f2) and (S.Y == R.Y).all()
    print("J-S view: every Suomi NPP column = s x the NOAA-20 column; Y untouched: ok")


def test_refuse_late():
    R = toy(n_regions=2)
    tr = fit_mask(R)
    late = tr | (R.ym == "2020-01").to_numpy()
    scored = np.ones(len(R), bool)
    years = list(range(2012, 2020))
    for name in CANDIDATES:
        try:
            fit(name, R, late, scored, years, "t")
        except ValueError as e:
            print(f"{name}: refused ({e})")
        else:
            raise AssertionError(f"{name} accepted a 2020 row")
    low = {"fit_class_a2 (C3)": lambda m: fit_class_a2(R, m, class_cols("V")[:4], 30),
           "fit_class_a2 (C4)": lambda m: fit_class_a2(R, m, class_cols("V")[4:], 30),
           "fit_c5_sums": lambda m: fit_c5_sums(R, m), "fit_c6": lambda m: fit_c6(R, m),
           "fit_c7": lambda m: fit_c7(R, m, scored, years), "fit_c8": lambda m: fit_c8(R, m)}
    for name, f in low.items():
        try:
            f(late)
        except ValueError as e:
            print(f"{name} called directly: refused ({e})")
        else:
            raise AssertionError(f"{name} accepted a 2020 row")
    # and every candidate still predicts 2020 rows from a 2012-2019 fit
    rows = np.flatnonzero(~tr)
    for name in CANDIDATES:
        m = fit(name, R, tr, scored, years, "t")
        assert np.all(np.isfinite(mean_of(forecast(m, R, rows))))
    print("every candidate fitted on 2012-2019 predicts 2020 rows: ok")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    test_classes()
    test_class_a2_one_class_is_a2()
    test_class_a2_hand()
    test_class_a2_fixed_point()
    test_c5_hand()
    test_c6()
    test_c7()
    test_c8()
    test_floor()
    test_swap_view()
    test_refuse_late()
    print("ALL TOURNAMENT TESTS PASSED")
