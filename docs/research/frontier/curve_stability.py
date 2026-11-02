"""Is the empirical dual-observer curve P(Aqua detects | S-NPP detects, FRP_S) stable across years?
Train 2012-2015, check 2016-2019 (all <=2019). Also: does curve-weighted S-NPP predict Aqua counts per month?"""
import sys; sys.argv=[sys.argv[0], sys.argv[1], "0.05"]
import numpy as np, pandas as pd
import importlib.util
spec = importlib.util.spec_from_file_location("cr", __file__.replace("curve_stability.py","cr_test.py")); cr = importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)
d = cr.load()
bins=[0,2,5,10,20,50,100,1e6]
for dn in "DN":
    h = cr.histories(d, dn); s = h[h.S==1].copy(); s["bin"]=pd.cut(s.frpS,bins)
    tab = s.groupby([np.where(s.y<=2015,"12-15","16-19"),"bin"],observed=True).A.mean().unstack(0).round(3)
    print(dn, "\n", tab.to_string())
    p = s[s.y<=2015].groupby("bin",observed=True).A.mean()
    t = s[s.y>=2016].copy(); t["p"]=t.bin.map(p).astype(float)
    # predicted Aqua-and-SNPP joint count vs observed, monthly; plus scaled to Aqua total via 1/P(S|A)
    m = t.groupby("ym").agg(pred=("p","sum"), obs=("A","sum"))
    m = m[m.obs>=5]
    print("monthly joint(A&S) pred vs obs 2016-19: WAPE %.1f%%, n=%d" % (100*abs(m.pred-m.obs).sum()/m.obs.sum(), len(m)))
