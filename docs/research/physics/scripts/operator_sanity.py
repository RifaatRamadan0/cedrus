"""VIIRS(S-NPP 375 m) -> MODIS(Aqua/Terra C6.1)-equivalent observation operator: sanity run.

TRAINING YEARS ONLY (2012-2019). Reads FIRMS country CSVs; writes nothing outside this folder.
Physics: Sofiev & Kouznetsov 2026 GMD 19:10123 (Eq. 1-3, 5-7, Table 1).
Usage: python -I operator_sanity.py <raw_portugal_dir> <out_dir>
"""
import sys, json
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
from scipy.sparse.csgraph import connected_components
from scipy.sparse import coo_matrix

RAW, OUT = sys.argv[1], sys.argv[2]
KAPPA = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
YEARS = range(2012, 2020)

# ---------------- geometry (Sofiev & Kouznetsov 2026 Eq. 1-3; MODIS ATBD) ----------------
RE = 6378.137
def pix_size(theta, h, p):
    r = RE + h; s = p / h
    root = np.sqrt((RE / r) ** 2 - np.sin(theta) ** 2)
    dS = RE * s * (np.cos(theta) / root - 1.0)
    dT = r * s * (np.cos(theta) - root)
    return dS, dT
def ground_dist(theta, h):  # cross-track ground distance (km) for scan angle theta
    r = RE + h
    return RE * (np.arcsin(r / RE * np.sin(theta)) - theta)
H_MODIS, P_MODIS, THMAX_MODIS = 705.0, 1.0, np.deg2rad(55.0)
H_VIIRS, THMAX_VIIRS = 828.0, np.deg2rad(56.28)

def theta_from_dS(dS, h=H_MODIS, p=P_MODIS):
    th = np.linspace(0, THMAX_MODIS, 5001); s, _ = pix_size(th, h, p)
    return np.interp(dS, s, th)

# ---------------- pixel-wise OOp (Eq. 5-7, Table 1 MODIS C6.1) ----------------
TAB1 = {'D': dict(lam=4.44, mu=0.52, r0=0.07, r1=1.26), 'N': dict(lam=4.43, mu=1.01, r0=0.11, r1=1.06)}
C_O = 0.045
def W(P, A, dn):
    """detection probability of a pixel with FRP P (MW) and area A (km2): Eq.7 factor (FRP_OOp observe())."""
    c = TAB1[dn]; D = c['lam'] * A + c['mu']; r = c['r0'] + c['r1'] / A
    z = np.clip(-r * (P - D), -50, 50)
    return np.maximum(0.0, 1.0 / (1.0 + np.exp(z)) - C_O) / (1.0 - C_O)

# climatological swath sampling: ground point uniform in cross-track distance x in [0, x_max]
NB = 16
xmax = ground_dist(THMAX_MODIS, H_MODIS)
th_grid = np.linspace(0, THMAX_MODIS, 20001); x_grid = ground_dist(th_grid, H_MODIS)
xb = (np.arange(NB) + 0.5) / NB * xmax
thb = np.interp(xb, x_grid, th_grid)
dSb, dTb = pix_size(thb, H_MODIS, P_MODIS); Ab = dSb * dTb

# looks per day at latitude phi (one node: day or night)
def looks(phi_deg, swath_km, orbits_per_day, incl_deg):
    phi = np.deg2rad(phi_deg)
    D = 2 * np.pi * RE / orbits_per_day * np.cos(phi)
    psi = np.arcsin(np.clip(np.cos(np.deg2rad(incl_deg)) / np.cos(phi), -1, 1))
    return swath_km / np.cos(psi) / D
PHI = 39.6
nA = looks(PHI, 2 * xmax, 233 / 16, 98.2)
nV = looks(PHI, 2 * ground_dist(THMAX_VIIRS, H_VIIRS), 14.195, 98.7)
NU = nA / nV

# ---------------- data ----------------
def load(kind):
    fs = [f"{RAW}/{kind}_{y}_Portugal.csv" for y in YEARS]
    d = pd.concat([pd.read_csv(f, dtype={'acq_time': str}) for f in fs], ignore_index=True)
    d = d[d['type'] == 0]
    if kind == 'modis':
        d = d[pd.to_numeric(d.confidence, errors='coerce') >= 30]
        d['sat'] = d.satellite.str[0]
    else:
        d = d[d.confidence.astype(str).str[0].isin(['n', 'h'])]
        d['sat'] = 'N'
    t = d.acq_time.str.zfill(4)
    d['tmin'] = t.str[:2].astype(int) * 60 + t.str[2:].astype(int)
    d['month'] = d.acq_date.str[:7]
    d['x'] = (d.longitude + 8.0) * 111.32 * np.cos(np.deg2rad(PHI))
    d['y'] = (d.latitude - PHI) * 110.57
    return d.reset_index(drop=True)
