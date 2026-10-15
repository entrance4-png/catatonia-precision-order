#!/usr/bin/env python3
"""
blind_rerating_analysis.py
Pre-specified analysis of the independent blinded re-rating of recovery milestones
(plan v1.0, fixed 1 October 2026). Implements sections 4 to 8 of the plan.

Input: two CSV files with identical layout, one per rater.
  columns: case, ps, beta, pm, pv_fast, pv_slow
  cell values: integer day counted from the per-patient reference fixed in the index
               dataset (date of onset of catatonic symptoms = day 1); the same reference
               is applied to both raters, and only the descriptive medians depend on it, or
               NA (not assessable: baseline disturbance not documented), or
               ND (not documented: baseline disturbance documented but no entry
               satisfying the definition up to the end of the record supplied).
  Any other value stops the run. Case IDs must be unique within a file and the two
  files must contain the same set of case IDs; otherwise the run stops.

Usage:
  python blind_rerating_analysis.py index.csv independent.csv [--out results.txt] [--plots DIR]

Nothing in this script is tuned to the data: it is fixed before any independent
rating is seen. Dependencies: numpy, scipy; matplotlib only if --plots is given.
"""
import sys, csv, math, argparse
import numpy as np
from scipy import stats

DOMAINS = ['ps', 'beta', 'pm', 'pv_fast', 'pv_slow']
LABEL = {'ps': 'πs', 'beta': 'β', 'pm': 'πm', 'pv_fast': 'πv_fast', 'pv_slow': 'πv_slow'}
PAIRS = [('ps', 'beta'), ('beta', 'pm'), ('pm', 'pv_fast'), ('pv_fast', 'pv_slow')]
SEPARABLE = {('ps', 'beta'), ('pm', 'pv_fast')}   # fixed by plan section 4.2; not to be edited
MISSING = ('NA', 'ND')


# ---------------------------------------------------------------- input
class InputError(Exception):
    pass


def read_rater(path):
    d = {}
    with open(path, newline='', encoding='utf-8-sig') as f:
        rd = csv.DictReader(f)
        need = ['case'] + DOMAINS
        if rd.fieldnames is None or [c.strip() for c in rd.fieldnames[:len(need)]] != need:
            raise InputError(f'{path}: columns must be exactly {need}; found {rd.fieldnames}')
        for i, row in enumerate(rd, start=2):
            cid = row['case'].strip()
            if not cid:
                raise InputError(f'{path} line {i}: empty case ID')
            if cid in d:
                raise InputError(f'{path} line {i}: duplicate case ID {cid}')
            d[cid] = {}
            for k in DOMAINS:
                v = (row[k] or '').strip().upper()
                if v in MISSING:
                    d[cid][k] = v
                else:
                    try:
                        d[cid][k] = int(v)
                    except ValueError:
                        raise InputError(f'{path} line {i}, column {k}: value {row[k]!r} is not an integer day, NA or ND')
    return d


def check_match(index, indep):
    a, b = set(index), set(indep)
    if a != b:
        raise InputError(f'case IDs differ: only in index {sorted(a - b)}; only in independent {sorted(b - a)}')
    if len(a) != 25:
        print(f'WARNING: {len(a)} cases found; the plan specifies 25.', file=sys.stderr)


def is_day(v):
    return isinstance(v, int)


# ---------------------------------------------------------------- section 4
def adjacent_pairs(r):
    out = {p: {'consistent': [], 'tied': [], 'inverted': [], 'noninformative': []} for p in PAIRS}
    for cid, row in r.items():
        for a, b in PAIRS:
            va, vb = row[a], row[b]
            if not (is_day(va) and is_day(vb)):
                out[(a, b)]['noninformative'].append(cid)
            elif va < vb:
                out[(a, b)]['consistent'].append(cid)
            elif va == vb:
                out[(a, b)]['tied'].append(cid)
            else:
                out[(a, b)]['inverted'].append(cid)
    return out


def exact_sign_test_two_sided(n_consistent, n_inverted):
    """Two-sided exact binomial test, as in the manuscript (15/15 gives 6.1e-5)."""
    n = n_consistent + n_inverted
    if n == 0:
        return float('nan')
    return stats.binomtest(n_consistent, n, 0.5, alternative='two-sided').pvalue


