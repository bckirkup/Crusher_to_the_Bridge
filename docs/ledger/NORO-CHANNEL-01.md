# NORO-CHANNEL-01
**Date:** 2026-09-26
**Commit:** 6774dcbf
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 2adf1bd0

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

Canary run 2026-09-26, seeds 8000–8019, `spirit_cruise_3000 × norwalk_only
× 168 epochs`, pooled default arm, at `2adf1bd0`. Per-seed payloads:
`docs/norovirus/noro_channel_01/observation_channel_funnel_pooled_default_{a,b}_seed*.json.gz`;
pooled readout `observation_channel_funnel_pooled_default_readout.json`.
"Median/q05/q95" are per-seed ratio distributions; "pooled" divides
summed counts.

### 4.1 The funnel (pooled over 20 seeds)

| rung | total | pax | crew |
|---|---|---|---|
| infected | 143 | 100 | 43 |
| symptomatic course | 106 | 76 | 30 |
| symptomatic onboard | 24 | 20 | 4 |
| syndrome-eligible | 106 | 76 | 30 |
| eligible onboard | 24 | 20 | 4 |
| reported infirmary | 9 (9 pre-recognition, 0 post) | 9 | 0 |
| lab-sampled | 5 | 5 | 0 |
| lab-confirmed | 3 | 3 | 0 |
| onset-dated | 3 | 3 | 0 |

Infections were 128 imported / 15 onboard-acquired; infected per seed
median 7, range 2–21.

### 4.2 Rung ratios vs tranche-48 bands

| ratio | pooled | per-seed median [q05,q95] | band | verdict |
|---|---|---|---|---|
| symptomatic / infected | 0.741 | 0.778 [0.44,1.0] | asympt. 0.20–0.40 → sympt. 0.60–0.80 | inside |
| symptomatic onboard / infected | 0.168 | 0.111 [0,0.25] | — (structural) | n/a |
| reported / eligible onboard | 0.375 | 0 [0,1] | ≈0.4–0.8 (pt 0.60) | **just under** |
| reported / eligible onboard, pax | 0.45 | — | same | inside-ish |
| reported / eligible onboard, crew | 0/4 | — | [?nr] | thin |
| confirmed / reported | 0.333 | 0 [0,1] | unbounded in lit | n/a |
| dated / confirmed | 1.000 | 1.0 [1.0,1.0] | per-case onset recorded | exact |
| dated / infected | 0.021 | — | — | n/a |

### 4.3 Decomposition — ascertainment, not dating

- **Dating rung is intact** — opposite of the COVID failure. All 3
  dated hosts: recorded onset == the engine's own onset arithmetic,
  max abs error 0, including one pre-boarding onset recorded 11 epochs
  before the first in-voyage symptomatic epoch. VSP practice carries
  per-case onset for reported cases (Crisp 2023); the channel does
  exactly that.
- **The dominant loss is upstream and mostly by design**: 82/106
  symptomatic courses (77%) are convalescent imports whose illness ended
  pre-voyage — the channel never had a draw to lose
  (`course_not_symptomatic_onboard`). Of the 24 onboard-symptomatic
  hosts, 15 exhausted their visible window without a successful draw
  (`visible_whole_course_draw_missed`), 9 reported. No host spent its
  whole course isolated.
- **Reported capture 0.375 vs band lower edge 0.4**: marginal miss.
  Composers: the eligible-onboard population is 68% subclinical
  (severity mix at this cell: subclin 72 / mild 31 / moderate 3),
  course length ~1–3 d leaves few eligible epochs, and the applied
  hazard is `declared × (0.5+0.5·trust)` with measured trust 0.78
  → ×0.89. The Wikswo 0.60 denominator is AGE-case-definition illness —
  closer to our mild+ subset than to all-eligible; the mild+ capture is
  inferred higher (reporters were 3 subclin / 5 mild / 1 moderate) but
  the per-severity onboard denominator is not in the payloads (hypothesis
  pending a severity-split rung).
- **Post-recognition rung never exercised**: 20/20 seeds end ALERT,
  never SUSPECTED — every report is pre-recognition, so the
  `isolation_avoidance_post_recognition` scenario vector is unreachable
  at this cell (measured, structural).
- **Noise dominates the infirmary stream**: 3,951 sick-call events
  pooled, 3,930 of them background noise (~99.5%); ~21 true-positive
  call events from 9 distinct reporters (measured).
- **Illness axes**: 80/106 symptomatic courses undrawn — convalescent
  imports never cross onset onboard so `symptom_axes` is never drawn
  (measured, by construction of `draw_symptom_onset`). Among the 26
  drawn: vomiting-containing 15/26 (57.7%) vs declared P(vomiting)=0.72 —
  n=26, weak (inferred).

### 4.4 Verdict vs the v2 priors

Not a contradiction. Asymptomatic share lands inside the challenge/
outbreak band; passenger capture is at/below the band edge but the
severity mix and the belief-seam multiplier account for the direction;
dating is exact. The funnel's effective exposure is much shorter than the
elicitation imagined (courses that end pre-voyage contribute zero
eligible epochs), which is what a voyage-bounded record should show.

## 5. Next decision

**Not an `onset_recording` seam** — the dating rung that motivated the
COVID proposal is intact here (exact arithmetic, pre-boarding onsets
carried). The open questions, in order:

1. **Denominator discipline for the 0.60 check.** Wikswo's capture is
   over AGE-case-definition illness; our all-eligible onboard denominator
   includes subclinical (eligibility 0.55). If the next session wants a
   sharper check, add a per-severity `eligible_onboard` severity table to
   the instrument (one-line change, ~1.3 h re-run) rather than inferring
   the mix.
2. **trust_medical in the reporting hazard.** The channel applies
   `declared × (0.5 + 0.5·trust)` (~×0.89 measured); the v2 elicitation
   does not say whether its 0.60 target is pre- or post-trust. Decide
   which side of the seam the elicitation names.
3. **Recognition is unreachable at small cells.** All seeds end ALERT;
   if post-recognition behaviour is to be checked, pick a cell that
   actually escalates (larger attack or seeded recognition) before
   reading the post-recognition vector.
