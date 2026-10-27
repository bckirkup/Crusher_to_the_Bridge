# D4 live return-canary runbook

Status: **machinery merged; live run pending owner approval.** This page
is the post-merge operator runbook for the synthetic `return_canary`
attempt that closes issue #1087: dispatch → Batch job → durable
`RECEIPT.json` → bounded collect → Edison ingest → idempotent
acknowledge. Every step is single-line bash; nothing runs until a human
fires `workflow_dispatch` on environment `aws-campaign`.

Offline-rigged fixtures live in `docs/campaign_reduction/canary/`:

| File | Role |
|------|------|
| `fused_canary.zip` | 3-member synthetic `campaign_summary_zip` source |
| `canary_spec_success.json` | worker spec, reduction `red-canary-ok` |
| `canary_spec_failure.json` | worker spec, reduction `red-canary-fail` (absent source → typed failed receipt, never a success) |
| `canary_bootstrap.json` | BOOTSTRAP request for `status`/`collect`/`acknowledge` |
| `canary_request.json` | execution REQUEST (phase `return_canary`) for `resume`/`query` |
| `canary_query.json` | QUERY doc — `max_export_rows: 2` forces a retained continuation token |

## 0. One-time setup (repo variables + optional secret)

The return workflow assumes two roles already created in account
`994254241749`. Set the repo variables once (Settings → Secrets and
variables → Actions → Variables):

```
gh variable set AWS_REDUCTION_COLLECTOR_ROLE_ARN --body arn:aws:iam::994254241749:role/github-crusher-reduction-collector
gh variable set AWS_REDUCTION_DISPATCH_ROLE_ARN --body arn:aws:iam::994254241749:role/github-crusher-reduction-dispatch
```

Optional Edison leg: repo secret `EDISON_PLATFORM_API_KEY`. If absent,
the ingest job still runs — it emits a typed `return_blocked`
`ingestion_receipt.json` (owner `edison_connector`, bounded retry + S3
pointer); the collect/ack legs still prove out.

## 1. Stage the canary fixtures (dispatcher role can write `requests/*`)

Run under `PowerUserAccess-994254241749` (or any principal with PutObject
on `campaign/_derived/reducer/v1/`):

```
B=crusherbucket-994254241749-us-east-1-an; aws s3 cp docs/campaign_reduction/canary/fused_canary.zip s3://$B/campaign/_derived/reducer/v1/canary/fused_canary.zip
B=crusherbucket-994254241749-us-east-1-an; aws s3 cp docs/campaign_reduction/canary/canary_spec_success.json s3://$B/campaign/_derived/reducer/v1/requests/canary_spec_success.json
B=crusherbucket-994254241749-us-east-1-an; aws s3 cp docs/campaign_reduction/canary/canary_spec_failure.json s3://$B/campaign/_derived/reducer/v1/requests/canary_spec_failure.json
```

## 2. Dispatch the success attempt (Batch submit)

`request_sha256` is the sha256 of the request **canonicalized**, not of
the file bytes — the worker hashes
`json.dumps(doc, sort_keys=True, separators=(",", ":"))` of the parsed
body. Recompute with:

`python3 -c "import json,hashlib,sys;print(hashlib.sha256(json.dumps(json.load(open(sys.argv[1])),sort_keys=True,separators=(',',':')).encode()).hexdigest())" <file>`

Committed canonical values: success `559ebbc6f2910323273ce2286969836328b55087b1649bf85d0f2b14996b1b4a`,
failure `f5c085f2634db04de8a22953d918e574cdd4f59aaf49295ee20a13f4b8fc617d`,
bootstrap `5e6f8641de4ecf0cbe5bec773aea6462ec7ac35268540a5fabb443783c8c87a7`.

```
gh workflow run campaign_reduction.yml -f phase=return_canary -f request_uri=s3://crusherbucket-994254241749-us-east-1-an/campaign/_derived/reducer/v1/requests/canary_spec_success.json -f request_sha256=559ebbc6f2910323273ce2286969836328b55087b1649bf85d0f2b14996b1b4a -f shard_index=0 -f job_queue=picard-analysis-queue -f job_definition=picard-reducer:2 -f attempt_id=red-canary-ok -f dry_run=false
```

