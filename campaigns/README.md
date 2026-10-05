# campaigns/ — conventions

One directory per campaign: `campaigns/<pathogen>/<name>/`. Everything a
campaign owns lives inside its directory; everything outside it is either
shared infrastructure (`scripts/campaign`, `deploy/aws/campaign_entrypoint.py`,
`tools/diag/`) or engine code.

Non-developers run campaigns exclusively through `scripts/campaign`. They
never open `campaigns/` or `deploy/aws/`: the CLI resolves the campaign
directory, validates the spec, runs the preflight gates, and submits.

## Required contents

| file | role |
|------|------|
| `campaign.json` | Declarative spec — the only required artifact (schema below). |
| `LEDGER.md` | Campaign-local findings, status, decisions. Committed, durable. |

## Optional contents

| file | role |
|------|------|
| `entry.py` | `build_argv(args, block, seed, out_dir) -> (cmd, artifact_path)` — custom per-block argv construction. Required when workers take non-standard arguments (see hand_occupancy). |
| `probe.py` / `readout.py` | Campaign-owned instrumentation / readout when the code graduates out of `tools/`. Filenames are positional — role suffixes (`_probe`, `_census`, ...) are not used inside a campaign directory. |
| `design/` | Build scripts / notes that produced `campaign.json`'s manifest reference. |

## campaign.json schema

```jsonc
{
  "name": "noro_hand_stationary_01",        // campaign id; default s3 prefix + jobdef stem
  "pathogen": "norovirus",
  "manifest": "picard_framework/runs/mega_cruise_campaign/<m>_manifest.json",
  "pathogen_id": "norwalk_gi",
  "epochs": 288,
  "s3_prefix": "campaign/noro_hand_stationary_01/",  // under the campaign bucket
  "queue": "picard-campaign-queue",
  "image_tag": "noro-hand-stat01",
  "resources": {"vcpu": "1", "memory": "4096", "shm": 512},
  "blocks": {
    "<block_name>": {
      "worker": "tools/noro_diag/growth_chain_census.py",  // argv[0] for the child
      "tier": "fl_spr_12d",          // manifest-tier worker: tier for seed->index translation...
      "artifact": "cell_seed{seed}.json",  // ...OR seeds worker: filename the worker writes (done-detection)
      "seeds": [8105, ...],          // flat list; array size = len(seeds)
      "args": {"platform": "..."}    // extra fixed worker args (optional)
    }
  },
  "readout": "tools/noro_diag/hand_occupancy_readout.py"   // optional
}
```

Field semantics follow the pre-rationalization submit scripts (`deploy/aws/submit_*.sh`)
they replace: `blocks` is the old `BLOCK` env, `seeds` the old `SEEDS` env,
`queue`/`resources` the jobdef container fields. `--index` overrides the array
index for canaries exactly as before (the Batch env var is reserved).

## Graduation rules

- **Never move or rename a file that a registered jobdef's command references**
  (argv[0] is a literal path). A campaign's files may graduate into
  `campaigns/<p>/<n>/` only once that campaign's array work is done; the next
  submit registers a new jobdef revision at the new path.
- New campaigns start inside `campaigns/` from day one — copy the nearest
  existing spec and edit `campaign.json`.
- Shared code lives in `tools/diag/` (readout/instrumentation/manifest
  helpers), not copied into campaign dirs.
- Deploy artifacts are generated, not authored: `scripts/campaign submit`
  derives the jobdef from `deploy/aws/campaign_jobdef.json` and builds the
  thin image from `deploy/aws/Dockerfile.campaign`. Only per-campaign
  overrides (`resources`, `image_tag`, fargate) are spec data.
- `scripts/campaign submit` registers a **new jobdef revision on every
  non-dry-run call** (`--register-only` produces `:1`, each subsequent block
  submit bumps it). Expected, not a bug — record the revision used per array
  in the campaign LEDGER.
- The worker owns its artifact filename — `entry.py`'s returned
  `artifact_path` and any `artifact` template in `campaign.json` must mirror
  the name the worker actually writes, not the other way around.
- Before the first submit through a new or touched Dockerfile, build it
  literally (`docker build -f deploy/aws/Dockerfile.campaign .`) and check
  inside the container that `deploy/aws/`, `tools/` and `campaigns/` are
  present — a once-committed recipe COPY'd nothing and produced a hollow
  image discovered only at submit time (see campaign-preflight step 3).

## CLI

```
scripts/campaign list
scripts/campaign describe <pathogen>/<name>
scripts/campaign run    <pathogen>/<name> --block B --index N [--out DIR]
scripts/campaign submit <pathogen>/<name> --block B [--canary] [--queue Q]
scripts/campaign readout <pathogen>/<name> [-- <readout args>]
```
