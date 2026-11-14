# Interannual over-dispersion of monthly MODIS counts, Portugal, 2012-2019 ONLY.
import pandas as pd, numpy as np, sys
base=sys.argv[1]
fr=[]
for y in range(2012,2020):
    d=pd.read_csv(f"{base}/modis_{y}_Portugal.csv",usecols=['latitude','longitude','acq_date','confidence','type'])
    d=d[(d.type==0)&(d.confidence>=30)]
    assert d.acq_date.str[:4].astype(int).eq(y).all()
    fr.append(d)
d=pd.concat(fr); d['y']=d.acq_date.str[:4].astype(int); d['m']=d.acq_date.str[5:7].astype(int)
d['c']=(np.floor(d.latitude/0.25)).astype(int).astype(str)+'_'+(np.floor(d.longitude/0.25)).astype(int).astype(str)
cells=d.c.unique()
g=d.groupby(['c','m','y']).size()
idx=pd.MultiIndex.from_product([cells,range(1,13),range(2012,2020)],names=['c','m','y'])
g=g.reindex(idx,fill_value=0).unstack('y')
mu=g.mean(1); var=g.var(1,ddof=1)
for lo,hi in [(1,3),(3,8),(8,20),(20,60),(60,1e9)]:
    s=(mu>=lo)&(mu<hi)
    print(f"cell-month mean in [{lo},{hi}): n={s.sum()}, median var/mean={np.median(var[s]/mu[s]):.1f}")
nat=d.groupby(['m','y']).size().unstack('y').fillna(0)
print("national month: median var/mean =", round(float(np.median(nat.var(1)/nat.mean(1))),1), " median CV =", round(float(np.median(nat.std(1)/nat.mean(1))),2))
