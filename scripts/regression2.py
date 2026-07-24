#!/usr/bin/env python3
"""Final regression: artillery + grenades + thermobaric, all in-game values."""
import math

class P:
    __slots__ = ('label','dmg','rad','filler','frags','therm','blast_eff','w')
    def __init__(s,l,d,r,f,fr,t,be,w=1.0):
        s.label=l;s.dmg=d;s.rad=r;s.filler=f;s.frags=fr;s.therm=t;s.blast_eff=be;s.w=w
    @property
    def blast(self): return self.filler*self.blast_eff

ALL = [P(*x) for x in [
    # label, dmg, rad, filler, frags, therm, blast_eff, w
    ("25x40mm HE",       18, 1.0, 0.020, 16, 0, 0.85, 0.8),
    ("30x29 VOG-17M",    22, 1.0, 0.050, 28, 0, 0.85, 0.8),
    ("40x46 M406 HE",    22, 1.0, 0.040, 20, 0, 0.85, 0.8),
    ("40x53 M430 HEDP",  23, 1.0, 0.045, 36, 0, 0.80, 0.7),
    ("40x53 VOG-25 HE",  26, 1.0, 0.048, 24, 0, 0.85, 0.8),
    ("M67 frag grenade", 80, 2.0, 0.240, 26, 0, 0.55, 1.0),
    ("RPG-7 OG-7V frag", 58, 1.5, 0.370, 80, 0, 0.50, 0.9),
    ("83mm PIAT HE",    139, 2.5, 0.450, 80, 0, 0.70, 0.8),
    ("37mm HE",          33, 1.0, 0.030,  4, 0, 0.70, 0.8),
    ("40mm Bofors HE",   64, 1.5, 0.100,  9, 0, 0.70, 0.8),
    ("50mm Type89 Mort", 42, 1.5, 0.150,  6, 0, 0.70, 0.8),
    ("57mm S-60 HE",     55, 1.5, 0.200, 21, 0, 0.70, 0.8),
    ("57mm Bofors HE",  108, 2.0, 0.350, 21, 0, 0.70, 0.7),
    ("81mm Mortar M43", 156, 2.5, 0.548, 41, 0, 0.70, 1.0),
    ("100mm naval HE",  209, 3.0, 1.500, 81, 0, 0.70, 0.8),
    ("105mm M1 HE",     217, 3.0, 2.180, 84, 0, 0.70, 1.0),
    ("105x607mmR HE",   331, 4.0, 2.000, 96, 0, 0.70, 0.7),
    ("105x617mmR HE",   199, 3.0, 1.800, 76, 0, 0.70, 0.7),
    ("120mm Mortar M57",237, 3.5, 3.000, 90, 0, 0.70, 0.9),
    ("120mm Cannon HE", 315, 4.0, 3.000,110, 0, 0.70, 0.8),
    ("15cm Nebelwerfer",228, 3.5, 2.500, 45, 0, 0.70, 0.8),
    ("152mm OF-540 HE", 578, 5.5, 5.860,120, 0, 0.70, 1.0),
    ("155mm M107 HE",   546, 5.5, 6.620,120, 0, 0.70, 1.0),
    ("28cm Spgr HE",    837, 7.0,20.000,120, 0, 0.70, 0.5),
    # thermobaric
    ("30x64 Thermobar",  78, 2.5, 0.035,  0, 1, 1.80, 1.0),  # ~35g thermobaric
    ("RPG-7 Thermobar", 275, 5.0, 1.800,  0, 1, 1.80, 0.8),
    ("SPG-9 Thermobar", 277, 5.0, 2.000,  0, 1, 1.80, 0.8),
    ("RPO-A Thermobar", 293, 5.0, 2.100,  0, 1, 1.80, 0.8),
    # airburst
    ("105mm M1 (air)",  216, 6.5, 2.180, 84, 0, 0.70, 1.0),
    ("152mm OF-540 (air)",478,10.0,5.860,120, 0, 0.70, 1.0),
    ("155mm M107 (air)",452, 9.5, 6.620,120, 0, 0.70, 1.0),
]]

