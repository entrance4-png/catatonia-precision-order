# catatonia-precision-order

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21405269.svg)](https://doi.org/10.5281/zenodo.21405269)

Analysis and figure code for

> **Recovery from catatonia follows a hierarchical precision order**
> Hiroki Saito, Yuichi Takizawa, Amane Tateno, Ryosuke Arakawa, Mikael Tiger (2026)

One self-contained script that reproduces Fig. 2 and **every number the manuscript quotes
from the milestone data**. Nothing is fitted and nothing is simulated: the script reads the
recorded milestone days and draws them.

---

## The input data are not in this repository

The milestone data are anonymized clinical records and are **not publicly available**, because
of their clinical nature and the risk of patient re-identification (see the manuscript's Data
availability statement). They are available from the corresponding author on reasonable
request, subject to institutional and ethical approval.

**Cloning this repository will therefore not reproduce the figure on its own.** The code is
published so that the *procedure* can be inspected and audited without access to the data,
and so that the same analysis can be run on other cohorts.

## Running it on your own cohort

The script expects an `.xlsx` with one row per patient and these columns:

```
patient | πs | β | πm | πvfast | πvslow
```

- cells hold strings of the form `day6`; the integer is parsed out
- a **blank** cell means the domain's baseline disturbance was not documented and the
  milestone is **not applicable**. Blanks stay missing: they are never imputed and never
  treated as day zero
- in the reported cohort this is the case for πv_fast in three patients, who received an
  antipsychotic from initiation
- `πv_fast` / `πv_slow` (with the underscore) are also accepted; column names are matched
  ignoring case and surrounding spaces

```bash
pip install -r requirements.txt
python catatonia_figure2.py your_milestones.xlsx
```

With no argument the workbook is located automatically: the default name `milestone.xlsx` is
tried in both NFC and NFD (Japanese file names differ between the two), and failing that any
single spreadsheet in the working directory, `/content`, `/content/drive/MyDrive` or the
script's own directory, up to three levels deep.

Requires pandas, numpy, scipy, matplotlib, openpyxl; Python >= 3.9.

## Running it in Google Colab

Paste the whole of `catatonia_figure2.py` into one cell and run it, or open
`catatonia_figure2.ipynb`. If no workbook is present in the session an upload dialog opens;
choose the `.xlsx`. The statistics print and the figure is drawn in the cell as well as saved
to `saito_companion_fig2.png`. All the required packages are preinstalled in Colab.

## What it prints, and where the manuscript's numbers come from

| Reported in the paper | Produced by |
| --- | --- |
| median (IQR) and range per domain, n applicable (Supplementary Table 1) | `describe()` |
| tie-corrected Kendall's W = 0.91, χ²(4) = 80.4, n = 22 | `kendalls_w()`, complete cases only |
| uncorrected W = 0.82, χ² = 72.2 | the same function, printed alongside |
| adjacent-pair ordering: n, strict precedence (the order-informative counts 15, 12, 18, 22), same-day ties, inversions, sign-test p (Supplementary Table 2) | `adjacent_pairs()` |
| Fig. 2, panels a and b | `figure2()` |

The BFCRS severity statistics (Table 2 of the manuscript) are scored from a separate record
sheet and are not computed here.

The tie correction is not cosmetic. Milestones are integer days and ties are common. Ties are
**predicted** by the ordering hypothesis, so deflating W for them would penalise the hypothesis
for a prediction it makes. The script prints both values; the manuscript reports both.

Missing πv_fast values are left missing. Setting them to day 0 would manufacture three
inversions at the single pair the ordering hypothesis permits. The script does not do this,
and says so.

## Panel a sort order

Rows are ordered by πv_slow ascending, ties broken by πv_fast descending, with non-applicable
πv_fast last. This is stated because a reader reproducing the panel from a different tie-break
will get a different picture of the same data.

## Legend placement

The legend sits clear of the data. Setting `LEGEND_INSIDE = True`, or passing
`--legend-inside` on the command line, reproduces an earlier placement, under which P10's two
rightmost points (πv_fast day 40, πv_slow day 42) are hidden behind the legend box. No number
changes either way.

## Output

`saito_companion_fig2.png` (300 dpi), the descriptive statistics, concordance values and
adjacent-pair table on stdout, and, in a notebook, the figure drawn in the cell.

## Citation

If you use this code, please cite the paper and the archived release:

> Saito, H. catatonia-precision-order: analysis and figure code for "Recovery from catatonia
> follows a hierarchical precision order". *Zenodo* <https://doi.org/10.5281/zenodo.21405269> (2026).

The concept DOI `10.5281/zenodo.21405269` always resolves to the latest version. The current
release is v1.0.1.

## License

MIT. See `LICENSE`.
