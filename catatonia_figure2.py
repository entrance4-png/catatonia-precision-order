#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
catatonia_figure2.py
====================
Reproduces Figures 2 and 3 of

    Saito, H., Takizawa, Y., Murata, I., Tateno, A., Theorell, J.,
    Arakawa, R. & Tiger, M.
    "Recovery from catatonia follows a hierarchical precision order."

    Fig. 2.  Temporal ordering of recovery milestones across precision
             domains (n = 25).                       [primary coding, H.S.]
    Fig. 3.  Temporal ordering of recovery milestones in the blinded
             re-rating (n = 25).                     [blind rating, I.M.]

from the two milestone sheets, together with every number the manuscript
quotes from them.  Nothing is fitted; nothing is simulated.  The script reads
the recorded milestone days and draws them.  Both figures are drawn by the
same function, so the two ratings are shown in an identical format.

HOW TO RUN IT
    Command line
        python catatonia_figure2.py primary.xlsx --blind blind.xlsx
        python catatonia_figure2.py primary.xlsx            (Fig. 2 only)
        python catatonia_figure2.py                        (auto-locate, see below)
    Google Colab / Jupyter
        Paste this whole file into one cell and run it.  If no workbook is in
        the session an upload dialog opens; choose the primary sheet (and,
        if you have it, the blind sheet) and the statistics print and the
        figures are drawn in the cell.

INPUT
    One row per patient.  Accepted layouts:

      (a) the primary sheet
            patient | πs | β | πm | πvfast | πvslow
      (b) the blind rating sheet as returned by the second rater
            <no.> | <reference date> | πs | β | πm | πv_fast | πv_slow | Pt

    Column names are matched ignoring case, surrounding spaces and the
    underscore in πv_fast / πv_slow.  The patient number is taken from a
    column named patient, case or Pt, or else from the first column.
    Cells hold "day6", "DAY6" or a bare integer: the day counted from the
    onset of catatonic symptoms (day of onset = day 1).  A blank, "NA" or
    "ND" means the milestone could not be dated and is left missing.
    Missing values are never imputed and never treated as day zero.  CSV
    files with the same columns (case, ps, beta, pm, pv_fast, pv_slow, as
    used by blind_rerating_analysis.py) are accepted as well.

    With no arguments the primary workbook is looked for under the default
    name, in NFC and NFD (Japanese file names differ between the two), then
    as the single spreadsheet in the working directory, /content,
    /content/drive/MyDrive or the script's own directory, up to three levels
    deep.  The blind sheet is only used when passed explicitly or when a
    file matching BLIND_XLSX is present.

OUTPUT
    saito_companion_fig2.png     Fig. 2, 300 dpi (primary coding)
    saito_companion_fig3.png     Fig. 3, 300 dpi (blind rating), if given
    stdout                       the statistics listed below, per rating
    in a notebook                the figures, drawn in the cell

WHAT THE MANUSCRIPT QUOTES, AND WHERE IT COMES FROM
    Median (IQR), range, per domain      ->  describe()        [Suppl. Table 4]
    Kendall's W = 0.91, chi2(4) = 80.4   ->  kendalls_w(), tie-CORRECTED,
    (primary; 0.89 in the blind rating)      complete cases only (n = 22 / 25)
    Adjacent-pair ordering: n, strict    ->  adjacent_pairs()  [Suppl. Table 5;
    precedence (the order-informative        Suppl. Table 6a for the blind rating]
    counts 15, 12, 18, 22 in the primary
    coding; 16, 11, 17, 24 in the blind
    rating), same-day ties, inversions,
    sign-test p
    Fig. 2 / Fig. 3, panels a and b      ->  figure()

    The agreement statistics between the two ratings (ICC, Bland-Altman,
    kappa, tau-b; Suppl. Table 6b) are computed by the pre-registered
    script blind_rerating_analysis.py, not here.  The BFCRS severity
    statistics are scored from a separate record sheet and are not computed
    here.

    The tie correction is not cosmetic.  Milestones are integer days and ties
    are common: without the correction W = 0.82 and chi2 = 72.2 in the
    primary coding.  Ties are permitted by the ordering hypothesis, so
    deflating W for them would penalise the hypothesis for a prediction it
    makes.  The manuscript reports both values.

PANEL a SORT ORDER
    Rows are ordered by πv_slow ascending, ties broken by πv_fast descending,
    with non-applicable πv_fast last.  This is stated because a reader
    reproducing the panel from a different tie-break will get a different
    picture of the same data.

PANEL LABELS
    Panels are labelled "a" and "b" in lower case, matching the figure
    legends in the manuscript (Nature style).

