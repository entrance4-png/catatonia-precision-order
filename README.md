# catatonia-precision-order

Analysis and figure code for

> Saito, H., Takizawa, Y., Murata, I., Tateno, A., Theorell, J., Arakawa, R. & Tiger, M.
> **Recovery from catatonia follows a hierarchical precision order.**

Two scripts, two inputs, no fitting and no simulation. The scripts read recorded
milestone days (one row per patient, one column per precision domain) and print
every number the manuscript quotes from them.

| Script | Input | Output |
|---|---|---|
| `catatonia_figure2.py` | primary milestone sheet; optionally the blind rating sheet (`--blind`) | Fig. 2 (`saito_companion_fig2.png`), Fig. 3 (`saito_companion_fig3.png`), and the per-rating statistics: median (IQR) and range per domain (Suppl. Table 4), tie-corrected and uncorrected Kendall's W, adjacent-pair ordering with strict precedence, same-day ties, inversions and exact sign tests (Suppl. Tables 5 and 6a) |
| `blind_rerating_analysis.py` | two CSVs, one per rater (`case, ps, beta, pm, pv_fast, pv_slow`) | the pre-registered analysis of the blinded re-rating, sections 4 to 8 of the plan: primary criterion (inversions of the separable transitions), Kendall's W per rater, ICC(A,1), Bland–Altman, Cohen's κ, per-patient Kendall's τ-b (Suppl. Tables 6a, 6b) |

`blind_rerating_analysis.py` is the script deposited with the pre-registered
plan at Zenodo (doi:10.5281/zenodo.23076104; plan v1.0 fixed on 1 October 2026,
before any blind rating was returned). It is reproduced here unchanged.

## Running

```bash
pip install -r requirements.txt

# Fig. 2 and Fig. 3 with their statistics
python catatonia_figure2.py milestone.xlsx --blind murata_day.xlsx

# Fig. 2 only
python catatonia_figure2.py milestone.xlsx

# pre-registered agreement analysis (SPSS v32 gives the same values)
python blind_rerating_analysis.py index.csv independent.csv --out report.txt --plots ba_plots
```

`catatonia_figure2.py` can also be pasted whole into a Google Colab or Jupyter
cell; if no sheet is in the session an upload dialog opens.

## Input format

**Milestone sheet** (`catatonia_figure2.py`): one row per patient, columns
`patient | πs | β | πm | πvfast | πvslow` (the blind sheet as returned by the
second rater, `no. | date | πs | β | πm | πv_fast | πv_slow | Pt`, is accepted
as well). Cells hold `day6`, `DAY6` or `6`: the day counted from the onset of
catatonic symptoms, with the day of onset as day 1. A blank, `NA` or `ND` means
the milestone could not be dated and is left missing; it is never imputed and
never treated as day 0. See `milestone_template.csv`.

**Rating CSVs** (`blind_rerating_analysis.py`): columns
`case, ps, beta, pm, pv_fast, pv_slow`, values an integer day, `NA` (baseline
disturbance not documented) or `ND` (documented, but no entry recording its
resolution). See `rating_template.csv`.

## What the manuscript quotes

Primary coding (H.S.): tie-corrected Kendall's W = 0.91 (uncorrected 0.82),
χ²(4) = 80.4, n = 22 complete cases; order-informative patients 15, 12, 18 and
22 for the four adjacent pairs; no inversion.

Blind rating (I.M.): tie-corrected W = 0.89, n = 25; order-informative
patients 16, 11, 17 and 24; no inversion of either separable transition
(primary criterion of the pre-registered plan: not refuted).

The tie correction is not cosmetic. Milestones are integer days and same-day
milestones are common; the ordering hypothesis permits them, so a coefficient
deflated by ties would penalise the hypothesis for its own prediction. Both
values are printed and both are reported.

## Data

De-identified milestone day counts (day from symptom onset, both raters, every
patient) are given in Supplementary Table 7 of the manuscript and are the only
input these scripts need. The sheets as used in the study carry patient-level
calendar dates and are not public; they are available from the corresponding
author on reasonable request, subject to institutional and ethical approval.
The two template files in this repository carry made-up rows and exist only to
show the column layout.

## Citation

Code archive: Saito, H. *catatonia-precision-order: analysis and figure code
for "Recovery from catatonia follows a hierarchical precision order".* Zenodo
https://doi.org/10.5281/zenodo.23388109

Pre-registered plan and `blind_rerating_analysis.py`: Saito, H. *Prespecified
analysis plan for blinded re-rating of recovery milestones in catatonia.*
Zenodo https://doi.org/10.5281/zenodo.23076104

## Licence

MIT. See `LICENSE`.
