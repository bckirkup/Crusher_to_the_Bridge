# HOST-AGE-01
**Date:** 2026-10-05
**Commit:** 6567f4d0
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** working tree on 6567f4d0

The COVID arm was age-blind at acquisition and flat at presentation:
every host drew the same `dose_response` susceptibility and the same
`symptomatic_fraction` 0.69 regardless of age, while only severity was
age-conditioned (#31's `severity_model`). The 2020 literature supports
age structure on both surfaces, and on the Diamond Princess question
the direction matters in two opposite ways — passengers are
elder-skewed, crew is young.

## Change (both maps shipped default-armed on `sars_cov2_resp`)

- `dose_response.susceptibility_by_age_band` — a per-band multiplier on
  the persistent per-host susceptibility, folded in at
  `_dose_response_susceptibility` alongside the frailty draw. Constant
  is the Ayoub 2020 decade ladder vs 60–69y = 1.00:
  0.06/0.34/0.57/0.69/0.79/1.00/0.94/0.88 (Grade B shape; register
  §3.2). Deliberately **not** renormalised to a population mean — the
  ladder is absolute at its reference decade, so on DP's age
  composition it lands as E[mult|crew] ≈ 0.53 vs E[mult|pax] ≈ 0.86:
  the crew channel becomes harder to infect, exactly the protection
  the record shows and the model lacked.
- `symptomatic_fraction_by_age_band` — a per-band replacement for the
  flat presentation share, read inside `presentation_probability`
  before the flat field. Constant is Wang 2022 (Pediatr Infect Dis J,
  PMC9935239) Fig. 2's pooled restricted-cubic-spline over 38 studies
  / 14,850 pre-vaccine infections — the only age-resolved synthesis of
  the same screened-denominator quantity `symptomatic_fraction` itself
  reads from Buitrago-García. Digitised reads: symptomatic 0.70/0.64/
  0.73/0.77/0.79/0.83/0.88 across bands (F2dig, calibrated to the two
  printed anchors). Davies/Poletti/Xu recorded as corroborating
  direction, incommensurable level, not used numerically.

Both maps key on the agent's `age_band` label under the severity
model's established band→decade convention (midpoint; open-ended
+5y; `child`/`young_adult`/`adult`/`middle_aged`/`senior` =
5–17/18–34/35–49/50–64/65+). An unnamed band multiplies 1.0 / falls
back to the flat share, so profiles that declare neither map run
unchanged — the arming lives entirely in profile data, the seam in
engine code. `_validate_age_graded_terms` bounds the map shapes for
every profile.

## Repins (each attributed, AGENTS convention)

- `tests/test_covid_hull_change_detector.py` GM cell (Θ 1e10, seed
  20200333): `(36, 19, 217, 55, 18)` → `(34, 17, 217, 56, 22)` on
  CPython 3.12. `campaign_asymptomatic_positives` 18 → 22 is the
  intended direction — young-band infections that would once have
  presented now stay silent and are caught by the campaign screen.
  The identical profile minus both maps reproduces the prior tuple
  exactly on the same tree, so the move is fully attributed to the
  two maps. 3.11 entry carries the same tuple pending its CI read.
- `tests/test_covid_hull_change_detector.py` DP cell (Θ 1e10, seed
  20200333, CPython 3.12, slow-marked): `(2480, 2215, 2827, 595, 542)`
  → `(2765, 2587, 2702, 398, 333)`. Composition: the presentation
  ladder's elder lift raises recorded onsets (+285) while the
  susceptibility ladder's acquisition suppression cuts campaign
  positives (595 → 398) and asymptomatic positives (542 → 333). The
  same profile minus both maps reproduces the pin exactly on this
  branch — fully attributed, both reads local venv CPython 3.12.

## Consequences recorded, not softened

- Elder-skewed hulls: the ladder's reference decade sits where DP
  passengers live, so mean passenger susceptibility is roughly flat
  while crew drops ~half — the direction the DP record demands
  (during-window crew share falls toward, not past, 29%).
- Presentation ladder raises dated onsets per infection for the
  elderly (0.83–0.88 vs flat 0.69) and lowers it for children — on an
  elder-skewed hull the net direction is *more* dated onsets per
  course, partially offsetting the acquisition suppression. Recorded
  as the measured composition, not an average.
- Declared sweep axes: the child end of the susceptibility ladder is
  the contested corner (Davies ~0.5 and Viner pooled OR 0.56 sit ~3–8×
  above Ayoub's 0.06) — a sweep axis, not an average; and
  `severity_model`'s vestigial flat 0.31 asymptomatic entry stays
  unaligned as recorded consistency debt.
