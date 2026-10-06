> **Status:** Living — jobdef quotes and peaks are measurements of record; add
> each new campaign's `rss_mb`/`peak_rss_mb` reading and retire stale rows.

# Model and campaign memory requirements

Why a 12-day `mega_cruise_5000` cell that a bare voyage completes in ~2 GB has
OOM-killed 4096 MB and 6144 MB jobdefs, and which feature combinations are
safe at which memory quote. "Memory" here means five distinct budgets that
different features touch — conflating them is how the wrong jobdef gets sized:

1. **Child RSS** — the Batch container's cgroup limit (`resources.memory` in
   `campaign.json`, or `resourceRequirements` MEMORY in a bespoke jobdef).
   Exceed it → SIGKILL, exit 137 / `OutOfMemoryError*`, no retry.
2. **The serialize spike** — census workers build the whole payload in RAM,
   then `json.dumps` + `gzip` it at fold time. VmHWM counts the peak wherever
   it occurs, so the post-voyage serialize spike is part of the child quote.
3. **Artifact volume** — bytes written into the per-run zip (and on to S3).
   Compresses well but still ~45–210 MB/cell.
4. **Readout memory** — what a readout job holds while consuming cells:
   ranged member GETs (small) vs decompressing the census member (~1 GB/cell
   on mega).
5. **Fleet concurrency** — CE RAM ÷ child quote = concurrent children =
   wall-clock. Over-quoting memory costs fleet time, under-quoting costs a
   resubmitted wave.

## The measured ladder

| cell shape | platform | epochs | retention | census payload | jobdef | outcome |
|---|---|---|---|---|---|---|
| generic shard voyage, no instrument | mega (7000 ag / 192 z) | ~288 | compact | — | 1 vCPU / 2048 MB | holds; earlier revs OOM'd at 1/4096 *in-process* before subprocess-per-run (`deploy/aws/README.md` §container sizing) |
| NORO-MEGA-01 `fl_mega_12d_scr` | mega | 288 | compact | `growth_chain_census` full | 1 / 4096 MB | **OOM ~28–33 min** (local probe: 4.76 GB and still climbing) |
| NORO-MEGA-01 `fl_mega_12d_scr` | mega | 288 | compact | full | 1 / 16384 MB | holds — ~34 min/child, ~3× headroom; zips ~210 MB |
| MEGA-IMPACT-01 (a0–a3) | mega | 288 | compact | `--payload lean` | 1 / 6144 MB | holds — lean peak med ~4.2 GB, **fleet max 4,355 MB** (~29% headroom) across the 926-voyage fleet |
| NORO-AGE-FOOD-01 wave-3 meg (`fl_meg_12d_scr_*`) | mega | 288 | compact | **full** (block `args` unset → `--payload` defaults `full`) | 1 / 6144 MB | **OOM ~55 min** — RSS grew ~0.4→4.6+ GiB and was still climbing at SIGKILL (`campaigns/noro/age_food_01_mega/LEDGER.md`) |
| noro probes on exp/cls/spr hulls (outbreak_01–04, food_01–02, channel_03/04, hand_occupancy, dose_challenge, leverage, venue_census, …) | 450–3000 ag | 168–288 | compact | full instruments | 1 / 4096 MB | holds across the board |
| covid hull / boarding-screen probes | ≤3000 ag | ≤288 | compact | probe instruments | 1 / 2048 MB EC2, 4096 MB Fargate | holds |
| analysis jobs (boundary surface/MC, Stan, sentinel NUTS) | — | — | n/a | n/a | 2–4 / 8192–30720 MB | separate regime — memory-bound fits, on r-family CEs |

The pattern: **4096 MB covers every instrumented cell on hulls ≤3000 agents;
mega only fits 6144 when the census payload is lean; full-payload census on
mega has never held below 16384.**

## Where one child's RSS goes

### A. Live voyage state (always allocated)

Scales with `num_agents` × armed pathways:

- `KorkinAgent` objects — ~30 lazily-filled per-pathogen dicts per host
  (hand loads, propensity, practice, emesis schedule/titre, pharma,
  `emesis_deposition_records_by_pathogen`, `immune_history`). Lazily filled
  means *the armed mechanisms decide the footprint*: an unarmed profile
  never allocates its dicts, an armed emesis+fomite+food profile grows the
  deposition-record list per emit.
- Zone pools per pathogen — surface pools, food pools, emesis patch pools
  (`emesis_patch_pools_by_pathogen`), pending/emitted aerosol maps. Bounded
  by zones × pathogens for the pool dicts; patch *lists* grow with emesis
  events until cleaning/decay sweeps them.
- Permanent engine logs — `_cs_event_log` (common-source witness rows),
  strain dose ledger, per-agent `immune_history` entries per cleared
  infection. All ∝ realized events.

### B. Per-epoch transient (freed at epoch end — sets the intra-epoch high-water)

