# FOOD-SUPPLY-01 seed-initiation scan

Status: frozen design, not yet run.

## Question

Which voyage seeds board contaminated supply-chain lots/receipts across the
four scored hulls, and how large are those lots? This is a boarding/prevalence
census for later paired full-fidelity posted-AR runs; it is not an anchor fit.

## Frozen scan contract

- Manifest tiers: `fl_{exp,cls,spr,meg}_12d_sens_p06_paxv` from
  `picard_framework/runs/mega_cruise_campaign/noro_provisioned_sensitivity_01_manifest.json`.
- Arms: `station_lots` (control), `single_line_receipt`, `declared_receipts`
  (`receipts_per_item_line=2`).
- Scan fidelity: `epochs=1`, `num_agents=100`, `payload_profile="lean"`,
  natural-history clock from the manifest (`hours`).
- Unique voyage seeds, dedicated non-overlapping hull ranges:
  - exp: 900000..955999 (56,000)
  - cls: 960000..993999 (34,000)
  - spr: 1000000..1018999 (19,000)
  - meg: 1020000..1037199 (17,200)
- Chunking: 100 seeds per Batch child; block `seeds` are chunk indices, not
  voyage seeds. Total unique seeds = 126,200; total one-epoch scans =
  378,600 across 3 arms; Batch children = 3,786.
- Output: one JSONL artifact per chunk under
  `campaign/noro_supply_seed_scan_01/<block>/`, row per seed with
  `seed/tier/arm/hull`, `provisioned_source`, receipt counts/states,
  contaminated receipts, provisioned objects (`lot_servings`,
  `lot_titre_gec_per_g`, item_line, venue/venues_served, quantity fields),
  source-kind counts, and telemetry counters. No per-seed run zips.

## Selection and reporting rules (frozen before cells run)

- Report, never select-on-anchor: `n_scanned`, `n_contaminated` by
  hull/arm/item_line/venue/source_kind, receipt contamination states, and lot
  size/titre distributions.
- A seed is "contaminated supply" if `provisioned_source.n_contaminated > 0`
  for `station_lots`, or `n_contaminated_receipts > 0` for receipt arms.
- Lot size is read from provisioned-lot objects (`lot_servings`,
  `lot_titre_gec_per_g`, `quantity_servings`/`quantity_g` when present).
- No VSP/attack-rate fitting, no default flip, no new epidemiological
  constants. The scan only nominates seeds for later paired full runs.

## Integrity gates

- Local smoke must show the arm fields reach `provisioned_source` in the
  emitted spec path and the artifact is JSONL-only.
- Agent-count neutrality was measured for `station_lots` seed 8114
  (`num_agents=100/1000/2000` identical provisioned plan and `lot_servings`);
  receipt arms get the same chunk-level witness check in the canary.
- Interpreter/hash pin: `campaigns/noro/supply_seed_scan_01/entry.py` exports
  `PYTHONHASHSEED=1` for the worker subprocess, so local campaign canaries and
  Batch children share the same seed-selection hash; direct worker invocations
  must set it explicitly.
- Error contract: any per-seed exception makes the worker exit nonzero after
  writing the chunk locally, so Batch retries instead of `_already_uploaded`
  treating error rows as a completed chunk.
- Canary before array: one chunk per representative block inspected for
  schema, nonzero supply witnesses where expected, and error rate.

## Stopping rule

Fixed budget, not "until N contaminated": run all 3,786 chunks unless a child
fails repeatedly. Aggregate with Beta-posterior prevalence estimates and
lot-size quantiles; if receipt yield is too low for the posted-AR question,
the next decision is a hull/venue-scaled receipt-count rule, not more quiet
seeds.
