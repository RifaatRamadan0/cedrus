"""Capture-recapture sanity test on Portugal FIRMS, TRAINING YEARS 2012-2019 ONLY.

Unit = (0.05 deg cell, UTC date, day/night). Observers = Terra, Aqua, S-NPP, NOAA-20.
Question: is a capture-recapture "true fire-unit count" N-hat sensor-independent,
i.e. does N-hat from the MODIS pair match N-hat from the VIIRS pair in overlap years?
Read-only on raw data. Usage: python -I cr_test.py <raw_dir> [cell_deg]
"""
import sys, itertools
import numpy as np, pandas as pd

RAW = sys.argv[1]
CELL = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05
YEARS = range(2012, 2020)  # never 2020+

def load():
    fr = []
    for y in YEARS:
        m = pd.read_csv(f"{RAW}/modis_{y}_Portugal.csv")
        m["sensor"] = m["satellite"].map({"Terra": "T", "Aqua": "A"})
        fr.append(m[["latitude", "longitude", "acq_date", "acq_time", "daynight", "type", "frp", "confidence", "sensor"]].assign(conf=m.confidence.astype(str)))
        for tag, s in (("viirs-snpp", "S"), ("viirs-jpss1", "N")):
            try:
                v = pd.read_csv(f"{RAW}/{tag}_{y}_Portugal.csv")
            except FileNotFoundError:
                continue
            v["sensor"] = s
            fr.append(v[["latitude", "longitude", "acq_date", "acq_time", "daynight", "type", "frp", "confidence", "sensor"]].assign(conf=v.confidence.astype(str)))
    d = pd.concat(fr, ignore_index=True)
    d = d[d["type"] == 0]  # presumed vegetation fire
    d["date"] = pd.to_datetime(d.acq_date)
    assert d.date.dt.year.max() <= 2019
    d["ci"] = np.floor(d.latitude / CELL).astype(int)
    d["cj"] = np.floor(d.longitude / CELL).astype(int)
    return d

def histories(d, dn="D"):
    x = d[d.daynight == dn]
    g = x.groupby(["ci", "cj", "date", "sensor"]).frp.max().unstack("sensor")
    for s in "TASN":
        if s not in g:
            g[s] = np.nan
    h = g.notna().astype(int)
    h["frpS"] = g["S"]
    h["ym"] = h.index.get_level_values("date").to_period("M")
    h["y"] = h.index.get_level_values("date").year
    return h

def chapman(h, a, b):
    n1, n2 = h[a].sum(), h[b].sum()
    m = (h[a] & h[b]).sum()
    N = (n1 + 1) * (n2 + 1) / (m + 1) - 1
    var = (n1 + 1) * (n2 + 1) * (n1 - m) * (n2 - m) / ((m + 1) ** 2 * (m + 2))
    return N, np.sqrt(var), n1, n2, m

def loglinear(h, srcs, inter=()):
    """Poisson log-linear MSE model on the 2^k-1 observed cells (IRLS); returns N-hat."""
    k = len(srcs)
    pats = [p for p in itertools.product([0, 1], repeat=k) if any(p)]
    key = h[list(srcs)].astype(str).agg("".join, axis=1).value_counts()
    y = np.array([key.get("".join(map(str, p)), 0) for p in pats], float)
    X = [[1.0] + list(p) + [p[i] * p[j] for (i, j) in inter] for p in pats]
    X = np.array(X)
    beta = np.zeros(X.shape[1]); beta[0] = np.log(y.mean() + 1)
    for _ in range(100):
        mu = np.exp(X @ beta)
        W = mu
        z = X @ beta + (y - mu) / mu
        beta_new = np.linalg.solve(X.T @ (W[:, None] * X), X.T @ (W * z))
        if np.max(abs(beta_new - beta)) < 1e-10:
            beta = beta_new; break
        beta = beta_new
    n0 = np.exp(beta[0])
    return y.sum() + n0, y.sum()

