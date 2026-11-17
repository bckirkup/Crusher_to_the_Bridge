# NORO-HAND-CASCADE-01-CONTINUOUS-FLOW
**Date:** 2026-11-16
**Commit:** 2a7bc166
**Pathogens:** all
**Status:** open

## What changed

The intra-epoch hand-mediated contamination loop is no longer tied to the
legacy epoch-order/substep arm. `transmission.contamination_solver` now
defaults to `continuous`; `discrete` remains as the labelled baseline and
still selects the legacy/ordered fomite+food pathway, including
`intra_epoch_substeps` where configured.

The continuous arm is a staged-aggregate RK4 flow solve in
`engines/contamination_flow.py`: within one epoch, hand mass exchanges with
pooled surface and food reservoirs, surface mass returns to hands, food is
removed by ingestion, and hand-to-mouth contact removes dose continuously.
Epoch-once events stay outside the integrator: sanitary visit draws,
isolated-quarters deposits, sanitary exposure, emesis-patch pickup,
hand maintenance/emesis deposition, HVAC/direct/droplet pathways, and the
once-per-epoch infection challenge.

No epidemiological constant was added or refit. The solver reuses the
existing fomite/food contact, transfer, area, hygiene, growth, removal, and
mouth-contact kernels as constant per-hour rates for the epoch.

## Gates preserved

- `hand_redeposit_mode` still selects shedder-only vs carrier redeposition.
- Cabin-corridor confinement keeps the `off` blanket gate and the
  `own_cabin` compartment scope for deposits, pickups, and hand-to-mouth.
- Susceptibility/challengeability gates fomite dose booking; wash-reuptake
  reservoir mechanics are unchanged.
- Per-surface fomite (`transmission.per_surface`) falls back to the discrete
  pathway because the flow solver is pooled-aggregate only.

## Validation run locally

- `ruff check --select E,F,W,I,C901 --ignore E501,E741 --target-version py311 engines/contamination_flow.py engines/transmission_core.py tests/test_contamination_flow.py`
- `python3 -m pytest tests/test_contamination_flow.py tests/test_hand_redeposit_cascade.py tests/test_cabin_corridor_transmission.py -q --tb=short` — 66 passed
- `python3 -m pytest tests/test_emesis_source_term.py tests/test_emesis_localized_footprint.py tests/test_surface_strain_recovery.py tests/test_env_pool_strains.py tests/test_cabin_corridor_transmission.py tests/test_dining_party_topology.py tests/test_sanitary_structure_readout.py tests/test_shared_sanitary_zones.py tests/test_food_supply_01.py tests/test_common_source_events.py tests/test_fomite_hand_chain.py tests/test_food_hand_chain.py tests/test_transmission_pathways.py tests/test_dose_pathway_invariants.py tests/test_stool_event_hand_load.py -q --tb=short` — 437 passed

## Caveats / open items

- This is aggregate flow, not literal per-contact CE: contact kernels are
  held constant over the epoch and integrated, so it removes the
  epoch-boundary ordering and fixed-M refinement artifact without new
  geometry.
- Strain-reservoir updates for flow-written surface/food mass are
  proportional/decay approximations; per-strain deposit attribution is not
  reconstructed inside the integrator.
- Posted-cell norovirus evidence still says acquired route-ledger mass is
  dominated by `common_source_food`; this solver addresses the intra-epoch
  hand-process update and should be read as a solver/secondary-process fix,
  not as a posted-tail attack-rate repair by itself.
- No campaign array has been submitted. The next gate is local paired-seed
  witnesses before any campaign preflight.