# ---------------------------------------------------------------- section 5
def kendall_w(r):
    rows = [[row[k] for k in DOMAINS] for row in r.values() if all(is_day(row[k]) for k in DOMAINS)]
    m = len(rows); n = len(DOMAINS)
    if m < 2:
        return (float('nan'),) * 4 + (m, float('nan'))
    ranks = np.array([stats.rankdata(x) for x in rows])
    R = ranks.sum(axis=0)
    S = ((R - R.mean()) ** 2).sum()
    denom = m ** 2 * (n ** 3 - n)
    W_unc = 12 * S / denom
    T = 0.0
    for x in rows:
        _, counts = np.unique(x, return_counts=True)
        T += sum(c ** 3 - c for c in counts)
    W_tie = 12 * S / (denom - m * T) if denom - m * T > 0 else float('nan')
    chi2 = m * (n - 1) * W_tie
    df = n - 1
    p = stats.chi2.sf(chi2, df)
    return W_tie, W_unc, chi2, df, m, p


def medians(r):
    out = {}
    for k in DOMAINS:
        x = [row[k] for row in r.values() if is_day(row[k])]
        out[k] = (np.median(x), np.percentile(x, 25), np.percentile(x, 75), len(x)) if x else (float('nan'),) * 3 + (0,)
    return out


