---
name: transmission-blocker-cascade
description: Ordered diagnostic cascade for "dose is being delivered, why is nobody infected?" in engines/transmission_core.py — route attribution, then pickup terms, then host blockers, then a forced challenge trace — with the recurring defect archetype (a route gated on shedder status that makes a carrier a dead end), the candidate blocker list with the cheapest discriminating evidence for each, and the two hard rules (prove the mechanism fired; compute the summed naive hazard before saying "blocked"). Use whenever a voyage, cell or arm shows zero or near-zero secondaries and a blocker is suspected.
---

# Transmission blocker cascade

Use this skill when a run delivers dose but produces no (or implausibly few)
infections and the question is *where the chain is broken*. It exists because
three long sessions spent hours each on this question, and each time the cost
was not the analysis but the order: expensive batches were run before cheap
discriminators, and diagnostics were run whose mechanism never fired.

The engine under test is `engines/transmission_core.py`. The chain, in the
order the engine evaluates it, is: **shedder selection → route pickup → route
dose ledger → protection and superinfection → persistent host susceptibility →
hazard → Bernoulli draw → `_establish`**. Walk it in that order, cheapest
evidence first, and write down what each step ruled out before moving on.

## Step 0: is there anything to explain?

Before any of the below, compute the **summed naive hazard**: for every
susceptible agent that received dose, the per-epoch probability the engine
would have drawn, summed over agents and epochs. The engine's hazard is

```python
# engines/transmission_core.py
def _dose_response_hazard(self, agent, pathogen_id, effective_dose):
    susceptibility = self._dose_response_susceptibility(agent, pathogen_id)
    return -math.expm1(-susceptibility * effective_dose)
```

so the expected infection count is `sum(-expm1(-s_i * d_i))` over
`(agent, epoch)`, using each agent's persistent
`agent.dose_response_susceptibility[pathogen_id]` and the
`effective_dose` after protection. Read `cumulative_exposure` and
`cumulative_exposure_by_route` off the agents at the end of a local run, or
sum `pathway_breakdown` from `contact_tracing.transmission_events` in the run
record (`orchestrator_record.py`).

**If the sum is 0.2, zero infections is the correct draw and there is no
blocker to find.** Report the sum and stop. A day was once spent hunting a
blocker in a cell whose expected secondaries were below one; the "defect" was
the design, not the engine.

Only proceed when the summed hazard is well above the observed count (a
Poisson tail below ~0.05 is the working threshold, and say which you used).

## Step 1: route attribution (minutes, one local run)

*Discriminates:* "no route delivers" from "a route delivers and downstream
blocks".

Every established infection records `pathway_breakdown` and
`dominant_pathway` in `matrix.transmission_events` (see
`_record_transmission_event`), and every challenged agent accumulates
`cumulative_exposure_by_route[pathogen_id]` even when the draw fails. Dump
both for one seed of the failing cell. If every route reads zero for every
susceptible, the problem is upstream of the challenge — go to Step 2. If dose
is present by route but no event exists, the problem is Step 3.

Cost: one local voyage of the failing cell — the campaign `--smoke` shape
(destroyer, 2 epochs, 20 agents) is seconds, a full hull voyage is minutes.
Use the seed the campaign readout says is the worst case, not a fresh one.

## Step 2: pickup terms — and the recurring defect archetype (minutes)

*Discriminates:* "the source never emits" from "the source emits but the
recipient never picks up" from "the route is gated shut for this source".

Check the route's own execution witness first (see Hard rule 1). Then read
the pickup function for the suspect route and ask one question:

> **Is this route gated on the source being a shedder or being clinical, when
> the reservoir it moves is something a non-shedder can also carry?**

This is the archetype to look for first. Hand load is the worked example.
`hand_load_by_pathogen` is a per-agent reservoir that anyone can acquire —
from a surface, from a handshake, from a patch — whether or not they are
shedding. But:

- **hand → surface** in `_sanitary_fomite_exposure` skips an agent unless
  `self._get_shedders([agent], pathogen_id, profile)` is non-empty, and
  `_food_deposits` iterates `self._get_shedders(occupants, ...)`. A passenger
  who touched a contaminated rail and then a shared head deposits nothing.
