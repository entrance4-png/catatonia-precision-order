#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

HOW TO RUN IT
    Google Colab / Jupyter
        Paste this whole file into one cell and run it.  If the workbook is
        not already in the session an upload dialog opens; choose the .xlsx
        and the statistics print and the figure is drawn in the cell.
    Command line
        python catatonia_figure2.py [milestones.xlsx]
        With no argument the workbook is located automatically (see below).

INPUT
    An .xlsx with one row per patient and the columns

        patient | πs | β | πm | πvfast | πvslow

    (πv_fast / πv_slow, with or without the underscore, are also accepted;
    column names are matched ignoring case and surrounding spaces.)

    Cells hold strings of the form "day6"; blank means the domain's baseline
    disturbance was not documented and the milestone is NOT APPLICABLE (this
    is the case for πv_fast in three patients, who received an antipsychotic
    from initiation).  Missing values are never imputed and never treated as
    day zero.

    The file is looked for in this order: an explicit path; the default name
    in both NFC and NFD (Japanese file names differ between the two, so an
    exact-name test can fail on a file that is plainly there); then any single
    spreadsheet in the working directory, /content, /content/drive/MyDrive or
    the script's own directory, up to three levels deep.

OUTPUT
    saito_companion_fig2.png          the figure, 300 dpi
    stdout                            the statistics listed below
    in a notebook                     the figure, drawn in the cell

WHAT THE MANUSCRIPT QUOTES, AND WHERE IT COMES FROM
    Median (IQR), range, per domain      ->  describe()        [Suppl. Table 1]
    Kendall's W = 0.91, chi2(4) = 80.4   ->  kendalls_w(), tie-CORRECTED,
                                             complete cases only (n = 22)
    Adjacent-pair ordering: n, strict    ->  adjacent_pairs()  [Suppl. Table 2]
    precedence (the order-informative
    counts 15, 12, 18, 22), same-day
    ties, inversions, sign-test p
    Fig. 2, panels a and b               ->  figure2()

    The BFCRS severity statistics (Table 2 of the manuscript) are scored from
    a separate record sheet and are not computed here.

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
    The legend is placed clear of the data (default).  Set LEGEND_INSIDE =
    True, or pass --legend-inside on the command line, to reproduce the
    earlier lower-right placement, under which P10's two rightmost points
    (πv_fast day 40, πv_slow day 42) are hidden.  No number changes either
    way.

