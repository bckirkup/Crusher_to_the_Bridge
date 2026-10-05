# MEGA-IMPACT-01 canary readout — the three frozen gates

**Measured at:** image `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign@sha256:9ac735daccc5e10e20f1945cd341f120b876a1efd6520fca2d51f56c77b7502a`
(`campaign-f31de83a`; engine SHA `f31de83aba3820f1c59ee705617c4ac92172e6fb`,
jobdef `picard-noro-mega-impact-01:3`). All 30 cells On-Demand
(`picard-analysis-queue`) after a Spot drought parked the original
`picard-campaign-queue` arrays ~1h RUNNABLE with zero placement. Zips under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_mega_impact_01/`.
Readout: `tools/noro_diag/mega_impact_canary_readout.py` (ranged zip-member
GETs, no full downloads).

## Gate 1 — bit-identity: **PASS** (10/10)

a0id tier (caregiver on / food off, seeds 8000-8009) vs the A0 zips at
`campaign/noro_mega_01/fl_mega_12d_scr` — every shared leaf of
`parameters` / `timeseries` / `derived` / `summary` / `cost_accounting` /
`census` / `initiation` identical. The only diffs are the two declared
provenance leaves, `parameters.engine_git_sha` (image stamp) and
`parameters.tier_id` (the tier label differs by construction — a0id is the
same voyage under a different tier name). New-schema keys on the canary zips
(`mechanisms`, `rss_mb`) are reported as additions, not voyage diffs.

**Measured**: 10/10 seeds bit-identical. Food-off on the new image reproduces
the A0 voyage exactly — the 0xF00D dedicated stream is confirmed
draw-isolated, so A1's paired-vs-A0 attribution design is sound.

## Gate 2 — exercise: **PASS** (mechanism fired on every voyage)

The frozen criterion reads `mechanisms.common_source_events > 0`. On this
image that summary field is a **broken witness** (see below) and reads 0 on
every zip. The durable truth — `growth_census.json.gz →
common_source.telemetry.events_*` — shows the mechanism firing on every a1
voyage:

| seed | events | ill_handler | ill_diner | provisioned_lot | takers |
|---|---|---|---|---|---|
| s8000 | 51 | 41 | 10 | 0 | 1261 |
| s8001 | 103 | 38 | 65 | 0 | 2840 |
| s8002 | 85 | 4 | 81 | 0 | 2649 |
| s8003 | 123 | 36 | 87 | 0 | 3762 |
| s8004 | 70 | 25 | 45 | 0 | 2110 |
| s8005 | 56 | 6 | 50 | 0 | 1659 |
| s8006 | 115 | 82 | 33 | 0 | 2944 |
| s8007 | 64 | 39 | 25 | 0 | 1632 |
| s8008 | 134 | 16 | 118 | 0 | 4031 |
| s8009 | 41 | 22 | 19 | 0 | 1227 |
| s8010 | 64 | 16 | 48 | 0 | 1426 |
| s8011 | 109 | 9 | 100 | 0 | 3201 |
| s8012 | 90 | 42 | 48 | 0 | 2478 |
| s8013 | 144 | 41 | 103 | 0 | 4257 |
| s8014 | 131 | 54 | 77 | 0 | 3663 |
| s8015 | 186 | 66 | 120 | 0 | 5105 |
| s8016 | 42 | 15 | 27 | 0 | 1048 |
| s8017 | 105 | 56 | 49 | 0 | 2605 |
| s8018 | 31 | 7 | 24 | 0 | 906 |
| s8019 | 80 | 27 | 53 | 0 | 2322 |

All 20 a1 cells fired (20/20).

**Measured**: 31-186 common-source events per voyage, 906-5105 takers
served, `common_source_food` dose share present but small (s8000: 0.0002 of
total dose share). `caregiver_responses` nonzero on all cells (5-17) —
CAREGIVER-V1 also exercised.

**Provisioned-lot arm silent on all 20 cells.** The lot is one Bernoulli per
voyage at `lot_event_probability ~ U(0.02, 0.15)`: P(0 lots in 20 voyages)
≈ 0.17 at the interval midpoint — a plausible draw, not evidence of a
defect. Fleet note: the 588-cell fleet will exercise the lot path on only
~6-9% of voyages (≈35-55 cells), so lot-pathway interpretation will rest on
a thin subsample — expected, but worth knowing before reading the
factorial.

### Defect found: common-source event witness undercounts to zero

`mechanisms.common_source_events` counts
`len(payload["common_source"]["events"])`, and `_common_source_block`
(`tools/noro_diag/growth_chain_census.py`) populated `events` from live
`_cs_windows` states. `_cs_expire_windows` deletes each window — with its
`state["event"]` record — once the meal window closes, so every event record
is gone by voyage end. The permanent accumulator `common_source_telemetry`
(`events_<kind>`, `takers_served`) is correct and proves the mechanism ran.

Fixed in this PR: `_cs_fire` now appends each event to a permanent
`self._cs_event_log`; `_common_source_block` reads that list. No draw or RNG
change (a0id bit-identity unaffected — food-off fires nothing; A1 voyage
draws identical — the log is pure witness). **Fleet image should be rebuilt
on this fix** so fleet zips carry event witness rows and the summary counter
works as designed; canary zips are scored on telemetry.

## Gate 3 — peak memory: 4.2 GB → fleet can drop to ~6 GB/child

n=30 cells (10 a0id + 20 a1):

- voyage_rss median **2289 MB**, fold_rss median 2303 MB
- `rss_samples.json` peak: median **4217 MB**, p90 4252, max **4313 MB**

The design's keep-16GB trigger (lean peak > ~10 GB) is not met — the 16 GB
quote was sized on the full-payload census spike that `--payload lean`
removes. Recommendation: **6144 MB/child** (45% headroom over max observed,
comfortable round quote; the script's ~30%-over-median formula yields 5632
MB). At 1 vCPU/6 GB the same CE memory footprint roughly doubles fleet
concurrency vs 16 GB.

## Fleet inputs for the decision

- Image: rebuild on the witness fix (new digest), jobdef rev 4, memory
  6144 MB (or keep 16 GB for zero risk — decide).
- Bit-identity pairing confirmed; per-seed attribution valid for all arms.
- Queue: On-Demand worked at 256 vCPU desired after a real Spot drought;
  Spot may still be cheaper if it recovers — the drought cost ~1h wall.
- Cells: ~34 min/voyage at these sizes.
