"""Interim VIIRS -> MODIS-equivalent weight model. Replaced by the bake-off winner (docs/BAKEOFF_PLAN.md).

The export (export_v2.py) only talks to this module through these functions, so the winning model
can be dropped in with the same signatures:

    model = fit(det, region)                    # det: filtered detections, any years; only TRAIN windows are used
    w     = hotspot_weights(model, rows)        # full MODIS-equivalent weight of each Suomi NPP / NOAA-20 row
    bg    = cell_month_background(model, cm)    # expected detections not carried by any row (interim: 0)
    p10, p90 = cell_month_interval(model, cm)   # 80% range for each estimated or bridged cell-month

The export decides how much of each weight counts: in a month both VIIRS satellites cover, each carries
half (the record is the average of the two estimates); in a month only one covers, it carries all.

Interim model (lead's rulings, 31 Oct 2026):
- one ratio per VIIRS satellite x region x calendar month x day/night, shrunk toward that satellite's pooled
  day/night ratio with PRIOR_V pseudo-detections: r = (sum MODIS + PRIOR_V * r_pool,dn) / (sum VIIRS + PRIOR_V),
  r_pool,dn = sum MODIS / sum VIIRS over all calendar months at that time of day. MODIS = Terra + Aqua.
- Suomi NPP fitted on 2012-02..2019-12, NOAA-20 on 2018-04..2019-12 (its first months). Never 2020 or later.
- interval: placeholder, not fitted. 10th/90th percentile of a negative binomial with mean m and size 5.

`det` / `rows` columns used: month ("YYYY-MM"), moy (1..12), dn ("D"/"N"), fam ("modis"/"snpp"/"noaa20").
"""
import numpy as np

NAME = "interim"
TRAIN = {"snpp": ("2012-02", "2019-12"), "noaa20": ("2018-04", "2019-12")}
LABEL = {"snpp": "Suomi NPP", "noaa20": "NOAA-20"}
NB_SIZE = 5
PRIOR_V = 30  # VIIRS pseudo-detections pulling a month's ratio toward the pooled day/night ratio


def _fit_one(det, fam, window):
    train = det[(det.month >= window[0]) & (det.month <= window[1])]
    assert train.month.max() <= "2019-12", "the interim model may not see 2020 or later"
    t = train[train.fam.isin(["modis", fam])].groupby(["moy", "dn", "fam"]).size().unstack(fill_value=0)
    for f in ("modis", fam):
        if f not in t:
            t[f] = 0
    by_dn = t.groupby(level="dn")[["modis", fam]].sum()
    overall = t.modis.sum() / t[fam].sum()
    pool = {dn: float(by_dn.loc[dn, "modis"] / by_dn.loc[dn, fam]) if dn in by_dn.index and by_dn.loc[dn, fam] > 0
            else float(overall) for dn in ("D", "N")}
    ratio, basis = {}, {}
    for moy in range(1, 13):
        for dn in ("D", "N"):
            y, v = (int(t.loc[(moy, dn), f]) if (moy, dn) in t.index else 0 for f in ("modis", fam))
            ratio[(moy, dn)] = (y + PRIOR_V * pool[dn]) / (v + PRIOR_V)
            basis[(moy, dn)] = f"{y} MODIS / {v} {LABEL[fam]}"
    return {"train": window, "ratio": ratio, "basis": basis, "pool": pool, "overall": float(overall),
            "train_counts": {"modis": int(t.modis.sum()), fam: int(t[fam].sum())}}


def fit(det, region):
    return {"name": NAME, "region": region, "nb_size": NB_SIZE,
            "fams": {fam: _fit_one(det, fam, window) for fam, window in TRAIN.items()}}


def hotspot_weights(model, rows):
    """Full MODIS-equivalent weight of each Suomi NPP or NOAA-20 row (the export decides which share counts)."""
    return np.array([model["fams"][f]["ratio"][(int(m), dn)] for f, m, dn in zip(rows.fam, rows.moy, rows.dn)], dtype=float)


def cell_month_background(model, cm):
    """Expected detections in each cell-month that no hotspot row carries. The interim model has none."""
    return np.zeros(len(cm))


def cell_month_interval(model, cm):
    """p10, p90 for each estimated or bridged cell-month. cm needs column m (the MODIS-equivalent mean, = sum of weights)."""
    return nb_quantiles(cm.m.to_numpy(float), model["nb_size"], (0.1, 0.9))


def nb_quantiles(mean, size, qs):
    """Quantiles of NB2(mean, size) for an array of means, by summing the pmf (no scipy needed)."""
    mean = np.asarray(mean, float)
    out = [np.zeros(mean.shape, int) for _ in qs]
    live = mean > 0
    if not live.any():
        return out
    m = mean[live]
    p = size / (size + m)
    pmf = p ** size
    cdf = pmf.copy()
    found = [np.full(m.shape, -1) for _ in qs]
    k = 0
    while True:
        for f, q in zip(found, qs):
            f[(f < 0) & (cdf >= q)] = k
        if all((f >= 0).all() for f in found):
            break
        pmf = pmf * (k + size) / (k + 1) * (1 - p)
        cdf = cdf + pmf
        k += 1
    for o, f in zip(out, found):
        o[live] = f
    return out


def describe(model):
    """Plain table of the fitted model for regions.json."""
    return {
        "name": model["name"],
        "satellites": {fam: {
            "train": list(f["train"]),
            "ratio": {f"{moy:02d}{dn}": round(float(r), 4) for (moy, dn), r in sorted(f["ratio"].items())},
            "ratio_basis": {f"{moy:02d}{dn}": b for (moy, dn), b in sorted(f["basis"].items())},
            "pooled_ratio": {dn: round(r, 4) for dn, r in f["pool"].items()},
            "overall_ratio": round(f["overall"], 4),
            "train_detections": f["train_counts"],
        } for fam, f in model["fams"].items()},
        "shrinkage": f"each ratio = (MODIS + {PRIOR_V} x pooled) / (VIIRS + {PRIOR_V}), pooled per satellite and day/night",
        "interval": f"interim placeholder, replaced by the bake-off winner: 10th/90th percentile of a negative "
                    f"binomial with mean m and size {model['nb_size']} (not fitted to data)",
    }


if __name__ == "__main__":
    # Self-check of the quantile routine against a direct sum for a few means.
    for mean in (0.3, 4.0, 50.0):
        p = NB_SIZE / (NB_SIZE + mean)
        ks = np.arange(0, 2000)
        from math import lgamma
        logpmf = np.array([lgamma(k + NB_SIZE) - lgamma(k + 1) - lgamma(NB_SIZE) for k in ks]) \
            + NB_SIZE * np.log(p) + ks * np.log1p(-p)
        cdf = np.cumsum(np.exp(logpmf))
        direct = [int(np.argmax(cdf >= q)) for q in (0.1, 0.9)]
        got = [int(a[0]) for a in nb_quantiles([mean], NB_SIZE, (0.1, 0.9))]
        print(mean, direct, got, "ok" if direct == got else "MISMATCH")
