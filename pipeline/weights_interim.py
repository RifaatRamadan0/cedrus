"""Interim VIIRS -> MODIS-equivalent weight model. Replaced by the bake-off winner (docs/BAKEOFF_PLAN.md).

The export (export_v2.py) only talks to this module through these functions, so the winning model
can be dropped in with the same signatures:

    model = fit(det, region)                    # det: filtered detections, any years; only TRAIN is used
    w     = hotspot_weights(model, rows)        # MODIS-equivalent contribution of each Suomi NPP row
    bg    = cell_month_background(model, cm)    # expected detections not carried by any row (interim: 0)
    p10, p90 = cell_month_interval(model, cm)   # 80% range for each estimated or bridged cell-month

Interim model (lead's ruling, 31 Oct 2026):
- ratio per region x calendar month x day/night, shrunk toward the region's pooled day/night ratio with
  PRIOR_V Suomi NPP pseudo-detections: r = (sum MODIS + PRIOR_V * r_pool,dn) / (sum Suomi NPP + PRIOR_V),
  r_pool,dn = sum MODIS / sum Suomi NPP over all calendar months at that time of day. Fitted on TRAIN only.
  MODIS = Terra + Aqua.
- each Suomi NPP detection in an estimated month weighs r for its calendar month and day/night.
- interval: placeholder, not fitted. 10th/90th percentile of a negative binomial with mean m and size 5.

`det` / `rows` columns used: month ("YYYY-MM"), moy (1..12), dn ("D"/"N"), fam ("modis"/"snpp"/"noaa20").
"""
import numpy as np

NAME = "interim"
TRAIN = ("2012-02", "2019-12")  # Suomi NPP's first full month to the last pre-test month; never 2020+
NB_SIZE = 5
PRIOR_V = 30  # Suomi NPP pseudo-detections pulling a month's ratio toward the pooled day/night ratio


def fit(det, region):
    train = det[(det.month >= TRAIN[0]) & (det.month <= TRAIN[1])]
    assert train.month.max() <= "2019-12", "the interim model may not see 2020 or later"
    t = train[train.fam.isin(["modis", "snpp"])].groupby(["moy", "dn", "fam"]).size().unstack(fill_value=0)
    for f in ("modis", "snpp"):
        if f not in t:
            t[f] = 0
    by_dn = t.groupby(level="dn")[["modis", "snpp"]].sum()
    overall = t.modis.sum() / t.snpp.sum()
    pool = {dn: float(by_dn.loc[dn, "modis"] / by_dn.loc[dn, "snpp"]) if dn in by_dn.index and by_dn.loc[dn, "snpp"] > 0
            else float(overall) for dn in ("D", "N")}
    ratio, basis = {}, {}
    for moy in range(1, 13):
        for dn in ("D", "N"):
            y, v = (int(t.loc[(moy, dn), f]) if (moy, dn) in t.index else 0 for f in ("modis", "snpp"))
            ratio[(moy, dn)] = (y + PRIOR_V * pool[dn]) / (v + PRIOR_V)
            basis[(moy, dn)] = f"{y} MODIS / {v} Suomi NPP"
    return {"name": NAME, "region": region, "train": TRAIN, "ratio": ratio, "basis": basis, "pool": pool,
            "overall": float(overall), "nb_size": NB_SIZE,
            "train_counts": {"modis": int(t.modis.sum()), "snpp": int(t.snpp.sum())}}


def hotspot_weights(model, rows):
    """MODIS-equivalent weight of each row as if it were a Suomi NPP detection (the caller decides which rows count)."""
    keys = list(zip(rows.moy.astype(int), rows.dn))
    return np.array([model["ratio"][k] for k in keys], dtype=float)


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
        "name": model["name"], "train": list(model["train"]),
        "ratio": {f"{moy:02d}{dn}": round(float(r), 4) for (moy, dn), r in sorted(model["ratio"].items())},
        "ratio_basis": {f"{moy:02d}{dn}": b for (moy, dn), b in sorted(model["basis"].items())},
        "shrinkage": f"each ratio = (MODIS + {PRIOR_V} x pooled) / (Suomi NPP + {PRIOR_V}), pooled per day/night",
        "pooled_ratio": {dn: round(r, 4) for dn, r in model["pool"].items()},
        "overall_ratio": round(model["overall"], 4),
        "train_detections": model["train_counts"],
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