def main():
    d = load()
    out = []
    for dn in ("D", "N"):
        h = histories(d, dn)
        print(f"\n=== {dn} passes, cell={CELL} deg, units={len(h)} ===")
        # 1. pairwise overlap: P(B | A) -- closure/simultaneity check
        print("P(row sensor detects | col sensor detects), 2018-2019:")
        hh = h[h.y >= 2018]
        for a in "TASN":
            print(" ", a, " ".join(f"{(hh[a] & hh[b]).sum() / max(hh[b].sum(), 1):.2f}" for b in "TASN"))
        # 2. Chapman N-hat by year for the three pairs
        print("year | n_T n_A n_S n_N | Nhat(T,A)  Nhat(A,S)  Nhat(S,N) | LL3(T,A,S) | union")
        for y, g in h.groupby("y"):
            ta = chapman(g, "T", "A"); as_ = chapman(g, "A", "S")
            sn = chapman(g, "S", "N") if g["N"].sum() > 0 else (np.nan,) * 5
            ll3 = loglinear(g, "TAS")[0]
            un = (g[list("TASN")].sum(axis=1) > 0).sum()
            print(f"{y} | {g['T'].sum():5d} {g['A'].sum():5d} {g['S'].sum():5d} {g['N'].sum():5d} | "
                  f"{ta[0]:8.0f}+-{ta[1]:5.0f} {as_[0]:8.0f}+-{as_[1]:5.0f} {sn[0]:8.0f}+-{(sn[1] if sn[1]==sn[1] else 0):5.0f} | {ll3:8.0f} | {un:6d}")
            out.append(dict(dn=dn, y=y, nT=g['T'].sum(), nA=g['A'].sum(), nS=g['S'].sum(), nN=g['N'].sum(),
                            N_TA=ta[0], N_AS=as_[0], N_SN=sn[0], N_LL3=ll3, union=un))
        # 3. the harmonization test: monthly MODIS-pair vs VIIRS-pair Nhat, 2018-2019
        rows = []
        for ym, g in hh.groupby("ym"):
            if g["S"].sum() < 20 or g["A"].sum() < 5:
                continue
            ta = chapman(g, "T", "A")[0]; sn = chapman(g, "S", "N")[0]
            rows.append((str(ym), ta, sn, g["T"].sum() + g["A"].sum(), g["S"].sum() + g["N"].sum()))
        r = pd.DataFrame(rows, columns=["ym", "N_TA", "N_SN", "raw_MODIS", "raw_VIIRS"])
        if len(r):
            r["cr_ratio"] = r.N_SN / r.N_TA
            r["raw_ratio"] = r.raw_VIIRS / r.raw_MODIS
            print("monthly 2018-19 (months with n_S>=20):")
            print(r.round(2).to_string(index=False))
            for c in ("cr_ratio", "raw_ratio"):
                lr = np.log(r[c].replace([np.inf, 0], np.nan).dropna())
                print(f"  {c}: median {np.exp(lr.median()):.2f}, sd(log) {lr.std():.2f}")
        # 4. heterogeneity: P(Aqua detects | S-NPP detects) by S-NPP FRP (same overpass time)
        s = h[h.S == 1].copy()
        s["bin"] = pd.cut(s.frpS, [0, 2, 5, 10, 20, 50, 100, 1e6])
        print("P(Aqua | S-NPP) by S-NPP max FRP (MW), all years:")
        print(s.groupby("bin", observed=True).A.agg(["mean", "size"]).round(3).to_string())
        s2 = h[(h.S == 1) & (h.y >= 2018)].copy()
        s2["bin"] = pd.cut(s2.frpS, [0, 2, 5, 10, 20, 50, 100, 1e6])
        print("P(NOAA-20 | S-NPP) by S-NPP FRP, 2018-19:")
        print(s2.groupby("bin", observed=True).N.agg(["mean", "size"]).round(3).to_string())
    pd.DataFrame(out).to_csv(f"cr_yearly_{CELL}.csv", index=False)

if __name__ == "__main__":
    main()