- **hand → hand** in `_per_partner_contact_dose` → `_hand_contact_transfers`
  iterates `sampled_shedders`, which `_direct_contact_unit` built from
  `self._get_shedders(occupants, ...)`. The same passenger shaking hands
  moves nothing, even though the function reads
  `shedder.hand_load_by_pathogen` and never uses the shedding value.

`_get_shedders` returns `(agent, sv)` only where
`agent.get_pathogen_shedding(pathogen_id, profile) > 0`. So on every
hand-mediated route, **a carrier is a dead end**: the route's *source set* is
the shedder set, not the set of agents with a non-zero reservoir. Any
two-hop chain — index sheds onto hands → contact → contact touches surface →
third party — is truncated at the second hop.

The same pattern appears wherever a phase or status gate sits in front of a
reservoir: `_emesis_phase` gating emesis on the host's clinical phase (correct,
emesis is clinical), `_cabin_confinement_active` skipping confined agents on
deposit loops (correct for movement, wrong if the confined agent's cabin-mate
is the only contact). For each gate ask: *is the gate about the source's state,
or about the reservoir's content?* Only the second is legitimate on a pickup
route.

Cheapest evidence: a two-agent unit test that gives a non-shedding agent
`hand_load_by_pathogen = {pid: 1e6}` and asserts the route moves mass. If it
moves nothing, you have found the archetype; file a ledger entry under
`docs/ledger/<ID>.md` before fixing anything.

## Step 3: host blockers (minutes each, local)

*Discriminates between* the terms multiplied into the challenge. Check them in
engine order; each has a one-line probe.

