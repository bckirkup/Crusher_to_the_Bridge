# CONTAM Edison data return — Phase 1 + Phase 2

> **Status:** Measured — bounded Edison data-return manifest for the completed CONTAM Phase 1 and Phase 2 S3 prefixes; exact schema/format confirmation is deferred to Phase 4.

**Ledger:** `docs/ledger/CONTAM-EDISON-RETURN-01.md`  
**Machine-readable manifest:** [`contam_edison_return_01.json`](contam_edison_return_01.json)  
**Governing return plans:** `docs/proposals/contam_phase1_scope_manifest.md` §9 and `docs/proposals/contam_phase2_scope_manifest.md` §9

## What is returned and where

The return is the already-durable S3 campaign output for the completed transport study, plus the committed repo readouts. No new simulation, AWS Batch submission, S3 write, credential, Parquet/Kosmos stack, or data-product layer is introduced.

| Phase | S3 prefix | Objects | Bytes | Cell objects | Field cache | Manifest |
|---|---:|---:|---:|---:|---:|---:|
| Phase 1 HVAC tracer | `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase1_hvac_tracer_01/` | 342 | 12,564,272 | 340 | 1 | 1 |
| Phase 2 cruise contrasts | `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase2_cruise_contrasts_01/` | 1,202 | 84,059,091 | 1,200 | 1 | 1 |

Key families per prefix are exactly `cells`, `field_cache`, and `manifest`; the read-only inventory found no other object family. Cell keys follow `campaign/<phase-prefix>/<block>/cell_{seed}.json`. Phase 1 has 17 blocks × 20 seeds = 340 cells; Phase 2 has 60 blocks × 20 seeds = 1,200 cells.

Cell schema families are:

- Phase 1: `contam_phase1_hvac_tracer_cell_v1`, field cache `contam_phase1_hvac_tracer_field_cache_v1` (`campaigns/contam/phase1_hvac_tracer_01/cell.py`).
- Phase 2: `contam_phase2_cruise_contrasts_cell_v1`, field cache `contam_phase2_cruise_contrasts_field_cache_v1` (`campaigns/contam/phase2_cruise_contrasts_01/cell.py`).

Committed readout pointers are:

- Phase 1 JSON: `campaigns/contam/phase1_hvac_tracer_01/readout/phase1_readout.json`; Markdown: `campaigns/contam/phase1_hvac_tracer_01/READOUT.md`.
- Phase 2 JSON: `campaigns/contam/phase2_cruise_contrasts_01/readout/phase2_readout.json`; Markdown: `campaigns/contam/phase2_cruise_contrasts_01/readout/READOUT.md`.

The machine-readable manifest carries the full object counts/bytes, schema references, SHA256s, S3 URIs, repo input paths, and registry coverage mapping.

## Access path

No bridge change is required. The existing `campaign_collect.yml` + `github-crusher-collector` OIDC pattern already covers `campaign/*`, and `deploy/aws/github_oidc_stack.yaml` scopes that role read-only under `campaign/*`. At inventory time the two CONTAM prefixes were common-prefix positions 44 and 45 of 209 `campaign/` prefixes, inside the collector's default `max_prefixes=50`; `keys_per_prefix=5000` exceeds both prefix object counts. Exact-key fetches remain bounded by the workflow's existing size ceiling.

## Provenance