Requires: pandas, numpy, scipy, matplotlib, openpyxl.  Python >= 3.9.
All of these are preinstalled in Google Colab.
"""

from __future__ import annotations

import glob
import os
import sys
import unicodedata
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy import stats

# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------
XLSX = "milestone.xlsx"          # default; any single spreadsheet is accepted
OUT = "saito_companion_fig2.png"
LEGEND_INSIDE = False            # True reproduces the earlier, data-covering legend
JITTER_SEED = 20240101           # fixed: panel b jitter must be reproducible

DOMAINS = ["πs", "β", "πm", "πvfast", "πvslow"]
LABELS = {"πs": "πs", "β": "β", "πm": "πm",
          "πvfast": "πv_fast", "πvslow": "πv_slow"}
COLOURS = {"πs": "#E69F00", "β": "#56B4E9", "πm": "#009E73",
           "πvfast": "#CC79A7", "πvslow": "#0072B2"}
PAIRS = [("πs", "β"), ("β", "πm"), ("πm", "πvfast"), ("πvfast", "πvslow")]

try:                                   # running as a saved script
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:                      # pasted straight into a notebook cell
    _HERE = os.getcwd()

SEARCH_DIRS = list(dict.fromkeys(
    [".", "/content", "/content/drive/MyDrive", _HERE]))
SKIP_DIRS = {"sample_data", ".config", ".ipynb_checkpoints", "__pycache__"}
SHEET_EXT = (".xlsx", ".xls", ".xlsm")


# --------------------------------------------------------------------------
# environment helpers
# --------------------------------------------------------------------------
def in_notebook() -> bool:
    """True inside Jupyter or Colab."""
    try:
        from IPython import get_ipython
        return get_ipython() is not None
    except Exception:
        return False


def in_colab() -> bool:
    try:
        import google.colab  # noqa: F401
        return True
    except Exception:
        return False


def spreadsheet_args(argv: list[str]) -> list[str]:
    """Positional spreadsheet paths from argv.

    Flags are ignored, as is the "-f <kernel.json>" pair that Jupyter and
    Colab place in sys.argv; without this the kernel connection file would be
    mistaken for the input workbook.
    """
    paths, skip = [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a in ("-f", "--f"):
            skip = True
            continue
        if a.startswith("-"):
            continue
        if a.lower().endswith(SHEET_EXT):
            paths.append(a)
    return paths


def _scan() -> list[str]:
    """Spreadsheets present in the search directories, three levels deep."""
    found = []
    for d in SEARCH_DIRS:
        if not os.path.isdir(d):
            continue
        for pattern in ("*", "*/*", "*/*/*"):
            for f in sorted(glob.glob(os.path.join(d, pattern))):
                if not f.lower().endswith(SHEET_EXT):
                    continue
                if set(os.path.normpath(f).split(os.sep)) & SKIP_DIRS:
                    continue
                if os.path.basename(f).startswith("~$"):
                    continue
                found.append(os.path.abspath(f))
    return sorted(dict.fromkeys(found))


def find_workbook(path: str | None = None) -> str:
    """Locate the milestone workbook, or ask for it when running in Colab."""
    names = [path] if path else [XLSX]
    for n in list(names):
        for form in ("NFC", "NFD"):
            names.append(unicodedata.normalize(form, n))
    for n in names:
        if os.path.exists(n):
            return n
        for d in SEARCH_DIRS:
            cand = os.path.join(d, n)
            if os.path.isdir(d) and os.path.exists(cand):
                return cand
    if path:                                  # an explicit path was wrong
        raise SystemExit(f"milestone workbook not found: {path!r}")

    found = _scan()
    if len(found) == 1:
        print(f"[using workbook: {found[0]}]")
        return found[0]
    if len(found) > 1:
        raise SystemExit(
            "several spreadsheets found; pass the one you want:\n    "
            + "\n    ".join(found)
            + "\n  e.g.  df = load('" + found[0] + "')")

    if in_colab():                            # ask for the file, then continue
        print("Milestone workbook not found in this session.")
        print("Choose the .xlsx file in the dialog below.")
        from google.colab import files
        uploaded = files.upload()
        picked = [f for f in uploaded if f.lower().endswith(SHEET_EXT)]
        if picked:
            print(f"[using workbook: {picked[0]}]")
            return picked[0]

    listing = []
    for d in SEARCH_DIRS:
        if os.path.isdir(d):
            entries = sorted(os.listdir(d))[:12]
            listing.append(f"    {d}: " + (", ".join(entries) or "(empty)"))
    raise SystemExit(
        "milestone workbook not found.\n"
        f"  looked for {XLSX!r} (NFC and NFD) in: {', '.join(SEARCH_DIRS)}\n"
        "  what is actually there:\n" + "\n".join(listing) + "\n"
        "  pass a path explicitly, e.g. load('/content/milestone.xlsx')")


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def load(path: str | None = None) -> pd.DataFrame:
    """Read the sheet and parse 'dayN' -> N.  Blanks stay NaN (not applicable)."""
    path = find_workbook(path)
    df = pd.read_excel(path)

    canon = {"πv_fast": "πvfast", "πv fast": "πvfast",
             "πv_slow": "πvslow", "πv slow": "πvslow"}
    df = df.rename(columns={c: canon.get(str(c).strip().lower(), str(c).strip())
                            for c in df.columns})

    missing = [c for c in ["patient", *DOMAINS] if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}; found {list(df.columns)}")

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


def adjacent_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Adjacent-domain ordering, one row per pair (Supplementary Table 2).

    n                    patients in whom both milestones are applicable
    strict precedence    earlier domain reached on a strictly earlier day;
                         these are the order-informative patients
    same day             tie, permitted by the ordering hypothesis
    inversion            later domain reached first: a falsifying observation
    consistent           strict precedence + same day
    sign-test p          two-sided exact binomial test on the non-tied pairs
    """
    rows = []
    for a, b in PAIRS:
        s = df[[a, b]].dropna()
        n = len(s)
        strict = int((s[a] < s[b]).sum())
        same = int((s[a] == s[b]).sum())
        inv = int((s[a] > s[b]).sum())
        informative = strict + inv
        if not informative:
            p = float("nan")
        elif hasattr(stats, "binomtest"):                  # SciPy >= 1.7
            p = stats.binomtest(strict, informative, 0.5).pvalue
        else:                                              # older SciPy
            p = stats.binom_test(strict, informative, 0.5)
        rows.append({"pair": f"{LABELS[a]} -> {LABELS[b]}", "n": n,
                     "strict precedence": strict, "same day": same,
                     "inversion": inv, "consistent": strict + same,
                     "sign-test p": p})
    return pd.DataFrame(rows)


