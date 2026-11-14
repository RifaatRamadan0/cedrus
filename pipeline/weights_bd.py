"""The burning-day model of the calendar's primary view: D-a, round-3 confirmed (docs/ROUND3_CONFIRMATION.md), with
NOAA-20 via Suomi NPP (J-S). Same interface spirit as weights_r2.py, in burning days instead of detections.

    model = fit(det, region)                     # never sees 2020 or later; a from frozen_round3.json only
    w     = burning_day_weights(model, rows)     # full MODIS-equivalent weight of each Suomi NPP / NOAA-20 burning day
    bg    = cell_month_background(model, grid)   # D-a's Poisson(b) where a covering satellite saw nothing
    p10, p90 = cell_month_interval(model, grid)  # D-a's predictive + the NOAA-20 calibration's uncertainty
    describe(model)

Burning day (the tournament's unit, pipeline/tournament/data.py): a 0.01 degree cell (floor(lon / 0.01),
floor(lat / 0.01)) counts once per date and day/night if it has any detection of the family (MODIS = Terra + Aqua
together; Suomi NPP; NOAA-20). It takes the FRP class of its largest-FRP detection: f0 FRP <= 0, f1 0 < FRP < 5,
f2 5 <= FRP < 20, f3 FRP >= 20 MW.

D-a is the tournament's C3 (one A2-style shrunk ratio per FRP class) in burning days, refitted here on the region's
own rows exactly as the round-3 exam refitted it: the rows are pipeline.round3.data.rows / burning_days, the fit is
pipeline.round3.model.fit_frozen with the frozen a, s is pipeline.round2.models.fit_s in burning days. Nothing is
re-implemented and nothing is tuned. data/processed/tournament/frozen_round3.json must have the SHA-256 recorded at the
freeze (pipeline.round3.data.load_frozen refuses anything else).

- Fitted on 2012-02..2019-12 only, over the fit's footprint: cells with a MODIS, Suomi NPP or NOAA-20 detection in
  that window (frozen by construction; a cell that first burns later gets the region-level ratio r0 of its slot and
  class).
- A Suomi NPP burning day of class k weighs D-a's posterior mean MODIS burning days per Suomi NPP burning day of that
  class in its cell x calendar month x day/night, (a + SY_k) / (a / r0_k + SV_k), 0 where r0_k = 0. D-a's mean is
  linear in the class counts, so these weights add up to its mean exactly.
- J-S: s = sum Suomi NPP / sum NOAA-20 burning days per day/night on 2018-04..2019-12 (month-block bootstrap for its
  variance); a NOAA-20 burning day weighs s x the Suomi NPP weight of its class.
- interval per cell-month: D-a's predictive (the class negative binomials summed and moment-matched for V > 0,
  Poisson(b) for V = 0) by day and night, plus, for NOAA-20, (mean / s)^2 x Var(s); the two satellites averaged with
  their shares (variance x share^2); 10th/90th percentile of the moment-matched negative binomial. Approximate: cells
  are treated as independent, though s is shared by every cell of the region.

`grid` columns: ci, moy, share_<s>_D / share_<s>_N, V_<s>_D / V_<s>_N (burning days) and V_<s>_<dn>_f0..f3 (burning
days by FRP class), for s in N, J1.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # the round-3 and tournament code import themselves as pipeline.*

from pipeline.round2.models import BOOT, fit_s, rng_for  # noqa: E402
from pipeline.round3 import data as r3  # noqa: E402
from pipeline.round3.model import fit_frozen, frozen_a, js_parts, parts  # noqa: E402
from pipeline.tournament.data import FINE, NF, NS, frp_class  # noqa: E402
from weights_r2 import moment_quantiles  # noqa: E402  (the same quantile rule as the hotspot view)

NAME = "D-a + NOAA-20 via Suomi NPP (burning days, round-3 confirmed)"
BADGE = "D-a · ROUND 3 CONFIRMED"
FROZEN_SHA256 = "f3130df9ed80894e0176866cd3c8e51a3c4a7233c3cb40dd1c7b93651d4357a2"  # docs/TOURNAMENT_RESULTS.md, Freeze
assert FROZEN_SHA256 == r3.FROZEN_SHA256, "weights_bd and pipeline/round3 disagree on the frozen file"
FZ, _ = r3.load_frozen()  # refuses unless the bytes are the frozen file
A = int(frozen_a(FZ))
WINDOWS = {"snpp": (r3.r2.FIRST_MONTH, r3.FIT_LAST), "noaa20": (r3.N20_FIRST, r3.FIT_LAST)}
TRAIN = WINDOWS  # read by export_v2 (drift band)
SAT = {"snpp": "N", "noaa20": "J1"}
CLASS_EDGES = "f0 FRP <= 0, f1 0 < FRP < 5, f2 5 <= FRP < 20, f3 FRP >= 20 MW"
PX_SENSOR = {"T": "terra", "A": "aqua", "N": "snpp", "J1": "noaa20"}


def fine_cells(det):
    """The burning-day cell of each detection: (floor(lon / 0.01), floor(lat / 0.01)), as the tournament."""
    return np.floor(det.longitude / FINE).astype(np.int64), np.floor(det.latitude / FINE).astype(np.int64)


def burning_class(frp_max):
    """FRP class of a burning day from its largest FRP (NaN when every detection's FRP is missing -> f0)."""
    return frp_class(frp_max)


def _px(det, region):
    """The export's detections as the tournament's pixel table (pipeline/tournament/data.py pixels())."""
    fx, fy = fine_cells(det)
    return pd.DataFrame({
        "sensor": det.sensor.map(PX_SENSOR).to_numpy(), "lat": det.latitude.to_numpy(), "lon": det.longitude.to_numpy(),
        "date": det.acq_date.to_numpy(), "dn": det.dn.to_numpy(),
        "frp": pd.to_numeric(det.frp, errors="coerce").to_numpy(), "scan": det.scan.to_numpy(),
        "cell": (det.ix.astype(str) + "_" + det.iy.astype(str)).to_numpy(),
        "fx": fx.astype(np.int32).to_numpy(), "fy": fy.astype(np.int32).to_numpy(),
        "ym": det.month.to_numpy(), "region": region})


def fit(det, region):
    """det needs the export's columns (month, moy, dn, sensor, longitude, latitude, acq_date, frp, scan, ix, iy) and ci
    (the export's cell index, 0..n_cells-1). Only rows inside the fit window are passed on."""
    for w in WINDOWS.values():
        assert w[1] <= "2019-12", "the burning-day model may not be fitted on 2020 or later"
    n_cells = int(det.ci.max()) + 1
    win = det[(det.month >= WINDOWS["snpp"][0]) & (det.month <= WINDOWS["snpp"][1])]
    assert win.month.max() <= "2019-12"
    px = _px(win, region)
    R, cover = r3.rows(region, px)                  # round 3's rows; cells = the window's cells (the fit footprint)
    T = r3.burning_days(R)                          # the one-region table in burning days
    train = (T.ym <= WINDOWS["snpp"][1]).to_numpy()
    m = fit_frozen(FZ, T, train, ("product", region, "D-a"))
    s_train = ((T.ym >= WINDOWS["noaa20"][0]) & (T.ym <= WINDOWS["noaa20"][1])).to_numpy()
    sfit = fit_s(T, s_train, rng_for("product", region, "J-S", "burning days"), n_boot=BOOT)
    f = m["fit"]
    first = np.unique(T.cid.to_numpy(), return_index=True)[1]
    fit_ix, fit_iy = T.ix.to_numpy()[first], T.iy.to_numpy()[first]
    by_xy = {(int(x), int(y)): k for k, (x, y) in enumerate(zip(fit_ix, fit_iy))}
    cells = det.groupby("ci")[["ix", "iy"]].first()
    unseen = len(first)  # one extra cell with no history stands for every cell outside the fit's footprint
    cmap = np.full(n_cells, unseen, int)
    for ci, (x, y) in cells.iterrows():
        cmap[ci] = by_xy.get((int(x), int(y)), unseen)
    pred = dict(f, SY=np.r_[f["SY"], np.zeros((24, NF))], SV=np.r_[f["SV"], np.zeros((24, NF))])
    pm = dict(m, fit=pred)
    # Per cell x calendar month x day/night x class: D-a's mean per burning day of that class (the class term of
    # pipeline.round3.model.class_means with one burning day of every class).
    ci, md = np.divmod(np.arange(n_cells * 24), 24)
    ones = _table(cmap[ci], md, {k: np.ones(len(ci)) for k in range(NF)})
    ratio = parts_class(pm, ones)  # (n_cells * 24, NF)
    s = np.asarray(sfit["s"], float)  # index 0 = day, 1 = night (one region)
    Yb, Vb, V20b = (int(T.loc[train, c].sum()) for c in ("Y", "V", "V20"))
    return {"name": NAME, "region": region, "a": int(f["a"]), "n_cells": n_cells, "fit": f, "m": pm, "cmap": cmap,
            "ratio": ratio, "s": s, "var_s": np.asarray(sfit["var_s"], float), "s_level": np.asarray(sfit["s_level"]),
            "fit_cells": int(unseen), "outside_fit_cells": int((cmap == unseen).sum()),
            "em": {"iterations": int(f["em_iterations"]), "delta": float(f["em_delta"]), "converged": bool(f["em_converged"])},
            "train_counts": {"modis": Yb, "snpp": Vb,
                             "snpp_in_s_window": int(T.loc[s_train, "V"].sum()),
                             "noaa20_in_s_window": int(T.loc[s_train, "V20"].sum())},
            "cover": cover, "table": T}  # the fit's own row table, for the export's check that its records are this unit


def _table(cid, md, classes, classes20=None):
    """A one-region row table with the columns D-a's predictive code reads (rid 0)."""
    n = len(cid)
    T = pd.DataFrame({"cid": np.asarray(cid, int), "md": np.asarray(md, int)})
    T["dnN"] = T.md % 2
    T["rd"], T["rmd"], T["cmd"] = T.dnN, T.md, T.cid * 24 + T.md
    for k in range(NF):
        T[f"Vf{k}"] = np.asarray(classes[k], float)
        T[f"V20f{k}"] = np.asarray(classes20[k], float) if classes20 is not None else np.zeros(n)
    for k in range(NS):  # scan classes: not read by D-a (FRP classes only); the J-S view copies them, so they exist
        T[f"Vs{k}"], T[f"V20s{k}"] = np.zeros(n), np.zeros(n)
    T["V"] = T[[f"Vf{k}" for k in range(NF)]].sum(axis=1)
    T["V20"] = T[[f"V20f{k}" for k in range(NF)]].sum(axis=1)
    T.attrs["n_regions"] = 1
    return T


def parts_class(m, T):
    """Per row and class, D-a's class term (pipeline.round3.model.class_means)."""
    from pipeline.round3.model import class_means
    return class_means(T, np.arange(len(T)), m["fit"])


def burning_day_weights(model, rows):
    """Full weight of each burning day: Suomi NPP = D-a's class ratio; NOAA-20 = s x that ratio (the export applies
    the share). rows: ci, moy, dn ("D"/"N"), fam ("snpp"/"noaa20"/"modis"), k (FRP class)."""
    out = np.zeros(len(rows))
    night = (rows.dn.to_numpy() == "N").astype(int)
    md = (rows.moy.to_numpy().astype(int) - 1) * 2 + night
    r = model["ratio"][rows.ci.to_numpy() * 24 + md, rows.k.to_numpy().astype(int)]
    fam = rows.fam.to_numpy()
    out[fam == "snpp"] = r[fam == "snpp"]
    out[fam == "noaa20"] = (r * model["s"][night])[fam == "noaa20"]
    return out


def _predictive(model, fam, grid, dn):
    """Mean and variance of D-a's forecast for one satellite and one time of day, per grid row."""
    md = (grid.moy.to_numpy().astype(int) - 1) * 2 + int(dn == "N")
    cid = model["cmap"][grid.ci.to_numpy()]
    cls = {k: grid[f"V_{SAT[fam]}_{dn}_f{k}"].to_numpy(float) for k in range(NF)}
    if fam == "snpp":
        p = parts(model["m"], _table(cid, md, cls), np.arange(len(grid)))
        return p["mean"], p["nbvar"]
    zero = {k: np.zeros(len(grid)) for k in range(NF)}
    T = _table(cid, md, zero, cls)
    p = js_parts(model["m"], T, np.arange(len(grid)), {"s": model["s"]})
    # the calibration's own uncertainty: the mean is s x k, so Var(mean) from s = k^2 x Var(s)
    var = p["nbvar"] + p["k"] ** 2 * model["var_s"][int(dn == "N")]
    return p["mean"], var


def prior_ratio_positive(model):
    """{fam: bool[24]}: where a satellite's burning days can weigh more than 0 in the region x calendar month x
    day/night (index md = (month - 1) * 2 + night): some FRP class has a prior ratio r0_k above 0, and for NOAA-20 also
    s > 0. Where no class does, every burning day of that slot weighs 0 (only the background is left)."""
    r0 = (np.asarray(model["fit"]["r0"]) > 0).any(axis=1)
    s_pos = np.tile(model["s"] > 0, 12)
    return {"snpp": r0, "noaa20": r0 & s_pos}


def _share(grid, s, dn):
    return grid[f"share_{s}_{dn}"].to_numpy(float)


def cell_month_background(model, grid):
    """Expected burning days no record carries: D-a's Poisson(b) where a covering satellite saw nothing."""
    bg = np.zeros(len(grid))
    for fam, s in SAT.items():
        for dn in ("D", "N"):
            mean, _ = _predictive(model, fam, grid, dn)
            zero_v = grid[f"V_{s}_{dn}"].to_numpy() == 0
            bg += np.where(zero_v, _share(grid, s, dn) * mean, 0.0)
    return bg


def cell_month_moments(model, grid):
    mean, var = np.zeros(len(grid)), np.zeros(len(grid))
    for fam, s in SAT.items():
        for dn in ("D", "N"):
            share = _share(grid, s, dn)
            m, v = _predictive(model, fam, grid, dn)
            mean += share * m
            var += share ** 2 * v
    return mean, var


def cell_month_interval(model, grid):
    mean, var = cell_month_moments(model, grid)
    return moment_quantiles(mean, var, (0.1, 0.9))


def describe(model):
    """Plain table of the fitted model for regions.json."""
    f = model["fit"]
    slot = [f"{md // 2 + 1:02d}{'DN'[md % 2]}" for md in range(24)]
    r0 = np.asarray(f["r0"], float)
    s = model["s"]
    tc = model["train_counts"]
    return {
        "name": model["name"], "badge": BADGE, "a": model["a"], "unit": "burning days",
        "frozen": {"file": "data/processed/tournament/frozen_round3.json", "sha256": FROZEN_SHA256, "commit": "80e297f",
                   "confirmation": "docs/ROUND3_CONFIRMATION.md"},
        "classes": CLASS_EDGES,
        "satellites": {
            "snpp": {"train": list(WINDOWS["snpp"]), "method": "D-a (C3 in burning days): one A2-style ratio per FRP class",
                     "prior_ratio_r0": {k: [round(float(x), 4) for x in r0[md]] for md, k in enumerate(slot)},
                     "background_b": {k: round(float(v), 4) for k, v in zip(slot, f["bA"])},
                     "train_burning_days": {"modis": tc["modis"], "snpp": tc["snpp"]}},
            "noaa20": {"train": list(WINDOWS["noaa20"]), "method": "J-S: x s (NOAA-20 to Suomi NPP, in burning days), then D-a",
                       "s": {"D": round(float(s[0]), 4), "N": round(float(s[1]), 4)},
                       "s_sd": {"D": round(float(np.sqrt(model["var_s"][0])), 4), "N": round(float(np.sqrt(model["var_s"][1])), 4)},
                       "train_burning_days": {"snpp": tc["snpp_in_s_window"], "noaa20": tc["noaa20_in_s_window"]}},
        },
        "fit_cells": model["fit_cells"], "cells_outside_fit_region_level": model["outside_fit_cells"],
        "em": model["em"],
        "method": "D-a: per 0.25 deg cell x calendar month x day/night x FRP class, posterior MODIS burning days per Suomi "
                  "NPP burning day (a + sum MODIS_k) / (a / r0_k + sum VIIRS_k) over rows with Suomi NPP > 0, MODIS split "
                  "over classes at the fitted fixed point; b = mean MODIS burning days where Suomi NPP saw nothing. "
                  "NOAA-20: x s, then D-a (pipeline/round3/model.py, pipeline/tournament/candidates.py)",
        "interval": "D-a's predictive per cell-month (class negative binomials summed and moment-matched for V > 0, "
                    "Poisson(b) for V = 0) plus Var(s) for NOAA-20, day + night added, satellites averaged; 10th/90th "
                    "percentile of the moment-matched negative binomial (approximate)",
        "evidence": ["docs/ROUND3_CONFIRMATION.md", "docs/TOURNAMENT_RESULTS.md"],
    }