def ols(pts, features, target_attr='blast'):
    fn_map = {'c':lambda p:1,'d':lambda p:math.log(p.dmg+1e-6),'r':lambda p:math.log(p.rad+1e-6),
              'f':lambda p:math.log(p.frags+1),'t':lambda p:float(p.therm)}
    fns = [fn_map[n] for n in features]
    k=len(fns); X=[[0.]*k for _ in range(k)]; y=[0.]*k; sw=0.
    for p in pts:
        w=p.w; fv=[f(p) for f in fns]; tv=math.log(getattr(p,target_attr)); sw+=w
        for i in range(k):
            y[i]+=w*fv[i]*tv
            for j in range(k): X[i][j]+=w*fv[i]*fv[j]
    a=[X[i][:]+[y[i]] for i in range(k)]
    for col in range(k):
        pv=max(range(col,k),key=lambda r:abs(a[r][col]))
        a[col],a[pv]=a[pv],a[col]
        for r in range(col+1,k):
            fac=a[r][col]/a[col][col]
            for j in range(col,k+1): a[r][j]-=fac*a[col][j]
    beta=[0.]*k
    for i in range(k-1,-1,-1): beta[i]=(a[i][k]-sum(a[i][j]*beta[j] for j in range(i+1,k)))/a[i][i]
    wm=sum(p.w*math.log(getattr(p,target_attr)) for p in pts)/sw
    ss_tot=sum(p.w*(math.log(getattr(p,target_attr))-wm)**2 for p in pts)
    ss_res=0.
    for p in pts:
        fv=[f(p) for f in fns]; pred=sum(beta[i]*fv[i] for i in range(k))
        ss_res+=p.w*(math.log(getattr(p,target_attr))-pred)**2
    return beta,1-ss_res/ss_tot if ss_tot>1e-12 else 1.

def pred(p,beta,features):
    m={'c':1,'d':math.log(p.dmg+1e-6),'r':math.log(p.rad+1e-6),'f':math.log(p.frags+1),'t':float(p.therm)}
    return math.exp(sum(beta[i]*m[features[i]] for i in range(len(beta))))

print("="*70)
print("  FINAL REGRESSION (in-game values, blast-efficiency adjusted)")
print("="*70)

configs = [
    (['c','d','r'], "A: ln(d)+ln(r)"),
    (['c','d','r','t'], "A: ln(d)+ln(r)+therm"),
    (['c','d','r','f'], "A: ln(d)+ln(r)+ln(f)"),
    (['c','d','r','f','t'], "A: ln(d)+ln(r)+ln(f)+therm"),
]
results = []
for feats,label in configs:
    beta,r2 = ols(ALL, feats)
    n_out = sum(1 for p in ALL if abs(math.log(max(pred(p,beta,feats)/p.blast,p.blast/pred(p,beta,feats))))>0.5)
    results.append((label,r2,n_out,beta,feats))
    print(f"  {label:<35s} R²={r2:.4f}  out={n_out}/{len(ALL)}")
    ps=' · '.join(f'{n}={beta[i]:+.4f}' for i,n in enumerate(feats))
    print(f"    {ps}")

print(f"\n  30x64mm prediction:")
for label,r2,n_out,beta,feats in results:
    p30 = pred(ALL[-5],beta,feats)  # 30x64 thermobaric = 5th from end
    print(f"    {label:<35s} → {p30:.3f} kg TNT")

best = max(results,key=lambda x:x[1])
print(f"\n  Best: {best[0]} (R²={best[1]:.4f})")

# Derive Overpressure settings from best model
beta,r2 = ols(ALL, best[4])
a,b = beta[1],beta[2]  # ln(d), ln(r) coefficients
w = 1.0 - b/3.0  # damageYieldWeight
ye = a/w if w>1e-6 else float('nan')
print(f"\n  Implied OverpressureSettings from {best[0]}:")
print(f"    damageYieldWeight  = {w:.3f}")
print(f"    YieldExponent       = {ye:.3f}")

# Predict 30mm thermobaric
tnt30 = pred(ALL[-5],beta,best[4])
print(f"\n  With these settings, 30x64mm thermobaric → {tnt30:.3f} kg TNT")
# Pressure at 1m
cr = tnt30**(1/3); z=1.0/cr
if z<1.35: pres=6.7/z**3+1
else: pres=0.975/z+1.455/z**2+5.85/z**3-0.019
kPa = pres*100*1.35*1.45
print(f"    → {kPa:.0f} kPa at 1m (real 40mm TB: 100 kPa)")
