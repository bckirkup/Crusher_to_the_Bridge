# Test plan — sr* secretor-axis repair (branch devin/1790420103-secretor-axis-repair)

Change under test: `_iter_synthetic_recovery_runs` in
`picard_framework/runs/mega_cruise_campaign/campaign_runner.py` now resolves
`secretor_negative_fraction` / `secretor_negative_relative_susceptibility`
per run (vector → arm overrides → bundle profile → 0.0), pins them into
`pathogen_overrides`, records them in `campaign_parameters`, and refuses the
withdrawn spellings `non_susceptible` / `innate_nonsusceptible_fraction`.
Previously it wrote `innate_nonsusceptible_fraction`, which the engine's
`_resolve_secretor_status` (orchestrator_init.py ~1778) silently shadows when
`secretor_negative_fraction` is present — and the `active_profiles` bundle's
`norwalk_gi` profile already declares `secretor_negative_fraction: 0.2`,
`secretor_negative_relative_susceptibility: 0.2`. So the old spec wrote an
axis that never reached the engine.

Critical adversarial note: because the bundle profile already carries the
SAME values (0.2/0.2), a run showing ~20% of agents with multiplier 0.2 does
NOT by itself prove the pin works — the profile alone produces that. The
discriminator is the contrast run in Test 3 where the vector pins 0.0: if
pinning works the merged profile shows 0.0 and ~0% of hosts are drawn; if
shadowing still existed the profile's 0.2 would leak through and ~20% would
be drawn.

Harness: single python3 script run under `source .venv/bin/activate` with
`PYTHONPATH=.`, run from repo root. Spec JSONs and run artifacts go under
`telemetry_buffer/secretor_axis_check/` (repo-local; `simulation_utils.paths`
refuses world-writable dirs).

## Test 1 — sr1_ridge spec carries the pinned axis, not the withdrawn alias

Steps: load `synthetic_recovery_v1_manifest.json`, call
`generate_tier_runs(manifest, "sr1_ridge", epochs_override=2)`, take first
spec.

Pass criteria (all must hold):
- `spec["pathogen_overrides"]["norwalk_gi"]["secretor_negative_fraction"] == 0.2`
- `spec["pathogen_overrides"]["norwalk_gi"]["secretor_negative_relative_susceptibility"] == 0.2`
- `spec["pathogen_overrides"]["norwalk_gi"]["dose_adjustment"] == 9.5`
- `"innate_nonsusceptible_fraction"` absent from the `norwalk_gi` override dict
- `spec["campaign_parameters"]["secretor_negative_fraction"] == 0.2` and
  `spec["campaign_parameters"]["secretor_negative_relative_susceptibility"] == 0.2`
- `"non_susceptible"` absent from `campaign_parameters`

Broken-change signature: old code would show `innate_nonsusceptible_fraction`
in the override and `non_susceptible` in parameters instead.

## Test 2 — real engine run applies the mechanism to ~20% of hosts

Steps: write spec to JSON, `PicardRunSpec.from_picard_json` +
`ShipSimulation(picard_spec)` + `sim.run()` (epochs=2, platform default
agents). Wrap `orchestrator_init._resolve_secretor_status` to record calls.
Post-run inspect `sim.engine.agents`.

Pass criteria:
- `_resolve_secretor_status` was called for the `norwalk_gi` profile and the
  merged `sim.pathogen_profiles["norwalk_gi"]` shows fraction=0.2, rel_susc=0.2
- count of agents with `secretor_negative_by_pathogen["norwalk_gi"] is True`
  equals count with `susceptibility_multiplier["norwalk_gi"] ≈ 0.2`, and the
  drawn share is in [0.10, 0.30] of N (binomial around p=0.2; at N≈450-550
  sd≈0.019, so ±3sd ⊂ [0.14,0.26] — the [0.10,0.30] band is generous)
- sim completes (result.num_epochs == 2) — proves the spec executes through
  the real run path, not just init

Broken-change signatures: 0 drawn (axis never reached engine), ~100% drawn or
multiplier≠1.0 on undrawn hosts (rel_susc applied globally).

## Test 3 — pinned vector value overrides bundle profile (shadowing check)

Steps: deep-copy manifest; set sr1_ridge `parameter_vectors[0]`
`secretor_negative_fraction = 0.0` (keep rel_susc 0.2); generate first spec;
assert `pathogen_overrides.norwalk_gi.secretor_negative_fraction == 0.0` is
PINNED (not dropped — 0.0 is a declared grid point); run it the same way.

Pass criteria:
- spec override pins 0.0
- merged `sim.pathogen_profiles["norwalk_gi"]["secretor_negative_fraction"] == 0.0`
- 0 agents drawn / all multipliers == 1.0

Broken-change signature: ~20% drawn would mean the profile's 0.2 leaked
through (the pin is not reaching the merged profile — same failure mode the
fix claims to repair).

## Test 4 — withdrawn spellings refused; dist/interval draw is seeded and bounded

Steps (cheap, same harness):
a) manifest copy with `"non_susceptible": 0.15` added to vector →
   `next(generate_tier_runs(...))` must raise `ValueError` (match "withdrawn").
b) same with `"innate_nonsusceptible_fraction": 0.15` → `ValueError`.
c) manifest copy with `secretor_negative_fraction` replaced by
   `{"dist": "uniform", "interval": [0.04, 0.83]}` → two generated specs for
   the same seed must pin the identical value, inside [0.04, 0.83], and
   != 0.2 boundary evidence optional. A second seed must give a different
   draw (with overwhelming probability; assert in-range + deterministic
   equality per seed).

Pass criteria: both ValueErrors raised with the withdrawn-key message;
dist draw in [0.04, 0.83], deterministic for fixed seed.
