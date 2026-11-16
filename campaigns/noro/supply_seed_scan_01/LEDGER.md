# noro_supply_seed_scan_01 ledger

**Status:** Batch scan submitted; awaiting JSONL aggregation.

## Design

- Frozen contract in `DESIGN.md`: 126,200 unique seeds across exp/cls/spr/meg,
  arms `station_lots` / `single_line_receipt` / `declared_receipts`, 100 seeds
  per child, `epochs=1`, `num_agents=100`, JSONL-only artifacts.
- `campaigns/noro/supply_seed_scan_01/entry.py` exports `PYTHONHASHSEED=1`
  for the worker subprocess; direct worker invocations must set it explicitly.

## Local canary (pre-Batch)

Measured with `scripts/campaign run` on this working tree, `epochs=1`,
`num_agents=100`, 100 seeds per chunk:

- `exp_station_lots` chunk 0 (seeds 900000..900099): 100 rows, 0 errors,
  9 contaminated station-lot rows, 9 provisioned-lot objects;
  `lot_servings` mean 169.1 / median 123 / max 420;
  `lot_titre_gec_per_g` mean 2056.3 / max 4992.5.
- `exp_declared_receipts` chunk 0 (same seeds): 100 rows, 0 errors,
  4 rows with contaminated receipts, 2 infectious served provisioned-lot
  objects; example shellfish receipt `csr-norwalk_gi-1` infectious,
  `quantity_servings=66`, `lot_servings=66`,
  `lot_titre_gec_per_g=316.0`, venue `MainDining`.
- Worker smoke also covered cls/spr/meg `station_lots` and meg
  `declared_receipts` at 2 seeds each: 0 errors; receipt arm emitted 14
  receipts/seed with `lot_layer_mode=declared_receipts`.

## AWS submission (2026-11-16)

- Image: `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:noro-supply-seed01`
  digest `sha256:54fc294e0f203e21952a31b1fef00f4294e46669eb6e3c1f9b657a6f39d6f521`,
  `ENGINE_GIT_SHA=357dfac06103ed6b496e2428099d13b8d5117ddc`.
- S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_seed_scan_01/`.
- Canary: job `616746f6-ad28-49f5-829d-43d10cce24d5`, jobdef `:1`,
  SUCCEEDED in ~18s container wall; `exp_station_lots` chunk 0 artifact had
  100 rows, 0 errors, 9 contaminated station-lot seeds.
- Array parent jobs (jobdef revision in parentheses):
  - `exp_station_lots` `5c1a657b-8956-4a13-b578-a5f27c3fbd67` (`:2`)
  - `exp_single_line_receipt` `bb332f21-5303-4b87-93ba-325f8d486d7e` (`:3`)
  - `exp_declared_receipts` `1e779dfb-5145-4b3d-a498-4ef2bc44c65f` (`:4`)
  - `cls_station_lots` `4a0499f6-2381-420d-9194-e65e8771345d` (`:5`)
  - `cls_single_line_receipt` `e6060304-6ad7-4e50-9be1-a64494b917d8` (`:6`)
  - `cls_declared_receipts` `bd5325f5-9a20-40d8-8cdf-aed2d818aa5d` (`:7`)
  - `spr_station_lots` `2e535da5-5329-4e26-a7f1-71aa029dda75` (`:8`)
  - `spr_single_line_receipt` `575c118c-dcce-4f31-88d9-959ad83bf467` (`:9`)
  - `spr_declared_receipts` `1d686d05-ec7e-4ad5-9a25-4e5a2296ece9` (`:10`)
  - `meg_station_lots` `86fc169a-2ff8-4392-8b53-92723e9d6ed5` (`:11`)
  - `meg_single_line_receipt` `09af048f-020e-4496-a7d2-4d6d54dbdb6d` (`:12`)
  - `meg_declared_receipts` `bded5992-b2f1-42fb-9296-bfa4761aa0e4` (`:13`)

## Next decision

Aggregate the 3,786 JSONL artifacts into prevalence and lot-size tables once
the arrays complete; no anchor fitting or default flip.
