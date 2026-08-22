---
name: picard-ship-simulation
description: Run and develop Picard_Framework ship-level steppable simulations. Use after modifying picard_framework/, ShipSimulation, PicardRunSpec, or orchestrator integration.
---

# Picard Ship Simulation

## Prerequisites

- Python 3.11+, repo root on `PYTHONPATH`
- `pip install --only-binary=:all: --require-hashes -r requirements.lock.txt` (or `requirements.txt` for editable local work)

## Quick commands

```bash
# Legacy CLI (uses Picard ShipSimulation internally)
python3 tools/sanity_checker.py --from-config
python3 orchestrator.py --epochs 24

# Programmatic steppable API
python3 -c "
from picard_framework import PicardRunSpec, ShipSimulation
spec = PicardRunSpec.from_legacy_yaml('.')
sim = ShipSimulation(spec, display=False)
sim.run(n_epochs=2)
sim.finalize(display=False)
"

# Picard run spec JSON
python3 -c "
from picard_framework import PicardRunSpec, ShipSimulation
spec = PicardRunSpec.from_picard_json('.', 'picard_framework/runs/smoke_2epoch.json')
ShipSimulation(spec).run()
"
```

## Layout

| Path | Role |
|------|------|
| `picard_framework/run_spec.py` | Immutable `PicardRunSpec` |
| `picard_framework/catalog/` | Platform/pathogen library index |
| `picard_framework/simulation/ship_simulation.py` | `ShipSimulation.step()` orchestrates `_begin_epoch` plus `_step_*` phases on `_EpochWork` (split Stackelberg when `social` enabled) |
| `picard_framework/simulation/action_applier.py` | Maps `ActionEnvelope` → `SimulationState` via `_ACTION_HANDLERS` / `_NEEDS_CTX` |
| `picard_framework/runs/*.json` | Ship run specifications |
| `data/` | Shared platform, pathogen, protocol libraries |

## Transmission / behavior knobs (`crusher_labs/config.yaml`)

| Block | Role |
|-------|------|
| `transmission.contact_mode` | `density_dependent` (default), `legacy`, or opt-in `heterogeneous_zone_dose` — see `docs/density_contact_spec.md` |
| `agent_behavior` | Dining/free rotation probabilities (default `0.0` for golden stability) — see `docs/multi_pathogen_model_changes_spec.md` |

Pathogen profiles may include `transmission_route_weights`, formal `dose_adjustment`
(log10 shedding offset), `innate_nonsusceptible_fraction`, and zone-scoped
`environmental_contamination.source_zones`.

## Emitting a sentinel observation bundle from a real run

The sentinel ledger (and therefore the wastewater channel) is only armed when
`run.sentinel_line_list` is set; the wastewater sampler is armed only when that
ledger exists *and* `wastewater_surveillance.enabled` is true
(`ship_simulation._init_sentinel_ledger` / `_init_wastewater_ops`).

- The output path **must live inside the repo tree** — `write_json`/`safe_path`
  silently refuses `/tmp/...` and the run then finishes with no bundle and no
  traceback in the tail of the log. Use e.g. `telemetry_buffer/<name>.json`.
- Strain-resolved channels (clinical typing, wastewater lineage deconvolution)
  need `variant_surveillance.enabled: true`; without it `tx_core.strain_registry`
  is `None` and the channel reports `no_composition`/`not_configured`.
- Genotype diversity comes from founder minting per seeded infection
  (`transmission_core._resident_strain_id`), so raise
  `pathogen_overrides.<pathogen>.initial_infected` (e.g. 12) to get a tank with
  more than one lineage; `founder_strains_per_pathogen` alone does not.
- `destroyer_baseline` + 72 epochs runs in ~1 s, which makes seeded outbreak
  end-to-end checks cheap.

```bash
# 72-epoch amplicon wastewater run with lineage deconvolution
cat > /tmp/spec.json <<'JSON'
{"schema_version":"1.0.0",
 "catalog":{"platform_id":"destroyer_baseline","pathogen_bundle_id":"active_profiles"},
 "run":{"random_seed":7,"num_epochs":72,"write_ground_truth":false,
        "history_retention":"compact",
        "sentinel_line_list":"telemetry_buffer/ww/amplicon_on.json"},
 "legacy_yaml":"crusher_labs/config.yaml",
 "pathogen_overrides":{"norwalk_gi":{"initial_infected":12}},
 "config_overrides":{
   "variant_surveillance":{"enabled":true},
   "wastewater_surveillance":{"enabled":true,"assay_mode":"amplicon",
     "sampling_interval_epochs":6,"pathogen":"norovirus","pathogen_id":"norwalk_gi",
     "strain_deconvolution":{"enabled":true}}},
 "actors":[],"incentives":{}}
JSON
mkdir -p telemetry_buffer/ww
PYTHONPATH=. python3 -c "
from picard_framework import PicardRunSpec, ShipSimulation
spec = PicardRunSpec.from_picard_json('.', '/tmp/spec.json')
sim = ShipSimulation(spec, display=False); sim.run(); sim.finalize(display=False)"
check-jsonschema --schemafile schemas/sentinel_observations.schema.json \
  telemetry_buffer/ww/amplicon_on.json
```

Useful invariants when grading such a bundle: for every wastewater row
`sum(lineage_calls[].reads) + lineage_unresolved_reads == pathogen_reads`, called
genotypes are a subset of the live `tx_core.strain_registry` genotypes, `qpcr`
and `metagenomic` rows carry no lineage fields at all, and `bundle_from_dict`
rejects a row whose lineage reads exceed `pathogen_reads` (the JSON schema does
not encode that bound — the parser is the only guard).

For a base-vs-branch regression on the same seed, use
`git worktree add /tmp/<base> <base-branch>` and diff the emitted bundles field
by field; a stepped run (`sim.step()` in a loop) lets you recompute ground truth
per epoch for cross-checks.

## Validation

```bash
python3 tools/sanity_checker.py --from-config
python3 -m pytest tests/test_picard_framework.py tests/test_golden_orchestrator.py \
  tests/test_golden_picard.py tests/test_ship_epoch_helpers.py \
  tests/test_shedding_variance_cabin_mates.py tests/test_action_applier.py \
  tests/test_density_contact.py tests/test_multi_pathogen_model_phase_a.py \
  tests/test_multi_pathogen_model_phase_b.py -v
```

Epoch **semantic** order: [docs/simulation_step_order.md](../../../docs/simulation_step_order.md).
Do not reorder phases when extracting; golden Picard is the behavior lock.
`tests/test_ship_epoch_helpers.py` grades `_merge_applied` and belief
clamping. Unknown action kinds and `_NEEDS_CTX` kinds with `ctx is None`
are no-ops.
