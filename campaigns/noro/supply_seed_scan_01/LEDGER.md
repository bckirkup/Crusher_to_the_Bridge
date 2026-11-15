# noro_supply_seed_scan_01 ledger

**Status:** scanner implemented; local campaign canary passed; awaiting Batch submit decision.

## Design

- Frozen contract in `DESIGN.md`: 126,200 unique seeds across exp/cls/spr/meg,
  arms `station_lots` / `single_line_receipt` / `declared_receipts`, 100 seeds
  per child, `epochs=1`, `num_agents=100`, JSONL-only artifacts.
- `tools/noro_diag/supply_seed_scan.py` re-execs under `PYTHONHASHSEED=1`
  before engine imports.

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

## Next decision

Submit the 3,786-child Batch array only after explicit go; then aggregate the
JSONL into prevalence and lot-size tables.