`ContactTracingMatrix` and the dose accumulators are rebuilt every epoch in
`step_transmission`: ten exposure lists (shared_room, droplet,
hvac_downstream, emesis_aerosol, flush_aerosol, fomite_trailing,
food_contamination, common_source events+exposures, environmental), plus
`zone_occupants` and per-agent dose dicts. Transient under any retention —
but a hot epoch (mass-emesis or a large common-source meal) spikes it. ∝
agents × armed pathways × realized events *in that epoch*.

### C. Retained history — `run.history_retention` (the biggest lever)

`record_epoch` appends one record to `simulation_history` per epoch; the
flag decides its content (`orchestrator_record.py`):

- **`full`** (the `PicardRunSpec` default!): a per-agent record for *every*
  agent + the entire `tracing_matrix.to_dict()` + observation/cascade/
  wearable/lab-notebook blobs per epoch. On mega that is ~7000 agent dicts
  × 288 epochs plus every epoch's exposure lists — grows ~linearly with
  epochs and is what made the legacy shard jobdef climb to 16 GB before the
  fix.
- **`compact`** (what campaign spec builders force — `campaign_runner`
  build spec, `campaign_execution._telemetry_run_spec` default): summary
  counts, spaces without by-id maps, infection counters, HVAC, protocols,
  cost. Lab notebook accumulation is disabled at init under compact.
- **`--full-telemetry`** (`campaign_execution`): flips retention to `full`
  *and* writes `simulation_history.json` + `artificial_lab_notebook.json` +
  `ground_truth.json` into the run dir → both budgets at once (RAM during
  the voyage and the heavy zip member).

Rule: detail that compact drops belongs on `sim.epoch_observer` — the
per-epoch seam handed the epoch's scratch pad — not on full retention
(`picard_framework/covid_boarding_screen.py` is the in-tree example).

### D. Instrument payload — the census workers' `--payload` lever

`growth_chain_census` keeps twelve per-event row streams live through the
voyage (`CensusRecorder.LEAN_DROPPED_STREAMS`): emit, deposit, stool, gate,
unit_epoch, pickup, dose, hazard, contact, food, patch, patch_sweep. Every
aggregate a readout consumes (ignited, emitting_hosts, acquisitions_by_gen,
hosts[], census_epochs, mechanism counters) is identical under either
profile; `lean` count-and-drops the rows.

Measured: the **emits log alone is ~1.5 GB of text on mega** — the streams,
not the voyage, are what push a 7000-agent child past the midsize jobdefs.

Kept under `lean` (so still counted in the quote): the per-host census
table (∝ infected hosts), `unit_mix`/`food_mix` pool mirrors (∝ units),
`emit_host_ids`, `census_rows` (per-epoch snapshots, tiny), and —
notably — `hand_occupancy_rows`, the per-replenish-call occupancy stream
installed alongside every census voyage. **The occupancy stream is not
covered by the lean lever** and scales with shedding/carrying hosts ×
epochs; if a meg cell ever outgrows the lean quote, this is the first
stream to check.

### E. Fold/serialize spike

The census member is serialized in memory before zip write
(`json.dumps(payload)` → `gzip.compress` → `writestr`): roughly one extra
transient copy of the whole payload. `meta.fold_rss_mb` (VmHWM after fold)
is the true child peak; `meta.voyage_rss_mb` (VmHWM right after
`sim.run()`) isolates the live-voyage share. Both land in `summary.json`'s
`rss_mb` block and `rss_samples.json` — read them by ranged GET, no census
member decompress needed.

### F. Artifact write (zip members)

`write_run_zip`: `summary.json` (~20 KB compressed) + payload members.
Full-payload `growth_census.json.gz` is the bulk — ~45 MB zips on the
classic hull (the per-agent census member is ~90% of campaign volume) and
~210 MB on mega. `--full-telemetry` runs additionally pack the full
history, lab notebook, and ground truth. Zip size is *storage* memory:
cells × bytes → S3 volume (a 12k-cell campaign lands ~350 GB) → readout
scan cost.

## Scaling axes — which feature multiplies which component

| axis | A live state | B epoch transient | C retained history | D instrument rows | F zip bytes |
|---|---|---|---|---|---|
| `num_agents` (platform) | agents, occupant maps, per-agent dicts | exposure lists ∝ occupants | per-agent records ∝ agents×epochs (full only) | emit/occupancy/dose rows ∝ hosts | census member ∝ hosts/rows |
| zones | pools per zone×pathogen | zone_contact_summary | spaces map | unit_mix, unit_epoch rows | — |
| `num_epochs` | — (steady-state) | — | ∝ epochs under full | ∝ events → ∝ epochs | ∝ epochs |
| armed pathways (emesis/fomite/food/common-source/caregiver/flush/near-field/droplet…) | lazily-filled agent dicts + pools + patches | that pathway's exposure list exists and fills | its rows ride every full record | adds its row stream(s) | adds its payload block |
| realized outbreak size (per-seed) | deposition records, immune_history, event logs | hot-epoch spike | exposure rows in hot epochs | every event stream | rows → compressed bytes |
| `history_retention=full` | — | — | the dominant term on mega | — | +simulation_history member |
| `--full-telemetry` | — | — | implies full | — | +3 members |
| census `--payload full` | — | — | — | the 12 streams retained | census member ≈ payload |
| subprocess-per-run (runner default) | parent stays small; pymalloc never returns pages between in-process runs — multi-seed *local* invocations ratchet RSS across the sequence | | | | |
| `num_agents`/`epochs` overrides (smoke knobs) | scale A–E down together — a downscaled smoke understates the production quote; never size a jobdef off `--num-agents-override` | | | | |

