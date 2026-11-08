# CONTAM Phase 1 HVAC tracer campaign ledger

Status: design frozen locally; no AWS submission, no array submit, no pilot submit.

## Frozen inputs

- Manifest: `docs/proposals/contam_phase1_scope_manifest.md` (PR #1172), signed off by Benjamin.
- Panel: six hulls; lanes N/E primary, P baseline for the five committed-bundle hulls; Fletcher is N/E only.
- Matrix: 20 paired seeds x 12 one-hour epochs per hull x lane; tracer mass `1e6`, `natural_decay_rate=0`, `filter_efficiency=0.5`.
- Source pools: deterministic metadata-only selection materialized in `source_pools.json` and `design/phase1_hvac_tracer_design.json`.
- Cost pilot/canary: `missouri_bb63` lane E, 20 paired seeds, after the one-job `field_cache` block.

## Design decisions

- Namespace: `campaigns/contam/phase1_hvac_tracer_01/`, submitted only through `scripts/campaign`.
- Execution split: one `field_cache` array child solves the 11 E/P ContamX fields once; 340 trajectory children read that cache. This preserves the manifest's one-solve-per-hull/lane field generation while keeping one artifact per trajectory seed.
- Worker: `cell.py` reuses `tools/contam_fleet_compare.py` field generation and the shared `engines/py_contam_bridge.py` propagator for N/E/P. No `engines/` or `tools/` changes.
- Readout: `readout.py` checks coverage against `campaign.json`, aggregates retained fraction / `B_V` / concentration AUC / peak concentration, forms paired N-E and P-N seed contrasts, and evaluates the pilot gate when `field_cache.json` is supplied.

## Local validation log

- `python3 campaigns/contam/phase1_hvac_tracer_01/design/build.py --check` -> `OK design=contam_phase1_hvac_tracer_01 trajectories=340 array_children=341`.
- `scripts/campaign describe contam/phase1_hvac_tracer_01` -> 18 blocks: `field_cache` plus 17 trajectory blocks; readout wired to `readout.py`.
- Submit dry-runs only (`--dry-run --account 994254241749`, no AWS submit): `missouri_bb63_e` array size 20; `field_cache` array size 1.
- Local smoke: `destroyer_baseline_n` and `destroyer_baseline_e` seed 1 wrote `cell_1.json`; E used the commissioned-export inline solve.
- Local field-cache smoke: `field_cache` wrote 11 fields (6 E + 5 P); max field solve 0.282 s on `missouri_bb63:E`; `/usr/bin/time -v` peak RSS 54.6 MiB for the whole 11-field child.
- Cache-consumption smoke: `missouri_bb63` lane E seed 1 and `destroyer_baseline` lane P seed 1 read `field_cache.json` and wrote slim `cell_1.json` artifacts with `field_source=field_cache` and zero dropped/unknown/alias counts.
- Readout smoke: `scripts/campaign readout contam/phase1_hvac_tracer_01 -- /tmp/contam_cache_traj ...` produced coverage/metrics/path-flow/pilot sections.
- Targeted pytest: `tests/test_contam_phase1_hvac_tracer_campaign.py` -> 17 passed.
- Lint/guards: Ruff, `scripts/sonar_guard.py`, and `pre-commit run --files` passed on changed files.
- Full fast tier: `python3 -m pytest tests/ -m 'not slow' -n auto -q` -> 8329 passed, 6 skipped, 1 failed: only the known local CmdStan drift `tests/test_sentinel_wastewater.py::test_stan_and_numpy_agree_on_the_wastewater_channel`.
- `python3 tools/sanity_checker.py --from-config` -> validation passed with 2 pre-existing TAT warnings.

## Stop rule

Stop after the Missouri lane-E pilot/canary readout. The full panel requires Benjamin's explicit decision.