LEGEND PLACEMENT
    The legend is placed clear of the data (default).  Set LEGEND_INSIDE =
    True, or pass --legend-inside on the command line, to reproduce the
    earlier lower-right placement, under which P10's two rightmost points
    are hidden.  No number changes either way.

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
XLSX = "milestone.xlsx"            # default primary sheet; any single spreadsheet is accepted
BLIND_XLSX = "murata_day.xlsx"     # default blind sheet, used only if present
OUT = "saito_companion_fig2.png"
OUT_BLIND = "saito_companion_fig3.png"
LEGEND_INSIDE = False              # True reproduces the earlier, data-covering legend
JITTER_SEED = 20240101             # fixed: panel b jitter must be reproducible
XLABEL = "Day from symptom onset"  # day of onset = day 1, as in the Methods

DOMAINS = ["πs", "β", "πm", "πvfast", "πvslow"]
LABELS = {"πs": "πs", "β": "β", "πm": "πm",
          "πvfast": "πv_fast", "πvslow": "πv_slow"}
COLOURS = {"πs": "#E69F00", "β": "#56B4E9", "πm": "#009E73",
           "πvfast": "#CC79A7", "πvslow": "#0072B2"}
PAIRS = [("πs", "β"), ("β", "πm"), ("πm", "πvfast"), ("πvfast", "πvslow")]
TITLES = {
    "primary": "Temporal ordering of recovery milestones across precision domains (n={n})",
    "blind":   "Temporal ordering of recovery milestones in the blinded re-rating (n={n})",
}

try:                                   # running as a saved script
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:                      # pasted straight into a notebook cell
    _HERE = os.getcwd()

SEARCH_DIRS = list(dict.fromkeys(
    [".", "/content", "/content/drive/MyDrive", _HERE]))
SKIP_DIRS = {"sample_data", ".config", ".ipynb_checkpoints", "__pycache__"}
SHEET_EXT = (".xlsx", ".xls", ".xlsm", ".csv")


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


def spreadsheet_args(argv: list[str]) -> tuple[list[str], str | None]:
    """Positional spreadsheet paths and the --blind path from argv.

    Flags are ignored, as is the "-f <kernel.json>" pair that Jupyter and
    Colab place in sys.argv; without this the kernel connection file would be
    mistaken for the input workbook.
    """
    paths, blind, skip, take_blind = [], None, False, False
    for a in argv:
        if skip:
            skip = False
            continue
        if take_blind:
            blind = a
            take_blind = False
            continue
        if a in ("-f", "--f"):
            skip = True
            continue
        if a == "--blind":
            take_blind = True
            continue
        if a.startswith("--blind="):
            blind = a.split("=", 1)[1]
            continue
        if a.startswith("-"):
            continue
        if a.lower().endswith(SHEET_EXT):
            paths.append(a)
    return paths, blind


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


def _lookup(name: str) -> str | None:
    names = [name]
    for form in ("NFC", "NFD"):
        names.append(unicodedata.normalize(form, name))
    for n in names:
        if os.path.exists(n):
            return n
        for d in SEARCH_DIRS:
            cand = os.path.join(d, n)
            if os.path.isdir(d) and os.path.exists(cand):
                return cand
    return None


def find_workbook(path: str | None = None) -> str:
    """Locate the primary milestone workbook, or ask for it when running in Colab."""
    hit = _lookup(path or XLSX)
    if hit:
        return hit
    if path:                                  # an explicit path was wrong
        raise SystemExit(f"milestone workbook not found: {path!r}")

    found = [f for f in _scan()
             if os.path.basename(f) != BLIND_XLSX and not f.endswith("_template.csv")]
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
_CANON = {
    "πs": "πs", "ps": "πs", "π s": "πs",
    "β": "β", "beta": "β", "b": "β",
    "πm": "πm", "pm": "πm", "π m": "πm",
    "πvfast": "πvfast", "πv_fast": "πvfast", "πv fast": "πvfast", "pv_fast": "πvfast", "pvfast": "πvfast",
    "πvslow": "πvslow", "πv_slow": "πvslow", "πv slow": "πvslow", "pv_slow": "πvslow", "pvslow": "πvslow",
    "patient": "patient", "case": "patient", "pt": "patient", "id": "patient",
}