M = load('modis'); V = load('viirs-snpp')

def overpass_id(d):
    d = d.sort_values(['acq_date', 'daynight', 'tmin']).copy()
    new = (d.acq_date != d.acq_date.shift()) | (d.daynight != d.daynight.shift()) | (d.tmin - d.tmin.shift() > 30)
    d['ov'] = new.cumsum()
    return d
V = overpass_id(V)

# ---------------- fire objects (connected components, link D_link km, per overpass) ----------------
def objects(d, link=1.0):
    lab = np.empty(len(d), int); base = 0
    for _, g in d.groupby('ov'):
        idx = g.index.values; pts = g[['x', 'y']].values
        if len(idx) == 1:
            lab[idx] = base; base += 1; continue
        pr = cKDTree(pts).query_pairs(link, output_type='ndarray')
        n = len(idx)
        A = coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(n, n)) if len(pr) else coo_matrix((n, n))
        _, l = connected_components(A, directed=False)
        lab[idx] = base + l; base += l.max() + 1
    return lab
V = V.reset_index(drop=True)
V['oid'] = objects(V, 1.0)

# ---------------- pseudo-MODIS tiling ----------------
OFFS = [(0, 0), (0.5, 0.5), (0.5, 0), (0, 0.5)]
def tile_sum(d, dS, dT, off, kappa=1.0):
    ix = np.floor(d.x.values / dS + off[0]).astype(np.int64)
    iy = np.floor(d.y.values / dT + off[1]).astype(np.int64)
    t = pd.DataFrame({'ov': d.ov.values, 'ix': ix, 'iy': iy, 'P': d.frp.values * kappa,
                      'dn': d.daynight.values, 'month': d.month.values, 'date': d.acq_date.values})
    return t.groupby(['ov', 'ix', 'iy'], sort=False).agg(P=('P', 'sum'), dn=('dn', 'first'),
                                                           month=('month', 'first'), date=('date', 'first')).reset_index()

def expected_counts(d, kappa=1.0, key='month'):
    """V2: sum over climatological swath bins and grid offsets of W(P_cell, A_bin); returns per key/dn."""
    acc = None
    for k in range(NB):
        for off in OFFS:
            c = tile_sum(d, dSb[k], dTb[k], off, kappa)
            w = np.where(c.dn == 'D', W(c.P.values, Ab[k], 'D'), W(c.P.values, Ab[k], 'N'))
            s = pd.Series(w).groupby([c[key].values, c.dn.values]).sum()
            acc = s if acc is None else acc.add(s, fill_value=0)
    return acc / (NB * len(OFFS)) * NU

def v1_counts(d, A_nom, key='month'):
    th = np.interp(A_nom, Ab, thb); dS, dT = pix_size(th, H_MODIS, P_MODIS)
    acc = None
    for off in OFFS:
        c = tile_sum(d, dS, dT, off)
        Dlim = np.where(c.dn == 'D', TAB1['D']['lam'] * A_nom + TAB1['D']['mu'], TAB1['N']['lam'] * A_nom + TAB1['N']['mu'])
        s = pd.Series((c.P.values >= Dlim).astype(float)).groupby([c[key].values, c.dn.values]).sum()
        acc = s if acc is None else acc.add(s, fill_value=0)
    return acc / len(OFFS) * NU

res = {}
res['geometry'] = dict(xmax_km=float(xmax), modis_edge_dS=float(pix_size(THMAX_MODIS, H_MODIS, 1)[0]),
                       modis_edge_dT=float(pix_size(THMAX_MODIS, H_MODIS, 1)[1]),
                       modis_edge_A=float(np.prod(pix_size(THMAX_MODIS, H_MODIS, 1))),
                       swath_uniform_mean_A=float(Ab.mean()), swath_uniform_median_A=float(np.median(Ab)),
                       nA_looks=float(nA), nV_looks=float(nV), NU=float(NU))
# observed MODIS pixel-area distribution (Aqua) from FIRMS scan (theta inverted from scan)
MA = M[M.sat == 'A']
thA = theta_from_dS(MA.scan.values); dS_, dT_ = pix_size(thA, H_MODIS, 1.0)
res['aqua_detected_area'] = dict(median_scanxtrack=float((MA.scan * MA.track).median()),
                                 median_from_theta=float(np.median(dS_ * dT_)),
                                 frp_weighted_mean_from_theta=float(np.average(dS_ * dT_, weights=MA.frp)))

