"""Hand checks of the round-2 pieces on a toy table.

    python -m pipeline.round2.test_round2
    python -m pipeline.bakeoff.test_nb      # the bake-off's NB2 / Poisson tests, still used for CRPS and A
    python -m pipeline.bakeoff.test_crps

R1 / Rm predictive means against hand sums; A2's sums over V > 0 rows only; every fit refuses rows after 2019-12
while the swap still scores 2020 rows; the moment-matched negative binomial; alpha by maximum likelihood; the
parameter variance of a total.
"""
import numpy as np
import pandas as pd
from scipy.stats import nbinom

from pipeline.bakeoff.models import add_groups
from pipeline.bakeoff.scores import score
from pipeline.bakeoff.test_crps import crps_kernel

from .models import (fit_A2, fit_alpha, fit_model, fit_ratio, fit_s, js_parts, nb_from_moments, parts, ratio_parts,
                     rng_for, totals)
from .validate import swap_table


def toy(last="2020-12"):
    """One region, two cells, every month 2012-02..last, day and night, small made-up counts."""
    rng = np.random.default_rng(7)
    months = [str(p) for p in pd.period_range("2012-02", last, freq="M")]
    idx = pd.MultiIndex.from_product([["0_0", "1_0"], months, ["D", "N"]], names=["cell", "ym", "dn"])
    R = idx.to_frame(index=False)
    n = len(R)
    R["V"] = np.where(rng.random(n) < 0.4, 0, rng.integers(1, 9, n))
    R["Y"] = rng.poisson(0.4 * R.V + 0.2)
    R["V20"] = np.where(R.ym >= "2018-04", np.where(rng.random(n) < 0.4, 0, rng.integers(1, 9, n)), 0)
    R["year"] = R.ym.str[:4].astype(int)
    R["moy"] = R.ym.str[5:7].astype(int)
    R.insert(0, "region", "toy")
    R["rid"] = 0
    R["cid"] = pd.factorize(R.cell)[0]
    R["dnN"] = (R.dn == "N").astype(int)
    return add_groups(R, 1)


def test_ratio_means():
    R = toy()
    tr = (R.ym <= "2019-12").to_numpy()
    rows = np.flatnonzero(~tr)  # 2020: scored, never fitted
    for per_month in (False, True):
        f = fit_ratio(R, tr, per_month, rng_for("test"))
        p = ratio_parts(R, rows, f)
        want = np.zeros(len(rows))
        for j, i in enumerate(rows):
            x = R.iloc[i]
            same = tr & (R.dn == x.dn).to_numpy() & ((R.moy == x.moy).to_numpy() if per_month else True)
            if x.V > 0:
                pos = same & (R.V > 0).to_numpy()
                want[j] = R.Y[pos].sum() / R.V[pos].sum() * x.V
            else:
                want[j] = R.Y[same & (R.V == 0).to_numpy()].mean()
        err = np.max(np.abs(p["mean"] - want))
        print(f"{'Rm' if per_month else 'R1'} predictive mean vs hand sums over {len(rows)} rows: max abs diff {err:.2e}")
        assert err < 1e-12
        # the predictive variance is the NB variance plus V^2 Var(r), with Var(r) the variance over the replicates
        g = R.rmd.to_numpy()[rows] if per_month else R.rd.to_numpy()[rows]
        V = R.V.to_numpy()[rows]
        alpha = f["alpha"][R.rd.to_numpy()[rows]]
        want_var = want + alpha * want ** 2 + np.where(V > 0, V ** 2 * f["r_boot"][:, g].var(axis=0, ddof=1), 0)
        assert np.allclose(p["nbvar"] + p["pvar"], want_var)
    print("R1 / Rm predictive variance = NB variance + V^2 Var(r): ok")


def test_bootstrap_by_hand():
    R = toy()
    tr = (R.ym <= "2019-12").to_numpy()
    f = fit_ratio(R, tr, False, rng_for("boot"))
    # redo replicate 0 by hand: same generator, same draw of years
    rng = rng_for("boot")
    years = sorted(set(R.year[tr]))
    pick = rng.integers(0, len(years), (200, len(years)))[0]
    pos = tr & (R.V > 0).to_numpy()
    for d in (0, 1):
        sy = sum(R.Y[pos & (R.year == years[k]).to_numpy() & (R.dnN == d).to_numpy()].sum() for k in pick)
        sv = sum(R.V[pos & (R.year == years[k]).to_numpy() & (R.dnN == d).to_numpy()].sum() for k in pick)
        assert abs(f["r_boot"][0, d] - sy / sv) < 1e-12
    print(f"year-block bootstrap replicate 0 rebuilt by hand from years {[years[k] for k in pick]}: ok")


def test_a2_sums():
    R = toy()
    tr = (R.ym <= "2019-12").to_numpy()
    f = fit_A2(R, tr)
    pos = tr & (R.V > 0).to_numpy()
    zero = tr & (R.V == 0).to_numpy()
    for moy in (1, 7):
        for d in (0, 1):
            grp = (R.moy == moy).to_numpy() & (R.dnN == d).to_numpy()
            k = (moy - 1) * 2 + d
            assert abs(f["r0"][k] - R.Y[pos & grp].sum() / R.V[tr & grp].sum()) < 1e-12
            assert abs(f["bA"][k] - R.Y[zero & grp].mean()) < 1e-12
            cell = grp & (R.cid == 1).to_numpy()
            assert f["SY"][24 + k] == R.Y[pos & cell].sum() and f["SV"][24 + k] == R.V[tr & cell].sum()
    print("A2: r0 and cell sums count Y on V > 0 rows only; b_A is the mean Y of V = 0 rows: ok")


