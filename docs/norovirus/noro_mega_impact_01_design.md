# MEGA-IMPACT-01 — mechanism-attribution factorial on mega_cruise_5000

Status: measured — fleet readout committed at
`noro_mega_impact_01_readout.md` (2026-10-05); measured state in
`docs/ledger/NORO-MEGA-IMPACT-01.md`. Fleet record: 618/618 cells
SUCCEEDED, zero failures, ~4.5 h wall on Spot
(`picard-campaign-queue`), jobdef `picard-noro-mega-impact-01:6`,
image `campaign-7e1b54bc` (sha256:60793dd3…, `--payload lean`,
6144 MB/child — canary lean peak max 4313 MB). Arrays:
a1 `3dd8057e-71c8-4dc7-b6da-1a71578b6437` (268 cells, index_offset 20 →
seeds 8020-8287; canary seeds 8000-8019 already on record),
a2 `551bb8b7-272f-4567-acf8-0ab5ac954bf0` (150, seeds 8000-8149),
a3 `a280586c-bce1-4b48-9a98-9589cdbb1d57` (150, seeds 8000-8149),
a1_bp40c30 `2a1f11f7-41d9-43b5-8851-5c93ed3e2e36` (50, seeds 8000-8049 —
optional distributional slice; no A0 exists at bp40c30 so no pairing).
Two burned submissions: rev 4 hit the 8192-char container-override cap
again at materialization (the cap measures the whole materialized
overrides object, so a 7,186-char `-c` blob does not fit) and rev 5's
bootstrap splice dropped a `;` producing `;;`/missing-separator
SyntaxErrors in every child — terminated within minutes, zero cells
ran. Rev 6 compresses every tier's consecutive `seeds` list to
`seed_range` expanded in the bootstrap (-c 4,165 chars, executed
locally before registering). Canary details below.
Canary read out — 2026-10-04. All three frozen gates PASS;

