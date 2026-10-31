# first_paper_scalar — Phase A specimen panel + extraction quote

**Status: measured live result (2026-10-30), picard role,
`crusherbucket-994254241749-us-east-1-an`. Companion to the
`first_paper_scalar` extraction mode (contract
`picard_framework/analysis/campaign_reducer/contracts/FIRST_PAPER_SCALAR.json`,
`definition_version first_paper_scalar/1.0.0`).**

Phase A panel: 16 run-zip specimens — 2 runs × {off, ps_ship} × all four
hulls (exp / cls / spr / meg), read by ranged GET (index tail + one
member body), plus the head line of each of the 8 arm scan-row files.
53 ranged GETs total, ~0.5 MB read. No census member was decompressed.

## Per-run member layout (all 16 specimens, all 4 hulls)

Every zip carries exactly three members:

| member | comp bytes | notes |
|---|---|---|
| `summary.json` | 12,742–31,148 (median ≈22 kB) | 409–428 kB uncompressed; the only member the mode reads |
| `growth_census.json.gz` | bulk of the object | never indexed past the central directory, never decompressed |
| `rss_samples.json` | ~238 B | never read |

## Per-field presence

- **summary fields (45 contract columns):** present in 16/16 specimens
  across all four hulls, after one pointer correction measured below.
- **scan fields (23 contract columns):** every field present in the head
  line of all 8 arm scan files, after one emission-shape correction
  measured below.
- **`posted` vs `trigger_status` divergence confirmed:** scan rows carry
  `posted` (bool); summary carries `trigger_status` (str, e.g.
  `BASELINE`/`ALERT`). The vector keeps both, separately named
  (`scan_posted`, `trigger_status`).
- **Seed pairing confirmed live:** off and ps_ship share seeds within a
  hull — e.g. cls seed 8109 appears in both arms' first lines, spr/meg
  share s8105–s8120. Pair within hull only.

## Measured deviations from the settled inputs (corrected in the contract)

1. **Zip sizes are 5.6 MB–210 MB, not uniformly 9–11 MB.** Measured:
   exp 5.6–10.1 MB, cls ≈50 MB, spr ≈76–83 MB, meg ≈207–210 MB. The
   settled "9–11 MB" figure holds only for exp. This does not change the
   quote — the mode reads the ~20 kB `summary.json` member, not the zip.
2. **All 46 scan-row files live under
   `campaign/noro_provisioned_source_01/_scan_rows/`** — including the 10
   `fl_meg_*` files. There is no `_scan_rows/` under the `_mega/` prefix.
3. **`summary.infection_attack_rate` does not exist.** The combined
   infection attack rate is emitted at `/derived/attack_rate`; only the
   per-segment `summary.infection_attack_rate_{passenger,crew}` exist.
   The contract field points at `/derived/attack_rate`; provenance for
   that column reads `derived` accordingly. (This was the single absent
   field in the whole panel — absent in all 16, i.e. a naming fact, not
   run-to-run missingness.)
4. **`cs_echo` is arm-shaped, not a flat `mode` string.** off rows carry
   `cs_echo:{mode:"off"}`; ps_ship rows carry
   `cs_echo:{lot_mode, handler_mode, diner_mode, lot_mint_model,
   provisioned_source:{source_id, q_source}}`. The contract emits
   `scan_cs_echo_json` (whole object, kind=json) instead of `mode`.

## Extraction quote (`first_paper_scalar`)

Separate compute / requests / storage / export terms. Read side assumes
~3 ranged GETs per zip (HEAD-pin, central-directory tail, member body —
the 53-GET panel measured ~2.8/zip) plus one ranged GET per scan file.

| term | Phase B — off + ps_ship, 8,000 runs | Phase C — all arms, 46,000 runs |
|---|---|---|
| **requests** | ~24k ranged GETs + 8 scan reads + ~150 partition PUTs | ~140k ranged GETs + 46 scan reads + ~800 partition PUTs |
| **bytes read (requests term)** | ~0.2 GB (8k × ~22 kB member + 24 MB scan files) | ~1.2 GB (46k × ~22 kB + 140 MB scan files) |
| **compute** | decompress + parse ~0.4 GB JSON: ~15–20 vCPU-min; peak RSS < 1 GiB (single-document streaming, shard checkpointing) | ~2.4 GB JSON: ~80–110 vCPU-min; same RSS bound |
| **storage (derived)** | `first_paper_vectors` ~8k wide rows ≈ 120 MB JSONL (~35 MB gz) + base tables (source_objects/assets/data_gaps, no run_scalars/distributions/weights) + 125 shard checkpoints | ~690 MB JSONL (~210 MB gz) + base tables + 719 shard checkpoints |
| **export** | table bytes above (~35 MB gz) out of S3 | ~210 MB gz out of S3 |

For scale: whole-zip fetch of the same corpora would be ~750 GB (B) /
~4.3 TB (C) of transfer. Ranged member reads reduce the request-side
bytes ~3,500×.

## Provenance guarantees (what the vector carries per row)

- `run_uid`, `source_key` (zip object key), `member` (full member path
  incl. fused folder), `member_asset_id`, `definition_version`,
  `definition_sha256`.
- Per-field `provenance[column] = {status, source_key, member}` —
  `exact_emitted` / `null_emitted` / `missing` for summary fields,
  `exact_emitted` / `missing` / `scan_source_absent` for scan fields,
  `recomputed_pair` / `invalid_pair_missing_operand` /
  `invalid_pair_zero_denominator` for recomputed rates, and
  `sum_consistent` / `sum_divergent` / `sum_uncomputable` for the
  channel/route consistency checks.
- `missing[]` lists every column absent — never zero, never borrowed.

## Reproduce

The panel is reproducible with the picard profile: ranged-GET the head
of each `campaign/noro_provisioned_source_01/_scan_rows/fl_{hull}_12d_scr_{arm}.jsonl`
(arm ∈ {off, ps_ship}), take the first two `key`s per file, then
`open_pinned` → `index_zip` → `read_member(summary.json)` per key
(repo: `picard_framework/analysis/campaign_reducer/{pinned_reader,zip_members}.py`).
