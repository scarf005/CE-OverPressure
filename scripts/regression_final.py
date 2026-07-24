#!/usr/bin/env python3
"""Final regression: HE (n=27) + Thermobaric (n=12), separate models."""
import math

class P:
    __slots__=('label','dmg','rad','filler','frags','therm','blast_eff','w')
    def __init__(s,l,d,r,f,fr,t,be,w=1.0):
        s.label=l;s.dmg=d;s.rad=r;s.filler=f;s.frags=fr;s.therm=t;s.blast_eff=be;s.w=w
    @property
    def blast(self): return self.filler*self.blast_eff

HE = [P(*x) for x in [
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
    ("105mm M1 (air)",  216, 6.5, 2.180, 84, 0, 0.70, 1.0),
    ("152mm OF540(air)",478,10.0, 5.860,120, 0, 0.70, 1.0),
    ("155mm M107(air)", 452, 9.5, 6.620,120, 0, 0.70, 1.0),
]]

TB = [P(*x) for x in [
    # label, dmg, rad, filler_kg, frags, therm, blast_eff, w
    # Small
    ("30x64 FuelCell",   78, 2.5, 0.035,  0, 1, 1.80, 1.0),
    ("ChargedRocket TB", 84, 3.9, 1.000,  0, 1, 1.80, 0.7),
    # Medium rockets
    ("57mm S5 TB",      160, 3.5, 0.400,  0, 1, 1.50, 0.8),  # S-5TB ~0.4kg
    ("84mm C-G TB",     160, 3.5, 0.600,  0, 1, 1.50, 0.8),  # Carl Gustav
    ("83mm SMAW TB",    260, 5.0, 1.500,  0, 1, 1.60, 0.8),
    # Large rockets
    ("RPG-7 TBG-7V",    275, 5.0, 1.800,  0, 1, 1.70, 0.9),
    ("SPG-9 TB",        277, 5.0, 2.000,  0, 1, 1.70, 0.8),
    ("80mm S8 TB",      309, 5.5, 1.000,  0, 1, 1.60, 0.8),  # S-8DM ~1kg
    ("RPO-A Shmel",     293, 5.0, 2.100,  0, 1, 1.80, 0.9),
    # Howitzer thermobaric (comp explosion)
    ("105mm Hw TB",     116, 2.5, 4.000,  0, 1, 1.70, 0.7),
    ("152mm Hw TB",     247, 4.0, 8.000,  0, 1, 1.70, 0.7),
    ("155mm Hw TB",     253, 4.0, 9.000,  0, 1, 1.70, 0.7),
]]

ALL = HE + TB

def ols(pts):
    k=3; X=[[0.]*k for _ in range(k)]; y=[0.]*k; sw=0.
    for p in pts:
        w=p.w; ld=math.log(p.dmg+1e-6); lr=math.log(p.rad+1e-6); tv=math.log(p.blast); sw+=w
        fv=[1.0,ld,lr]
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
    wm=sum(p.w*math.log(p.blast) for p in pts)/sw
    ss_tot=sum(p.w*(math.log(p.blast)-wm)**2 for p in pts)
    ss_res=0.
    for p in pts:
        ld=math.log(p.dmg+1e-6); lr=math.log(p.rad+1e-6)
        pred=beta[0]+beta[1]*ld+beta[2]*lr; ss_res+=p.w*(math.log(p.blast)-pred)**2
    return beta,1-ss_res/ss_tot if ss_tot>1e-12 else 1.

def pred(p,beta):
    return math.exp(beta[0]+beta[1]*math.log(p.dmg+1e-6)+beta[2]*math.log(p.rad+1e-6))

def combined_r2(he_pts,tb_pts,bh,bt):
    allp=he_pts+tb_pts
    wm=sum(p.w*math.log(p.blast) for p in allp)/sum(p.w for p in allp)
    ss_tot=sum(p.w*(math.log(p.blast)-wm)**2 for p in allp)
    ss_res=sum(p.w*(math.log(p.blast)-pred(p,bh))**2 for p in he_pts)
    ss_res+=sum(p.w*(math.log(p.blast)-pred(p,bt))**2 for p in tb_pts)
    return 1-ss_res/ss_tot if ss_tot>1e-12 else 1.

bh,r2h = ols(HE)
bt,r2t = ols(TB)
r2c = combined_r2(HE,TB,bh,bt)
b1,r2a = ols(ALL)

def show(title,beta,r2,pts):
    k=math.exp(beta[0]); a,b=beta[1],beta[2]
    w=1-b/3; ye=a/w if w>1e-6 else 0
    print(f"  {title}")
    print(f"    tntKg = {k:.6g} · d^{a:.4f} · r^{b:.4f}")
    print(f"    R²={r2:.4f}  n={len(pts)}  weight={w:.3f}  YieldExp={ye:.3f}")
    return k,a,b,w,ye

print("="*72)
print(f"  HE MODEL (n={len(HE)})")
print("="*72)
kh,ah,bh_,wh,yeh = show("",bh,r2h,HE)

print(f"\n{'='*72}")
print(f"  THERMOBARIC MODEL (n={len(TB)})")
print("="*72)
kt,at,bt_,wt,yet = show("",bt,r2t,TB)

print(f"\n{'='*72}")
print(f"  COMBINED R² = {r2c:.4f}")
print(f"  (baseline single model: R²={r2a:.4f})")
print(f"{'='*72}")

print(f"\n{'='*72}")
print(f"  PREDICTIONS")
print(f"{'='*72}")
print(f"  {'Weapon':<22s} {'Actual':>7s} {'HE pred':>9s} {'TB pred':>9s} {'Used':>10s} {'Err':>7s}")
print(f"  {'-'*22} {'-'*7} {'-'*9} {'-'*9} {'-'*10} {'-'*7}")

for p in ALL:
    ph = pred(p,bh)
    pt = pred(p,bt)
    use = pt if p.therm else ph
    err = use/p.blast
    mark = " ←" if abs(math.log(err))>0.5 else ""
    print(f"  {p.label:<22s} {p.blast:7.3f} {ph:9.3f} {pt:9.3f} {use:10.3f} {err:7.3f}{mark}")

# Key numbers for Overpressure
print(f"\n{'='*72}")
print(f"  OVERPRESSURE SETTINGS")
print(f"{'='*72}")
print(f"  HE:  damagePerKgTnt ≈ {1/kh:.0f}   damageYieldWeight={wh:.3f}  YieldExponent={yeh:.3f}")
print(f"  TB:  damagePerKgTnt ≈ {1/kt:.0f}   damageYieldWeight={wt:.3f}  YieldExponent={yet:.3f}")
