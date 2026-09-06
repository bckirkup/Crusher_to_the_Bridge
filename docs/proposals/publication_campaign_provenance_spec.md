# Publication campaign provenance and lineage specification

Status: **proposed, not yet wired into campaign execution**.

Every exploratory, confirmatory, revision, review-response, or qualification campaign receives a UUID and records its paper, intent, exact source tree, resolved environment, hashed inputs, effective configuration, seed policy, and parent/supersession lineage. Confirmatory and revision records require a non-null analysis plan and parent campaign; review-response records additionally require a review-response identifier.

`tools/campaign_fingerprint.py` computes a deterministic SHA-256 fingerprint from the pre-run envelope. Outputs and any stored fingerprint are excluded so identity can be computed before execution. Resume must compare the archived fingerprint and fail closed on mismatch. Attempts are append-only; retries create new attempt records rather than replacing prior output.

```bash
python tools/campaign_fingerprint.py docs/examples/publication_campaign_provenance.example.json --validate
```

Next: populate this envelope from resolved runtime state—not user labels—write it inside every run archive, bind result hashes after execution, and distinguish per-run archives from fused shard archives during analysis discovery.

For LLM-operated safety, the command-line validator accepts manifests only beneath its working directory and always loads the repository-owned schema relative to the tool itself.
