# OVERRIDE-FLAGS-01
**Date:** 2026-09-26
**Commit:** f242a055
**Pathogens:** all
**Status:** closed

Adds a compact `provenance_flags` block to every campaign run's
`summary.json`, so an archive can no longer read as exercising a mechanism
it silently dropped or never switched on. Three flag kinds, all computed
against what the run actually executed (the merged spec's overrides, the
merged config, the resolved pathogen profiles):

- **`active`** — every override leaf path the spec declared,
  `pathogen.<id>.<key>` and `cfg.<key>` prefixed. Which knobs the run moved
  is now in the artifact, not implied by the tier name.
- **`shadowed`** — override paths written to a slot a preferred key already
  resolves (currently: `innate_nonsusceptible_fraction` under a profile
  carrying `secretor_negative_fraction`, the NORO-SUSCEPT-04 defect).
  Written but never reached the engine.
- **`window`** — effective values outside the sourced interval their
  `Factor` table declares (`bounded_screen.py`; `norwalk_gi` → the noro
  box + expedition table). Emitted as `"<pathogen>.<factor>": [value, lo,
  hi]`. Out-of-window is not necessarily wrong — a deliberately extreme
  arm should flag — but the archive must say when a run stood on a value
  no source supports.
- **`gates_off`** — every inert feature gate in the merged config
  (`<block>.enabled: false`, or `mode`/`*_mode` set to `off`/`none`), plus
  three code-defaulted gates the structural walk cannot see
  (`transmission.blackwater_plumbing`,
  `observation.wastewater_assay_mode`, `observation.surface_swab_source`
  — engine `.get` defaults / selector keys the structural walk cannot
  see). An archive that claims a mechanism while its gate was off now
  says so.

Implementation: `sourced_window_flags.py::provenance_flags(spec, cfg,
profiles)`, emitted from `campaign_execution.run_simulation` into
`summary["provenance_flags"]`. Empty sub-keys are omitted; a clean run
carries only `active` (plus whichever gates are legitimately off).

## The default-off audit that prompted `gates_off`

Reviewed every `enabled:`/`mode:` gate in `crusher_labs/config.yaml` and the
code-defaulted gates in `engines/`:

| Gate | Shipped state | Verdict |
|------|---------------|---------|
| `crew_duty_exclusion.enabled` | false | Policy arm — "off in every production run" by design |
| `service_surface_knockout.enabled` | false | Ablation arm by design |
| `variant_surveillance.enabled` | false | Deliberate: off keeps legacy runs bit-identical; sentinel lineage features need it |
| `variant_surveillance.surface_sampling.enabled` | false | Operator dial, no anchor |
| `wastewater_surveillance.enabled` | false | Opt-in subsystem; `sentinel_ww_ops_scan_v1` sweeps it |
| `wastewater_surveillance.strain_deconvolution.enabled` | false | Requires variant_surveillance |
| `long_read_sequencing.enabled` | false | Escalation-only by design |
| `wearable_monitoring.detection_sensitivity_sweep.enabled` | false | Sweep harness, not a mechanism |
| `transmission.sanitary_visit_mode` | none | **Measured inert** — item 42: structure-only arm is a null at 500 seeds/cell without a flush term; correctly off pending that decision |
| `transmission.blackwater_plumbing` | false (code default) | **Flipped** — item 57: additive mechanism, measured; now defaults `true`, `false` is the labelled pre-change baseline |
| `observation.wastewater_assay_mode` | none (code default) | **Flipped** — defaults `holding_tank`; `none` is the labelled baseline. The assay draws on its own seeded instrument stream, so no dose/RNG golden moves; the observation record gains the post-discharge read |
| `observation.surface_swab_source` | airborne_fraction (code default) | **Flipped** — defaults `surface_pool_density` (the repaired channel, item 56); `airborne_fraction` is the labelled baseline. Swab outputs change to real deposited-pool densities — the intent; no dose/RNG touched |

**Finding:** the repo's default-off surface is almost entirely deliberate —
knockouts, sweep harnesses, and subsystems waiting on evidence — not
forgotten repairs. The exception class was `blackwater_plumbing` +
`wastewater_assay_mode` + `surface_swab_source`: measured mechanisms left
default-off. All three flipped to default-on, keeping their off spellings
as labelled pre-change baselines (`false` / `none` /
`airborne_fraction`). The observation record changes where the repaired
channels differ from the legacy ones — that is the intent; no dose or
engine-RNG stream is touched. The systemic guard
is `gates_off`:
from this change forward, every campaign archive lists its inert gates, so
"was this run actually running it?" is a readout question, not an audit.
