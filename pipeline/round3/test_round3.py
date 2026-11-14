"""Hand checks of the round-3 runner on toy tables, plus its refusals.

    python -m pipeline.round3.test_round3
    python -m pipeline.tournament.test_tournament   # C3 itself (D-a's code), unchanged
    python -m pipeline.round2.test_round2           # R1 (F1), s for J-S, totals(), unchanged

The frozen file is refused when its bytes change; sealed regions are refused without the flag, and the flag runs only
the four sealed regions (both before any file is opened); completeness lists every missing 2012-2025 file; D-a's
class terms add up to its mean and its f0 part is the FRP <= 0 term; J-S is linear in s so k * s is the mean; every
fit refuses rows after 2019-12; the swap metrics and the f0 list against hand numbers. With the tournament's table on
disk, round 3's rows for one development region reproduce the tournament's rows up to 2021-12.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from pipeline.round2 import data as r2
from pipeline.round2.models import fit_s, rng_for, totals
from pipeline.tournament.candidates import predict_class_a2
from pipeline.tournament.test_tournament import toy

from . import data, confirm
from .confirm import f0_tail, swap_metrics, swap_table
from .model import class_means, fit_frozen, forecast, js_parts, parts

FZ = {"champion_json": {"burning_days_model": {"frozen_setting": 10}}}
_scratch = tempfile.TemporaryDirectory(prefix="cedrus-round3-test-")
SCRATCH = Path(_scratch.name)


def fit_mask(T):
    return (T.ym <= "2019-12").to_numpy()


def test_frozen_sha():
    fz, sha = data.load_frozen()
    assert sha == data.FROZEN_SHA256 and fz["entrant"] == "D-a"
    assert fz["champion_json"]["burning_days_model"]["frozen_setting"] == 10
    SCRATCH.mkdir(parents=True, exist_ok=True)
    bad = SCRATCH / "frozen_round3_altered.json"
    shutil.copyfile(data.FROZEN, bad)
    bad.write_bytes(bad.read_bytes().replace(b'"frozen_setting": 10', b'"frozen_setting": 30'))
    try:
        data.load_frozen(bad)
    except SystemExit as e:
        assert "refused" in str(e) and "SHA-256" in str(e), e
        print(f"altered frozen file: {e}")
    else:
        raise AssertionError("an altered frozen_round3.json was accepted")
    print(f"frozen_round3.json SHA-256 {sha}: ok")


def test_complete():
    full = {(s, y): True for s in r2.STEMS for y in range(r2.FIRST_YEAR[s], data.LAST_YEAR + 1)}
    assert data.complete(full) == []
    assert len(full) == 14 + 14 + 8
    gap = dict(full)
    gap[("noaa20", 2025)] = False
    del gap[("modis", 2013)]
    assert sorted(data.complete(gap)) == [("modis", 2013), ("noaa20", 2025)]
    print("completeness: MODIS and Suomi NPP 2012-2025 and NOAA-20 2018-2025 (36 files), gaps listed: ok")


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "pipeline.round3.confirm", *args], cwd=r2.ROOT, capture_output=True,
                          text=True, timeout=120)


def test_refusals():
    """Historical sealed-role fixture: current product regions may already be spent.

    Assert refusals before any frozen model or raw input can be read.
    """
    sealed = {"northern_algeria", "southern_france", "south_australia", "n_california"}
    fixture = {r: dict(v, roles={"sealed"} if r in sealed else {"dev"})
               for r, v in confirm.REGIONS.items()}
    cases = ((["--regions", "northern_algeria"], "refused: northern_algeria sealed"),
             (["--regions", "portugal", "n_california"], "refused: n_california sealed"),
             (["--i-am-the-lead-running-it-once", "--regions", "portugal"], "runs exactly the four sealed"),
             (["--i-am-the-lead-running-it-once", "--regions", "northern_algeria"], "runs exactly the four sealed"))
    for args, want in cases:
        with patch.dict(confirm.REGIONS, fixture, clear=True), \
             patch.object(sys, "argv", ["confirm", *args]), \
             patch.object(data, "load_frozen", side_effect=AssertionError("Read model before refusal")):
            try:
                confirm.main()
            except SystemExit as exc:
                assert want in str(exc), (args, str(exc))
                print(f"{' '.join(args)}: {exc}")
            else:
                raise AssertionError(f"Expected refusal: {args}")


def test_class_terms():
    T = toy()
    tr = fit_mask(T)
    m = fit_frozen(FZ, T, tr, ("t",))
    rows = np.flatnonzero((T.year >= 2019).to_numpy())
    mk = class_means(T, rows, m["fit"])
    p = parts(m, T, rows)
    pos = T.V.to_numpy()[rows] > 0
    assert np.allclose(mk.sum(1)[pos], p["mean"][pos]) and (mk[~pos] == 0).all()
    assert np.allclose(p["f0"], mk[:, 0])
    # hand: the f0 term of one row with Vf0 > 0
    f = m["fit"]
    i = rows[np.flatnonzero(T.Vf0.to_numpy()[rows] > 0)[0]]
    rmd, cmd = T.rmd.iloc[i], T.cmd.iloc[i]
    hand = T.Vf0.iloc[i] * (10 + f["SY"][cmd, 0]) / (10 / f["r0"][rmd, 0] + f["SV"][cmd, 0])
    j = int(np.flatnonzero(rows == i)[0])
    assert abs(p["f0"][j] - hand) < 1e-9, (p["f0"][j], hand)
    # V = 0 rows predict b_A and have no f0 part
    assert np.allclose(p["mean"][~pos], f["bA"][T.rmd.to_numpy()[rows][~pos]])
    # the forecast is C3's own
    k_, a_, b_ = forecast(m, T, rows)
    k2, a2, b2 = predict_class_a2(T, rows, m["fit"])
    assert (k_ == k2).all() and np.allclose(a_, a2) and np.allclose(b_, b2)
    assert m["fit"]["a"] == 10 and m["setting"] == 10 and m["inner"] is None
    print(f"D-a (a = 10, not tuned): class terms add up to the mean on {pos.sum()} V > 0 rows; f0 part by hand "
          f"{hand:.4f}: ok")


def test_js_linear():
    T = toy()
    tr = fit_mask(T)
    m = fit_frozen(FZ, T, tr, ("t",))
    n20 = ((T.ym >= "2018-04") & (T.ym <= "2019-12")).to_numpy()
    sfit = fit_s(T, n20, rng_for("t", "J-S"))
    rows = np.flatnonzero((T.year == 2020).to_numpy())
    p = js_parts(m, T, rows, sfit)
    s_row = sfit["s"][T.rd.to_numpy()[rows]]
    live = T.V20.to_numpy()[rows] > 0
    assert np.allclose(p["k"][live] * s_row[live], p["mean"][live]) and (p["k"][~live] == 0).all()
    s2 = dict(sfit, s=2 * sfit["s"])
    p2 = js_parts(m, T, rows, s2)
    assert np.allclose(p2["mean"][live], 2 * p["mean"][live]) and np.allclose(p2["mean"][~live], p["mean"][~live])
    assert np.allclose(p2["f0"][live], 2 * p["f0"][live])
    # the totals' s-bootstrap variance by hand: var over replicates of sum_k k * s*
    g = swap_table(T, rows, m, sfit)
    unit = pd.factorize(T.region.to_numpy()[rows].astype(object) + "|" + T.ym.to_numpy()[rows].astype(object))[0]
    tN, nbN, pvN = totals(p, unit, len(g), sfit["s_boot"])
    hand = np.array([[np.sum(p["k"][unit == u] * sfit["s_boot"][b, p["h"][unit == u]]) for u in range(len(g))]
                     for b in range(sfit["s_boot"].shape[0])]).var(axis=0, ddof=1)
    assert np.allclose(pvN, hand) and np.allclose(g.pvar_N, hand) and (g.pvar_S == 0).all()
    assert np.allclose(g.tot_N, tN) and np.allclose(g.f0_N, np.bincount(unit, p["f0"], len(g)))
    print(f"J-S: mean = k * s on {live.sum()} rows, doubling s doubles mean and f0 part, s-bootstrap variance of "
          "the totals by hand: ok")


def test_refuse_late():
    T = toy()
    late = fit_mask(T) | (T.ym == "2020-01").to_numpy()
    try:
        fit_frozen(FZ, T, late, ("t",))
    except ValueError as e:
        print(f"D-a refit: refused ({e})")
    else:
        raise AssertionError("D-a accepted a 2020 row")


def test_swap_metrics():
    g = pd.DataFrame({"tot_S": [10.0, 20.0, 5.0, 0.0, 40.0, 100.0], "tot_N": [10.0, 10.0, 5.0 * np.e, 3.0, 40.0, 50.0]})
    s = swap_metrics(g)
    lg = np.array([0.0, np.log(2), 1.0, 0.0, np.log(2)])  # both > 0: rows 0, 1, 2, 4, 5
    assert s["used_pos"] == 5 and abs(s["median_pos"] - np.median(lg)) < 1e-12
    assert abs(s["p90_pos"] - np.quantile(lg, 0.9)) < 1e-12 and abs(s["max_pos"] - 1.0) < 1e-12
    assert s["used_ge10"] == 4 and abs(s["median_ge10"] - np.log(2) / 2) < 1e-12
    print(f"swap metrics by hand (median {s['median_pos']:.4f}, p90 {s['p90_pos']:.4f}): ok")


def test_f0_tail():
    t1 = pd.DataFrame({"region": ["x", "x", "x", "y"], "ym": ["2020-01", "2020-01", "2020-02", "2020-01"],
                       "mean_M": [10.0, 2.0, 4.0, 0.0], "f0_M": [3.0, 0.1, 1.0, 0.0], "Y": [5, 1, 3, 0],
                       "V": [7, 1, 2, 0], "Vf0": [1, 0, 1, 0]})
    t2 = pd.DataFrame({"region": ["x"], "ym": ["2021-03"], "tot_S": [8.0], "f0_S": [2.0], "tot_N": [8.0],
                       "f0_N": [2.1], "V": [5], "Vf0": [1], "V20": [6], "V20f0": [1]})
    fl, counts = f0_tail(t1, t2)
    got = sorted(zip(fl.source, fl.ym, fl.share.round(4)))
    assert got == [("Test 1, Suomi NPP", "2020-01", round(3.1 / 12, 4)), ("Test 2, NOAA-20-based (J-S)", "2021-03",
                                                                          round(2.1 / 8, 4))], got
    assert counts == {"Test 1, Suomi NPP": 2, "Test 2, Suomi NPP-based": 1, "Test 2, NOAA-20-based (J-S)": 1}, counts
    print("f0 list: 25.8% and 26.3% listed, 25.0% (not more than 25%) and 25.0% not, zero totals skipped: ok")


def test_rows_match_tournament(region="portugal"):
    """Round 3's rows for one development region, up to 2021-12, against the tournament's own table."""
    tab = data.td.OUT / "table.pkl"
    if not tab.exists():
        print(f"rows against the tournament: skipped ({tab} not on disk)")
        return
    R3, _ = data.rows(region, data.pixels(region))
    Rt = pd.read_pickle(tab)["R"]
    Rt = Rt[Rt.region == region]
    R3 = R3[R3.ym <= data.td.LAST_MONTH]
    cols = [c for c in R3.columns if c in Rt.columns]
    key = ["cell", "ym", "dn"]
    a = R3[cols].sort_values(key).reset_index(drop=True)
    b = Rt[cols].sort_values(key).reset_index(drop=True)
    assert len(a) == len(b) and set(a.cell) == set(b.cell), (len(a), len(b))
    for c in cols:
        assert (a[c].astype(str).to_numpy() == b[c].astype(str).to_numpy()).all(), c
    print(f"rows against the tournament ({region}, up to 2021-12): {len(a):,} rows, {len(cols)} columns identical: ok")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    test_frozen_sha()
    test_complete()
    test_refusals()
    test_class_terms()
    test_js_linear()
    test_refuse_late()
    test_swap_metrics()
    test_f0_tail()
    test_rows_match_tournament()
    print("all round-3 checks passed")
