# CONTAM Phase 1 HVAC tracer campaign ledger

Status: Phase 1 panel complete — Option A field pre-stage, `missouri_bb63_e` pilot, and all 340 trajectories executed on AWS Batch; readout coverage 340/340; Phase 3 decision remains Benjamin's.

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

## Phase 2 pilot execution (2026-11-08)

- Field cache: 11 fields (schema `contam_phase1_hvac_tracer_field_cache_v1`), 2,015,906 bytes, SHA256 `b91665323192f95591f538aeb9badfefc1c6e7393aa7c4cafaef0748a496f5b5`, uploaded to `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase1_hvac_tracer_01/field_cache/field_cache.json`; generated at repo SHA `a3dab46fcf50ee4c51b5962d9139c27a3f76e0f3` with NIST ContamX `3.4.0.3 64 bit` binary SHA256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`. Design manifest mirrored byte-identically to `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase1_hvac_tracer_01/manifest.json`.
- Image/jobdef: `picard-campaign:contam-phase1-hvac-tracer-01@sha256:8956cf37e530e9ccda1f349580727f0a51e95fe052206bf7d1170827cfd4d42f` built from root `Dockerfile` + `deploy/aws/Dockerfile.campaign` at `a3dab46f`; jobdef `picard-contam-phase1-hvac-tracer-01:1`; `campaign.json` and `design/build.py` now pin that digest so later submits stay digest-pinned.
- Batch pilot: job `3d8d615c-b35d-4a23-a96b-b2f384c12345` (`picard-contam-phase1-hvac-tracer-01-missouri_bb63_e-20261108-155628`), array size 20 -> SUCCEEDED 20/20; artifacts at `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase1_hvac_tracer_01/missouri_bb63_e/cell_{1..20}.json`.
- Readout: `readout.py` pilot gate `go=True`; all frozen §7 thresholds pass (E field solve 0.240678 s, trajectory p95 2.597248 s, array wall-clock 2.199567 min, CPU 0.0131034 CPU-h, peak RSS 100.894531 MiB, artifacts 892,670 bytes, audit counts 0). Conservative full-panel extrapolation is 3.343x size-proportional / 9.052x conservative vs pilot, both ≤12x. Full entry: `docs/ledger/CONTAM-PHASE1-PILOT-01.md`.
- Phase 2 validation: `design/build.py --check` OK; `scripts/campaign describe` still 17 blocks / 340 cells; targeted pytest `tests/test_contam_phase1_hvac_tracer_campaign.py` 16 passed; Ruff and `scripts/sonar_guard.py` on `design/build.py` passed.

## Phase 3 full-panel execution (2026-11-08)

- Authorization: Benjamin's "go ahead" after the `CONTAM-PHASE1-PILOT-01` GO; no other blocks were submitted before that message.
- Submit: 16 non-pilot trajectory blocks via `scripts/campaign submit` on merged `main` `801ea44c`; jobdef revisions `picard-contam-phase1-hvac-tracer-01:2`–`:17`, same image digest `sha256:8956cf37e530e9ccda1f349580727f0a51e95fe052206bf7d1170827cfd4d42f`; per-block parent job IDs and wall-clocks are tabulated in `docs/ledger/CONTAM-PHASE1-FULL-01.md`.
- Result: all 16 arrays SUCCEEDED 20/20 (320/320 cells); with the pilot, coverage is 340/340. Full-panel remaining wall-clock 3.842567 min; per-array 2.925783–3.500983 min.
- Readout/cost: `readout.py` coverage 340/340, missing 0, pilot gate `go=True`, no `BLOCKED_ENGINE_FALLBACK`, audit counts 0; trajectory p95 2.454948 s, peak RSS 100.894531 MiB, artifacts 10,505,015 bytes, trajectory CPU-hours 0.141446. Full entry: `docs/ledger/CONTAM-PHASE1-FULL-01.md`.

## Stop rule

Phase 1 panel is complete. Coupled epidemiology and Edison data-return packaging remain separate Phase 3+ decisions.
