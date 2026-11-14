# CS-WINDOW-ORDER-01
**Date:** 2026-11-14
**Commit:** e46742af
**Pathogens:** all
**Status:** measured
**Measured at:** 07106b7b

Defect/fix: `TransmissionCore._cs_window_tokens` returned a `set[str]` of meal
tokens. `_pathway_common_source` iterates those tokens and `_cs_window_step`
consumes the dedicated `_cs_rng` per `(zone, meal token, day)` window, so when a
dining zone had two meal tokens in one epoch the draw assignment depended on
`PYTHONHASHSEED`. The helper now returns `sorted(tokens)`; `_cs_served_windows`
already sorted voyage-level lot-plan tokens.

Measured: a pre-fix probe on `fl_exp_12d_sens_p06_paxv` seed 8038
`carriers_ordered` showed that forcing sorted token order made
`PYTHONHASHSEED=0` and `PYTHONHASHSEED=1` produce the same witness row and
reproduced the committed hash-1 artifact: infected 124, symptomatic 63, dose
302232.5893064003 GEC, delivered 10931565.497396061 GEC, deposited
6264823.076130032 GEC. That cell had 1152 `_cs_window_tokens` calls, 20
multi-token windows, and max 2 tokens. Post-fix verification at `07106b7b`
under `PYTHONHASHSEED=0` and `PYTHONHASHSEED=1` produced identical rows and
matched the reference artifact exactly on the same fields.

Audit: checked runtime-path string-set returns/iterations in
`engines/transmission_core.py`, `engines/infection_dynamics_bridge.py`,
`engines/crew_duty_exclusion.py`, `engines/strain_state.py`,
`engines/strain_dose_ledger.py`, `engines/scenario_schedule.py`,
`engines/rhythm_layer.py`, `picard_framework/simulation/ship_simulation.py`,
`picard_framework/simulation/action_applier.py`, and `engines/hazard_sources.py`.
Dispositions: service/food-employee zone sets, crew cohort zones, closed venue
ids, SOP/protocol forced-id sets, strain live-id sets, hazard known-profile
ids, and rhythm venue indexes are membership-only, int-keyed, already sorted at
use, or built from stable list/dict order; no other RNG-consuming string-set
iteration was found in this pass.

Inferred: uncontrolled-`PYTHONHASHSEED` witness rows that exercised
multi-token common-source windows are not stable; in particular the seed-8038
DS-M pilot rows and any random-hash witness comparisons should be re-run under
fixed hash or the fixed engine before reuse. Hypothesis: if another
hash-sensitive witness appears, look first for a string set/frozenset iterated
before an RNG draw or float accumulation; this audit was targeted, not a proof
of completeness.