# counts
obs = M.groupby(['month', 'sat', 'daynight']).size().unstack(['sat', 'daynight'], fill_value=0)
vcnt = V.groupby(['month', 'daynight']).size().unstack(fill_value=0)
nobj = V.groupby(['month', 'daynight'])['oid'].nunique().unstack(fill_value=0)
e2 = expected_counts(V, KAPPA).unstack(fill_value=0)
e1n = v1_counts(V, 1.0).unstack(fill_value=0)           # nadir-equivalent
e1m = v1_counts(V, float(Ab.mean())).unstack(fill_value=0)  # swath-mean area
e1f = v1_counts(V, 2.45).unstack(fill_value=0)          # FRP_OOp mean_pixel_size MODIS
tot = lambda s: float(np.asarray(s).sum())
A_D, A_N = obs[('A', 'D')], obs[('A', 'N')]
T_D, T_N = obs[('T', 'D')], obs[('T', 'N')]
res['totals_2012_2019'] = dict(
    viirs_pixels_D=tot(vcnt['D']), viirs_pixels_N=tot(vcnt['N']),
    viirs_objects_D=tot(nobj['D']), viirs_objects_N=tot(nobj['N']),
    aqua_D=tot(A_D), aqua_N=tot(A_N), terra_D=tot(T_D), terra_N=tot(T_N),
    V2_aqua_eq_D=tot(e2['D']), V2_aqua_eq_N=tot(e2['N']),
    V1_nadir_D=tot(e1n['D']), V1_nadir_N=tot(e1n['N']),
    V1_meanA_D=tot(e1m['D']), V1_meanA_N=tot(e1m['N']),
    V1_A245_D=tot(e1f['D']), V1_A245_N=tot(e1f['N']))
res['ratios'] = dict(viirs_over_modis_all=tot(vcnt.values) / tot(obs.values),
                     viirs_over_aqua=tot(vcnt.values) / (tot(A_D) + tot(A_N)),
                     terra_over_aqua_D=tot(T_D) / tot(A_D), terra_over_aqua_N=tot(T_N) / tot(A_N))
# fraction of VIIRS objects whose summed FRP exceeds MODIS D_p at A=1 and at swath-mean A
og = V.groupby('oid').agg(P=('frp', 'sum'), dn=('daynight', 'first'))
for A in (1.0, float(Ab.mean())):
    Dl = np.where(og.dn == 'D', TAB1['D']['lam'] * A + TAB1['D']['mu'], TAB1['N']['lam'] * A + TAB1['N']['mu'])
    res[f'frac_objects_above_Dp_A{A:.2f}'] = dict(D=float((og.P[og.dn == 'D'] >= Dl[og.dn == 'D']).mean()),
                                                N=float((og.P[og.dn == 'N'] >= Dl[og.dn == 'N']).mean()))

# monthly correlation and multiplicity calibration (Aqua only); m = sum(obs)/sum(pred) per day/night
mon = pd.DataFrame({'aD': A_D, 'aN': A_N, 'e2D': e2['D'], 'e2N': e2['N'], 'e1D': e1m['D'], 'e1N': e1m['N'],
                    'vD': vcnt['D'], 'vN': vcnt['N']}).fillna(0)
mon['year'] = mon.index.str[:4].astype(int)
cal = {}
for dn in 'DN':
    m2 = mon[f'a{dn}'].sum() / mon[f'e2{dn}'].sum(); m1 = mon[f'a{dn}'].sum() / mon[f'e1{dn}'].sum()
    r_raw = mon[f'a{dn}'].sum() / mon[f'v{dn}'].sum()
    lc = lambda a, b: float(np.corrcoef(np.log1p(a), np.log1p(b))[0, 1])
    # LOYO WAPE on monthly Aqua counts within training years (fit scale on 7 yrs, test 1)
    wape = {'raw_ratio': [], 'V1': [], 'V2': []}
    for y in YEARS:
        tr, te = mon[mon.year != y], mon[mon.year == y]
        for name, col in (('raw_ratio', f'v{dn}'), ('V1', f'e1{dn}'), ('V2', f'e2{dn}')):
            k = tr[f'a{dn}'].sum() / tr[col].sum()
            wape[name].append((np.abs(te[f'a{dn}'] - k * te[col]).sum(), te[f'a{dn}'].sum()))
    cal[dn] = dict(m_V2=float(m2), m_V1meanA=float(m1), aqua_per_viirs_pixel=float(r_raw),
                   logcorr_V2=lc(mon[f'a{dn}'], mon[f'e2{dn}']), logcorr_V1=lc(mon[f'a{dn}'], mon[f'e1{dn}']),
                   logcorr_raw=lc(mon[f'a{dn}'], mon[f'v{dn}']),
                   LOYO_WAPE={k: float(sum(a for a, _ in v) / sum(b for _, b in v)) for k, v in wape.items()})