# ---------------------------------------------------------------- section 6
def icc_a1(x, y):
    """ICC(A,1): two-way random, absolute agreement, single rater (McGraw & Wong 1996, ICC(2,1)).
    Returns (icc, lo, hi). With zero residual variance the ICC is 1 and the CI is not estimable."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    n = len(x); k = 2
    if n < 3:
        return float('nan'), float('nan'), float('nan')
    data = np.vstack([x, y]).T
    grand = data.mean(); row_m = data.mean(axis=1); col_m = data.mean(axis=0)
    MSR = k * ((row_m - grand) ** 2).sum() / (n - 1)
    MSC = n * ((col_m - grand) ** 2).sum() / (k - 1)
    MSE = ((data - row_m[:, None] - col_m[None, :] + grand) ** 2).sum() / ((n - 1) * (k - 1))
    denom = MSR + (k - 1) * MSE + k * (MSC - MSE) / n
    if denom <= 0:
        return float('nan'), float('nan'), float('nan')      # no between-patient variance: ICC undefined
    icc = (MSR - MSE) / denom
    if MSE <= 1e-12 and MSC <= 1e-12:
        return 1.0, float('nan'), float('nan')               # perfect agreement: CI not estimable
    a = k * icc / (n * (1 - icc)) if icc < 1 else float('inf')
    b = 1 + k * icc * (n - 1) / (n * (1 - icc)) if icc < 1 else float('inf')
    v_num = (a * MSC + b * MSE) ** 2
    v_den = (a * MSC) ** 2 / (k - 1) + (b * MSE) ** 2 / ((n - 1) * (k - 1))
    if not np.isfinite(v_num) or v_den <= 0:
        return icc, float('nan'), float('nan')
    v = v_num / v_den
    F1 = stats.f.ppf(0.975, n - 1, v); F2 = stats.f.ppf(0.975, v, n - 1)
    lo = n * (MSR - F1 * MSE) / (F1 * (k * MSC + (k * n - k - n) * MSE) + n * MSR)
    hi = n * (F2 * MSR - MSE) / (k * MSC + (k * n - k - n) * MSE + n * F2 * MSR)
    return icc, max(lo, -1.0), min(hi, 1.0)


def date_agreement(r1, r2):
    out = {}
    for k in DOMAINS:
        pairs = [(r1[c][k], r2[c][k]) for c in r1 if is_day(r1[c][k]) and is_day(r2[c][k])]
        if not pairs:
            out[k] = None; continue
        x = np.array([p[0] for p in pairs]); y = np.array([p[1] for p in pairs]); d = y - x
        icc, lo, hi = icc_a1(x, y)
        out[k] = dict(n=len(pairs), x=x, y=y, d=d,
                      exact=np.mean(d == 0), within1=np.mean(np.abs(d) <= 1), within3=np.mean(np.abs(d) <= 3),
                      med=np.median(d), q1=np.percentile(d, 25), q3=np.percentile(d, 75), mn=int(d.min()), mx=int(d.max()),
                      icc=icc, lo=lo, hi=hi, ba_mean=d.mean(), ba_sd=d.std(ddof=1) if len(d) > 1 else float('nan'))
    return out


def bland_altman_plots(da, outdir):
    import os
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    os.makedirs(outdir, exist_ok=True)
    for k in DOMAINS:
        d = da[k]
        if d is None:
            continue
        mean = (d['x'] + d['y']) / 2.0
        fig, ax = plt.subplots(figsize=(4.5, 3.2))
        ax.scatter(mean, d['d'], s=18, color='0.2')
        ax.axhline(d['ba_mean'], color='0.2', lw=1)
        if not math.isnan(d['ba_sd']):
            for lim in (d['ba_mean'] - 1.96 * d['ba_sd'], d['ba_mean'] + 1.96 * d['ba_sd']):
                ax.axhline(lim, color='0.5', lw=1, ls='--')
        ax.set_xlabel('Mean of the two raters (day)'); ax.set_ylabel('Independent minus index (day)')
        ax.set_title(f'{LABEL[k]} (n = {d["n"]})')
        fig.tight_layout(); fig.savefig(os.path.join(outdir, f'bland_altman_{k}.png'), dpi=200); plt.close(fig)


# ---------------------------------------------------------------- section 7
def cohen_kappa(a, b):
    a = list(a); b = list(b); n = len(a)
    cats = sorted(set(a) | set(b))
    if n == 0 or len(cats) < 2:
        return float('nan'), float('nan'), float('nan')
    idx = {c: i for i, c in enumerate(cats)}
    M = np.zeros((len(cats), len(cats)))
    for x, y in zip(a, b):
        M[idx[x], idx[y]] += 1
    P = M / n
    po = np.trace(P); pi_ = P.sum(axis=1); pj = P.sum(axis=0); pe = (pi_ * pj).sum()
    if pe >= 1:
        return 1.0, 1.0, 1.0
    kappa = (po - pe) / (1 - pe)
    A = sum(P[i, i] * (1 - (pi_[i] + pj[i]) * (1 - kappa)) ** 2 for i in range(len(cats)))
    B = (1 - kappa) ** 2 * sum(P[i, j] * (pi_[j] + pj[i]) ** 2 for i in range(len(cats)) for j in range(len(cats)) if i != j)
    C = (kappa - pe * (1 - kappa)) ** 2
    se = math.sqrt(max(A + B - C, 0) / (n * (1 - pe) ** 2))
    return kappa, max(kappa - 1.96 * se, -1.0), min(kappa + 1.96 * se, 1.0)


def status(v):
    return 'dated' if is_day(v) else v


def applicability_agreement(r1, r2):
    out = {}
    for k in DOMAINS:
        cases = list(r1)
        s1 = [status(r1[c][k]) for c in cases]; s2 = [status(r2[c][k]) for c in cases]
        tab = {}
        for x, y in zip(s1, s2):
            tab[(x, y)] = tab.get((x, y), 0) + 1
        dated = cohen_kappa(['dated' if x == 'dated' else 'not' for x in s1], ['dated' if y == 'dated' else 'not' for y in s2])
        na = cohen_kappa(['NA' if x == 'NA' else 'not' for x in s1], ['NA' if y == 'NA' else 'not' for y in s2])
        out[k] = dict(n=len(cases), tab=tab, kappa_dated=dated, kappa_na=na,
                      agree3=np.mean([x == y for x, y in zip(s1, s2)]))
    return out


# ---------------------------------------------------------------- section 8
def per_patient_tau(r1, r2):
    taus = {}
    for c in r1:
        ks = [k for k in DOMAINS if is_day(r1[c][k]) and is_day(r2[c][k])]
        if len(ks) >= 3:
            x = [r1[c][k] for k in ks]; y = [r2[c][k] for k in ks]
            taus[c] = float('nan') if (len(set(x)) == 1 or len(set(y)) == 1) else stats.kendalltau(x, y).statistic
    return taus


# ---------------------------------------------------------------- report
def fmt(x, d=2):
    return 'NA' if x is None or (isinstance(x, float) and math.isnan(x)) else f'{x:.{d}f}'


def fmtp(p):
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return 'NA'
    return f'{p:.3f}' if p >= 0.001 else f'{p:.2e}'


def report(index, indep, out, plots):
    L = []; W = L.append
    W('Pre-specified analysis of independent blinded re-rating (plan v1.0, 1 Oct 2026)')
    W(f'Patients: {len(index)} (case IDs verified identical in both files)')
    W('')
    W('SECTION 4. Adjacent-pair classification, independent rater alone')
    ap = adjacent_pairs(indep)
    inverted_sep = []; informative_sep = 0
    for (a, b) in PAIRS:
        d = ap[(a, b)]
        kind = 'separable' if (a, b) in SEPARABLE else 'nested'
        p = exact_sign_test_two_sided(len(d['consistent']), len(d['inverted']))
        W(f"  {LABEL[a]} -> {LABEL[b]} ({kind}): consistent {len(d['consistent'])}, tied {len(d['tied'])}, "
          f"inverted {len(d['inverted'])}, non-informative {len(d['noninformative'])}; two-sided exact sign test P = {fmtp(p)}")
        if (a, b) in SEPARABLE:
            informative_sep += len(d['consistent']) + len(d['inverted'])
            inverted_sep += d['inverted']
        for c in d['inverted']:
            W(f"    INVERSION case {c}: independent {LABEL[a]}={indep[c][a]}, {LABEL[b]}={indep[c][b]}; "
              f"index {LABEL[a]}={index[c][a]}, {LABEL[b]}={index[c][b]}")
        if d['noninformative']:
            W("    non-informative: " + ', '.join(f"{c} ({status(indep[c][a])}/{status(indep[c][b])})" for c in d['noninformative']))
    W('')
    if informative_sep == 0:
        verdict = 'NOT EVALUABLE: no patient informative at either separable transition.'
    elif inverted_sep:
        verdict = f'REFUTED: inversion of a separable transition under blind rating in case(s) {", ".join(inverted_sep)}.'
    else:
        verdict = f'not refuted: no inversion of a separable transition in {informative_sep} informative separable-pair observations.'
    W('  PRIMARY CRITERION (plan 4.2): ' + verdict)
    W('')
    W('SECTION 5. Sequence analyses recomputed on each rater\'s dates')
    for name, r in (('index', index), ('independent', indep)):
        Wt, Wu, chi2, df, m, p = kendall_w(r)
        W(f"  {name}: tie-corrected Kendall W = {fmt(Wt)} (uncorrected {fmt(Wu)}), chi2({df}) = {fmt(chi2, 1)}, P = {fmtp(p)}, "
          f"m = {m} patients with all five milestones dated")
        md = medians(r)
        W('    median (IQR) day: ' + '; '.join(f"{LABEL[k]} {fmt(md[k][0], 1)} ({fmt(md[k][1], 1)}-{fmt(md[k][2], 1)}), n={md[k][3]}" for k in DOMAINS))
    W('')
    W('SECTION 6. Agreement on milestone dates (independent minus index)')
    da = date_agreement(index, indep)
    for k in DOMAINS:
        d = da[k]
        if d is None:
            W(f"  {LABEL[k]}: no patient dated by both raters"); continue
        loa = (f"LoA {fmt(d['ba_mean'] - 1.96 * d['ba_sd'])} to {fmt(d['ba_mean'] + 1.96 * d['ba_sd'])}"
               if not math.isnan(d['ba_sd']) else 'LoA NA')
        W(f"  {LABEL[k]} (n={d['n']}): exact {d['exact']:.0%}, within ±1 d {d['within1']:.0%}, within ±3 d {d['within3']:.0%}; "
          f"difference median {fmt(d['med'], 1)} (IQR {fmt(d['q1'], 1)} to {fmt(d['q3'], 1)}; range {d['mn']} to {d['mx']}); "
          f"ICC(A,1) = {fmt(d['icc'])} (95% CI {fmt(d['lo'])} to {fmt(d['hi'])}); Bland-Altman mean {fmt(d['ba_mean'])}, {loa}")
    if plots:
        bland_altman_plots(da, plots)
        W(f'  Bland-Altman plots written to {plots}/bland_altman_<domain>.png')
    W('')
    W('SECTION 7. Agreement on applicability (dated / NA / ND)')
    aa = applicability_agreement(index, indep)
    for k in DOMAINS:
        d = aa[k]
        cells = ', '.join(f"index {x}/independent {y}: {n}" for (x, y), n in sorted(d['tab'].items()))
        kd = d['kappa_dated']; kn = d['kappa_na']
        W(f"  {LABEL[k]} (n={d['n']}): three-way agreement {d['agree3']:.0%}; {cells}")
        W(f"    kappa dated vs not dated {fmt(kd[0])} ({fmt(kd[1])} to {fmt(kd[2])}); kappa NA vs not NA {fmt(kn[0])} ({fmt(kn[1])} to {fmt(kn[2])})")
    W('  (kappa is NA when one or both raters used a single category for every patient)')
    W('')
    W('SECTION 8. Per-patient Kendall tau-b between raters (patients with >= 3 milestones dated by both)')
    taus = per_patient_tau(index, indep)
    vals = [v for v in taus.values() if not math.isnan(v)]
    if vals:
        W(f"  n = {len(taus)}; median tau-b {fmt(np.median(vals))}, range {fmt(min(vals))} to {fmt(max(vals))}; "
          f"tau-b = 1 in {sum(v == 1 for v in vals)} patients; undefined (all-tied) in {len(taus) - len(vals)}")
    else:
        W('  no patient with >= 3 milestones dated by both raters')
    txt = '\n'.join(L)
    print(txt)
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            f.write(txt + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('index_csv'); ap.add_argument('independent_csv')
    ap.add_argument('--out', default=None); ap.add_argument('--plots', default=None, help='directory for Bland-Altman PNGs')
    a = ap.parse_args()
    try:
        index = read_rater(a.index_csv); indep = read_rater(a.independent_csv); check_match(index, indep)
    except InputError as e:
        print('INPUT ERROR:', e, file=sys.stderr); sys.exit(2)
    report(index, indep, a.out, a.plots)


if __name__ == '__main__':
    main()