def test_refuse_late():
    R = toy()
    tr = (R.ym <= "2019-12").to_numpy()
    late = tr | (R.ym == "2020-01").to_numpy()
    n20 = ((R.ym >= "2018-04") & (R.ym <= "2019-12")).to_numpy()
    scored = np.ones(len(R), bool)
    fits = {
        "R1": lambda m: fit_model("R1", R, m, rng_for("t")),
        "Rm": lambda m: fit_model("Rm", R, m, rng_for("t")),
        "A2": lambda m: fit_model("A2", R, m, rng_for("t"), a=30),
        "A2 tuned": lambda m: fit_model("A2", R, m, rng_for("t"), inner_years=[2018, 2019], scored=scored),
        "R1 on NOAA-20 (J-M)": lambda m: fit_model("R1", R, m & n20 | (R.ym == "2020-02").to_numpy(), rng_for("t"),
                                                   vcol="V20"),
        "s (J-S)": lambda m: fit_s(R, m & n20 | (R.ym == "2020-03").to_numpy(), rng_for("t")),
    }
    for name, fit in fits.items():
        try:
            fit(late)
        except ValueError as e:
            print(f"{name}: refused ({e})")
        else:
            raise AssertionError(f"{name} accepted a 2020 row")
    # the swap window is scored with fits that never saw it
    for name in ("R1", "Rm", "A2"):
        mS = fit_model(name, R, tr, rng_for("s"), a=30)
        mN = fit_model(name, R, n20, rng_for("n"), vcol="V20", a=30)
        sf = fit_s(R, n20, rng_for("j"))
        rows = np.flatnonzero((R.year == 2020).to_numpy())
        a, b = swap_table(R, rows, mS, mN), swap_table(R, rows, mS, None, sf)
        assert len(a) == 12 and len(b) == 12 and np.isfinite(a.tot_N).all() and np.isfinite(b.hi_N).all()
    print("swap tables on 2020 rows from fits on 2012-2019 / 2018-04..2019-12: ok")


def test_moment_nb():
    mean = np.array([0.0, 0.3, 2.0, 2.0, 15.0, 40.0])
    var = np.array([0.0, 0.3, 2.0, 5.0, 60.0, 900.0])
    kind, a, b = nb_from_moments(mean, var)
    assert kind.tolist() == [0, 1, 1, 2, 2, 2]
    for k, aa, bb, m, v in zip(kind, a, b, mean, var):
        if k == 2:
            assert abs(nbinom.mean(aa, bb) - m) < 1e-9 and abs(nbinom.var(aa, bb) - v) < 1e-9
    y = np.array([0, 1, 4, 0, 30, 3])
    got = score(kind, a, b, y)["crps"]
    for k, aa, bb, t, g in zip(kind, a, b, y, got):
        if k == 2:
            ref = crps_kernel(nbinom.pmf(np.arange(4000), aa, bb), t)
            assert abs(g - ref) < 1e-6, (g, ref)
    print("moment-matched negative binomial: mean and variance exact; summed CRPS = kernel CRPS: ok")


def test_alpha():
    rng = np.random.default_rng(11)
    mu = rng.choice([0.05, 0.4, 2.0, 9.0], 200_000)
    for alpha in (0.3, 1.5):
        y = rng.poisson(mu * rng.gamma(1 / alpha, alpha, len(mu)))
        got = fit_alpha(y.astype(float), mu)
        print(f"alpha true {alpha} fit {got:.4f}")
        assert abs(got - alpha) < 0.05 * alpha
    y = rng.poisson(mu)
    assert fit_alpha(y.astype(float), mu) < 0.02
    print("alpha by maximum likelihood with the means held fixed: ok")


def test_total_variance():
    R = toy()
    tr = (R.ym <= "2019-12").to_numpy()
    n20 = ((R.ym >= "2018-04") & (R.ym <= "2019-12")).to_numpy()
    f = fit_ratio(R, tr, False, rng_for("tv"))
    rows = np.flatnonzero((R.year == 2020).to_numpy())
    unit = np.zeros(len(rows), int)  # one unit: the whole year
    p = ratio_parts(R, rows, f)
    _, _, pv = totals(p, unit, 1)
    V, d = R.V.to_numpy()[rows], R.dnN.to_numpy()[rows]
    W = np.array([V[d == 0].sum(), V[d == 1].sum()])
    want = np.var(f["r_boot"] @ W, ddof=1)  # sum_d r*_d W_d per replicate
    assert abs(pv[0] - want) < 1e-9 * max(1, want)
    sf = fit_s(R, n20, rng_for("sv"))
    pj = js_parts(f, R, rows, sf)
    _, _, pvj = totals(pj, unit, 1, sf["s_boot"])
    V20 = R.V20.to_numpy()[rows]
    W20 = np.array([V20[d == 0].sum(), V20[d == 1].sum()])
    want = np.var((f["r_boot"] * sf["s_boot"]) @ W20, ddof=1)
    assert abs(pvj[0] - want) < 1e-9 * max(1, want)
    assert np.allclose(pj["mean"].sum(), (f["r"] * sf["s"] * W20).sum() + pj["mean"][V20 == 0].sum())
    print(f"parameter variance of a total = variance of sum(r* W) over replicates ({pv[0]:.3f}); "
          f"J-S with r* s* ({pvj[0]:.3f}): ok")


if __name__ == "__main__":
    test_ratio_means()
    test_bootstrap_by_hand()
    test_a2_sums()
    test_refuse_late()
    test_moment_nb()
    test_alpha()
    test_total_variance()
    print("ALL ROUND-2 TESTS PASSED")