res['monthly_calibration'] = cal
yr = mon.groupby('year')[['aD', 'aN', 'e2D', 'e2N', 'vD', 'vN']].sum()
yr['m2_D'] = yr.aD / yr.e2D; yr['m2_N'] = yr.aN / yr.e2N; yr['raw_D'] = yr.vD / yr.aD; yr['raw_N'] = yr.vN / yr.aN
res['yearly'] = yr.round(3).reset_index().to_dict(orient='records')

# ---------------- matched detection curve: S-NPP day objects vs Aqua day pixels ----------------
MA = M[(M.sat == 'A')].copy(); MA['tmin'] = MA.tmin
rows = []
for dn in 'DN':
    vo = V[V.daynight == dn].groupby('oid').agg(date=('acq_date', 'first'), t=('tmin', 'mean'), P=('frp', 'sum'),
                                              n=('frp', 'size'), x=('x', 'mean'), y=('y', 'mean'),
                                              px=('x', lambda s: list(s)), py=('y', lambda s: list(s)))
    ma = MA[MA.daynight == dn]
    aqua_days = ma.groupby('acq_date').tmin.median()
    for date, g in vo.groupby('date'):
        if date not in aqua_days.index:
            continue  # Aqua overpass time unknown that day (no Aqua pixel anywhere in PT) -> skip
        tA = aqua_days[date]
        if dn == 'N' and abs(tA - g.t.mean()) > 720: tA = tA  # (night times both near 01-03 UTC)
        ag = ma[ma.acq_date == date]
        tree = cKDTree(ag[['x', 'y']].values)
        for _, o in g.iterrows():
            pts = np.c_[o.px, o.py]
            dmin = tree.query(pts, k=1)[0].min()
            rows.append((dn, o.P, o.n, float(dmin), float(abs(tA - o.t))))
mt = pd.DataFrame(rows, columns=['dn', 'P', 'n', 'dmin', 'dt'])
mt['hit'] = (mt.dmin <= 2.0).astype(int)
mt.to_csv(f"{OUT}/matched_objects_2012_2019.csv", index=False)
bins = [0, 2, 4, 6, 8, 10, 15, 20, 30, 50, 100, 200, 1e6]
curve = {}
for dn in 'DN':
    s = mt[(mt.dn == dn) & (mt.dt <= 60)]
    g = s.groupby(pd.cut(s.P, bins), observed=True)
    pr = []
    for iv, gg in g:
        Pm = float(gg.P.median())
        pred = float(np.mean([W(Pm, a, dn) for a in Ab]))
        pr.append(dict(bin=str(iv), n=int(len(gg)), hit=float(gg.hit.mean()), P_median=Pm, pred_swathavg=pred,
                       pred_nadir=float(W(Pm, 1.0, dn))))
    curve[dn] = pr
res['matched_curve_dt_le_60min'] = curve
res['matched_n'] = int(len(mt))

# logistic fit hit ~ log P (marginal over swath position), per dn
from scipy.optimize import minimize
fits = {}
for dn in 'DN':
    s = mt[(mt.dn == dn) & (mt.dt <= 60)]
    X = np.log(s.P.clip(lower=0.05).values); y = s.hit.values
    def nll(b):
        z = b[0] + b[1] * X; p = 1 / (1 + np.exp(-z)); p = np.clip(p, 1e-9, 1 - 1e-9)
        return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    b = minimize(nll, [-3, 1], method='Nelder-Mead').x
    fits[dn] = dict(b0=float(b[0]), b1=float(b[1]), P50_MW=float(np.exp(-b[0] / b[1])), n=int(len(s)))
    # asymptote-capped version: p = pmax * logistic
    def nll2(b):
        pm = 1 / (1 + np.exp(-b[2])); z = b[0] + b[1] * X; p = pm / (1 + np.exp(-z)); p = np.clip(p, 1e-9, 1 - 1e-9)
        return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    b2 = minimize(nll2, [-3, 1, 1], method='Nelder-Mead', options=dict(maxiter=4000)).x
    fits[dn + '_capped'] = dict(b0=float(b2[0]), b1=float(b2[1]), pmax=float(1 / (1 + np.exp(-b2[2]))),
                               P50_MW=float(np.exp(-b2[0] / b2[1])))
res['logistic_fits'] = fits

json.dump(res, open(f"{OUT}/sanity_2012_2019_k{KAPPA}.json", 'w'), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
