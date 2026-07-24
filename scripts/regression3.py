#!/usr/bin/env python3
"""Compare piecewise & split models for realistic blast-yield prediction."""

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
    ("30x64 Thermobar",  78, 2.5, 0.035,  0, 1, 1.80, 1.0),
    ("RPG-7 Thermobar", 275, 5.0, 1.800,  0, 1, 1.80, 0.8),
    ("SPG-9 Thermobar", 277, 5.0, 2.000,  0, 1, 1.80, 0.8),
    ("RPO-A Thermobar", 293, 5.0, 2.100,  0, 1, 1.80, 0.8),
    ("105mm M1 (air)",  216, 6.5, 2.180, 84, 0, 0.70, 1.0),
    ("152mm OF-540 (air)",478,10.0,5.860,120, 0, 0.70, 1.0),
    ("155mm M107 (air)",452, 9.5, 6.620,120, 0, 0.70, 1.0),
]]

he_only = [p for p in ALL if not p.therm]
therm_only = [p for p in ALL if p.therm]

def ols_custom(pts, design_fn, k):
    X=[[0.]*k for _ in range(k)]; y=[0.]*k; sw=0.
    for p in pts:
        w=p.w; fv=design_fn(p); tv=math.log(p.blast); sw+=w
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
        fv=design_fn(p); pred=sum(beta[i]*fv[i] for i in range(k))
        ss_res+=p.w*(math.log(p.blast)-pred)**2
    return beta,1-ss_res/ss_tot if ss_tot>1e-12 else 1.,sw

def r2_combined(pts_he, pts_therm, beta_he, dfn_he, k_he, beta_therm, dfn_therm, k_therm):
    wm=sum(p.w*math.log(p.blast) for p in (pts_he+pts_therm))/sum(p.w for p in (pts_he+pts_therm))
    ss_tot=sum(p.w*(math.log(p.blast)-wm)**2 for p in (pts_he+pts_therm))
    ss_res=0.
    for p in pts_he:
        fv=dfn_he(p); pred=sum(beta_he[i]*fv[i] for i in range(k_he)); ss_res+=p.w*(math.log(p.blast)-pred)**2
    for p in pts_therm:
        fv=dfn_therm(p); pred=sum(beta_therm[i]*fv[i] for i in range(k_therm)); ss_res+=p.w*(math.log(p.blast)-pred)**2
    return 1-ss_res/ss_tot if ss_tot>1e-12 else 1.

# ── Model 1: single baseline ──
dfn1 = lambda p: [1.0, math.log(p.dmg+1e-6), math.log(p.rad+1e-6)]
b1,r1,_ = ols_custom(ALL, dfn1, 3)

# ── Model 2: separate HE / thermobaric ──
dfn_he = lambda p: [1.0, math.log(p.dmg+1e-6), math.log(p.rad+1e-6)]
dfn_th = lambda p: [1.0, math.log(p.dmg+1e-6), math.log(p.rad+1e-6)]
b_he,r_he,_ = ols_custom(he_only, dfn_he, 3)
b_th,r_th,_ = ols_custom(therm_only, dfn_th, 3)
r2_sep = r2_combined(he_only, therm_only, b_he, dfn_he, 3, b_th, dfn_th, 3)

# ── Model 3: piecewise segmented regression (breakpoint on ln(damage)) ──
# Design: [1, ln(d), max(0, ln(d)-bpoint), ln(r)]
# Scan breakpoints at each data point's ln(damage)
best_bp, best_r2, best_beta = 0, 0, None
for bp_candidate in sorted(set(p.dmg for p in he_only if 30 < p.dmg < 500)):
    bp = math.log(bp_candidate)
    dfn_pw = lambda p, bp=bp: [1.0, math.log(p.dmg+1e-6), max(0.0, math.log(p.dmg+1e-6)-bp), math.log(p.rad+1e-6)]
    beta,r2,_ = ols_custom(he_only, dfn_pw, 4)
    if r2 > best_r2:
        best_r2, best_bp, best_beta = r2, bp_candidate, beta

# ── Model 4: piecewise on HE + separate thermobaric ──
bp_he = best_bp
dfn_pw_he = lambda p: [1.0, math.log(p.dmg+1e-6), max(0.0, math.log(p.dmg+1e-6)-math.log(bp_he)), math.log(p.rad+1e-6)]
beta_pw_he,r_pw_he,_ = ols_custom(he_only, dfn_pw_he, 4)
r2_pw_sep = r2_combined(he_only, therm_only, beta_pw_he, dfn_pw_he, 4, b_th, dfn_th, 3)

def pred_fn(p, beta, dfn):
    return math.exp(sum(beta[i]*dfn(p)[i] for i in range(len(beta))))

print("="*72)
print("  MODEL COMPARISON")
print("="*72)

