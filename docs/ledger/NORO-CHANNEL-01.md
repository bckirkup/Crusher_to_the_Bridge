# NORO-CHANNEL-01
**Date:** 2026-09-26
**Commit:** 20086708
**Pathogens:** norwalk_gi
**Status:** declared

Measures the norovirus observation funnel **as the declared channel emits
it today** — the VSP_AGE syndromic block in
`data/pathogens/norwalk_only.json` (Grade C, origin
`../norovirus/cruise_pathogen_severity_observation_priors_v2.md`,
explicitly not identified) — and reads each rung's ratio against the
literature bands in
`../literature/consensus_tranche_48_noro_observation_channel.md`. Same
ascertainment-vs-dating decomposition as the COVID channel audit
(`../covid/covid_channel_anchor_handoff_2026_09_25.md` §2).

Nothing in this entry tunes a constant, creates an anchor, or changes
default behaviour. The instrument (`tools/noro_diag/observation_channel_funnel.py`,
PR #691) is read-only: it attaches an `epoch_observer` to a spec-built
`ShipSimulation` and mutates nothing.

## 0. Settled inputs (quoted, not re-derived)

- **Frozen cell** (`NORO-COINCIDENCE-CELL-01`): seeds **8000–8019**,
  platform `spirit_cruise_3000` (3000 agents, 168 epochs × 1 h), bundle
  `norwalk_only`, pooled **default arm only**.
- **COVID handoff §2/§8** (`../covid/covid_channel_anchor_handoff_2026_09_25.md`):
  that record gap decomposed into ascertainment (confirm rate already
  period-rough) vs onset *dating* (broken rung); the proposed
  `onset_recording` seam is a proposal only — not built here.
- **v2 priors** (`../norovirus/cruise_pathogen_severity_observation_priors_v2.md`):
  cruise infirmary capture ≈0.60 [E] among AGE-eligible symptomatic;
  challenge illness 67–100% [E] of infected; asymptomatic 0.19–0.35 [E/M];
  shipped vectors yield ≈0.50 eligible symptomatic mass and ≈0.30 reported
  eligible mass (≈0.61 ratio, M/A).

## 1. The funnel (measured rungs)

Per seed, per role (passenger / crew / other):

`infected` (split imported / acquired-onboard) → `symptomatic_course`
(presented ever, with Kirby illness class vomiting/diarrhoea/undrawn)
→ `symptomatic_onboard` (≥1 in-voyage epoch reading SYMPTOMATIC —
excludes convalescent imports whose course predates boarding) →
`syndrome_eligible` (peak severity with eligibility > 0) →
`eligible_onboard` → `reported_infirmary` (first syndromic
true-positive call, split pre/post recognition where recognition =
prior-epoch trigger status ≥ SUSPECTED) → `lab_sampled` → `lab_confirmed`
→ `onset_dated`.

Alongside: per-severity tables, non-report decomposition
(`course_not_symptomatic_onboard` / `isolated_whole_symptomatic_course` /
`partially_isolated_but_draw_missed` / `visible_whole_course_draw_missed`),
undated-confirmation reasons, sick-call vs noise-report totals, dating
fidelity (recorded onset epoch vs the engine's own onset arithmetic and
vs the first observed symptomatic epoch), and the declared per-severity
episode hazards computed from the shipped vectors.

## 2. Literature checks (tranche 48)

| Check | Band | Grade |
|---|---|---|
| Asymptomatic share of infections | 0.20–0.40 | [E] Miura 2018 0.321 (0.277–0.367), GII.4 0.407; Kirby 2016 challenges 0.60–1.00 ill |
| Infirmary capture, eligible symptomatic passengers | ≈0.4–0.8 (point 0.60) | [E] Wikswo 2011; single outbreak |
| Infirmary capture, crew | [?nr] | Dahl 2005 documents presenteeism, unquantified |
| Onset dating in VSP records | per-case onset date on reported cases, incl. pre-boarding onsets | [E] Crisp 2023; finer precision [?nr] |

## 3. Canary (frozen before run)

20 seeds, `spirit_cruise_3000 × norwalk_only × 168 epochs`, seeds
8000–8019, pooled default arm, local. Readout:
`docs/norovirus/noro_channel_01/observation_channel_funnel_pooled_default_*.json`
(per-seed `.json.gz` + pooled readout). Ratios read per seed with
median/q05/q95 spread; a rung is flagged where the pooled median sits
outside the §2 band, decomposed into ascertainment vs dating.

## 4. Measured block

_To be filled only from the canary readout at the measuring commit._

## 5. Next decision

_To be filled from measurement._ Candidate standing question, recorded
now so it cannot be retro-fitted: the reporting hazard the channel
actually applies is `declared_vector × (0.5 + 0.5·trust_medical)` — the
trust multiplier (~0.875–0.89 under `information_diffusion_default`) is
not part of the v2 elicitation. If the measured reported/eligible-onboard
ratio lands below the §2 band by roughly that factor, the diagnosis is
in the belief seam, not the vectors — and the decision is whether the
elicitation targets the pre-trust or post-trust probability.