## Combinations that decide the quote

| combination | verdict |
|---|---|
| hull ≤3000 agents × compact × any current instrument | 4096 MB — established |
| mega × compact × bare voyage (no census worker) | ~2 GB class — the generic `picard-campaign` shard jobdef runs 7000-agent sims at 2048 MB |
| mega × compact × census **lean** | 6144 MB — validated fleet-wide (max 4355 MB) |
| mega × compact × census **full** | **>6144 MB** — died at 4096 and again at 6144; 16384 MB is the only proven quote |
| mega × `full` retention | untested and unadvisable — adds ~2M per-agent epoch records on top of the voyage |
| analysis (Stan/MC/surface/bundle) | 8192–30720 MB on r-family — different CE pathway entirely |

Multiplication is not additive: full retention dominates everything under it;
under compact, the instrument payload is the next-largest term; under lean,
the voyage + occupancy + fold spike floor (~4.2–4.4 GB on mega) is what the
quote must cover.

## Campaign-level consequences of the child quote

- **Packing is memory-bound, not vCPU-bound.** Spot CE instance types carry
  ~2 GB/vCPU, so the 256-vCPU CE packs ~30 concurrent 16384-MB children (or
  ~80 at 6144, ~125 at 4096). NORO-MEGA-01's 16-GB fleet measured ~18–20
  concurrent and projected 75–100 h for 3000 cells — the quote, not vCPU
  count, set wall time (fleet cancelled on cost). Every doubling of `memory`
  halves fleet throughput at fixed CE size.
- **OOM is countable, not retried.** Jobdefs exit on `OutOfMemoryError*` /
  bare 137 while Spot `Host EC2*` reclaims still retry — so an undersized
  quote shows up as settled FAILED children, not retries
  (`deploy/aws/classify_batch_failures.py` separates the two).
- **Readout memory follows the member you fetch.** `summary.json` is a
  ~20 KB ranged GET (EOCD→CD→member blob — `outbreak_anchor_readout._s3_member_blob`);
  the census member decompresses to ~1 GB/cell on mega, so census-member
  readouts cap `--census-workers` and belong on an analysis queue, not a
  laptop. `.summary.json` sidecars keep re-readouts off the zip entirely.
- **Deep-Archive caveat for baselines:** pairing campaigns that re-read
  archived prefixes need restores scheduled before the lifecycle rule
  lands; a restored-prefix readout is an hours-scale dependency, not a
  memory problem.

## Sizing procedure for a new cell

1. Set `resources.memory` in `campaign.json` from the nearest row of the
   combinations table — same hull class, same worker, same payload profile.
   A new *combination* gets a sizing canary, not a guess.
2. Canary ≥20 seeds at the fleet's heaviest tier × payload. Read
   `rss_samples.json.peak_rss_mb` and `summary.json.rss_mb.{voyage,fold}`
   (ranged GETs; `mega_impact_canary_readout.py` already prints the
   medians).
3. Quote the fleet at **fleet max × ~1.3**, not median — realized outbreak
   size is a per-seed tail and the p-max voyage is the one that OOMs.
4. Before raising the quote: prefer `--payload lean` for scale tiers and
   keep `full` for ≤ a few hundred debug cells; never run `full` retention
   or `--full-telemetry` on mega; check whether a bespoke worker's row
   streams belong in `LEAN_DROPPED_STREAMS`.
5. If the quote must exceed ~2 GB/vCPU, the cell belongs on the
   memory pathway (`picard-analysis-memory-ondemand`, r-family) rather than
   stranding the c-family CE's cores.
6. `scripts/campaign submit` renders and registers a fresh jobdef revision
   at submit time and pins the array to it — a raised `resources.memory`
   reaches only arrays submitted after the bump; already-queued arrays keep
   their original revision. Resubmit the affected blocks: a cell whose zip
   already exists in S3 prints `SKIP … already uploaded`
   (`campaign_entrypoint._already_uploaded`), so re-running a block is
   seed-safe, but there is no seed-level masking — the whole block's array
   runs and only completed cells skip.

## Open items

- AGE-FOOD-01 wave-3 meg fleets are queued under 6144 MB with the full
  payload — per the ledger they need a raised meg jobdef + resubmit before
  the blocks reach the queue head (or a resubmit under `--payload lean`
  via block `args`).
- The occupancy stream has no lean gate (§D).
- No measured quote exists yet for mega × full retention, or for
  multi-pathogen arming on mega — treat both as unpriced.
