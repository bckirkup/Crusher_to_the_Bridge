# COVID-TAKEOFF-ATTR-01-RERANK
**Date:** 2026-09-27
**Commit:** 264fa5cb
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 264fa5cb

SHIP-RHYTHM-02 bounded re-rank of the two COVID-TAKEOFF-ATTR-01 (`bcf2ac95`)
exposure-set metrics — per-epoch dosed-set size and
`challenged_share_of_aboard` — with the day-program rhythm layer ON. Same
instrument (`tools/covid_takeoff_attribution.py`), same Θ = 2.37e11
(admissible-band midpoint), same cell family as the baseline: 10 of the
20 stage-2 replay cells, seeds 20200205–20200214, 768 epochs,
diamond_princess_2020 (mega_cruise_5000). Measured on the PR #742/#746
tree; rhythm default-on, no Θ or dose-ledger change (non-goal). Two local
jobs (5 cells each) on the session box; raw readouts at
`telemetry_buffer/rhythm_rerank_{A,B}.json`.

## Headline moves vs baseline

Per-seed figures across the 10 re-rank cells (baseline column: the 20-cell
ATTR-01 record at `bcf2ac95`):

| seed | rec onsets | infections | dosed/epoch median | dosed/epoch mean | challenged |
|---|---|---|---|---|---|
| 20200205 | 1,520 | 3,588 | 657 | 1,421 | 3,710/3,711 |
| 20200206 | 3,497 | 3,557 | 644 | 1,024 | 3,710/3,711 |
| 20200207 | 3,567 | 3,581 | 558 | 785 | 3,710/3,711 |
| 20200208 | 1,911 | 3,599 | 730 | 1,369 | 3,710/3,711 |
| 20200209 | 3,091 | 3,541 | 811 | 1,216 | 3,710/3,711 |
| 20200210 | 3,542 | 3,575 | 618 | 938 | 3,710/3,711 |
| 20200211 | 3,340 | 3,409 | 607 | 764 | 3,710/3,711 |
| 20200212 | 3,528 | 3,537 | 659 | 867 | 3,710/3,711 |
| 20200213 | 3,466 | 3,577 | 690 | 1,088 | 3,710/3,711 |
| 20200214 | 3,433 | 3,586 | 604 | 1,051 | 3,710/3,711 |

- **Median dosed set: 705 → 650.5** (median-of-medians; per-seed range
  558–811 vs baseline 577–865). A real but modest shrink (~8%) at the
  median. The distribution's tail got *heavier*, not lighter: per-seed
  means run 764–1,421 and per-epoch q95 reaches 3,648 (baseline ceiling
  3,621) — pour-out corridor fronts and whole-ship program templates
  concentrate co-presence into mass epochs instead of uniformly thinning
  every epoch.
- **`challenged_share_of_aboard` stays 1.0 on every seed** (3,710 of
  3,711 aboard challenged at least once — identical to the baseline
  reading). The re-rank target `< 1.0` is not met on this metric. The
  metric is a voyage union: ~600+ dosed hosts/epoch over 768 epochs
  covers the whole ship regardless of how the per-epoch set is
  partitioned. The meaningful per-epoch figure is the *share per epoch*:
  median 650/3,711 ≈ 17.5% of aboard, vs baseline 705/3,711 ≈ 19%.
- **Takeoff mass unchanged in the median.** Recorded onsets median
  3,449.5 (baseline 3,475); infections median 3,576 (baseline ~3,590).
  Two seeds fell out of the baseline range entirely (2,050,205 → 1,520;
  2,050,208 → 1,911 recorded) — schedule clustering suppresses the burn
  on some draws — but the pooled mass class (~12–18× over the 197 record)
  holds.
- Per-channel footprints all shrink at the median (median-of-medians,
  targets/epoch): hvac 560→~460 (q95 ceiling 3,548→3,648 widened),
  cabin_mate_ring 150→~135, contact 66→~60, near_field_plume 10→~7.5,
  dining_ring 10→~8.5; **zone_pool 16→~20 grows**.
- Onset route mix shifts toward the corridor pool: zone_pool share of
  onsets 43.3%→53% median (46–67% per-seed), plume 22.6%→16%,
  dining ~22%, cabin_mate ~7%, hvac ~1% — consistent with the
  sleep-in-cabin share of the 24-tuple concentrating co-presence in
  cabin corridors.
- Infecting λ medians rise (per-seed 0.49–1.75 vs baseline 0.42) and
  `share_ge_1` 34.6%→36–59%: the residual challenge mass is more
  concentrated into sure-thing draws when a crowded program epoch fires.
- `droplet_unattributed_onsets` = 0 across all 10 cells — attribution
  remains complete under the new placement layer.

## Verdict

The named mechanism class stands **weakened, not closed**. Rhythm
partitions the per-epoch exposure set in the right direction — every
dosed/footprint median moved down, and two seeds' recorded burns dropped
out of the baseline range — but the moved magnitude (~8% at the median)
is far short of the order-of-magnitude partitioning (705 → ~50–100
hosts/epoch) the baseline estimated the 197-record requires, and the
voyage-union `challenged_share_of_aboard` cannot move under any
per-epoch partition: with ~600 hosts dosed per epoch, everyone aboard is
challenged within days of epoch count. The exposure-partitioning deficit
ATTR-01 named therefore survives in bound form: closing it needs a
per-epoch cap mechanism (venue capacity, contact budget) — still the
sourcing question the baseline left open — not schedule assignment
alone. The lottery signature persists (median λ ~0.5–1.7, ~26–60% of
infections at λ ≥ 1), so the residual remains challenge-count-shaped,
not titre-shaped.

## Scope note

Measured only. No constants, Θ, or dose-ledger fields moved; flag-off
byte-identity re-proven (`rhythm.enabled: false` reproduces the baseline
draws bitwise — fingerprint 92c9a154…). Raw cell payloads:
`telemetry_buffer/rhythm_rerank_{A,B}.json` (scratch; this entry is the
durable record).
