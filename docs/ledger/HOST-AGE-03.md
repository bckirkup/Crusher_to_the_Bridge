# HOST-AGE-03
**Date:** 2026-10-05
**Commit:** 17201970
**Pathogens:** norwalk_gi, influenza_a
**Status:** declared

The severity draw's age structure is armed on the norovirus and
influenza arms, shipped default-ON — continuing the HOST-AGE-01/02 line
(age-graded susceptibility + presentation → age-graded case mix).
Design frozen in `docs/host_age_03_design.md`; pooled-hull consequences
under the armed arm are a later stage.

## Change

- **Baseline axis** (`engines/natural_history.py`): `severity_age_mode`
  is the labelled-baseline switch on the severity map, the severity
  analogue of `presentation_age_mode` — `"flat"` reads the pooled
  `base_probabilities` for every band; the unstated default applies the
  declared `base_probabilities_by_age_band` map. `severity_probabilities`
  gained the profile argument to read the mode; the draw
  (`draw_symptom_severity`) is otherwise unchanged, so the map's arm
  moves case mix among presenters only. `_validate_age_graded_terms`
  rejects unknown mode values; `PathogenProfile` declares the field.
- **norwalk_gi**: `severity_model.base_probabilities_by_age_band` arms a
  senior-only partition — `senior`/`65-74`/`75+` get
  `[0.25, 0.55, 0.17384, 0.008235, 0.017925]`; every unnamed band reads
  the pooled vector. Severe share 0.0239 among cases is Calderwood 2021
  (CID, DOI 10.1093/cid/ciab808, US NORS LTCF outbreaks 2009–2018:
  21.6 hospitalisations + 2.3 deaths per 1000 cases — both endpoints
  fold into `severe_critical`, fatality unmodelled). Grade C
  institutional analog; Trivedi 2012 bounds the non-attributable
  background ~9–11%. No per-case severe-outcome design exists for
  non-institutional ages, so nothing finer is declared.
- **influenza_a**: a 17-label map from CDC 2023–24 burden estimates
  (Rolfes 2018 methodology) — severe share per symptomatic illness
  0-4 0.0071, 5-17 0.0028, 18-49 0.0058, 50-64 0.0112, 65+ 0.0982;
  `severe_critical` = share × the 0.8 non-asymptomatic mass, mild and
  moderate resplit at Carrat's pooled ratio. Grade B; U-shaped at the
  young end (0-4 above 5-17).
- **Consequence, recorded not softened**: on a senior-heavy hull both
  arms' pooled severe share rises well above the flat references (noro
  0.001, flu 0.01) — the licensed direction, same as covid's ladder.
- `host_factors.age_bands` (incubation) considered and left undeclared —
  no admissible by-age incubation design for either pathogen.

## Caveats

- Noro's armed source population is institutionalised (NORS pools
  residents and staff; shipboard care differs; GII.4-dominant record on
  a partly GI-analog profile). The ≥65 *presentation* null the register
  records is a different quantity — per-case severity in outbreak
  settings IS measured; only p(sym|infection) at ≥65 is not.
- Flu's ladder is a preliminary single-season estimate; season/strain
  mix moves the ratios. `55+` reads the 50-64 group by declaration.
- Both maps hold the reference asymptomatic share (validator-enforced):
  a band moves case mix, never presentation share.
