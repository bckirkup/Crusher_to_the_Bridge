# DATING-RES-01
**Date:** 2026-10-09
**Commit:** #979
**Pathogens:** sars_cov2_resp
**Status:** measured

The dating residual after ONSET-REC-01 decomposed end-to-end on the
record-truth replica (`boxed_s1s2` arm of the CREW-REACH-01 design —
retest tiers + crew wave, the record's full observation structure), two
DP-realization cells by same-realization rerun (local, not a campaign).
Tool `tools/covid_specimen_timing_probe.py`; evidence
`reports/specimen_timing/smoke_{20200218,20200223}.json`.

## The arithmetic chain (all verified)

`dated share = presented-at-specimen share of confirmed × recall draw`.
On the boxed cells: gate-pass share 0.762 × 0.56 ≈ 0.43 ≈ the measured
0.416 (ONSET-REC-01). The channel executes its declared semantics
exactly; the residual lives entirely in the first factor.

**Gate semantics: NO DEFECT.** `symptomatic_at_specimen` in the model
means *true symptom onset preceded the specimen day* — the
`_presentation_onset_epoch` is back-dated from the infection record's
`epochs_since_symptom_onset` (`syndromic.py` `_observed_onset_epoch`),
not the sick-call arrival day. That is precisely the record's own field
(`covid_fit_targets.json`: "no onset had been recorded for that host by
the day its specimen was taken"; the undated remainder "had onset
imputed from a report lag").

**Record decomposition** (Mizumoto 2020, Eurosurveillance
25(10):2000180 — the same paper the campaign volumes cite): ~0.49
asymptomatic-at-specimen = delay-adjusted **never-symptomatic 0.179**
(95% CrI 15.5–20.2) + **pre-symptomatic-at-test ~0.31**.

**Model decomposition** (pooled over the two cells):

| component | model | record |
|---|---|---|
| never-present share of confirmed | ~0.22–0.25 | ~0.179 |
| pre-onset catches (onset after specimen) | ~0.04–0.05 | ~0.31 |
| **asym-at-specimen share** | **~0.27** | **~0.49** |

- 20200218: 872 infections / 809 confirmed; asym 0.268 = 176
  never-present + 41 pre-onset. Specimen dpi at confirmation p25/p50/p75
  = 5/6/8; pre-onset window median 4 d.
- 20200223: 770 infections / 605 confirmed; asym 0.269 = 150
  never-present + 13 pre-onset. Specimen dpi 5/6/7; window median 4 d.
- In-window coverage: 266/872 and ~similar of 770 infections swabbed
  inside their pre-onset window; the rest first-swabbed outside it.
- Counterfactual (contacts of confirmeds swabbed the day after the index
  confirmation): only ~10.5 / ~22.0 expected extra pre-onset positives —
  contact-priority densification cannot move the metric materially.
- Incidence tail: max infection day 30–31 vs the last specimen mass
  ~day 33–34 — the wave lands on infections ~6 dpi, post-onset for the
  ~4–5-day typical window.

## Verdict

The whole dating residual is a **pre-onset-catch deficit (~0.04 vs
~0.30)**, not a never-symptomatic shortfall — the model's never-present
share already sits at/above the record's delay-adjusted 0.179 (the
declared 0.31 asymptomatic rung is, if anything, generous against DP's
elderly-skewed estimate). The catch deficit is a specimen-timing joint
artifact: first positive specimens land at median dpi ~6 against a
~4–5-day pre-onset window, and the realized incidence tail extinguishes
~3–5 days before the last specimen mass arrives, so the wave finds
old infections. On the record, transmission ran to the final test days
(the dated onset curve and the crew wave overlap), so the wave caught
hosts mid-incubation.

**No record-faithful observation-seam lever remains:** the volumes,
dates, and crew-last ordering are the record's own declarations;
contact-priority bounds at ~+0.02; the Sah 0.351 axis adds ~+0.03
never-present on a side that is already above the record's estimate.
What is left underneath is a **transmission-timing question** — whether
the model's outbreak tail dies too early relative to the record's —
and refitting incidence timing to the dating anchor is the forbidden
move. Bound statement for the scoreboard: dated share lands ~0.42–0.47
under the truthful channel vs record 0.277; the residual is decomposed
and named, not unexplained.
