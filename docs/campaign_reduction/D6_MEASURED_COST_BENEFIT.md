# D6 Measured Cost-Benefit — pilot receipt and phase quote

**Status: measured live result (2026-10-29). The first cost-benefit measurement
of the reduction program — the basis for the D7 envelope decision.**
Artifact for Edison/Kosmos consumption; supersedes the declared bootstrap
estimate for all planning purposes.

## What was measured

Attempt `red-d6-pilot-b` (workflow run `40802806913`, `picard-reducer:4` @ 60 GiB,
image `sha256:b916c4be…`) materialized 11 stratified specimen sources
(PS01 × all four hulls + summary-archive, census ×2, embedded-timeseries,
legacy-nested, clinical-non-AGE, unsupported-witness classes, plus a
missing-witness row excluded at pin time).

| quantity | measured |
|---|---|
| sources | 11 objects, 9 coverage cells, 40 selected runs |
| compressed bytes read | 74.86 MB (ranged reads, not whole-object) |
| rows emitted | 4,070,885 run_scalars / 3,353,412 distributions / 15,281 data_gaps |
| derived output | 3.64 GB (~49× compressed-read expansion) |
| peak memory | 10,229 MiB |
| API calls | 184 GET / 11 HEAD, zero list |
| receipt status | `quarantined` — designed: deliberately-included `legacy_nested` + `unsupported_witness` specimens fired `unsupported_family`/`schema_or_corruption`/`coverage_gaps` disqualifiers |

Durable evidence: `s3://crusherbucket-994254241749-us-east-1-an/campaign/_derived/reducer/v1/attempts/red-d6-pilot-b/`
(RECEIPT.json, COMMIT.json, MANIFEST.json, pilot_evidence.json + shard/derived partitions);
run artifacts `pilot-submit-40802806913` / `pilot-collect-*` on the same run.

## The measured phase quote (`analysis quote`, `quote-5a98544c742ef4a4`)

Extrapolating measured per-family unit draws over the dated Oct-19 register
counts (447,190 objects / 11 schema families), phase-shaped per the declared
multiplier profile:

| phase | objects | read | output | wall | cost |
|---|---|---|---|---|---|
| materialize | 442,050 | 2.91 TB | 141.5 TB | 170.7 h | $14,922.56 |
| finalize | 44,205 | 0.29 TB | 14.1 TB | 17.1 h | $1,493.39 |
| query | 88,410 | 0.58 TB | 28.3 TB | 34.1 h | $2,984.51 |
| return | 22,102 | 0.15 TB | 7.1 TB | 8.5 h | $746.13 |
| **central** | | | | | **$40,293.18** |

`exceeds_declared_envelope: true` against the $500 approved bootstrap envelope.
The earlier bootstrap estimate (~$738 central) was ~55× low — it under-modeled
the **distributions table**, not request counts.

### Driver decomposition

- ~606 MB of derived output per `growth_census_zip` object at pilot
  (3.64 GB / 6 census objects) × 233,429 census objects in the register
  ≈ **141 TB of derived output** — S3 storage ($0.023/GB-mo) and
  transfer-out ($0.09/GB) dominate the total.
- Request counts are non-binding: 184 GETs for 11 objects at pilot rates
  extrapolate to ~1.5 M calls — tens of dollars.
- Memory is non-binding: 10.2 GiB measured peak; even 16 GiB jobdef bindings fit.
- 5 schema families correctly landed `unmeasured` (bounded_region_jsonl,
  flu_cell_json, fomite_diagnostic_gzip, perturbation_json, stan_nuts_json) —
  typed uncertainty rows, no inferred compatibility.

## The D7-gating decision this creates

The full corpus is **not a bigger-budget problem**. The `distributions` /
`run_scalars` materialization contract itself must change before any
full-scope envelope is admissible — candidate directions (no pick made here):

- **bounded emission**: cap distributions rows per source (per-run summaries
  only, or quantile-bucketed emission rather than per-epoch rows);
- **columnar output**: parquet partitions instead of jsonl (the schema already
  permits partition_format — a format change alone could cut output volume
  ~10×, though read-side consumers must follow);
- **aggregate-at-source**: emit per-run distribution moments/quantiles rather
  than full curves where the query plan only needs moments;
- **scoped materialization**: emit distributions only for families/metrics the
  publication actually consumes (the query contract can declare the set).

## Defects the pilot found (dispositioned)

- [#1115](https://github.com/bckirkup/Crusher_to_the_Bridge/pull/1115) merged —
  collect-leg contract bugs (bootstrap-vs-execution request doc, `status.json`
  filename, `--receipt` flag).
- [#1116](https://github.com/bckirkup/Crusher_to_the_Bridge/issues/1116) filed —
  `_restore_state` restores shard completion but not `_ShardAccumulator` →
  resume writes empty derived partitions → `DerivedConflict` (or silent empty
  coverage if the prior run died pre-`_finalize`). Attempt-a objects preserved
  under `attempts/red-d6-pilot/` as evidence.
- Worker-request create-only staging: re-running under a fresh `reduction_id`
  avoids both stale-key conflicts and evidence deletion.

## What this is / is not

- **Measured**: every number above derives from the pinned pilot evidence doc
  + the dated register; the quote is reproducible from `attempts/red-d6-pilot-b/pilot_evidence.json`
  + the declared price snapshot `s3-batch-us-east-1-2026-10-27-request-declared`.
- **Not** a statement that science is unaffordable — it is a measurement that
  the *current materialization contract* emits ~49× its compressed input, and
  that ratio, not the corpus size, prices D7.
- Uncertainty: dated counts carry `counts_are_dated_not_current`; bands ±2×
  around measured wall seconds per family; unmeasured families excluded
  rather than guessed.
