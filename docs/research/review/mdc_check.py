# Recompute the Poisson MDC table in ALGORITHM.md s4. Read-only, no data.
from scipy.stats import binom, poisson
import numpy as np
def power_cond(lam, n, d, a=0.05):
    # exact conditional test: X|X+S=T ~ Bin(T, p), p0=1/(n+1)
    p0=1/(n+1); p1=(1+d)/(n+1+d)
    Tmax=int(lam*(n+1+d)*3+60)
    pw=0.0
    for T in range(Tmax):
        pT=poisson.pmf(T, lam*(n+d+1))
        if pT<1e-14 and T>lam*(n+1+d): continue
        # smallest c with P0(X>=c)<=a
        c=int(binom.ppf(1-a,T,p0))+1
        while c>0 and binom.sf(c-2,T,p0)<=a: c-=1
        pw+=pT*binom.sf(c-1,T,p1)
    return pw
def power_known(lam,d,a=0.05):
    c=int(poisson.ppf(1-a,lam))+1
    return poisson.sf(c-1,lam*(1+d))
def mdc(f):
    lo,hi=0.0,50.0
    for _ in range(50):
        m=(lo+hi)/2
        if f(m)>=0.9: hi=m
        else: lo=m
    return hi
for lam in [1,2,5,10,20,50,100]:
    print(lam, "n=10 cond: +%.0f%%"%(100*mdc(lambda d:power_cond(lam,10,d))),
          " n=20 cond: +%.0f%%"%(100*mdc(lambda d:power_cond(lam,20,d))),
          " known-mean: +%.0f%%"%(100*mdc(lambda d:power_known(lam,d))))
