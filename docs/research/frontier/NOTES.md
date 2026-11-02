Frontier scan scratch notes (31 Oct 2026). Data used: Portugal FIRMS 2012-2019 ONLY, type==0, read-only.

## Scripts and outputs (this folder)
- cr_test.py -> cr_out_0.05.txt, cr_out_0.1.txt, cr_yearly_*.csv : capture-recapture (Chapman pairs, 3-source log-linear)
- curve_stability.py -> curve_out.txt : P(Aqua | S-NPP, FRP_S) stable 2012-15 vs 2016-19
- dual_observer_operator.py -> dual_out.txt ; dual_observer_tm.py -> dual_tm_out.txt : FRP-conditioned operator vs single ratio
- etc_test.py -> etc_out.txt : extended triple collocation T/A/S on log1p cell-month counts

## Capture-recapture result (unit = 0.05 deg cell x UTC day x D/N)
- Day, 2018-19: P(S-NPP | Aqua)=0.58, P(NOAA-20 | S-NPP)=0.38, P(S-NPP | NOAA-20)=0.33. Night: 0.83 / 0.58 / 0.56.
  -> even same-instrument VIIRS pair 50 min apart overlaps only ~1/3 in daytime: closure/independence badly broken.
- Monthly N-hat(VIIRS pair)/N-hat(MODIS pair), 2018-19: day median 1.87, sd(log) 0.59; raw count ratio sd(log) 0.31.
  Night 0.71 / 0.55 vs raw 0.48. At 0.1 deg: day 1.99/0.57 vs raw 0.29.
  -> CR "true count" is NOT sensor-independent and is LESS stable than the raw ratio. Verdict: reject as harmonized unit.
- Strong Mh heterogeneity: P(Aqua | S-NPP) day by FRP_S bin 0-2,2-5,5-10,10-20,20-50,50-100,>100 MW:
  0.03 0.09 0.21 0.39 0.56 0.70 0.80. Night: 0.02 0.13 0.38 0.56 0.74 0.89 0.90.
- Same curve, train 12-15 vs 16-19 (day): 0.046/0.022, 0.087/0.086, 0.209/0.220, 0.405/0.365, 0.559/0.569, 0.719/0.684, 0.841/0.760.

## Dual-observer operator (what survives from CR)
Pred MODIS-units = sum over S-NPP units of p(FRP_S) / q, q = P(S | MODIS) (train 2012-15, test 2016-19).
WAPE operator vs single national ratio:
- Aqua day: national-month 17.8 vs 32.6 ; 0.25deg cell-month 67.0 vs 85.2
- Aqua night: 24.1 vs 58.7 ; 49.8 vs 94.6
- Any-MODIS day: 19.6 vs 25.2 ; 66.7 vs 78.2
- Any-MODIS night: 18.8 vs 51.8 ; 53.1 vs 80.4
- Terra day: 26.9 vs 36.3 ; 92.9 vs 107.3
Caveats: cell-day units, not pixel counts; baseline is one national ratio, not the team's shrunk r(cell,month); split differs from team's 2020-25 test. Not yet compared to the Sofiev operator.

## ETC (log1p cell-month counts, 0.25 deg, cell-months with any detection, n=5870)
rho^2 vs common signal: Terra 0.64, Aqua 0.76, S-NPP 0.77 (fire season 0.73/0.79/0.82).
Caveat: Aqua and S-NPP share overpass time -> correlated errors -> TC biased; quadruple collocation with NOAA-20 (2018+) would be needed.

## Literature verified (see final report for list)
GFED5NRT Chen et al. 2026 ESSD 18:7535 doi:10.5194/essd-18-7535-2026; CAMS GFAS VIIRS from 4 Dec 2025 (CAMS news 25 Feb 2026);
Weatherhead 2017 ACP 17:15069; Weatherhead 1998 JGR 103(D14):17149; Menne & Williams 2009 PHA; Gruber 2019 ESSD 11:717;
Kang, Lee, Im 2026 RSE 333:115136; Correll, Moritz, Heer CHI 2018 VSUP; Fernandes et al. CHI 2018 quantile dotplots;
Joslyn & LeClerc 2012 JEP:Applied 18(1):126; Budescu et al. 2009 Psych Sci 20:299 and 2014 Nat Clim Change (doi:10.1038/nclimate2194);
Corringham, Westerling, Morehouse 2008 J Forestry 106(2):71 decision calendar; NIFC monthly outlook above/near/below normal.
No precedent found for capture-recapture on satellite active fires (absence = not exhaustively verified).
