# Proposals

> **Status:** Proposed. **Nothing in this directory describes current
> behaviour.**

A document lives here until the artifact it specifies exists in-tree; then it
moves to its subject directory or to the `docs/` root. Do not cite these as
documentation of what the model does.

| Doc | What is missing | Evidence |
|-----|-----------------|----------|
| [covid_trajectory_fit_spec.md](covid_trajectory_fit_spec.md) | All of it — the observation layer, the scenarios, and the re-sourced respiratory emission scale it depends on | The train/test split (Diamond Princess to fit; Greg Mortimer and the Willebrand 2022 104-voyage distribution held out) is fixed here *before* implementation, so it cannot be chosen after seeing which hull fits. Prerequisites are listed in its §7; none are done |
| [bounded_sensitivity_and_admissible_region_spec.md](bounded_sensitivity_and_admissible_region_spec.md) | The screen itself — `telemetry_buffer/observation_model/bounded_screen.py` does not exist — and the influenza and SARS-CoV-2 interval ledgers | The norovirus interval ledger in its §3 is written: transform, interval, evidence grade and basis per factor, and §3.3 withdraws the standing 0.0 → 0.2 FUT2 target. §4 is explicitly blocked on task #30, the SARS-CoV-2 emission/β re-sourcing, and says so rather than guessing the box |
| [acceptance_tests.md](acceptance_tests.md) | The tests themselves | The seams it targets exist (`engines/transmission_core.py`, `orchestrator_epoch.py`, `engines/infection_dynamics_bridge.py`, `engines/sim_clock.py`), but no `tests/test_acceptance_*.py` or CEX/EIC/SHD-named test file exists. The document says some tests are expected to fail until the formal within-host spec is implemented |
| [sentinel_stan_fix_spec.md](sentinel_stan_fix_spec.md) | Three of four fixes, and the target model | It prescribes four edits to `sentinel_attribution.stan`. Only the wastewater likelihood landed, and in `stan/sentinel_fleet.stan` — the single-ship model it targets still carries port and onboard hazard terms only |
| [wastewater_mode_switch_spec.md](wastewater_mode_switch_spec.md) | Modes 1 and 2 as specified | Modes 3 and 4 are self-labelled EXISTING and are present. The `wastewater_qpcr.py` and `wastewater_hydraulics.py` it names do not exist; the holding-tank convolution instead lives in `sentinel/wastewater_ops.py`. Amplicon is deferred to the genomics phase by the doc itself. Stale-but-not-wrong: the capability arrived in a different shape |
| `pre_establishment_clearance_params.json` | The pre-establishment clearance model | Parameter set with no consumer in-tree. See [`../history/migration_feasibility.md`](../history/migration_feasibility.md), which found the proposed `challenge()` API is not a drop-in replacement as written |
