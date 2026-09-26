# CABIN-FLOOR-01
**Date:** 2026-09-26
**Commit:** 4e499daa
**Pathogens:** norovirus_gii4, norwalk_gi, sars_cov2_resp, influenza_a, measles_virus, legionella_pneumophila, vibrio_cholerae_parahaemolyticus, campylobacter_jejuni, clostridioides_difficile, andes_hantavirus, ebola_virus
**Status:** measured
**Measured at:** 4e499daa

## Measurement

`tools/cabin_floor_probe.py` ran the `CabinPairChallengeLedger` /
`cabin_pair_challenge_table` instrument over every real pathogen profile in the
Edison roster (`edison_10pathogen_profiles`, 10 arms) plus the active bundle
(`active_profiles`: norwalk_gi, sars_cov2_resp, influenza_a, 3 arms) —
13 (bundle, pathogen) arms at paired seeds 8105/8106, `classic_cruise_1900`,
288 epochs. Each arm isolates its pathogen (`initial_infected: None` overrides)
and plants `explicit_seeds` at epoch 0 (party size from the profile's
`boarding.party.size`), so every arm has a guaranteed index aboard regardless
of boarding probability.

Two confinement modes per arm:

- **declared** — `scenario_schedule` forces SOP-017
  (`confine_all_to_quarters`, crew exempt) day 1 → end, so every paired cabin
  spends the whole infectious span confined; the confined window is the
  household-quarantine window the sourced floors describe. Primary verdict
  basis.
- **organic** — confinement only where the outbreak's own escalation produces
  it; diagnostic column for which pathogens reach confinement at all.

AWS Batch: organic array `19e09a07-e3e4-4f12-9ee3-77e81f3166e9`
(`picard-cabin-floor:1`, image digest `sha256:ba0a7144`, = 844acc5d tree),
prefix `campaign/cabin_floor_01/`; declared array
`f5fd9d39-01d1-4eaa-a347-8011c28b6a30` (`picard-cabin-floor:4`, image digest
`sha256:c14a3d84`, = 4e499daa tree), prefix `campaign/cabin_floor_01_declared/`.
26/26 cells succeeded in each array; the instrument ran clean on every arm.

Definitions: a confined index pair has ≥1 member infected before the pair's
first confined epoch; a slot is a mate uninfected at that epoch; a secondary
is that mate's first infection inside `[confined_first, confined_last]`.
Attack = secondaries / slots, pooled over the two seeds.

## Verdict table (declared confinement, seeds 8105+8106 pooled)

| Arm | Confined idx pairs | Slots | Secondaries | Confined mate attack | Sourced floor | Verdict |
|---|---|---|---|---|---|---|
| active influenza_a | 1147 | 713 | 332 | 46.6% | 15–25% (Lau 3–38%) | MISS high |
| edison influenza_a | 13 | 12 | 6 | 50.0% | 15–25% | MISS high |
| edison sars_cov2_resp | 7 | 7 | 2 | 28.6% | 15–25% | in band (edge) |
| active sars_cov2_resp | 9 | 8 | 0 | 0.0% | 15–25% | MISS low |
| edison norovirus_gii4 | 77 | 76 | 0 | 0.0% | 15–25% (Wikswo/Chimonas) | MISS low |
| active norwalk_gi | 1 | 1 | 0 | 0.0% | 15–25% | MISS low (n=1) |
| edison measles_virus | 1 | 1 | 1 | 100% | 75–90% | consistent (n=1) |
| edison andes_hantavirus | 2 | 2 | 1 | 50.0% | 1.2–3.4% | MISS high (n=2) |
| edison clostridioides_difficile | 135 | 129 | 0 | 0.0% | ~5% | MISS low |
| edison vibrio_cholerae_parahaemolyticus | 3 | 3 | 0 | 0.0% | ~0 | pass |
| edison campylobacter_jejuni | 41 | 40 | 0 | 0.0% | ~0 | pass |
| edison legionella_pneumophila | 0 | 0 | — | vacuous | ~0 | consistent (0 secondaries) |
| edison ebola_virus | 56 | 56 | 5 | 8.9% | (no floor) | measured only |

Legionella's explicit seeds landed in non-paired cabins on both seeds, so no
confined index pair exists to measure; total infections were the 2 planted
seeds per arm with zero secondaries, consistent with its ~0 person-to-person
floor. Vibrio/campylobacter read 0 secondaries across all confined slots —
consistent with ~0. Norwalk_gi has a single confined index pair across both
seeds (15 total infections): the ~0% reading misses the 15–25% floor but is
underpowered.

## Organic-confinement column (diagnostic)

Confinement fired organically only where outbreaks escalated to CONFIRMED:
active influenza_a 202/707 = 28.6% (1367 confined idx pairs), edison
ebola_virus 23/71 = 32.4%, edison influenza_a 11/54 = 20.4%, edison
norovirus_gii4 4/146 = 2.7%, edison vibrio 0/58. All other arms produced zero
confined index pairs organically — their outbreaks never triggered cabin
confinement — which is itself a measured property of the escalation chain,
not a floor miss.

## Reported on discovery (per session rule)

- **~0% for noro/covid:** norovirus_gii4 0/76 slots, norwalk_gi 0/1, active
  sars_cov2_resp 0/8 — all under declared confinement that guarantees the
  exposure window. Reported in-session.
- **≥90% non-measles:** andes_hantavirus read 1.0 on seed 8105 — 1 slot, 1
  conversion; seed 8106 reads 0/1. n=2 pooled, so the ≥90% trigger fired on a
  coin flip, not a sustained rate. Reported in-session.

## Interpretation (hypothesis, not measured)

- The noro miss replicates NORO-CABIN-01's 0/266 confined targets on a fresh
  instrument and a second confinement regime — consistent with the open-ledger
  item-00 dose-scale gap, not channel geometry. Same shape for active-bundle
  covid. (measured: the 0% values; hypothesis: the dose-scale explanation)
- Influenza overshoots its floor 2–3× in both bundles (46.6% / 50.0% vs
  15–25%), the opposite direction from noro — a per-pathogen scale asymmetry,
  not a uniform dose offset. (measured: the attack values; hypothesis:
  per-pathogen scale asymmetry)
- c.diff reads 0/129 vs a "~5%" floor: the 95% upper bound (~2.8%) sits below
  5%, a miss — but the floor is approximate and the channel may legitimately
  be contact-only outside healthcare settings. (measured: 0/129; hypothesis:
  floor mismatch)
- Ebola (no floor) reads 8.9% confined-mate — plausible for a high-virulence
  direct-contact pathogen; recorded as measured-only.

No model constants were touched this session; misses are reported, not fixed.