The workflow's dispatch step validates inputs, describes the queue/jobdef,
then `batch:SubmitJob` with argv `--phase return_canary --request-uri …
--request-sha256 … --shard-index 0`. The worker materializes the fused
zip and writes
`s3://$B/campaign/_derived/reducer/v1/attempts/red-canary-ok/RECEIPT.json`
(`status: completed`, manifest/commit keys, typed failure statuses on
any error — a failure receipt never reads as success).

Optional forced-failure leg (same inputs with `attempt_id=red-canary-fail`,
`request_uri=…/canary_spec_failure.json`, sha
`f5c085f2634db04de8a22953d918e574cdd4f59aaf49295ee20a13f4b8fc617d`) — its
receipt must carry a non-`completed` status.

## 3. Return leg (poll → collect → ingest → acknowledge)

```
gh workflow run campaign_return.yml -f attempt_id=red-canary-ok -f request_uri=s3://crusherbucket-994254241749-us-east-1-an/campaign/_derived/reducer/v1/requests/canary_bootstrap.json -f request_sha256=5e6f8641de4ecf0cbe5bec773aea6462ec7ac35268540a5fabb443783c8c87a7 -f job_id=<batch-job-id-from-dispatch-artifact> -f poll_interval_seconds=60 -f max_polls=30 -f issue_number=1087 -f edison_ingest=true -f dry_run=false
```

Stage `canary_bootstrap.json` to `requests/` first, same as step 1 —
`request_sha256` is the canonicalized sha256 of that uploaded body.

What each job does:

- **poll** (collector role): `head-object` on
  `campaign/_derived/reducer/v1/attempts/red-canary-ok/RECEIPT.json` with
  bounded backoff (`max_polls`, ×1.5 to 600s cap — no long-poll) plus an
  optional `batch:DescribeJobs` cursor. Expiry writes a typed
  `return_blocked` envelope (kind `missing_receipt`) — never a fake
  success — and posts it deduplicated on `issue_number`.
- **collect** (collector role):
  `scripts/campaign analysis collect --request bootstrap_request.json
  --receipt s3://…/RECEIPT.json --store-uri s3://$B/ --out return_run`.
  Bounded fetch (receipt ≤256KiB, manifest ≤1MiB, ≤20 files, ≤50MiB
  total), sha256 verification of every declared member, then
  `durable_ingestion_request.json`.
- **ingest**: `edison_ingest` uploads each verified file via
  `astore_file_content` → `ingestion_receipt.json` with
  `project_asset_ids`; connector/key absent → typed `return_blocked`
  receipt (P19: no secret prompt, no file relay, bounded retry + S3
  pointer).
- **acknowledge** (dispatch role — the only role with PutObject on
  `requests/*`):
  `analysis acknowledge` writes the idempotent
  `(attempt, query, page, hash)` record to
  `campaign/_derived/reducer/v1/requests/acks/<ack_id>.json`; an
  identical re-run deduplicates, conflicting bytes at the same ack_id
  → `derived_conflict`. The ≤32KiB `ack_envelope.json` posts to
  `issue_number` deduplicated on `<!-- crusher-reducer-ack:… -->`.

Runs for the same `attempt_id` serialize through the
`campaign-return-${{ inputs.attempt_id }}` concurrency group.

## 4. Where Kosmos/Edison picks up

Edison does not read S3. Its side of the chain is exactly one of:

- the uploaded `project_asset_ids` in `ingestion_receipt.json` when
  `EDISON_PLATFORM_API_KEY` is set — Kosmos consumes the Edison project
  assets directly, or
- the collector-artifact publication when it is not: Edison fetches the
  `return-collect-*/` + `return-ack-*` run artifacts itself via its PAT
  (the S1 pattern proven on issue #1077), keyed off the `s3_pointer` in
  `durable_ingestion_request.json` / `ack_envelope.json`.

## 5. Evidence for closing #1087

- `attempts/red-canary-ok/RECEIPT.json` (`status: completed`) +
  `attempts/red-canary-fail/RECEIPT.json` (typed non-success).
- `return-poll-*`, `return-collect-*`, `return-ingest-*`, `return-ack-*`
  workflow artifacts.
- `requests/acks/ack-*.json` in S3 (idempotent on re-run).
- The deduplicated ack comment on the tracking issue.

Every failure type is typed per STATUS_NAMESPACES —
`return_blocked`, `source_changed`, `derived_conflict`,
`budget_stopped` — never rendered as success.
