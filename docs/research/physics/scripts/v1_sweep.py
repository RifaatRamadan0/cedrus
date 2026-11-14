# V1 sweep over nominal MODIS pixel area A_nom (training years 2012-2019 only)
import sys
src = open(__file__.replace('v1_sweep.py', 'operator_sanity.py'), encoding='utf-8').read()
exec(src.split('res = {}')[0])
obsM = M.groupby(['sat', 'daynight']).size()
rhoD = obsM[('T', 'D')] / obsM[('A', 'D')]; rhoN = obsM[('T', 'N')] / obsM[('A', 'N')]
nV = len(V); nM = len(M)
print('rhoD', rhoD, 'rhoN', rhoN, 'VIIRS/MODIS obs', nV / nM)
for A in [1.0, 1.2, 1.47, 1.8, 2.0, 2.45, 3.36]:
    e = v1_counts(V, A).groupby(level=1).sum()
    aq = e['D'] + e['N']; full = e['D'] * (1 + rhoD) + e['N'] * (1 + rhoN)
    print(f"A_nom={A:.2f} Dp_day={4.44*A+0.52:.2f} Dp_night={4.43*A+1.01:.2f} aqD={e['D']:.0f} aqN={e['N']:.0f} "
          f"aqua_ratio_obs/pred D={obsM[('A','D')]/e['D']:.2f} N={obsM[('A','N')]/e['N']:.2f} full_pred={full:.0f} obs={nM} VIIRS/pred={nV/full:.2f}")
