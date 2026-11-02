"""Dual-observer (Huggins/Horvitz-Thompson style) operator: predict Aqua-detected fire units from S-NPP
detections alone, using P(Aqua | S-NPP detects, FRP_S) learned on matched units 2012-2015,
tested on 2016-2019 (all <=2019; never touches 2020+). Unit = 0.05deg cell x UTC day x day/night.
Prediction of Aqua total = sum_i p(FRP_i) / q, q = P(S-NPP | Aqua) from training.
Baseline = Aqua/S-NPP unit-count ratio from training. Scores at national-month and 0.25deg cell-month."""
import sys, numpy as np, pandas as pd, importlib.util
spec = importlib.util.spec_from_file_location("cr", __file__.replace("dual_observer_operator.py","cr_test.py"))
sys.argv=[sys.argv[0], sys.argv[1], "0.05"]; cr = importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)
d = cr.load()
bins=[0,1,2,3,5,7,10,15,20,30,50,100,1e6]
for dn in "DN":
    h = cr.histories(d, dn).reset_index()
    h["c25i"]=(h.ci*0.05//0.25).astype(int); h["c25j"]=(h.cj*0.05//0.25).astype(int)
    tr, te = h[h.y<=2015], h[h.y>=2016].copy()
    s = tr[tr.S==1]; p = s.groupby(pd.cut(s.frpS,bins),observed=False).A.mean()
    q = (tr.A & tr.S).sum()/tr.A.sum()
    ratio = tr.A.sum()/tr.S.sum()
    te["p"] = np.where(te.S==1, pd.cut(te.frpS,bins).map(p).astype(float), 0.0)
    te["pred_op"] = te.p/q; te["pred_ratio"]=te.S*ratio
    for lvl, keys in (("national-month",["ym"]),("0.25deg cell-month",["c25i","c25j","ym"])):
        g = te.groupby(keys)[["A","pred_op","pred_ratio"]].sum()
        g = g[(g.A>0)|(g.pred_ratio>0)]
        w = lambda c: 100*abs(g[c]-g.A).sum()/g.A.sum()
        print(f"{dn} {lvl:20s} n={len(g):5d} Aqua={g.A.sum():.0f}  WAPE operator {w('pred_op'):.1f}%  ratio {w('pred_ratio'):.1f}%  | totals op {g.pred_op.sum():.0f} ratio {g.pred_ratio.sum():.0f}")
    print(f"   q=P(S|A) train {q:.2f}, test {(te.A & te.S).sum()/te.A.sum():.2f}; ratio A/S train {ratio:.3f}, test {te.A.sum()/te.S.sum():.3f}")
