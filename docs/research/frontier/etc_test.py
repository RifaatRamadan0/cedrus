"""Extended triple collocation (McColl et al. 2014) on Portugal monthly 0.25deg cell counts,
sensors Terra, Aqua, S-NPP; 2012-2019 only. Variable = log(1+count). Reports each sensor's
correlation with the unknown truth (rho^2) and error SD in its own units, and the
TC-optimal merge weights. Caveat: TC needs mutually independent errors; Aqua/S-NPP share overpass time."""
import sys, numpy as np, pandas as pd
import importlib.util
spec = importlib.util.spec_from_file_location("cr", __file__.replace("etc_test.py","cr_test.py"))
sys.argv=[sys.argv[0], sys.argv[1], "0.25"]; cr = importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)
d = cr.load(); d["ym"]=d.date.dt.to_period("M")
c = d.groupby(["ci","cj","ym","sensor"]).size().unstack("sensor").fillna(0)
c = c[(c[["T","A","S"]].sum(axis=1))>0]   # cell-months with any detection (selection caveat)
def etc(X):
    Q = np.cov(X.T)
    r2 = np.array([Q[0,1]*Q[0,2]/(Q[0,0]*Q[1,2]), Q[0,1]*Q[1,2]/(Q[1,1]*Q[0,2]), Q[0,2]*Q[1,2]/(Q[2,2]*Q[0,1])])
    ev = np.array([Q[0,0]-Q[0,1]*Q[0,2]/Q[1,2], Q[1,1]-Q[0,1]*Q[1,2]/Q[0,2], Q[2,2]-Q[0,2]*Q[1,2]/Q[0,1]])
    return r2, ev
for name, sub in (("all cell-months", c), ("fire season Jun-Oct", c[c.index.get_level_values("ym").month.isin([6,7,8,9,10])])):
    X = np.log1p(sub[["T","A","S"]].values)
    r2, ev = etc(X)
    # bootstrap over cells
    rs=[]; rng=np.random.default_rng(0)
    for _ in range(200):
        i = rng.integers(0,len(X),len(X)); rs.append(etc(X[i])[0])
    lo,hi=np.percentile(rs,[2.5,97.5],axis=0)
    print(f"{name} n={len(X)}  rho^2 vs truth  T={r2[0]:.2f}[{lo[0]:.2f},{hi[0]:.2f}]  A={r2[1]:.2f}[{lo[1]:.2f},{hi[1]:.2f}]  S={r2[2]:.2f}[{lo[2]:.2f},{hi[2]:.2f}]")
    print(f"   error var (log units) T={ev[0]:.3f} A={ev[1]:.3f} S={ev[2]:.3f}")
