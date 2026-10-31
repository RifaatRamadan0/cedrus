"""Model A, the bake-off winner (docs/BAKEOFF_RESULTS.md): the Poisson-gamma shrinkage ratio, a = 30.

Same interface as weights_interim.py, so export_v2.py only changes its import:

    model = fit(det, region)                     # one fit per VIIRS satellite; never sees 2020 or later
    w     = hotspot_weights(model, rows)         # posterior mean ratio of the row's cell x calendar month x day/night
    bg    = cell_month_background(model, grid)   # b_A where a covering satellite saw nothing in a cell x month x day/night
    p10, p90 = cell_month_interval(model, grid)  # from A's predictive distribution, per cell-month
    describe(model)

The fitting and the predictive distributions are pipeline/bakeoff/models.py (fit_A, predict_A), imported, not
re-implemented. This module only builds A's row table from the product's detections and reads A's answers:

- rows: cell x month x day/night for every cell of the region's footprint, Y = Terra + Aqua, V = one VIIRS satellite;
  Suomi NPP trained on 2012-02..2019-12, NOAA-20 on 2018-04..2019-12 (its first complete month).
- a detection's weight = A's posterior mean MODIS per VIIRS detection, shape / rate, for its cell x calendar month x
  day/night (read from predict_A with V = 1: mean = shape (1 - p) / p with p = rate / (rate + 1)).
- background = A's forecast for V = 0, Poisson(b_A), for every footprint cell x month x day/night where the satellite
  saw nothing.
- interval: each cell-month x day/night's predictive (negative binomial for V > 0, Poisson(b_A) for V = 0) gives a
  mean and a variance; day and night are added; two satellites are averaged (mean = sum of share x mean,
  variance = sum of share^2 x variance, as if independent); the 10th/90th percentiles are those of a negative
  binomial with that mean and variance (Poisson when the variance is not above the mean). Approximate.

`grid` columns: ci (cell index), moy, m (the cell-month expected value), and for s in N, J1:
share_<s>_D, share_<s>_N (that satellite's share of the month by time of day: 1, 1/2 or 0; share_<s> if the same for
both) and V_<s>_D, V_<s>_N (its detections by day and night). The shares are the export's combination rule, not A.
"""
import numpy as np
import pandas as pd
from scipy.stats import nbinom, poisson

from bakeoff.models import add_groups, fit_A, predict_A

NAME = "A — shrinkage ratio (bake-off winner)"
A = 30  # chosen by the bake-off's leave-one-year-out (data/processed/bakeoff/frozen_A.json); fixed here
TRAIN = {"snpp": ("2012-02", "2019-12"), "noaa20": ("2018-04", "2019-12")}
SAT = {"snpp": "N", "noaa20": "J1"}
LABEL = {"snpp": "Suomi NPP", "noaa20": "NOAA-20"}


def _months(window):
    return [str(p) for p in pd.period_range(window[0], window[1], freq="M")]


def _table(ci, moy, dn_night, V, Y=None):
    """A's row table for one region (rid 0): the columns models.add_groups and fit_A / predict_A read."""
    R = pd.DataFrame({"rid": 0, "cid": np.asarray(ci, int), "moy": np.asarray(moy, int),
                      "dnN": np.asarray(dn_night, int), "V": np.asarray(V, float),
                      "Y": np.zeros(len(ci)) if Y is None else np.asarray(Y, float)})
    return add_groups(R, 1)


