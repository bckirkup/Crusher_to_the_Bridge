---
name: reducer-dispatch-pins
description: Dispatch pins for the campaign-reducer materialize/return workflows — the three parameter traps that burned a full round-trip each (canonical vs raw request_sha256 per verification site, attempt_id = reduction_id on the return leg, no DeleteObject on the derived store). Use before every `gh workflow run campaign_reduction.yml` / `campaign_return.yml` dispatch, and before post-hoc patching of `campaign/_derived/reducer/` attempt prefixes.
---

# Reducer dispatch pins

`.agents/skills/campaign-preflight/SKILL.md` owns the science gate (smoke,
dry-run, canary, pinned image digest + jobdef revision). This skill owns the
*request-level pins* on the dispatch commands themselves — each rule below
cost one failed run to learn.

## 1. `request_sha256` — two different hashes, two verification sites

The worker and the workflow verify the request hash **differently**. Passing
the same sha to both fails one of them, and the failure looks like a bad pin
rather than a bad convention.

- **Materialize leg** (`campaign_reduction.yml` → Batch worker):
  `worker._verify_sha` hashes the *canonicalized parsed document* —
  `json.dumps(doc, sort_keys=True, separators=(",", ":"))` — not raw file
  bytes. Compute and pass the canonical sha:

  ```bash
  python3 -c "import hashlib,json; print(hashlib.sha256(json.dumps(json.load(open('REQUEST.json')),sort_keys=True,separators=(',',':')).encode()).hexdigest())"
  ```

  Failure signature: job dies in ~2 s, log shows
  `invalid_contract: request sha256 <canonical> != declared <raw>`.

- **Return leg** (`campaign_return.yml` → "Fetch + pin the bootstrap
  request" step): verifies the *raw file bytes* sha:
  `sha256sum REQUEST.json`.

  Failure signature: collect step exits with
  `request sha256 <raw> != declared <canonical>`.

Both legs exist in one session; keep the two shas side-by-side in the request
doc or a scratch note and label each with which site consumes it.

## 2. Return-leg `attempt_id` = the reduction id, not the labelled attempt

The attempt prefix is `campaign/_derived/reducer/v1/attempts/{reduction_id}`
(`materialize._attempt_prefix` — keyed by `ctx.reduction_id`, never by the
attempt label like `-v2`). The return workflow builds
`attempts/{attempt_id}/RECEIPT.json` directly from the `attempt_id` input.

Pass the **request's `reduction_id`** (e.g. `red-fps01-b-obsclock`), not the
attempt label you gave the materialize dispatch (`red-fps01-b-obsclock-v2`).
Wrong id → the bounded poll expires into a typed `missing_receipt` envelope
~30 min later instead of failing fast.

The field name is misleading — renaming it `reduction_id` in the workflow is
a reasonable follow-up.

## 3. The derived store is create-only

`s3:DeleteObject` is denied on `campaign/_derived/` for the deploy role —
`aws s3 mv`/`rm` fail on the delete step while put/copy succeed. Consequences:

- Never plan a post-hoc fix that deletes or overwrites an attempt object;
  rewrite at a new key or accept the stray object (manifest readers only
  follow manifest entries — strays are inert).
- When synthesizing missing attempt objects (e.g. a dangling
  `pages_manifest_key`), write the *exact published key*; there is no second
  chance to relocate.
- `put_idempotent` semantics: identical content at the same key is fine;
  different content at the same key is a `DerivedConflict`.

## 4. Receipt keys can dangle — verify before the return leg

`worker._attempt_receipt` published `pages_manifest_key`/`status_key`/
`asset_index_key` unconditionally while `_emit_pages` only emitted for the
`first_paper_vectors` table — any profile with a different `table_name`
produced a receipt pointing at objects that don't exist, and the collector's
preferred path then raises `ReturnFailure("missing_object")`.

Fixed by the table-agnostic `_emit_pages` (receipt now publishes only keys
that exist; `status.json`/`asset_index.json` written unconditionally).
Until every running jobdef's image carries that fix, **HEAD-check the
receipt's published keys** before dispatching collect:

```bash
aws s3api head-object --bucket crusherbucket-994254241749-us-east-1-an \
  --key <attempts/RID/pages/....pages_manifest.json> --profile picard
```

If keys dangle, synthesize the pages + manifest + status + asset_index at
the published keys first (byte-faithful re-chunk of the shard partitions —
never recompute row content), then collect.
