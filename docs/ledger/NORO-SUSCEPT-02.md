# NORO-SUSCEPT-02
**Date:** 2026-09-19
**Commit:** dbddd47
**Pathogens:** norwalk_gi
**Status:** open

Per-host join of credited dose against evaluated challenge, to settle the one
open finding of `NORO-SUSCEPT-01`: a whole-run summed naive hazard of 0.197
against 394,281 GEC credited is an ordinary draw only if the dose effectively
reached one or two hosts, while the recovered per-host maximum (49,572 GEC,
12.6% of the total) needs at least eight. Either the credited dose and the
evaluated hazard are taken over different host sets, or they are taken over
different quantities.

## Attribution criterion, declared before the run

Runs: seeds 8105 and 8106, `classic_cruise_1900` at its declared complement
(1,910 agents), 288 epochs, shipped `data/pathogens/active_profiles.json`, no
configuration, profile or constant override. The two arms differ from a shipped
run only by read-only wrappers
(`tools/noro_diag/per_host_dose_challenge.py`).

Statistics, in the order they are read:

1. `hosts_for_90pct` — the number of hosts holding 90% of the dose credited to
   `agent_pathogen_doses` over the voyage.
2. `dose_to_never_evaluated_hosts_gec` — dose credited to hosts for which
   `_dose_response_hazard` was never evaluated, and its share of the credited
   total, classified by the state that held at the crediting epochs
   (infected, immune/recovered, secretor-negative) and by the exit reason
   recorded at `_resolve_pathogen_challenge`.
3. The reconciliation chain, each term measured at its own seam: mass
   accumulated by `_accumulate` → dose credited after the route-efficiency
   multiplier → dose scaled by `susceptibility_multiplier` in
   `_merge_pathogen_doses` → dose read at `_resolve_pathogen_challenge` →
   effective dose passed to `_dose_response_hazard` → summed hazard.
4. Emesis witness counters: `draw_emesis_schedule` calls, scheduled episodes,
   `_emit_emesis` events, patch mass filed, patch-pickup sweeps that found a
   filed patch, sweeps whose filed unit matched a pickup unit, susceptible
   occupants at those matched units, and `_emesis_patch_pickup_one` deliveries.

Decision rules, fixed before execution:

- **Host-set mismatch is declared** only if `dose_to_never_evaluated_hosts_gec`
  exceeds 1% of the credited total in *both* seeds. Below that, the
  "different host sets" reading of the open finding is refuted and the
  divergence must be named as a quantity mismatch instead, at the specific
  seam where two adjacent terms of the chain disagree.
- **Concentration** is reported as measured; no threshold is attached to it,
  because `NORO-SUSCEPT-01`'s eight-host floor is an arithmetic consequence of
  its own recovered maximum and is not re-derived here.
- **The emesis pathway is declared to fire** only if a witness counter is
  non-zero at every link: schedule draw, emitted event, filed patch, matched
  pickup unit, and a delivered patch dose. A single witness in a single seed is
  sufficient for existence. Zero at a link in both seeds is a blocker claim at
  that link, and is entered as its own finding.
- Two seeds cannot bound a rate. No per-voyage rate, attack rate or secondary
  count is claimed from this measurement, and nothing here is fitted or
  selected: reported but not selected are `hosts_for_50pct`,
  `hosts_for_95pct`, `hosts_for_99pct`, the per-route dose split, the fomite
  transfer-chain terms, and the per-host hazard sums.

## Result

Pending; this entry is filled from the measured run.
