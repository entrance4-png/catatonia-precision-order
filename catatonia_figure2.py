#!/usr/bin/env python3
"""
catatonia_figure2.py
====================
Reproduces Figure 2 of

    Saito, H., Takizawa, Y., Tateno, A., Arakawa, R. & Tiger, M.
    "Recovery from catatonia follows a hierarchical precision order."

    Fig. 2.  Temporal ordering of recovery milestones across precision
    domains (n = 25).

from the milestone spreadsheet, together with every number the manuscript
quotes from it.  Nothing is fitted; nothing is simulated.  The script reads
the recorded milestone days and draws them.

INPUT
    An .xlsx with one row per patient and the columns

        patient | πs | β | πm | πvfast | πvslow

    Cells hold strings of the form "day6"; blank means the domain's baseline
    disturbance was not documented and the milestone is NOT APPLICABLE (this
    is the case for πv_fast in three patients, who received an antipsychotic
    from initiation).  Missing values are never imputed and never treated as
    day zero.

OUTPUT
    saito_companion_fig2.png          the figure, 300 dpi
    stdout                            descriptive statistics and Kendall's W

WHAT THE MANUSCRIPT QUOTES, AND WHERE IT COMES FROM
    Median (IQR), range, per domain      ->  describe()
    Kendall's W = 0.91, chi2(4) = 80.4   ->  kendalls_w(), tie-CORRECTED,
                                             complete cases only (n = 22)

    The tie correction is not cosmetic.  Milestones are integer days and ties
    are common: without the correction W = 0.82 and chi2 = 72.2.  Ties are
    permitted by the ordering hypothesis, so deflating W for them would
    penalise the hypothesis for a prediction it makes.  The manuscript reports
    both values.

PANEL a SORT ORDER
    Rows are ordered by πv_slow ascending, ties broken by πv_fast descending,
    with non-applicable πv_fast last.  This is stated because a reader
    reproducing the panel from a different tie-break will get a different
    picture of the same data.

PANEL LABELS
    Panels are labelled "a" and "b" in lower case, matching the Fig. 2 legend
    in the manuscript (Nature style).

LEGEND PLACEMENT
    The legend is placed clear of the data (default).  Pass --legend-inside to
    reproduce the earlier lower-right placement, under which P10's two
    rightmost points (πv_fast day 40, πv_slow day 42) are hidden.  No number
    changes either way.

Requires: pandas, numpy, scipy, matplotlib.  Python >= 3.9.
"""

from __future__ import annotations

import sys
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy import stats

XLSX = "マイルストーンのコヒ_ー.xlsx"
OUT = "saito_companion_fig2.png"

DOMAINS = ["πs", "β", "πm", "πvfast", "πvslow"]
LABELS = {"πs": "πs", "β": "β", "πm": "πm",
          "πvfast": "πv_fast", "πvslow": "πv_slow"}

COLOURS = {"πs": "#E69F00", "β": "#56B4E9", "πm": "#009E73",
           "πvfast": "#CC79A7", "πvslow": "#0072B2"}

JITTER_SEED = 20240101   # fixed: panel B jitter must be reproducible

# The legend now sits clear of the data.  --legend-inside restores the earlier
# lower-right placement, which covers P10's two rightmost points.
LEGEND_INSIDE = False