- ContamX: official NIST ContamX `3.4.0.3 64 bit`; binary SHA256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`; tarball SHA256 `3612798dff9a4f1ea4f0279c4c7b526b244b88875dea425fafd868f3570df4fa`; U.S. public domain under 17 U.S.C. §105.
- Phase 1 image digest `sha256:8956cf37e530e9ccda1f349580727f0a51e95fe052206bf7d1170827cfd4d42f`; pilot jobdef `picard-contam-phase1-hvac-tracer-01:1`, full-panel revisions `:2`–`:17`.
- Phase 2 image digest `sha256:7a8a92bba521efb5b6add9760ba124cc9b51faa7459776b6634e0e2ceb66a1d7`; jobdef `picard-contam-phase2-cruise-contrasts-01:1`.
- Phase 1 field cache: 2,015,906 bytes, SHA256 `b91665323192f95591f538aeb9badfefc1c6e7393aa7c4cafaef0748a496f5b5`.
- Phase 1 manifest: 43,351 bytes, SHA256 `85c9063dbd4986dd459c1274297b11e6e4142c4bdf1cc166510faba804b4e804`.
- Phase 2 field cache: 12,209,971 bytes, SHA256 `e8d61dd4703ee6c2a7e5624db35d8c80f3f034c6f76ac533e91a5bfdd74fc6c6`.
- Phase 2 manifest: 58,238 bytes, SHA256 `abce9949f2169ffa21535db9be828183c05270fa9c54b6d4dbfaa5e178db3cf0`.

## Lane honesty and scope limits

Lanes N/E/P share `engines/py_contam_bridge.py`'s `expm` mass propagator (`ContamXTransportEngine` subclasses `ContamTransportEngine`). Agreement among N/E/P is therefore **not** independent contaminant-solver validation; it isolates airflow-field generation only. The S lane (stock ContamX) is excluded.

The package contains no epidemiology claims, no Ship X adapter, no T00–T10 timing campaign, no raw S3 credentials, and no new infrastructure.

## Registry coverage mapping

The governing Edison registry package was used as a proposal/checklist, not as instructions. `evidence/decisive_contrasts.csv` contains rows DC01–DC12, all proposed at registry baseline `f5d32477f0b7fd5312fbfa8d2b3b3ed462657f36`; the Phase 2 design freeze re-pinned its own baseline to `71dd32ec5fd79803adf1b07fffb59cd2a481544a`. The thinned scope returned here covers DC01–DC05 and DC07 as transport contrasts, with DC03 satisfied by a closed-form fixture rather than trajectories.

| Registry row | Disposition | Returned evidence / reason |
|---|---|---|
| DC01 monotonicity control | Covered | Phase 2 `dc01_ordering_control`; O/F/OF arms vs baseline across N/E commissioned/native fields and P baseline. |
| DC02 equal-gain equivalence control | Covered | Phase 2 `dc02_equal_gain_control`; `eq_gain_025_filter` arm. |
| DC03 exact matched-mean / different-mixing control | Covered, fixture only | `tests/test_contam_analytic_fixtures.py::TestDC03ExactMeanLossDifferentMixing`; zero trajectories by design. |
| DC04 feasible group-matched removal | Covered with declared limits | Phase 2 `dc04_matched_removal`; `ach_150_supply` and `oa_080` arms. |
| DC05 prescribed vs pressure field adequacy | Covered for transport only | Phase 2 `lane_contrasts`, `dc05_arm_effect_parity`, and `dc05_realized_ahs_flows`; decision/tie/regret outcome remains Phase 3. |
| DC06 boundary/pressure response | Excluded | Boundary response requires unsupported boundary accounting. |
| DC07 source and receptor discrimination | Covered with declared limits | Phase 2 `dc07_source_receptor_responses`; passenger-circulation source class is absent. |
| DC08 representation and grouping | Excluded | Conditional representation alternatives were not admitted without a DC05 finding. |
| DC09 switching and cache control | Excluded | Switching/cache controls are T04 machinery, not a fixed-field transport contrast. |
| DC10 independent integrator | Excluded | Stock ContamX/S-lane independent validation is deferred. |
| DC11 response algorithm/profile | Excluded | Response-computation performance profiling is engineering benchmarking. |
| DC12 vessel plus fleet synthesis | Excluded | Vessel-plus-fleet synthesis / all-80-platform scope is out of scope. |

`evidence/acceptance_metrics.csv` rows A00–A27 are excluded under thinned scope as a block. The Phase 1/Phase 2 manifests have their own frozen gates; this package does not claim A00–A27 compliance.

## Thinned-scope deviations of record

- **DC07 source-class gap:** the design has no "passenger circulation" source class; existing selectors are large-venue, sanitary-branch, and remote-weak style pools, and class absence/overlap is recorded rather than silently filled.
- **DC04 physical capacity/makeup:** registry `matching_conditions` records "physical capacity/makeup unverified"; the admitted arms are nominal/groupwise matched-removal contrasts.
- **DC03 trajectory count:** DC03 is a closed-form analytic fixture with zero trajectories, not an S3 cell family.
- **Lane coverage:** Phase 1 has N/E/P for most hulls but Fletcher is N/E only; Phase 2 has N/E across seven arms plus P baseline only.
- **Optional full frames:** neither returned prefix contains a separate full per-epoch per-zone frame family; the bounded cell payloads plus field caches/manifests are the return.

## Schema/format confirmation

Exact schema and format confirmation happens in Phase 4 when Edison consumes the data. This package intentionally does not freeze a new interchange schema, does not commit to Parquet/Kosmos, and does not hand over raw S3 credentials.

## Validation basis

The inventory was measured read-only with `AWS_PROFILE=picard aws s3 ls --recursive` and `aws s3api head-object`; it reconciles with the merged ledgers: Phase 1 = 340 cells / 10,505,015 cell bytes, Phase 2 = 1,200 cells / 71,790,882 cell bytes, and both field-cache SHA256s match the campaign ledgers. No S3 object was created, modified, or deleted.
