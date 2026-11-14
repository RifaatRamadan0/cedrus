"""Same as dual_observer_operator.py but target = Terra units (T) and any-MODIS units (M = T or A). 2012-2019 only."""
import sys, numpy as np, pandas as pd, importlib.util
spec = importlib.util.spec_from_file_location("cr", __file__.replace("dual_observer_tm.py","cr_test.py"))
sys.argv=[sys.argv[0], sys.argv[1], "0.05"]; cr = importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)
d = cr.load()
bins=[0,1,2,3,5,7,10,15,20,30,50,100,1e6]
for dn in "DN":
    h = cr.histories(d, dn).reset_index(); h["M"]=(h["T"]|h["A"]).astype(int)
    h["c25i"]=(h.ci*0.05//0.25).astype(int); h["c25j"]=(h.cj*0.05//0.25).astype(int)
    for T in ("T","M"):
        tr, te = h[h.y<=2015], h[h.y>=2016].copy()
        s = tr[tr.S==1]; p = s.groupby(pd.cut(s.frpS,bins),observed=False)[T].mean()
        q = (tr[T] & tr.S).sum()/tr[T].sum(); ratio = tr[T].sum()/tr.S.sum()
        te["p"] = np.where(te.S==1, pd.cut(te.frpS,bins).map(p).astype(float), 0.0)
        te["op"]=te.p/q; te["rt"]=te.S*ratio
        for lvl, keys in (("national-month",["ym"]),("0.25deg cell-month",["c25i","c25j","ym"])):
            g = te.groupby(keys)[[T,"op","rt"]].sum(); g=g[(g[T]>0)|(g.rt>0)]
            w=lambda c:100*abs(g[c]-g[T]).sum()/g[T].sum()
            print(f"{dn} target={T} {lvl:20s} WAPE operator {w('op'):.1f}%  ratio {w('rt'):.1f}%   q train {q:.2f}")