| Candidate | Where | Cheapest discriminating evidence |
|-----------|-------|----------------------------------|
| Protection | `_challenge_protection`; returns early when `>= 1.0` | Print `protection` per challenged agent. `agent.immune` is absolute (1.0) unless `cross_immunity` is configured. A hull whose `immune_fraction` was meant as 0.3 and landed as 0.97 shows here and nowhere else. |
| Persistent susceptibility draw | `_dose_response_susceptibility`: `rng.beta(alpha, beta) * _beta_poisson_susceptibility_scale(...)`, drawn once per host and cached in `agent.dose_response_susceptibility` | Histogram the cached values against the profile's own pair in `data/pathogens/active_profiles.json` (norovirus GII: `alpha 0.111`, `beta 32.81`; the COVID frailty is `Beta(0.18, 58)` per `DOSE-FRAIL-01`). These are strongly skewed — the median sits far below the mean, so a design sized on the mean expects an order of magnitude more infection than the draw delivers. Confirm the *pathogen* key too: a value cached under another `pathogen_id` is not read for this one. |
| Hazard | `_dose_response_hazard`; `-expm1(-s * d)` | Recompute by hand for one agent from the printed `s` and `d`. If the engine's number differs, the profile's `dose_response.model` is not what you think (`exponential` uses `k`, not the Beta draw). |
| Upstream clinical state | `crusher_labs/clinical_presentation.py::resolve_phase`; `_emesis_phase` | Count agents per phase per epoch. If nobody is ever symptomatic, no clinical route (emesis, droplet on `emesis_conditioned` arms) can fire regardless of dose. |
| Emesis timing | `_emesis_phase`, `_emesis_host_titre`, `_emesis_patch_pickup` | Assert the emesis event counter is non-zero (Hard rule 1). Check the event lands in a zone with co-occupants at that epoch — an event in an empty cabin exposes `footprint_area / floor_area` of nobody (`EMESIS-FOOTPRINT-01`). |
| Confinement | `_cabin_confinement_active` (only in `Cabin_Corridor` zones), `_confinement_factor`, `DEFAULT_CONFINEMENT_ISOLATION_FACTOR`, `_cabin_pair_contact_factor` | Print the factor applied to the index case's contacts. If the index is confined from epoch 0 (a seed declared symptomatic on boarding under a quarantine SOP), every route through it is scaled to the isolation factor before it ever sheds. |
| Dose-response wiring | `pathogen_profiles[pid]["dose_response"]`: `model`, `alpha`/`beta` vs `k` | Read the profile in `data/pathogens/active_profiles.json` for the key actually consumed — `model: exponential` takes `k` and never draws the Beta at all. `DOSE-FRAIL-01` (#603) found Theta wired as an exponential `k`, which made all 3,711 hosts identically susceptible on the one arm the grid was scored on; the wiring, not the value, was the blocker. |
| Surface removal | `_parse_surface_cleaning_cfg`; SOP-triggered disinfection | `CLEAN-OUTBREAK-01`: a per-epoch instead of on-the-clock pass removed ~100 log10/day and produced 12/12 zero-secondary seeds on two hulls. Log the removal per epoch; anything above the declared `routine_log10_reduction` × events/day is this. |

Write down the value of each term for one challenged agent in one epoch. The
blocker is the term that is zero or ~1e-N when the design says it should not
be.

## Step 4: forced challenge trace (tens of minutes, local)

*Discriminates:* "the engine cannot infect anyone" from "the engine can, but
this design never reaches the threshold".

Only after Steps 1-3: take the failing cell, one seed, and force a challenge
that must succeed if the downstream chain is intact — set one susceptible's
`hand_load_by_pathogen[pid]` (or the zone's surface pool) to a dose where
`-expm1(-s*d)` ≈ 1 for that host's cached `s`, run one epoch, and assert an
event appears in `transmission_events` with the expected `dominant_pathway`.
If it does not, the blocker is in `_establish` or later (strain registry,
`_draw_source`, superinfection) and is independent of every upstream term.

This is the only step that costs real time and the only one that should
touch engine state directly. Do it in a throwaway script under the repo (not
`/tmp`; `simulation_utils.paths` refuses it), and delete the script — the
finding goes in the ledger, not the tree.

## Hard rule 1: assert the mechanism under test fired

A diagnostic that does not prove its own mechanism ran measures nothing. A
12-seed local batch was run against the emesis pathway to test whether emesis
deposition reached third parties; the emesis event count across all 12 seeds
was **0** — no host reached the vomiting phase in the voyage window — and four
hours of wall clock produced a result about nothing.

Every route in this engine has, or must be given, an execution witness. The
flush route's is the model: `sanitary_telemetry["flush_events"]`,
`flush_aerosol_emitted`, `flush_recipients`, `flush_dose_delivered`, whose
comment reads *"an all-zero witness distinguishes 'flush off' from 'witness
missing'"*, and whose design (`flush_sweep_v1_*` manifests) states that the
witness "distinguishes 'the route ran and moved nothing' from 'the route never
ran'". Before reading any outcome from a diagnostic:

1. Name the counter that proves the mechanism fired.
2. Print it. If it is zero, the diagnostic is void; say so and stop.
3. If no such counter exists, add one to `sanitary_telemetry` (or the
   route's equivalent) *as its own change* before running the diagnostic.

## Hard rule 2: compute the summed naive hazard before saying "blocked"

Stated in Step 0 and repeated because it is the one most often skipped. "Zero
infections" is a draw, not a measurement, until the expected count is known.
Report the expected count alongside the observed one in every diagnostic
readout and every ledger entry, e.g. *"expected 0.2 secondaries from the
delivered dose under the cached susceptibilities; observed 0"*. A reader who
sees only the second number will hunt a blocker that is not there.

## Closing the cascade

The output of this skill is a ledger entry (`docs/ledger/<ID>.md`, header per
`docs/ledger/README.md`) that records, in order: the summed naive hazard; the
route-attribution dump; the pickup gate inspected and whether the archetype
applied; the per-term table from Step 3 for one agent; and, if reached, the
forced-trace result. Update `docs/norovirus/norovirus_open_ledger.md` §1 or
`docs/covid/covid_open_ledger.md` §1 in the same change if the finding voids
any recorded measurement. A blocker found and not written down is
indistinguishable from one not found — see
`.agents/skills/session-handoff-ledger/SKILL.md`.

## Related

- `.agents/skills/model-parameter-provenance/SKILL.md` — the *other* recurring
  archetype (a well-mixed pool standing in for concentrated events); check
  both.
- `.agents/skills/stochastic-attribution/SKILL.md` — once a blocker is fixed,
  attributing the resulting move needs paired seeds.
- `.agents/skills/orchestrator-smoke-test/SKILL.md` — the 24-epoch loop used
  for Step 1 dumps.
- `docs/norovirus/route_attribution_headcount_scaling.md` — how route shares
  are read at hull scale.
