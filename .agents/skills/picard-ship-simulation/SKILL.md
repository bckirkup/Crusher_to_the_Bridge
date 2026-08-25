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

## Clock modes: hours vs legacy_epoch_day

`engines/sim_clock.py` is the only place epoch counters become day-valued
pathogen parameters. `ShipSimulation.initialize()` builds one `SimClock` and
hands the *same object* to the engine, agents, observation engine and the
instrument-turnaround registry — `sim.clock is sim.engine.clock is
sim.engine.agents[i].clock` is a cheap way to catch a second opinion about epoch
length. Note `sim.clock` only exists after `initialize()`.

Flip the mode with `config_overrides.natural_history_clock`
(`"hours"` default, `"legacy_epoch_day"` control arm) and the epoch length with
`epoch_duration_hours` (must agree between the top level and the `voyage` block,
or `SimClock.for_run` raises). Shipped platform voyage configs use 1 h/epoch, so
a norovirus case incubates ~24-29 epochs and clears at ~72 epochs; budget
`num_epochs >= 168` for any run that must observe recovery. In
`legacy_epoch_day` the same run collapses to onset in 1-2 epochs and recovery at
3 — the old-behaviour control. Physical `delay_hours` in
`data/config/instrument_turnaround.json` are read on that arm's day-long epoch
(`SimClock.hours_per_epoch` is 24 in legacy mode whatever the voyage grid says),
so a 72 h microbiology TAT is 3 legacy epochs, matching pre-clock behaviour.

Fast ways to grade timing without a long voyage:
- `InstrumentTurnaroundRegistry.load('data/config/instrument_turnaround.json',
  clock=SimClock(h, "hours")).delay_epochs_for(name)` — physical hours should
  scale inversely with `h`. `full_run_hours` outranks a profile's grid-native
  `epoch_fraction` (every shipped fraction was written against the day-per-epoch
  grid); a TAT that is still clock-insensitive means the block declares only
  `epoch_fraction` or `delay_epochs`.
- `orchestrator_epoch.step_mid_cruise_introductions` converts a profile's
  `initial_time_infected` (days) through the clock: 2 days -> 48 epochs at
  1 h/epoch, 2 at legacy.
- The sentinel line list (`run.sentinel_line_list`) records `onset_epoch` /
  `report_epoch` in epochs and echoes `epoch_duration_hours`, which is the
  cheapest end-to-end evidence that natural history moved to the physical clock.
- `python3 scripts/clock_guard.py <files>` / `--configs` is the mechanical
  guard; it recognises names like `time_infected`, `days_post_infection`,
  `*_day`, so aliased comparisons can slip past it.

## Auditing immune memory / re-infection at runtime

Protection is applied as a hazard multiplier: `inf_prob *= 1 - protection` in
`TransmissionCore` (dose-response loop). So a `refractory_protection` of 0.98
is *not* sterilising — it leaves 2 % of the per-epoch hazard, which at the
Paper 1 operating point (450 agents, `dose_adjustment` 10.6, hourly epochs)
still produces a handful of homologous, zero-escape re-infections inside the
refractory window. That is arithmetic, not escape: only
`refractory_protection: 1.0` yields zero, which is why every shipped bundle
declares it and a test asserts it. Read any within-window value below 1.0 as a
per-hour hazard, never as a percentage of protection.

For a control arm, monkeypatch `ImmuneWaningConfig.protection_at` to return the
matched protection at any age *before* constructing `ShipSimulation` — the
config objects are built at `initialize()`, and this keeps every other draw on
the same RNG stream, so arms are comparable seed-by-seed.

Watch out when probing the strain layer directly:
- `StrainRegistry` is empty until the first `sim.step()` mints founders, so pick
  a challenge strain after stepping, not right after `initialize()`.
- `TransmissionCore._strain_doses[agent_id][pathogen_id]` is keyed by
  `(strain_id, source)` tuples, not bare strain ids.
- `StrainEvolutionConfig.from_profile(profile)` takes the whole profile dict.
- Mutated escape phenotypes are rare in a 200-epoch run: every circulating
  strain can still carry `immune_escape == 0.0`, so an "escape breaches the
  window" hypothesis has to be exercised by evaluating the kernel directly
  (`immune_waning.protection_at(matched, days, escape)`) rather than by hoping
  the run produces one.
- Immune records are written only when a lineage clears
  (`orchestrator_epoch._record_cleared_immunity`), so hosts still infected at
  the end of the run legitimately have no `origin == "infection"` record; count
  them against the still-active set before calling it lost memory.

Legacy-vs-record agreement is the cheap regression check for the agent-level
projection: per epoch, compare `agent.infection_status` / `illness_status`
counts against `agent.infections[pid]["status"] / ["illness"]`. They should be
equal except for record-less hosts (the fixed-day fallback still owns those),
so a persistent difference larger than the record-less population means the
summary channel has drifted from the records again.