models = [
    ("1. baseline (all one model)",        r1,   dfn1,     b1,   ALL,    "tntKg = k·d^a·r^b"),
    ("2. separate HE + thermobaric",        r2_sep, None,  None,  ALL,   "A:HE only  B:thermo only"),
    (f"3. piecewise HE (break at dmg={best_bp})", best_r2, dfn_pw, best_beta, he_only, "slope changes at breakpoint"),
    ("4. piecewise HE + separate thermo",   r2_pw_sep, None, None, ALL, "3 + 2 combined"),
]
for name, r2, dfn, beta, pts, _ in models:
    print(f"  {name:<50s} R²={r2:.4f}")

print(f"\n{'='*72}")
print(f"  DETAILS")
print(f"{'='*72}")

# Model 1 detail
k1 = math.exp(b1[0])
a1,b_r1 = b1[1],b1[2]
w1 = 1-b_r1/3; ye1 = a1/w1 if w1>1e-6 else float('nan')
print(f"\n  Model 1 (baseline):")
print(f"    tntKg = {k1:.6g} · d^{a1:.4f} · r^{b_r1:.4f}")
print(f"    damageYieldWeight={w1:.3f}  YieldExponent={ye1:.3f}")

# Model 2 detail
k_he = math.exp(b_he[0]); a_he,b_rhe = b_he[1],b_he[2]
k_th = math.exp(b_th[0]); a_th,b_rth = b_th[1],b_th[2]
w_he = 1-b_rhe/3; ye_he = a_he/w_he if w_he>1e-6 else 0
w_th = 1-b_rth/3; ye_th = a_th/w_th if w_th>1e-6 else 0
print(f"\n  Model 2 (separate):")
print(f"    HE:  tntKg = {k_he:.6g} · d^{a_he:.4f} · r^{b_rhe:.4f}  (R²={r_he:.4f})")
print(f"         weight={w_he:.3f}  YieldExp={ye_he:.3f}")
print(f"    TB:  tntKg = {k_th:.6g} · d^{a_th:.4f} · r^{b_rth:.4f}  (R²={r_th:.4f})")
print(f"         weight={w_th:.3f}  YieldExp={ye_th:.3f}")

# Model 3 detail
bp_val = best_bp
b0,b1a,b1b,b2 = best_beta
print(f"\n  Model 3 (piecewise HE, break at dmg={bp_val}):")
print(f"    tntKg = exp({b0:.4f}) · d^{b1a:.4f} "
      f"· exp({b1b:.4f}·max(0,ln(d)-ln({bp_val}))) · r^{b2:.4f}")
print(f"    Below {bp_val}: slope on ln(d) = {b1a:.4f}")
print(f"    Above {bp_val}: slope on ln(d) = {b1a+b1b:.4f}")

pw_pred = lambda p: pred_fn(p, best_beta, dfn_pw)
th_pred = lambda p: pred_fn(p, b_th, dfn_th)

# ── Predictions table ──
print(f"\n{'='*72}")
print(f"  PREDICTIONS (blast-adjusted kg TNT)")
print(f"{'='*72}")
print(f"  {'Weapon':<22s} {'Actual':>7s} {'M1(base)':>9s} {'M2(sep)':>9s} {'M3(pw)':>9s} {'M4(pw+sep)':>10s}")
print(f"  {'-'*22} {'-'*7} {'-'*9} {'-'*9} {'-'*9} {'-'*10}")

key_points = [
    ALL[-7],  # 30x64 thermobaric
    ALL[-6],  # RPG-7 thermobaric
    ALL[-2],  # 152mm airburst
    ALL[-3],  # 105mm airburst
]
for p in key_points:
    m1 = pred_fn(p, b1, dfn1)
    m2 = pred_fn(p, b_he if not p.therm else b_th, dfn_he if not p.therm else dfn_th)
    m3 = pred_fn(p, best_beta, dfn_pw) if not p.therm else pred_fn(p, b_th, dfn_th)
    m4 = pred_fn(p, beta_pw_he if not p.therm else b_th, dfn_pw_he if not p.therm else dfn_th)
    kind = "TB" if p.therm else "HE"
    print(f"  {p.label:<22s} {p.blast:7.3f} {m1:9.3f} {m2:9.3f} {m3:9.3f} {m4:10.3f}")

# Also show some HE examples
for p in [ALL[13], ALL[15], ALL[21]]:  # 81mm, 105mm, 155mm
    m1 = pred_fn(p, b1, dfn1)
    m2 = pred_fn(p, b_he, dfn_he)
    m3 = pred_fn(p, best_beta, dfn_pw)
    m4 = pred_fn(p, beta_pw_he, dfn_pw_he)
    print(f"  {p.label:<22s} {p.blast:7.3f} {m1:9.3f} {m2:9.3f} {m3:9.3f} {m4:10.3f}")
