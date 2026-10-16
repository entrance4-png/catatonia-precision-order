# Changelog

## v1.1.3 — 2026-10-16
- `supp_table7_primary.csv` and `supp_table7_blind.csv` added: the milestone
  day counts of both raters for all 25 patients, identical to Supplementary
  Table 7 (checked cell by cell; no calendar dates). With these the manuscript's
  figures and statistics reproduce from a clean clone with two commands.
- README: "Reproducing the manuscript" section; Data section updated.
- `.gitignore`: the two data CSVs are no longer ignored.
- No change to either script. Statistics unchanged.

## v1.1.2 — 2026-10-16
- README: data statement aligned with the submitted manuscript (de-identified
  day counts for both raters are in Supplementary Table 7; calendar-dated
  sheets remain restricted); pre-registered plan, now open at Zenodo, cited
  by its concept DOI (10.5281/zenodo.23076104), as in the manuscript.
- Code archive cited by its Zenodo concept DOI (10.5281/zenodo.23388109),
  which resolves to the latest version; the DOI previously given in README
  and CITATION.cff (10.5281/zenodo.21405269) was wrong.
- CITATION.cff: version and date updated (was still 1.1.0 at v1.1.1).
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