def sort_for_panel_a(df: pd.DataFrame) -> pd.DataFrame:
    """πv_slow ascending; ties broken by πv_fast descending, NaN last."""
    return df.sort_values(["πvslow", "πvfast"],
                          ascending=[True, False],
                          na_position="last").reset_index(drop=True)


# --------------------------------------------------------------------------
# figure
# --------------------------------------------------------------------------
def figure2(df: pd.DataFrame, out: str = OUT,
            legend_inside: bool = LEGEND_INSIDE,
            show: bool | None = None) -> str:
    """Draw Fig. 2, save it at 300 dpi and, in a notebook, display it."""
    if show is None:
        show = in_notebook()
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
    if show:
        plt.show()
    else:
        plt.close(fig)
    return out


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def report(df: pd.DataFrame, legend_inside: bool = LEGEND_INSIDE) -> str:
    """Print every number the manuscript quotes, then draw the figure."""
    line = "=" * 76

    print(line)
    print("Milestone days, n = %d patients" % len(df))
    print(line)
    d = describe(df)
    for _, r in d.iterrows():
        print(f"  {r['domain']:<9} n={int(r['n applicable']):2d}   "
              f"median {r['median']:.1f} ({r['q1']:.1f}-{r['q3']:.1f})   "
              f"range {r['min']:.0f}-{r['max']:.0f}")
    na = int((len(df) - d["n applicable"]).max())
    print(f"\n  πv_fast is NOT APPLICABLE in {na} patients and is left missing.")
    print("  Setting those to day 0 would manufacture three inversions at the")
    print("  single pair the ordering hypothesis permits. It is not done here.")

    print()
    print(line)
    print("Concordance of the milestone ordering (complete cases)")
    print(line)
    w = kendalls_w(df)
    print(f"  raters (patients) m = {w['m']},  items (domains) k = {w['k']}")
    print(f"  S = {w['S']:.1f},  sum of tie corrections T = {w['sum_T']}")
    print(f"  Kendall's W, uncorrected     = {w['W_uncorrected']:.4f}  "
          f"(chi2 = {w['m'] * (w['k'] - 1) * w['W_uncorrected']:.1f})")
    print(f"  Kendall's W, tie-corrected   = {w['W']:.4f}  "
          f"(chi2({w['df']}) = {w['chi2']:.1f}, p = {w['p']:.2e})")
    print("  The manuscript reports both: tie-corrected W = 0.91 (uncorrected")
    print("  0.82), chi2(4) = 80.4, n = 22. Ties are permitted by the hypothesis.")

    print()
    print(line)
    print("Adjacent-domain ordering (Supplementary Table 2)")
    print(line)
    ap = adjacent_pairs(df)
    print(f"  {'pair':<20}{'n':>4}{'strict':>8}{'same':>6}{'inv':>5}"
          f"{'consistent':>12}{'sign-test p':>14}")
    for _, r in ap.iterrows():
        consistent = f"{r['consistent']}/{r['n']}"
        print(f"  {r['pair']:<20}{r['n']:>4}{r['strict precedence']:>8}"
              f"{r['same day']:>6}{r['inversion']:>5}{consistent:>12}"
              f"{r['sign-test p']:>14.2e}")
    informative = ", ".join(str(int(v)) for v in ap["strict precedence"])
    print(f"\n  Order-informative (non-tied) patients per pair: {informative}.")
    print("  Inversions in any pair: %d." % int(ap["inversion"].sum()))

    print()
    out = figure2(df, legend_inside=legend_inside)
    print("Figure 2 written to:", os.path.abspath(out))
    if legend_inside:
        print("NOTE: with this legend placement, P10's pi_v,fast (day 40) and")
        print("      pi_v,slow (day 42) fall underneath the legend box.")
    return out


def main(path: str | None = None) -> None:
    args = spreadsheet_args(sys.argv[1:])
    if path is None and args:
        path = args[0]
    legend_inside = LEGEND_INSIDE or ("--legend-inside" in sys.argv)
    report(load(path), legend_inside=legend_inside)


if __name__ == "__main__":
    main()
