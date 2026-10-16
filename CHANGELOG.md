# Changelog

## v1.1.2 — 2026-10-16
- README: data statement aligned with the submitted manuscript (de-identified
  day counts for both raters are in Supplementary Table 7; calendar-dated
  sheets remain restricted); pre-registered plan, now open at Zenodo, cited
  by its concept DOI (10.5281/zenodo.23076104), as in the manuscript.
- No change to either script. Statistics unchanged.

## v1.1.1 — 2026-10-15
- `catatonia_figure2.py`: draws Fig. 3 (blinded re-rating, I.M.) with the same
  layout as Fig. 2 when a second sheet is passed with `--blind`; accepts the
  second rater's sheet layout and CSV input; x-axis label corrected to
  "Day from symptom onset" (day of onset = day 1), matching the Methods;
  author list updated. All statistics unchanged.
- `blind_rerating_analysis.py` added (identical to the Zenodo deposit).
- Templates, requirements and licence added.
- Supplementary table numbers in docstrings and README follow the submitted
  manuscript (blind-rating tables are Suppl. Table 6a/6b; both raters' days, Table 7).

## 2026-09
- `catatonia_figure2.py`: initial release (Fig. 2 and its statistics).
