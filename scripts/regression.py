#!/usr/bin/env python3
"""Compare two approaches for blast-yield-aware regression.

Method A — adjusted ground truth: apply blast efficiency multipliers to TNT kg
  based on warhead type (frag-optimized vs blast vs thermobaric).

Method B — categorical predictors: add ln(fragmentCount) and isThermobaric
  as extra regression features while keeping filler kg unchanged.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Point:
    label: str
    damage: float
    radius: float
    tnt_filler_kg: float
    frag_count: int = 0
    is_thermobaric: int = 0
    blast_eff: float = 1.0
    weight: float = 1.0
    tnt_blast_kg: float = 0.0

    def __post_init__(self):
        if self.tnt_blast_kg == 0.0:
            self.tnt_blast_kg = self.tnt_filler_kg * self.blast_eff


POINTS = [
    # label,           dmg, rad,  filler_kg, frag_cnt, therm, blast_eff, weight
    ("25x40mm HE",       18, 1.0,   0.020,    16, 0,  0.85,  0.8),
    ("30x29mm VOG-17M",  22, 1.0,   0.050,    28, 0,  0.85,  0.8),
    ("40x46mm M406",     22, 1.0,   0.040,    20, 0,  0.85,  0.8),
    ("40x53mm VOG-25",   26, 1.0,   0.048,    24, 0,  0.85,  0.8),
    ("M67 frag grenade", 80, 2.0,   0.240,    26, 0,  0.55,  1.0),
    ("RPG-7 OG-7V frag", 58, 1.5,   0.370,    80, 0,  0.50,  0.9),
    ("83mm PIAT HE",    139, 2.5,   0.450,    80, 0,  0.70,  0.8),
    ("37mm HE",          33, 1.0,   0.030,     4, 0,  0.70,  0.8),
    ("40mm Bofors HE",   64, 1.5,   0.100,     9, 0,  0.70,  0.8),
    ("50mm Type89 Mort", 42, 1.5,   0.150,     6, 0,  0.70,  0.8),
    ("57mm S-60 HE",     55, 1.5,   0.200,    21, 0,  0.70,  0.8),
    ("57mm Bofors HE",  108, 2.0,   0.350,    21, 0,  0.70,  0.7),
    ("81mm Mortar M43", 156, 2.5,   0.548,    41, 0,  0.70,  1.0),
    ("100mm naval HE",  209, 3.0,   1.500,    81, 0,  0.70,  0.8),
    ("105mm M1 HE",     217, 3.0,   2.180,    84, 0,  0.70,  1.0),
    ("105x607mmR HE",   331, 4.0,   2.000,    96, 0,  0.70,  0.7),
    ("105x617mmR HE",   199, 3.0,   1.800,    76, 0,  0.70,  0.7),
    ("120mm Mortar M57",237, 3.5,   3.000,    90, 0,  0.70,  0.9),
    ("120mm Cannon HE", 315, 4.0,   3.000,   110, 0,  0.70,  0.8),
    ("15cm Nebelwerfer",228, 3.5,   2.500,    45, 0,  0.70,  0.8),
    ("152mm OF-540 HE", 578, 5.5,   5.860,   120, 0,  0.70,  1.0),
    ("155mm M107 HE",   546, 5.5,   6.620,   120, 0,  0.70,  1.0),
    ("28cm Spgr HE",    837, 7.0,  20.000,   120, 0,  0.70,  0.5),
    ("RPG-7 Thermobar",  275, 5.0,  1.800,     0, 1,  1.80,  0.8),
    ("SPG-9 Thermobar",  277, 5.0,  2.000,     0, 1,  1.80,  0.8),
    ("RPO-A Thermobar",  293, 5.0,  2.100,     0, 1,  1.80,  0.8),
    ("105mm M1 (air)",   216, 6.5,  2.180,    84, 0,  0.70,  1.0),
    ("152mm OF-540 (air)",478,10.0, 5.860,   120, 0,  0.70,  1.0),
    ("155mm M107 (air)", 452, 9.5,  6.620,   120, 0,  0.70,  1.0),
]


def make_features(feature_names):
    fns = []
    for name in feature_names:
        if name == 'const':
            fns.append(lambda p: 1.0)
        elif name == 'ln(d)':
            fns.append(lambda p: math.log(p.damage + 1e-6))
        elif name == 'ln(r)':
            fns.append(lambda p: math.log(p.radius + 1e-6))
        elif name == 'ln(f)':
            fns.append(lambda p: math.log(p.frag_count + 1))
        elif name == 'therm':
            fns.append(lambda p: float(p.is_thermobaric))
        else:
            raise ValueError(name)
    return fns


def weighted_ols(pts, feature_names):
    fns = make_features(feature_names)
    k = len(fns)
    XTWX = [[0.0]*k for _ in range(k)]
    XTWy = [0.0]*k
    sw = 0.0

    for p in pts:
        w = p.weight
        f = [fn(p) for fn in fns]
        y = math.log(p.tnt_blast_kg)
        sw += w
        for i in range(k):
            XTWy[i] += w * f[i] * y
            for j in range(k):
                XTWX[i][j] += w * f[i] * f[j]

    a = [row[:] + [XTWy[i]] for i, row in enumerate(XTWX)]
    for col in range(k):
        pivot = max(range(col, k), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError("singular")
        a[col], a[pivot] = a[pivot], a[col]
        for row in range(col + 1, k):
            fac = a[row][col] / a[col][col]
            for j in range(col, k + 1):
                a[row][j] -= fac * a[col][j]
    beta = [0.0]*k
    for i in range(k - 1, -1, -1):
        beta[i] = (a[i][k] - sum(a[i][j] * beta[j] for j in range(i + 1, k))) / a[i][i]

    wmean = sum(p.weight * math.log(p.tnt_blast_kg) for p in pts) / sw
    ss_tot = sum(p.weight * (math.log(p.tnt_blast_kg) - wmean)**2 for p in pts)
    ss_res = 0.0
    for p in pts:
        f = [fn(p) for fn in fns]
        pred = sum(beta[i] * f[i] for i in range(k))
        ss_res += p.weight * (math.log(p.tnt_blast_kg) - pred)**2
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0
    return beta, r2


def predict(p, beta, feature_names):
    fns = make_features(feature_names)
    return math.exp(sum(beta[i] * fns[i](p) for i in range(len(beta))))


def model_stats(pts, beta, feature_names):
    max_err = 0.0
    n_out = 0
    for p in pts:
        ratio = predict(p, beta, feature_names) / p.tnt_blast_kg
        le = abs(math.log(max(ratio, 1.0 / ratio)))
        max_err = max(max_err, le)
        if le > 0.5:
            n_out += 1
    return max_err, n_out


def fmt_model(feature_names, beta):
    k_val = math.exp(beta[0])
    parts = []
    for i, name in enumerate(feature_names):
        if i == 0:
            continue
        if name.startswith('ln('):
            parts.append(f"{name}^{beta[i]:.4f}")
        elif name == 'therm':
            parts.append(f"exp({beta[i]:.4f}·therm)")
    return f"tntKg = {k_val:.6g} · {' · '.join(parts)}"


if __name__ == "__main__":
    pts = [Point(*args) for args in POINTS]
    all_features = [
        ['const', 'ln(d)', 'ln(r)'],
        ['const', 'ln(d)', 'ln(r)', 'ln(f)'],
        ['const', 'ln(d)', 'ln(r)', 'ln(f)', 'therm'],
    ]
    results = []

    for method, use_blast_adj in [("A. blast-adjusted yield", True), ("B. raw filler + predictors", False)]:
        print(f"\n{'='*70}")
        print(f"  {method}")
        print(f"{'='*70}")

        for p in pts:
            p.tnt_blast_kg = (p.tnt_filler_kg * p.blast_eff) if use_blast_adj else p.tnt_filler_kg

        for feats in all_features:
            beta, r2 = weighted_ols(pts, feats)
            max_err, n_out = model_stats(pts, beta, feats)
            model = fmt_model(feats, beta)
            effects = [f"{n}={beta[i]:+.4f}" for i, n in enumerate(feats) if i > 0]
            print(f"\n  {'+'.join(feats[1:]):<24s}  R²={r2:.4f}  out={n_out}/{len(pts)}  max|ln|={max_err:.3f}")
            print(f"    {model}")
            for e in effects:
                print(f"    {e}")
            results.append((f"{method} {'+'.join(feats[1:])}", r2, r2 - 0.000, n_out, max_err))

    print(f"\n{'='*70}")
    print(f"  Summary")
    print(f"{'='*70}")
    results.sort(key=lambda x: -x[1])
    for r in results:
        name, r2, _, n_out, max_err = r
        print(f"  R²={r2:.4f}  out={n_out:>2d}/{len(pts)}  max_ln_err={max_err:.3f}  |  {name}")

    print(f"\n  Best: {results[0][0]}  (R²={results[0][1]:.4f})")
