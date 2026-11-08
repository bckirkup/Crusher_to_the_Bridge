# CONTAM Phase 1 HVAC tracer campaign ledger

Status: design amended locally for Option A local field pre-staging; no AWS submission, no array submit, no pilot submit.

## Frozen inputs

- Manifest: `docs/proposals/contam_phase1_scope_manifest.md` (PR #1172), signed off by Benjamin.
- Amendment: Benjamin authorized Option A on 2026-11-08 — generate the 11 E/P ContamX fields locally, upload `field_cache.json` to S3, and run only trajectory cells on AWS Batch. The amendment is recorded in manifest §6.
- Panel: six hulls; lanes N/E primary, P baseline for the five committed-bundle hulls; Fletcher is N/E only.
- Matrix: 20 paired seeds x 12 one-hour epochs per hull x lane; tracer mass `1e6`, `natural_decay_rate=0`, `filter_efficiency=0.5`.
- Source pools: deterministic metadata-only selection materialized in `source_pools.json` and `design/phase1_hvac_tracer_design.json`.
- Cost pilot/canary: `missouri_bb63` lane E, 20 paired seeds, after the local field-cache pre-stage upload. There is no Batch `field_cache` block.

## Design decisions

- Namespace: `campaigns/contam/phase1_hvac_tracer_01/`, submitted only through `scripts/campaign`.
- Execution split (amended): no `field_cache` array child. `cell.py --mode field-cache` runs locally to write `field_cache.json` (schema `contam_phase1_hvac_tracer_field_cache_v1`, 11 fields: 6 E + 5 P; Fletcher is E only); the object is uploaded to `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase1_hvac_tracer_01/field_cache/field_cache.json`; all 340 trajectory children consume `--field-cache-uri`. This keeps one solve per hull/lane while removing ContamX from the Batch image.
- ContamX provenance: official NIST ContamX `3.4.0.3 64 bit`; binary `third_party/contamx/contamx3` (gitignored) SHA256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`; official tarball `contam-x-3.4.0.3-Linux-64bit.tar.gz` SHA256 `3612798dff9a4f1ea4f0279c4c7b526b244b88875dea425fafd868f3570df4fa` from `https://www.nist.gov/document/contam-x-3403-linux-64bittargz`; NIST Contam is U.S. public domain (17 U.S.C. §105) and the tarball is redistributable with notice. Amendment base repo SHA `e2eb71634851bb676806488a588cf5afce3e9bec`; Phase 2 must record the exact repo SHA used for field generation in the pilot ledger.
- Worker: `cell.py` reuses `tools/contam_fleet_compare.py` field generation and the shared `engines/py_contam_bridge.py` propagator for N/E/P. No `engines/` or `tools/` changes.
- Readout: `readout.py` checks coverage against `campaign.json`, aggregates retained fraction / `B_V` / concentration AUC / peak concentration, forms paired N-E and P-N seed contrasts, and evaluates the pilot gate when `field_cache.json` is supplied.

## Local validation log

- `python3 campaigns/contam/phase1_hvac_tracer_01/design/build.py --check` -> `OK design=contam_phase1_hvac_tracer_01 trajectories=340 array_children=340`.
- `PYTHONPATH=. python3 scripts/campaign describe contam/phase1_hvac_tracer_01` -> 17 trajectory blocks, 340 cells; no `field_cache` block; readout wired to `readout.py`.
- Submit dry-runs only (`--dry-run --account 994254241749`, no AWS submit): every one of the 17 trajectory blocks rendered `arrayProperties.size=20`; `missouri_bb63_e` array size 20.
- Targeted pytest: `.venv/bin/python -m pytest tests/test_contam_phase1_hvac_tracer_campaign.py -q` -> 16 passed.
- Lint/guards: Ruff, `scripts/sonar_guard.py`, and `pre-commit run --files` passed on changed files.
- Full fast tier: `.venv/bin/python -m pytest tests/ -m 'not slow' -n auto -q` -> `1 failed, 8333 passed, 6 skipped`; the only failure is the known local CmdStan drift `tests/test_sentinel_wastewater.py::test_stan_and_numpy_agree_on_the_wastewater_channel` (CI is the authority).
- `python3 tools/sanity_checker.py --from-config` -> validation passed with 2 pre-existing TAT warnings.
- `git diff --check` -> clean.

## Stop rule

Stop after the Missouri lane-E pilot/canary readout. The full panel requires Benjamin's explicit decision.