def load(path: str = XLSX) -> pd.DataFrame:
    """Read the sheet and parse 'dayN' -> N.  Blanks stay NaN (not applicable)."""
    df = pd.read_excel(path)
    missing = [c for c in ["patient", *DOMAINS] if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    for c in DOMAINS:
        parsed = df[c].astype(str).str.extract(r"(\d+)", expand=False)
        df[c] = pd.to_numeric(parsed, errors="coerce")
    df["patient"] = df["patient"].astype(int)
    return df[["patient", *DOMAINS]]


def describe(df: pd.DataFrame) -> pd.DataFrame:
    """Median (IQR) and range per domain, over applicable milestones only."""
    rows = []
    for c in DOMAINS:
        s = df[c].dropna()
        q1, q3 = np.percentile(s, [25, 75])
        rows.append({"domain": LABELS[c], "n applicable": int(s.size),
                     "median": float(np.median(s)), "q1": q1, "q3": q3,
                     "min": float(s.min()), "max": float(s.max())})
    return pd.DataFrame(rows)


def kendalls_w(df: pd.DataFrame) -> dict:
    """Tie-corrected coefficient of concordance over complete cases."""
    M = df[DOMAINS].dropna().to_numpy(float)
    m, k = M.shape
    R = np.apply_along_axis(stats.rankdata, 1, M)
    Rj = R.sum(axis=0)
    S = float(((Rj - Rj.mean()) ** 2).sum())
    T = sum(t ** 3 - t for row in M for t in Counter(row).values())
    denom_unc = m ** 2 * (k ** 3 - k)
    W_unc = 12 * S / denom_unc
    W_cor = 12 * S / (denom_unc - m * T)
    chi2 = m * (k - 1) * W_cor
    return {"m": m, "k": k, "S": S, "sum_T": T,
            "W_uncorrected": W_unc, "W": W_cor,
            "chi2": chi2, "df": k - 1,
            "p": float(stats.chi2.sf(chi2, k - 1))}


def sort_for_panel_a(df: pd.DataFrame) -> pd.DataFrame:
    """πv_slow ascending; ties broken by πv_fast descending, NaN last."""
    return df.sort_values(["πvslow", "πvfast"],
                          ascending=[True, False],
                          na_position="last").reset_index(drop=True)


def figure2(df: pd.DataFrame, out: str = OUT,
            legend_inside: bool = LEGEND_INSIDE) -> str:
    ordered = sort_for_panel_a(df)
    n = len(ordered)
    fig, (axA, axB) = plt.subplots(
        1, 2, figsize=(12.8, 9.4),
        gridspec_kw={"width_ratios": [1.62, 1.0], "wspace": 0.16})
    fig.suptitle("Temporal ordering of recovery milestones across "
                 f"precision domains (n={n})",
                 fontsize=15, fontweight="bold", y=0.965)

    for y, (_, row) in enumerate(ordered.iterrows()):
        days = [row[c] for c in DOMAINS if not np.isnan(row[c])]
        if len(days) > 1:
            axA.plot([min(days), max(days)], [y, y],
                     color="#b8b8b8", lw=1.1, zorder=1)
        for c in DOMAINS:
            if not np.isnan(row[c]):
                axA.scatter(row[c], y, s=52, color=COLOURS[c],
                            edgecolor="white", linewidth=.6, zorder=3)

    axA.set_yticks(range(n))
    axA.set_yticklabels([f"P{p}" for p in ordered["patient"]], fontsize=9)
    axA.set_ylim(n - 0.5, -0.5)
    axA.set_xlabel("Day from treatment initiation", fontsize=11)
    axA.set_ylabel("Patient (sorted by πv_slow)", fontsize=11)
    axA.set_title("a  Per-patient recovery milestones",
                  fontsize=12, fontweight="bold", loc="left")
    axA.grid(axis="x", ls=":", color="#cccccc", lw=.8)
    axA.set_axisbelow(True)

    handles = [Line2D([], [], marker="o", ls="", markersize=8,
                      markerfacecolor=COLOURS[c], markeredgecolor="white",
                      label=LABELS[c]) for c in DOMAINS]
    if legend_inside:
        axA.legend(handles=handles, title="Milestone", loc="lower right",
                   fontsize=10, title_fontsize=11, framealpha=.95)
    else:
        axA.legend(handles=handles, title="Milestone", loc="upper left",
                   bbox_to_anchor=(0.0, -0.075), ncol=5, frameon=False,
                   fontsize=10, title_fontsize=11)

    rng = np.random.default_rng(JITTER_SEED)
    for i, c in enumerate(DOMAINS):
        y0 = -i
        s = df[c].dropna().to_numpy(float)
        q1, med, q3 = np.percentile(s, [25, 50, 75])
        axB.hlines(y0, q1, q3, color=COLOURS[c], lw=3.2, alpha=.85, zorder=2)
        axB.vlines(med, y0 - .13, y0 + .13, color="black", lw=3.4, zorder=4)
        axB.scatter(s, y0 + rng.uniform(-.09, .09, s.size), s=34,
                    color=COLOURS[c], alpha=.85, edgecolor="none", zorder=3)

    axB.set_yticks([-i for i in range(len(DOMAINS))])
    axB.set_yticklabels([LABELS[c] for c in DOMAINS], fontsize=11)
    axB.set_ylim(-len(DOMAINS) + 0.55, 0.55)
    axB.set_xlabel("Day from treatment initiation", fontsize=11)
    axB.set_title("b  Milestone day by domain\n(median |, IQR bar)",
                  fontsize=12, fontweight="bold", loc="left")
    axB.grid(axis="x", ls=":", color="#cccccc", lw=.8)
    axB.set_axisbelow(True)

    lo = min(axA.get_xlim()[0], axB.get_xlim()[0])
    hi = max(axA.get_xlim()[1], axB.get_xlim()[1])
    axA.set_xlim(lo, hi)
    axB.set_xlim(lo, hi)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    legend_inside = "--legend-inside" in sys.argv
    path = args[0] if args else XLSX
    df = load(path)

    print("=" * 76)
    print("Milestone days, n = %d patients" % len(df))
    print("=" * 76)
    d = describe(df)
    for _, r in d.iterrows():
        print(f"  {r['domain']:<9} n={int(r['n applicable']):2d}   "
              f"median {r['median']:.1f} "
              f"({r['q1']:.1f}-{r['q3']:.1f})   "
              f"range {r['min']:.0f}-{r['max']:.0f}")
    na = int((len(df) - d['n applicable']).max())
    print(f"\n  πv_fast is NOT APPLICABLE in {na} patients and is left missing.")
    print("  Setting those to day 0 would manufacture three inversions at the")
    print("  single pair the ordering hypothesis permits. It is not done here.")

    print()
    print("=" * 76)
    print("Concordance of the milestone ordering (complete cases)")
    print("=" * 76)
    w = kendalls_w(df)
    print(f"  raters (patients) m = {w['m']},  items (domains) k = {w['k']}")
    print(f"  S = {w['S']:.1f},  sum of tie corrections T = {w['sum_T']}")
    print(f"  Kendall's W, uncorrected     = {w['W_uncorrected']:.4f}  "
          f"(chi2 = {w['m']*(w['k']-1)*w['W_uncorrected']:.1f})")
    print(f"  Kendall's W, tie-corrected   = {w['W']:.4f}  "
          f"(chi2({w['df']}) = {w['chi2']:.1f}, p = {w['p']:.2e})")
    print("  The manuscript reports both: tie-corrected W = 0.91 (uncorrected")
    print("  0.82), chi2(4) = 80.4, n = 22. Ties are permitted by the hypothesis.")

    print()
    out = figure2(df, legend_inside=legend_inside)
    print("Figure 2 written to:", out)
    if legend_inside:
        print("NOTE: with the earlier legend placement, P10's pi_v,fast (day 40)")
        print("      and pi_v,slow (day 42) fall underneath the legend box.")


if __name__ == "__main__":
    main()