readout in `noro_mega_impact_01_canary_readout.md`. Canary ran On-Demand
(`picard-analysis-queue`) after a Spot drought: a0id
`d448f12c-420e-4edf-8776-c594d83ab2b9` (n=10, tier
`fl_mega_impact_a0id` — caregiver on / food off, seeds 8000-8009) and
a1 `23c2b524-0413-4a0f-ab76-ba3102b965e3` (n=20, seeds 8000-8019).
jobdef `picard-noro-mega-impact-01:3`, image
`campaign-f31de83a` (sha256:9ac735da…, `--payload lean`, 16 GB/child).
One witness defect found and fixed (common-source event rows expired
with their meal windows; permanent `_cs_event_log` added) — fleet image
should rebuild on this commit.
Baseline evidence: `noro_mega_01_baseline_reanalysis.md`
(committed, measured). Driver: `tools/noro_diag/growth_chain_census.py`
with `--payload lean` (PR #888).

## Question

Why does the model's mega-class fleet never post to VSP? Specifically:
what does each of the two newest observation/transmission mechanisms —
**CAREGIVER-V1** (cleanup/tending/service roles, default-ON since its
ship) and **FOOD-COMMON-SOURCE-01** (provisioned-lot / ill-handler /
ill-diner events, default-ON, norwalk_gi armed) — move on the mega cell
that NORO-MEGA-01 measured?

This is an arm comparison, not a lattice: the question is which
mechanism moves which readout, by how much, on the one cell the fleet
already measured.

## What the baseline already says (do not re-derive)

From `noro_mega_01_baseline_reanalysis.md` (308 zips, ranged reads):

- **No tail at the threshold.** Best voyage reaches 72–75% of either
  channel's report threshold; 0/308 reach 80%. Medians: pax 56 reports
  (38% of threshold), crew 18 (29%).
- **Every curve is a ramp clipped at disembarkation.** peak_epoch = 287
  on all 308 voyages; 291/308 still acquiring in the final 2 epochs.
- **Onset is smooth.** burst12 median 0.184, max 0.285 — no voyage
  concentrates even 29% of aboard cases in a 12-epoch window (the
  point-source signature the common-source mechanism exists to inject).
- **Aboard chain is surface-dominated.** 24-zip census sample:
  fomite 95.1%, caregiver 3.3%, direct_contact 1.1%,
  emesis_aerosol 0.4% of aboard acquisitions. `food` /
  `common_source_food` share is zero by construction in these runs —
  any nonzero share in the new arms is a pure mechanism effect.
- **Detection is last-day.** 33/308 detect at median epoch 282.

Honest expectation frozen here: the question is whether the gap
*moves materially* and how much of the move is food's burst vs
caregiver's discovery/crew channel — not whether posting closes
outright. A closing move would need ~1.4–2.6× more reports on the
typical voyage or concentrated onset the ramp cannot produce.

## Design

2×2 factorial on `fl_mega_12d_scr × bp25c7`, seeds 8000–8287 (the
measured window):

| arm | caregiver | food | n | role |
|---|---|---|---|---|
| A0 | on | off | 288 | **existing zips — free** |
| A1 | on | on | 288 | per-seed paired to A0 |
| A2 | off | off | 150 | distributional baseline for caregiver |
| A3 | off | on | 150 | food-without-caregiver + interaction |

~588 new cells. Two properties make the design cheap in information
terms:

1. **Food pairs per-seed almost exactly.** Every food draw rides a
   dedicated `SeedSequence(spawn_key=0xF00D)`; same seed with food ON =
   identical voyage plus injected events (divergence only through
   food-attributed infections). A1-vs-A0 at the same seed is near-exact
   attribution with no new baseline cost.
2. **Caregiver is distributional** (shared-RNG draws) — but A0 already
   measured the caregiver-ON distribution, so only the OFF arms cost.

Arms are `config_overrides` on the manifest tiers
(`transmission.caregiver.mode`, `transmission.common_source.mode` —
both default `on`; A2/A3 switch them off). `norwalk_gi` is armed for
`common_source_events` in `active_profiles.json`.

## Memory plan (the prior blocker)

NORO-MEGA-01 ran 16 GB/child and the fleet never measured where it
went. The decompose is voyage RSS + census event streams + the
dumps→gzip finalize spike (emits ≈ 1.5 GB text on mega). This campaign
runs `--payload lean`: the twelve per-event row streams are counted,
not retained, while every aggregate the readouts need (ignited,
emitting_hosts, acquisitions_by_gen, hosts[], census_epochs, occupancy,
mechanism counters) is identical. Each run zip also carries
`rss_samples.json` — wall-clock RSS curve + post-serialize VmHWM peak —
so the fleet quote is re-derived from measurement, not the blanket
16 GB. Jobdef keeps 16384 for the canary; the canary's `peak_rss_mb`
decides the fleet value (expect ~6–9 GB).

## Output contract (new fields the scan reads)

`summary.json` gains a compact `mechanisms` block
(`common_source_events`, `common_source_takers`,
`caregiver_responses`, `caregiver_reports`, `payload_profile`) and
`rss_mb` — readable by ranged GETs without decompressing the census
member. The census member gains `caregiver_telemetry` and
`common_source` (event witness records harvested from
`core._cs_windows`: zone/meal/service_type/source_kind/pan_mass/
per_serving_dose/cohort_size/taker_ids).

## Readouts (per arm)

- report-count distributions vs the 150/60-equivalent thresholds
  (3% of complement, rounded up) — med/p90/max and the ≥80%/90%/95%
  reach counts;
- burst12 share, still-climbing share, peak-epoch placement;
- detection-epoch distribution;
- funnel rungs with the via_caregiver split (A0/A1 vs A2/A3);
- caregiver share of aboard acquisitions (>10% triggers a deeper look);
- food: events provisioned/handler/diner counts, takers served,
  `common_source_food` pathway share, event-positive-vs-negative
  voyage split (the per-voyage rate draw is where the tail lives);
- per-seed A1-vs-A0 deltas on every above (paired).

## Admissibility criteria (frozen before any cell runs)

- **Bit-identity gate**: a food-OFF, ~10-seed canary at the new image
  must reproduce the corresponding existing zips' `summary.json`
  voyage fingerprints bit-for-bit (parameters, timeseries, derived
  blocks). Any mismatch → the new image realizes different voyages;
  per-seed pairing is void and the campaign redesigns on
  distributional arms only.
- **Exercise gate**: A1 canary n=20 must record
  `common_source_events > 0` on at least one voyage (proves the
  mechanism fired — the blocker-cascade rule). Zero events → inspect
  arming before spending cells.
- **Peak-memory report**: canary `rss_samples.json` medians decide the
  fleet memory quote; if lean-mode peak still exceeds ~10 GB, keep
  16 GB and cap fleet concurrency at the memory-bound ~30 rather than
  quoting OD ~100.
- No constants are fitted to the VSP/Park/attack-rate anchors;
  every number above is reported measured/inferred/hypothesis as
  marked in the reanalysis.

## Fleet plan

- Image: current merge SHA (lean payload + mechanisms block).
- Jobdef: `deploy/aws/batch_job_definition_noro_mega_impact_01.json`
  (manifest embedded in the `-c` bootstrap; `--payload lean`; per-tier
  submission via `tier` parameter, array index maps one child → one
  voyage).
- Order: canary (bit-identity n=10 food-OFF + A1 n=20) → **stop and
  report** → user decides the fleet (A1 288 + A2/A3 150+150).
- Cost at canary-proven concurrency: ~588 cells ≈ 4.5–6 h On-Demand
  (~100/hr) or 12–18 h Spot (~25–40/hr). Open decision, deferred to
  canary report: queue choice; optional n≈50 A1 slice at bp40c30.

## Non-goals

No boarding-prevalence or rung sweep (single cell). No re-measurement
of A0 (the zips exist). No constant refits. No emits-based
growth-chain attribution — that is deliberately what `lean` drops.