def load(path: str | None = None) -> pd.DataFrame:
    """Read a sheet and parse 'dayN' / 'DAYN' / N -> N.  Blank, NA and ND stay NaN."""
    path = find_workbook(path)
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path, encoding="utf-8-sig")
    else:
        df = pd.read_excel(path)

    def canon(c) -> str:
        s = unicodedata.normalize("NFKC", str(c)).strip().lower()
        return _CANON.get(s, s)

    df = df.rename(columns={c: canon(c) for c in df.columns})
    df = df.loc[:, ~df.columns.duplicated()]

    if "patient" not in df.columns:           # blind sheet: number is the first column
        df = df.rename(columns={df.columns[0]: "patient"})
    missing = [c for c in ["patient", *DOMAINS] if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}; found {list(df.columns)}")

    df = df[df["patient"].notna()].copy()
    for c in DOMAINS:
        txt = df[c].map(lambda v: "" if pd.isna(v) else unicodedata.normalize("NFKC", str(v)))
        parsed = txt.str.extract(r"(\d+)", expand=False)
        df[c] = pd.to_numeric(parsed, errors="coerce")
    df["patient"] = pd.to_numeric(df["patient"], errors="coerce").astype(int)
    return df[["patient", *DOMAINS]].reset_index(drop=True)


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
    """Adjacent-domain ordering, one row per pair (Suppl. Table 5 / 6a).

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
def figure(df: pd.DataFrame, out: str = OUT, kind: str = "primary",
           legend_inside: bool = LEGEND_INSIDE,
           show: bool | None = None) -> str:
    """Draw the two-panel milestone figure, save it at 300 dpi and, in a
    notebook, display it.  kind = "primary" gives Fig. 2, "blind" gives Fig. 3;
    the layout is identical."""
    if show is None:
        show = in_notebook()
    ordered = sort_for_panel_a(df)
    n = len(ordered)
    fig, (axA, axB) = plt.subplots(
        1, 2, figsize=(12.8, 9.4),
        gridspec_kw={"width_ratios": [1.62, 1.0], "wspace": 0.16})
    fig.suptitle(TITLES[kind].format(n=n),
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
    axA.set_xlabel(XLABEL, fontsize=11)
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
    axB.set_xlabel(XLABEL, fontsize=11)
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


def figure2(df: pd.DataFrame, out: str = OUT, **kw) -> str:
    """Fig. 2 (primary coding).  Kept for backward compatibility."""
    return figure(df, out=out, kind="primary", **kw)


def figure3(df: pd.DataFrame, out: str = OUT_BLIND, **kw) -> str:
    """Fig. 3 (blind rating), same layout as Fig. 2."""
    return figure(df, out=out, kind="blind", **kw)


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def report(df: pd.DataFrame, kind: str = "primary",
           legend_inside: bool = LEGEND_INSIDE) -> str:
    """Print every number the manuscript quotes from one rating, then draw it."""
    line = "=" * 76
    label = {"primary": "PRIMARY CODING (Fig. 2)", "blind": "BLIND RATING (Fig. 3)"}[kind]

    print(line)
    print(f"{label}: milestone days, n = {len(df)} patients")
    print(line)
    d = describe(df)
    for _, r in d.iterrows():
        print(f"  {r['domain']:<9} n={int(r['n applicable']):2d}   "
              f"median {r['median']:.1f} ({r['q1']:.1f}-{r['q3']:.1f})   "
              f"range {r['min']:.0f}-{r['max']:.0f}")
    na = int((len(df) - d["n applicable"]).max())
    if na:
        print(f"\n  A milestone is NOT APPLICABLE in {na} patients and is left missing.")
        print("  Setting it to day 0 would manufacture inversions at a pair the")
        print("  ordering hypothesis permits. It is not done here.")
    else:
        print("\n  Every milestone carries a day in every patient.")

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
    if kind == "primary":
        print("  The manuscript reports both: tie-corrected W = 0.91 (uncorrected")
        print("  0.82), chi2(4) = 80.4, n = 22. Ties are permitted by the hypothesis.")
    else:
        print("  The manuscript reports the tie-corrected value, W = 0.89 (n = 25),")
        print("  beside the primary 0.91, without a threshold.")

    print()
    print(line)
    print("Adjacent-domain ordering (Suppl. Table %s)" % ("5" if kind == "primary" else "6a"))
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
    out = figure(df, out=OUT if kind == "primary" else OUT_BLIND, kind=kind,
                 legend_inside=legend_inside)
    print(f"Figure {'2' if kind == 'primary' else '3'} written to:", os.path.abspath(out))
    if legend_inside:
        print("NOTE: with this legend placement the rightmost points of the")
        print("      slowest patient may fall underneath the legend box.")
    print()
    return out


def main(path: str | None = None, blind: str | None = None) -> None:
    args, blind_arg = spreadsheet_args(sys.argv[1:])
    if path is None and args:
        path = args[0]
    if blind is None:
        blind = blind_arg or (args[1] if len(args) > 1 else None) or _lookup(BLIND_XLSX)
    legend_inside = LEGEND_INSIDE or ("--legend-inside" in sys.argv)
    report(load(path), kind="primary", legend_inside=legend_inside)
    if blind:
        report(load(blind), kind="blind", legend_inside=legend_inside)
    else:
        print("[no blind rating sheet given: Fig. 3 not drawn; pass --blind <sheet>]")


if __name__ == "__main__":
    main()
