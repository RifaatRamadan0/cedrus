"""The round-2 choice, frozen (docs/ROUND2_SELECTION.md, commit 617daff): A2 for Suomi NPP, and NOAA-20 via
Suomi NPP (J-S). Same interface as weights_a.py, so export_v2.py only changes its import.

    model = fit(det, region)                     # never sees 2020 or later; settings from frozen.json only
    w     = hotspot_weights(model, rows)         # full MODIS-equivalent weight of each Suomi NPP / NOAA-20 row
    bg    = cell_month_background(model, grid)   # A2's Poisson(b) where a covering satellite saw nothing
    p10, p90 = cell_month_interval(model, grid)  # A2's predictive + the NOAA-20 calibration's uncertainty
    describe(model)

The models are pipeline/round2/models.py (fit_A2, predict_A2, fit_s, rng_for), imported, not re-implemented.
Settings (a, fit windows, bootstrap size and seed) come from data/processed/round2/frozen.json, which must have the
SHA-256 recorded at the freeze; anything else stops the export.

- A2 = the bake-off's A with its ratio sums taken over rows with V > 0 only; rows with V = 0 predict Poisson(b),
  b = A's b_A. Fitted on Suomi NPP, 2012-02..2019-12, a = 30, over the fit's footprint: cells with a MODIS, Suomi NPP
  or NOAA-20 detection in that window (frozen by construction; a cell that first burns later gets A2's region-level
  forecast for its slot).
- J-S: s = sum Suomi NPP / sum NOAA-20 per region x day/night on 2018-04..2019-12 (month-block bootstrap for its
  variance); a NOAA-20 detection is put on the Suomi NPP scale (x s) and then through A2. So a NOAA-20 detection
  weighs s x (A2's posterior mean ratio of its cell x calendar month x day/night).
- interval per cell-month: A2's predictive (negative binomial for V > 0, Poisson(b) for V = 0) by day and night,
  plus, for NOAA-20, (ratio x V20)^2 x Var(s); the two satellites averaged with their shares (variance x share^2);
  10th/90th percentile of the moment-matched negative binomial. Approximate: cells are treated as independent,
  though s is shared by every cell of the region.

`grid` columns as weights_a.py: ci, moy, m, share_<s>_D / share_<s>_N and V_<s>_D / V_<s>_N for s in N, J1.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import nbinom, poisson

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # pipeline/round2 imports itself as the package pipeline.round2

from pipeline.bakeoff.models import add_groups  # noqa: E402
from pipeline.round2.models import fit_A2, fit_s, predict_A2, rng_for  # noqa: E402

NAME = "A2 + NOAA-20 via Suomi NPP (round-2 choice, frozen)"
BADGE = "MODEL A2 · ROUND 2, FROZEN"
FROZEN = ROOT / "data" / "processed" / "round2" / "frozen.json"
FROZEN_SHA256 = "bedc56d5ba85b851931cd6912dfcab832dc38b26a8fe80712a72974cf46e0686"
SAT = {"snpp": "N", "noaa20": "J1"}
LABEL = {"snpp": "Suomi NPP", "noaa20": "NOAA-20"}


def check_frozen(raw):
    """The frozen settings, only if these bytes are the file recorded at the freeze."""
    digest = hashlib.sha256(raw).hexdigest()
    if digest != FROZEN_SHA256:
        raise SystemExit(f"data/processed/round2/frozen.json has SHA-256 {digest}, not the frozen {FROZEN_SHA256}: "
                         "the round-2 model is not the one that was frozen; refusing to export")
    return json.loads(raw)["settings"]


SETTINGS = check_frozen(FROZEN.read_bytes())
WINDOWS = {"snpp": tuple(SETTINGS["fit_window_suomi_npp"]), "noaa20": tuple(SETTINGS["fit_window_noaa20"])}
A = int(SETTINGS["a"])
TRAIN = {"snpp": WINDOWS["snpp"], "noaa20": WINDOWS["noaa20"]}  # read by export_v2 (DRIFT_FROM, band)


def _months(window):
    return [str(p) for p in pd.period_range(window[0], window[1], freq="M")]


def _table(ci, moy, night, V, Y=None, V20=None, ym=None):
    """Round 2's row table for one region (rid 0)."""
    n = len(ci)
    R = pd.DataFrame({"rid": 0, "cid": np.asarray(ci, int), "moy": np.asarray(moy, int), "dnN": np.asarray(night, int),
                      "V": np.asarray(V, float), "Y": np.zeros(n) if Y is None else np.asarray(Y, float),
                      "V20": np.zeros(n) if V20 is None else np.asarray(V20, float),
                      "ym": np.full(n, "2019-12") if ym is None else np.asarray(ym)})
    R["year"] = R.ym.str[:4].astype(int)
    return add_groups(R, 1)


