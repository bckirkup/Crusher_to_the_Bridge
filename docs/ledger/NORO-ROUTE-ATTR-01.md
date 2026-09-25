# NORO-ROUTE-ATTR-01
**Date:** 2026-09-25
**Commit:** 8662a76f
**Pathogens:** norwalk_gi
**Status:** declared

`NORO-TOUCH-SHARE-RATE-01` (measured `411b0dbe`) measured the declared
touch-share table's *dose-crediting* expression rate at the frozen cell:
49/100 seeds express, and a fresh n = 20 canary fires the frozen
coincidence rule only ~11% of the time — the n = 20 indeterminate is
structural. What the crediting analysis cannot answer is whether the
reallocation changes **infection outcomes**: in the n = 100 block,
secondaries moved only −1..+1 per seed, hinting that declared-vs-areal
shifts who is *credited* dose but barely shifts who gets *infected*.

The engine now records `acquired_particles_by_route` per established
infection (and tallies `infections_by_dominant_route` /
`infection_dose_share_by_route` in the run record), so the question can
be asked directly at the infection level: **does the declared touch-share
table change which hosts acquire norwalk via the fomite route?**

## 0. Settled inputs (quoted, not re-derived)

- **Frozen cell** (`NORO-COINCIDENCE-CELL-01` §2): `spirit_cruise_3000`
  × `--bundle norwalk_only` × 168 epochs.
- **Mechanism** (`NORO-GATE-FLOOR-02`, merged): every A-vs-D divergence
  is the declared table's own reallocation tipping a pickup across the
  1-GEC gate; deposits draw no RNG.
- **n = 100 crediting readout** (`NORO-TOUCH-SHARE-RATE-01` §3,
  measured `411b0dbe`): expression 49/100 (Wilson 95% [0.394, 0.587]);
  secondaries −1..+1 per seed; 13/100 seeds carry ≥1 secondary in the
  areal arm, 14 in either arm; 8 extinct seeds (8001, 8018, 8021, 8054,
  8059, 8079, 8085, 8094); DISAGG-01 identity holds 100/100.
- **Power note (measured, this entry's design constraint):** only
  ~14/100 seeds have any secondary, so route attribution reads ~40–80
  infections total. Sparse but paired — every statistic below handles
  zeros honestly.
- **Operator decisions:** declared table stays pathogen-agnostic; pooled
  stays default; no constant changes; `HIGH_TOUCH_AREA_M2` untouched;
  `per_surface`/`declared` stay non-default. No dose or attack-rate
  selection — absolute dose figures are withdrawn.
- **DISAGG-01 re-witnessed, not re-derived:** this entry's diff adds
  read-only recorder fields (post-challenge reads of the infection
  record and the run history); no RNG path is touched, so runs are
  byte-identical to the `411b0dbe` block. Local smoke on seed 8022
  confirms identical acquisition rows (`dose_read`, `effective_dose`,
  `frailty`, `hazard`) vs the committed dump. The `pooled` arm is kept
  in the block anyway so the areal-vs-pooled identity is re-checked on
  the rebuilt image for all 100 seeds.

## 1. Design (declared before submit)

**Cell:** frozen `spirit_cruise_3000` × `norwalk_only` × 168 epochs.

**Arms:** the frozen triad — `per_surface_areal`,
`per_surface_declared` (table
`data/config/fomite_touch_share_declared.json`), and `pooled` as the
DISAGG-01 identity witness on the new image.

**Seeds:** 8000–8099 (n = 100). All seeds re-run — the committed dumps
predate the route-ledger instrumentation — so each new run carries the
same instance as the crediting block (engine byte-identical), letting
the attribution readout join the crediting readout per seed.

**Driver change:** `tools/noro_diag/per_host_dose_challenge.py` —
acquisition records gain `acquired_particles_by_route` +
`dominant_route`; the dump gains `transmission.route_attribution` =
{`engine_tally` harvested from the final epoch record's
`infections_by_dominant_route` / `infection_dose_share_by_route`,
`recomputed` independently tallied from the recorded acquisitions}.
Verified on smoke seed 8022: engine tally and recompute agree exactly.

**Submission:** AWS Batch EC2 Spot array on `picard-campaign-queue`,
300 children = 3 arms × 100 seeds, worker
`deploy/aws/dose_challenge_entrypoint.py` (unchanged — same arm
matrix), image `picard-boundary-analysis:dose-challenge-v2`,
1 vCPU / 4096 MB, job def `picard-dose-challenge`. Cost ≈ 20 CPU-h at
the measured ~237 s/run; wall ≈ 20–35 min. Dumps upload to
`s3://<BUCKET>/campaign/route_attr_01/arm_<tag>/` and sync to
`docs/norovirus/route_attr_01/arm_<tag>/`.

**Stop conditions (frozen).**

| condition | action |
|---|---|
| canary child fails / writes no dump / dump lacks route fields | stop, fix, report |
| engine_tally ≠ recomputed dominant counts on any dump | report — attribution witness broken |
| every acquisition lacks `acquired_particles_by_route` on a seed with secondaries | report — attribution not firing |
| Spot/OOM failure rate makes 100 seeds unreachable | sync partial, report partial stats |

## 2. Readout (frozen)

Over 100 paired seeds (declared arm vs areal arm, same seed = same run):

1. **Route composition per arm**: total secondaries per arm; dominant-
   route counts (fomite / droplet / direct_contact / other) summed over
   100 seeds; fomite share of secondaries with Wilson 95% per arm.
2. **Paired secondary count delta**: per-seed `secondaries_D −
   secondaries_A`; distribution, median; two-sided sign test on nonzero
   pairs.
3. **Fomite-attributed infection sets**: per seed, the set of hosts
   whose `dominant_route == "fomite"` per arm; Jaccard per seed
   (0/0 → 1.0 vacuous, flagged), fraction of seeds with differing
   fomite-attributed sets, and the count of seeds where the arms'
   *infected host sets* differ at all.
4. **Dose-share comparison**: per-seed `fomite` entry of
   `infection_dose_share_by_route` D − A among seeds with ≥1 secondary
   in either arm; median and distribution.
5. **Discordant acquisitions**: seeds where an agent is infected in one
   arm and not the other, or infected in both with different dominant
   route — counted and listed.
6. **Readout question answered**: does the declared table move
   infection-level route attribution, or is its expression confined to
   dose-crediting bookkeeping? Verdict reported as measured with the
   n = 100 confidence intervals, not a binary fire/no-fire rule.

## 3. Measured

<!-- measured -->