def _fit_one(det, fam, n_cells):
    months = _months(TRAIN[fam])
    assert max(months) <= "2019-12", "model A may not be fitted on 2020 or later"
    train = det[det.month.isin(months) & det.fam.isin(["modis", fam])]
    assert train.month.max() <= "2019-12"
    cnt = train.groupby(["ci", "month", "dn", "fam"]).size().unstack("fam", fill_value=0)
    full = pd.MultiIndex.from_product([range(n_cells), months, ["D", "N"]], names=["ci", "month", "dn"])
    cnt = cnt.reindex(full, fill_value=0).reset_index()
    for f in ("modis", fam):
        if f not in cnt:
            cnt[f] = 0
    R = _table(cnt.ci, cnt.month.str[5:7].astype(int), cnt.dn == "N", cnt[fam], cnt.modis)
    fit = fit_A(R, np.ones(len(R), bool))
    # Posterior mean ratio per cell x calendar month x day/night: A's forecast for V = 1.
    ci, md = np.divmod(np.arange(n_cells * 24), 24)
    ones = _table(ci, md // 2 + 1, md % 2, np.ones(len(ci)))
    kind, fa, fb = predict_A(ones, np.ones(len(ones), bool), fit, A)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(kind == 2, fa * (1 - fb) / fb, 0.0)
    return {"fit": fit, "ratio": ratio, "train": TRAIN[fam],
            "train_counts": {"modis": int(cnt.modis.sum()), fam: int(cnt[fam].sum())}, "rows": len(R)}


def fit(det, region):
    """det needs columns month, moy, dn, fam and ci (the export's cell index, 0..n_cells-1)."""
    n_cells = int(det.ci.max()) + 1
    return {"name": NAME, "region": region, "a": A, "n_cells": n_cells,
            "fams": {fam: _fit_one(det, fam, n_cells) for fam in TRAIN}}


def hotspot_weights(model, rows):
    """Full weight (A's posterior mean ratio) of each Suomi NPP or NOAA-20 row; the export applies the share."""
    out = np.zeros(len(rows))
    md = (rows.moy.to_numpy().astype(int) - 1) * 2 + (rows.dn.to_numpy() == "N")
    for fam, f in model["fams"].items():
        sel = (rows.fam == fam).to_numpy()
        out[sel] = f["ratio"][rows.ci.to_numpy()[sel] * 24 + md[sel]]
    return out


def _predictive(model, fam, grid, dn):
    """Mean and variance of A's forecast for one satellite and one time of day, per grid row."""
    s = SAT[fam]
    R = _table(grid.ci, grid.moy, np.full(len(grid), dn == "N"), grid[f"V_{s}_{dn}"])
    kind, fa, fb = predict_A(R, np.ones(len(R), bool), model["fams"][fam]["fit"], model["a"])
    mean, var = np.zeros(len(R)), np.zeros(len(R))
    pois, nb = kind == 1, kind == 2
    mean[pois] = var[pois] = fa[pois]
    q = (1 - fb[nb]) / fb[nb]
    mean[nb] = fa[nb] * q
    var[nb] = fa[nb] * q / fb[nb]
    return mean, var, kind


def prior_ratio_positive(model):
    """{fam: bool[24]}: where A's prior ratio r0 for the region x calendar month x day/night is above 0
    (index md = (month - 1) * 2 + night). Read from the fit; A itself is not changed."""
    return {fam: np.asarray(f["fit"]["r0"]) > 0 for fam, f in model["fams"].items()}


def _share(grid, s, dn):
    col = f"share_{s}_{dn}"
    return grid[col].to_numpy(float) if col in grid else grid[f"share_{s}"].to_numpy(float)


def cell_month_background(model, grid):
    """Expected detections no hotspot row carries: Poisson(b_A) where a covering satellite saw nothing."""
    bg = np.zeros(len(grid))
    for fam, s in SAT.items():
        for dn in ("D", "N"):
            share = _share(grid, s, dn)
            mean, _, kind = _predictive(model, fam, grid, dn)
            zero_v = grid[f"V_{s}_{dn}"].to_numpy() == 0
            bg += np.where(zero_v, share * mean, 0.0)
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
    """p10, p90 per cell-month from A's predictive (moment-matched; approximate)."""
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
    sats = {}
    for fam, f in model["fams"].items():
        fit = f["fit"]
        sats[fam] = {
            "train": list(f["train"]),
            "prior_ratio_r0": {f"{md // 2 + 1:02d}{'DN'[md % 2]}": round(float(r), 4) for md, r in enumerate(fit["r0"])},
            "background_bA": {f"{md // 2 + 1:02d}{'DN'[md % 2]}": round(float(b), 4) for md, b in enumerate(fit["bA"])},
            "r0_fallback_months": int((fit["r0_level"] > 0).sum()),
            "train_detections": f["train_counts"], "train_rows": f["rows"],
        }
    return {
        "name": model["name"], "a": model["a"], "satellites": sats,
        "method": "per 0.25 deg cell x calendar month x day/night: posterior MODIS per VIIRS detection "
                  "(a + sum MODIS) / (a / r0 + sum VIIRS), r0 = the region's ratio for that month and time of day; "
                  "b_A = mean MODIS where VIIRS saw nothing (pipeline/bakeoff/models.py fit_A, predict_A)",
        "interval": "A's predictive per cell-month (negative binomial for V > 0, Poisson(b_A) for V = 0), day + night "
                    "added, two satellites averaged with variances combined; 10th/90th percentile of the moment-matched "
                    "negative binomial (approximate)",
        "evidence": "docs/BAKEOFF_RESULTS.md",
    }
