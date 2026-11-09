# CONTAM-EDISON-RETURN-01
**Date:** 2026-11-08
**Commit:** 1c059625bb750dfff9f26599ecb2e5d4207d9fc5
**Pathogens:** all
**Status:** measured
**Measured at:** 1c059625bb750dfff9f26599ecb2e5d4207d9fc5

Bounded Edison data-return package for the completed CONTAM transport study.
This entry records a read-only S3 inventory and the repo return artifacts; it
authorizes no new simulation, AWS Batch submission, S3 write, credential handoff,
Parquet/Kosmos stack, epidemiology claim, Ship X adapter, or Phase 3 work.

## Return inventory

Measured with `AWS_PROFILE=picard` using read-only `aws s3 ls --recursive` and
`aws s3api head-object`:

| Prefix | Objects | Bytes | Cells | Cell bytes | Field cache bytes / SHA256 | Manifest bytes / SHA256 |
|---|---:|---:|---:|---:|---|---|
| `campaign/contam_phase1_hvac_tracer_01/` | 342 | 12,564,272 | 340 | 10,505,015 | 2,015,906 / `b91665323192f95591f538aeb9badfefc1c6e7393aa7c4cafaef0748a496f5b5` | 43,351 / `85c9063dbd4986dd459c1274297b11e6e4142c4bdf1cc166510faba804b4e804` |
| `campaign/contam_phase2_cruise_contrasts_01/` | 1,202 | 84,059,091 | 1,200 | 71,790,882 | 12,209,971 / `e8d61dd4703ee6c2a7e5624db35d8c80f3f034c6f76ac533e91a5bfdd74fc6c6` | 58,238 / `abce9949f2169ffa21535db9be828183c05270fa9c54b6d4dbfaa5e178db3cf0` |

Both prefixes contain only the `cells`, `field_cache`, and `manifest` key
families. Phase 1 cells reconcile with `CONTAM-PHASE1-FULL-01` (340/340); Phase 2
cells reconcile with `CONTAM-PHASE2-FULL-01` (1,200/1,200). Cell schema families
are `contam_phase1_hvac_tracer_cell_v1` /
`contam_phase1_hvac_tracer_field_cache_v1` and
`contam_phase2_cruise_contrasts_cell_v1` /
`contam_phase2_cruise_contrasts_field_cache_v1`.

## Return artifacts

- Machine-readable manifest: `docs/contam_edison_return_01.json`.
- Human-readable return doc: `docs/contam_edison_return_01.md`, registered in
  `docs/README.md`.
- Committed readouts remain at
  `campaigns/contam/phase1_hvac_tracer_01/readout/phase1_readout.json` +
  `campaigns/contam/phase1_hvac_tracer_01/READOUT.md` and
  `campaigns/contam/phase2_cruise_contrasts_01/readout/phase2_readout.json` +
  `campaigns/contam/phase2_cruise_contrasts_01/readout/READOUT.md`.

## Registry coverage

The Edison `decisive_contrasts.csv` rows DC01–DC12 are mapped exactly once in
the return doc/manifest: DC01–DC05 and DC07 are covered as thinned transport
contrasts, with DC03 as a closed-form fixture and declared DC04/DC07 limits;
DC06, DC08, DC09, DC10, DC11, and DC12 are excluded. `acceptance_metrics.csv`
rows A00–A27 are excluded under thinned scope as a block.

## Access and provenance

No bridge config or IAM change was needed: `campaign_collect.yml` and the
`github-crusher-collector` OIDC role already cover read-only `campaign/*`; at
inventory time the two prefixes were positions 44 and 45 of 209 campaign
prefixes, inside the default `max_prefixes=50`. Provenance recorded in the
return doc includes ContamX 3.4.0.3 binary/tarball SHA256s, Phase 1/Phase 2
image digests and jobdefs, and the field-cache/manifest SHA256s above.

Lane honesty is preserved: N/E/P share `engines/py_contam_bridge.py`'s `expm`
propagator, so agreement isolates airflow-field generation rather than
independent solver validation; the S lane is excluded. Exact schema/format
confirmation remains a Phase 4 Edison-consumption step.