def fit(det, region):
    """det needs columns month, moy, dn, fam and ci (the export's cell index, 0..n_cells-1)."""
    for w in WINDOWS.values():
        assert w[1] <= "2019-12", "the round-2 model may not be fitted on 2020 or later"
    n_cells = int(det.ci.max()) + 1
    months = _months(WINDOWS["snpp"])
    win = det[det.month.isin(months)]
    assert win.month.max() <= "2019-12"
    fit_cells = np.array(sorted(win.ci.unique()), int)  # the fit's footprint: cells with any detection in the window
    cid = {c: k for k, c in enumerate(fit_cells)}
    cnt = win.groupby(["ci", "month", "dn", "fam"]).size().unstack("fam", fill_value=0)
    full = pd.MultiIndex.from_product([fit_cells, months, ["D", "N"]], names=["ci", "month", "dn"])
    cnt = cnt.reindex(full, fill_value=0).reset_index()
    for f in ("modis", "snpp", "noaa20"):
        if f not in cnt:
            cnt[f] = 0
    R = _table(cnt.ci.map(cid), cnt.month.str[5:7].astype(int), cnt.dn == "N", cnt.snpp, cnt.modis, cnt.noaa20, cnt.month)
    a2 = fit_A2(R, (R.ym >= WINDOWS["snpp"][0]).to_numpy() & (R.ym <= WINDOWS["snpp"][1]).to_numpy())
    s_train = (R.ym >= WINDOWS["noaa20"][0]).to_numpy() & (R.ym <= WINDOWS["noaa20"][1]).to_numpy()
    sfit = fit_s(R, s_train, rng_for("product", region, "s"), n_boot=int(SETTINGS["bootstrap_resamples"]))
    # For prediction only: one extra cell with no history stands for every cell outside the fit's footprint.
    unseen = len(fit_cells)
    pred = dict(a2, SY=np.r_[a2["SY"], np.zeros(24)], SV=np.r_[a2["SV"], np.zeros(24)])
    cmap = np.full(n_cells, unseen, int)
    cmap[fit_cells] = np.arange(len(fit_cells))
    ci, md = np.divmod(np.arange(n_cells * 24), 24)
    ones = _table(cmap[ci], md // 2 + 1, md % 2, np.ones(len(ci)))
    kind, fa, fb = predict_A2(ones, np.ones(len(ones), bool), pred, A)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(kind == 2, fa * (1 - fb) / fb, 0.0)  # A2's posterior mean MODIS per Suomi NPP detection
    s = np.asarray(sfit["s"], float)  # index 0 = day, 1 = night (one region)
    return {"name": NAME, "region": region, "a": A, "n_cells": n_cells, "a2": a2, "pred": pred, "cmap": cmap,
            "ratio": ratio, "s": s, "var_s": np.asarray(sfit["var_s"], float), "s_level": np.asarray(sfit["s_level"]),
            "fit_cells": int(len(fit_cells)), "outside_fit_cells": int((cmap == unseen).sum()),
            "train_counts": {"modis": int(cnt.modis.sum()), "snpp": int(cnt.snpp.sum()),
                             "noaa20_in_s_window": int(cnt.noaa20[s_train].sum()),
                             "snpp_in_s_window": int(cnt.snpp[s_train].sum())}}


def hotspot_weights(model, rows):
    """Full weight of each row: Suomi NPP = A2's ratio; NOAA-20 = s x A2's ratio (the export applies the share)."""
    out = np.zeros(len(rows))
    night = (rows.dn.to_numpy() == "N").astype(int)
    md = (rows.moy.to_numpy().astype(int) - 1) * 2 + night
    r = model["ratio"][rows.ci.to_numpy() * 24 + md]
    fam = rows.fam.to_numpy()
    out[fam == "snpp"] = r[fam == "snpp"]
    out[fam == "noaa20"] = (r * model["s"][night])[fam == "noaa20"]
    return out


def _predictive(model, fam, grid, dn):
    """Mean and variance of the forecast for one satellite and one time of day, per grid row."""
    s_dn = model["s"][int(dn == "N")]
    V = grid[f"V_{SAT[fam]}_{dn}"].to_numpy(float)
    Vs = V if fam == "snpp" else s_dn * V
    R = _table(model["cmap"][grid.ci.to_numpy()], grid.moy, np.full(len(grid), dn == "N"), Vs)
    kind, fa, fb = predict_A2(R, np.ones(len(R), bool), model["pred"], model["a"])
    mean, var = np.zeros(len(R)), np.zeros(len(R))
    pois, nb = kind == 1, kind == 2
    mean[pois] = var[pois] = fa[pois]
    q = (1 - fb[nb]) / fb[nb]
    mean[nb] = fa[nb] * q
    var[nb] = fa[nb] * q / fb[nb]
    if fam == "noaa20":  # the calibration's own uncertainty: mean = ratio x s x V20 where V20 > 0
        md = (grid.moy.to_numpy().astype(int) - 1) * 2 + int(dn == "N")
        r = model["ratio"][grid.ci.to_numpy() * 24 + md]
        var = var + np.where(V > 0, (r * V) ** 2 * model["var_s"][int(dn == "N")], 0.0)
    return mean, var, kind


def prior_ratio_positive(model):
    """{fam: bool[24]}: where a satellite's ratio for the region x calendar month x day/night is above 0
    (index md = (month - 1) * 2 + night): A2's prior r0, and for NOAA-20 also s."""
    r0 = np.asarray(model["a2"]["r0"]) > 0
    s_pos = np.tile(model["s"] > 0, 12)
    return {"snpp": r0, "noaa20": r0 & s_pos}


def _share(grid, s, dn):
    col = f"share_{s}_{dn}"
    return grid[col].to_numpy(float) if col in grid else grid[f"share_{s}"].to_numpy(float)


def cell_month_background(model, grid):
    """Expected detections no hotspot row carries: Poisson(b) where a covering satellite saw nothing."""
    bg = np.zeros(len(grid))
    for fam, s in SAT.items():
        for dn in ("D", "N"):
            mean, _, _ = _predictive(model, fam, grid, dn)
            zero_v = grid[f"V_{s}_{dn}"].to_numpy() == 0
            bg += np.where(zero_v, _share(grid, s, dn) * mean, 0.0)
    return bg


def cell_month_moments(model, grid):
    mean, var = np.zeros(len(grid)), np.zeros(len(grid))
    for fam, s in SAT.items():
        for dn in ("D", "N"):
            share = _share(grid, s, dn)
            m, v, _ = _predictive(model, fam, grid, dn)
            mean += share * m
            var += share ** 2 * v
    return mean, var


def cell_month_interval(model, grid):
    mean, var = cell_month_moments(model, grid)
    return moment_quantiles(mean, var, (0.1, 0.9))


def moment_quantiles(mean, var, qs):
    """Quantiles of a negative binomial with this mean and variance; Poisson where var <= mean."""
    out = [np.zeros(len(mean)) for _ in qs]
    live = mean > 0
    nbm = live & (var > mean * (1 + 1e-9))
    pom = live & ~nbm
    with np.errstate(divide="ignore", invalid="ignore"):
        size = mean[nbm] ** 2 / (var[nbm] - mean[nbm])
        p = mean[nbm] / var[nbm]
    for o, q in zip(out, qs):
        o[nbm] = nbinom.ppf(q, size, p)
        o[pom] = poisson.ppf(q, mean[pom])
    return out


def describe(model):
    """Plain table of the fitted model for regions.json."""
    a2 = model["a2"]
    slot = [f"{md // 2 + 1:02d}{'DN'[md % 2]}" for md in range(24)]
    r0 = np.asarray(a2["r0"], float)
    s = model["s"]
    return {
        "name": model["name"], "badge": BADGE, "a": model["a"],
        "frozen": {"file": "data/processed/round2/frozen.json", "sha256": FROZEN_SHA256, "commit": "617daff",
                   "selection": "docs/ROUND2_SELECTION.md"},
        "satellites": {
            "snpp": {"train": list(WINDOWS["snpp"]), "method": "A2",
                     "prior_ratio_r0": {k: round(float(v), 4) for k, v in zip(slot, r0)},
                     "background_b": {k: round(float(v), 4) for k, v in zip(slot, a2["bA"])},
                     "train_detections": {"modis": model["train_counts"]["modis"], "snpp": model["train_counts"]["snpp"]}},
            "noaa20": {"train": list(WINDOWS["noaa20"]), "method": "J-S: x s (NOAA-20 to Suomi NPP), then A2",
                       "s": {"D": round(float(s[0]), 4), "N": round(float(s[1]), 4)},
                       "s_sd": {"D": round(float(np.sqrt(model["var_s"][0])), 4), "N": round(float(np.sqrt(model["var_s"][1])), 4)},
                       "prior_ratio_r0": {k: round(float(v * s[md % 2]), 4) for md, (k, v) in enumerate(zip(slot, r0))},
                       "train_detections": {"snpp": model["train_counts"]["snpp_in_s_window"],
                                            "noaa20": model["train_counts"]["noaa20_in_s_window"]}},
        },
        "fit_cells": model["fit_cells"], "cells_outside_fit_region_level": model["outside_fit_cells"],
        "method": "A2: per 0.25 deg cell x calendar month x day/night, posterior MODIS per Suomi NPP detection "
                  "(a + sum MODIS) / (a / r0 + sum VIIRS) over rows with Suomi NPP > 0; b = mean MODIS where it saw "
                  "nothing. NOAA-20: x s, then A2 (pipeline/round2/models.py)",
        "interval": "A2's predictive per cell-month (negative binomial for V > 0, Poisson(b) for V = 0) plus Var(s) for "
                    "NOAA-20, day + night added, satellites averaged; 10th/90th percentile of the moment-matched "
                    "negative binomial (approximate)",
        "evidence": ["docs/ROUND2_SELECTION.md", "docs/CONFIRMATION_RESULTS.md"],
    }