### Protection is a dose-share-weighted mean, so every share has to be accounted

`TransmissionCore._challenge_protection` averages protection over the strains challenging the host,
weighted by their dose shares. Dose carrying no strain label (`"unresolved"`, the sub-floor tail of
a pool) is in that denominator too: it earns the genotype-blind refractory window (via
`_nonspecific_protection`) and nothing from the matched `cross_immunity` matrix, so past the window
it is unprotected dose. Before that rule existed, a fresh homologous in-window record returned
`1 - unattributed_dose_fraction` — ~0.999, just under the `if protection >= 1.0: continue`
short-circuit, i.e. ~0.1 %/epoch of residual hazard, enough for "impossible" homologous
within-window re-infections over a couple of hundred epochs at high dose. The lesson generalises:
any new dose bin added to that mean needs an explicit protection value, or it silently leaks.

Do not diagnose such events by evaluating `_challenge_protection` after the epoch: `_strain_doses`
is rebuilt each epoch, so a post-hoc call returns 1.0 and hides the cause. Instead monkeypatch the
method for the run and log `self._strain_doses[agent_id][pathogen_id]` at the call, together with
`_prior_exposures` (its ages are `None` while the lineage is still resident, numeric once a record
exists — a useful marker of the resolution epoch).

### Forcing (and auditing) the VSP reported-case confinement counter

The VSP rule is no longer the engine's internal instantaneous-prevalence check:
`orchestrator_init.build_engine` passes `vsp_isolation=False`, so
`KorkinShipEngine._check_vsp_trigger` never sets `vsp_triggered`; that engine
attribute is not emitted as run telemetry because it can never be true there.
All confinement comes from the counter path
(`orchestrator_epoch.step_counter_thresholds` → `confine_agents`) driven by
`crusher_labs/config.yaml` counter `passenger_reported_case_rate`
(metric `reported_case_rate`, threshold 0.03, `on_exceed: confine_symptomatic`).
Audit the counter with `derived.vsp_trigger_epoch` /
`passenger_reported_case_rate_exceeded`, not with `vsp_triggered`.

A cheap way to make the rule fire in a real full-length run (~40 s, 450 agents,
168 hourly epochs) is to generate a spec from the calibration manifest tier and
run it single:

```bash
python3 - <<'PY'
import json, picard_framework.runs.mega_cruise_campaign.campaign_runner as cr
m = json.load(open("picard_framework/runs/mega_cruise_campaign/"
                   "clock_arm_c1_v1_manifest.json"))
runs = dict(cr.generate_tier_runs(m, "c1_expedition_cruise_450",
                                  natural_history_clock="hours"))
json.dump(runs["c1_norovirus_expedition_cruise_450_dose8_init5_syndromic_s700"],
          open("telemetry_buffer/vsp_probe/syndromic.json", "w"), indent=1)
PY
python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py \
  --single telemetry_buffer/vsp_probe/syndromic.json telemetry_buffer/vsp_probe/out
```

`dose_adjustment 8.0` + `initial_infected 5` on `expedition_cruise_450` crosses
3 % reported passenger cases around epoch 100 (seed 700 → 101).
Artifacts land in `<out>/<run_id>.zip` and `<out>/_shard_runs/single/<run_id>/`
(`/tmp` is refused by `paths.py`).

Caveats worth re-checking whenever this area changes:

- The counter *firing* and the quarantine curve *rising* are different claims.
  SOP-008/011 already confine every symptomatic agent, so `confine_agents` from
  the counter usually adds ~0 agents. Prove causality with a control run using
  `config_overrides.ship_graph.counter_confinement_enabled = false` (same seed):
  if the quarantine trajectory is unchanged, the counter had no effect. Each
  exceeded counter now reports how many agents its action newly confined, via
  the timeseries field `passenger_reported_case_rate_newly_confined`; it is
  usually 0 for exactly this reason.
- `cumulative_reported_cases` counts only agents that sick-called *while*
  symptomatic. Syndromic `_process_symptomatic_agent` treats
  `compliance == non_compliant` agents as reporters, so `true_positive_ids`
  still contains susceptible/immune asymptomatic refusers;
  `update_ever_reported_ids` intersects it with the symptomatic roster, which is
  what keeps `cumulative_reported_cases <= cumulative_ever_ill`.
- The `none_true` surveillance arm is report-free: chronic-disease
  `sick_call_probability_boost` (up to 0.30 from
  `data/config/chronic_diseases.json`) no longer bypasses
  `syndromic.sick_call_probability = 0.0`, so no reported cases accumulate and
  `derived.vsp_trigger_epoch` stays null.
- `derived.reported_case_attack_rate_passenger` / `ever_ill_attack_rate_passenger` are
  *passenger-complement* rates (final `reported_case_rate_passenger` /
  `ever_ill_rate_passenger`), not counts over `num_agents`.
