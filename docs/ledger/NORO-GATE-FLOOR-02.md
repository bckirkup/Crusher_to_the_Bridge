# NORO-GATE-FLOOR-02
**Date:** 2026-09-25
**Commit:** 89b91ac
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 37dc215

A **null result**. `NORO-GATE-FLOOR-01` §6.2 recorded one residual
sub-copy asymmetry — seed 8001, epoch 61, `Engine_Room`, "diverges on a
*deposit* into a still-sub-copy pool" — and proposed a deposit-side
counterpart of `SURFACE_PICKUP_MIN_GEC` to remove it. Re-reading that
entry's own committed lockstep artifacts shows the residual does not
exist: the arms' deposits are identical, and the first draw that differs
is the **existing** pickup gate opening legitimately in one arm. The
same is true of all seven divergences in the 96-epoch window. The
deposit-side gate is therefore **withdrawn, not implemented**; this entry
makes no engine change, runs no new canary and changes no rule.

## 0. Settled inputs (quoted, not re-derived)

- `NORO-GATE-FLOOR-01` (merged, #677): `SURFACE_PICKUP_MIN_GEC = 1.0`
  closes the pickup gate on sub-copy pools, pooled and per_surface, all
  pathogens, default path; `SURFACE_RESIDUE_FLOOR_GEC = 1e-12` stays
  beneath it; `DISAGG-01` identity holds (worst `1.5e-15`). Both
  constants stay unchanged.
- Its frozen canary (§4): seeds 8000–8019, `classic_cruise_1900`,
  `--bundle norwalk_only`, 288 epochs, arm A = `per_surface + areal +
  shipped`, arm D = `per_surface + declared + shipped`; the §4.1
  coincidence rule and the §4.2 event-alignment witness and
  interpretation rule. Measured 10/20 deposit-aligned at 288 epochs,
  13/20 in lockstep at epoch 96, rule indeterminate.
- Evidence read here, all committed with `-01` and measured at
  `37dc215`: `../norovirus/noro_gate_floor_01/lockstep_probe_a.json.gz`,
  `lockstep_probe_b.json.gz` (the `NORO-TOUCH-SHARE-02` lockstep
  instrumentation, `tools/noro_diag/touch_share_lockstep_probe.py`,
  96 epochs) and `touch_share_coincidence_per_surface_declared.json`.
  No engine file changed between `37dc215` and `89b91ac`, so the code
  reading in §3 applies to the measured commit.

## 1. The §6.2 misreading (measured)

Seed 8001, epoch 61, `norwalk_gi`, `Engine_Room`, from the probe's
divergence witness:

| quantity | arm A (areal) | arm D (declared) |
|---|---|---|
| pool before the epoch-61 deposit (GEC) | 0.589 | **0.965** |
| epoch-61 deposit (GEC), draw index 1167 | 0.054923 | 0.054923 |
| pool after the deposit (GEC) | 0.644 | 1.0195 |
| `pickup_gate_open` | shut (< 1) | open (≥ 1) |
| next draw | `challenge|norwalk_gi` `random` | `fomite.pickup_requests_by_class|norwalk_gi|Engine_Room` `uniform` |

- The `0.965 GEC` quoted in `-01` §6.2 (and in its "max |mass| at
  divergence" column) is **arm D's pre-deposit pool**, not the size of
  the deposit. The deposit was `0.0549 GEC`, **identical in both arms**,
  at the same draw index.
- The draw streams are identical in context, method and argument shape
  through draw 1168; the first differing draw (1169) is the pickup-
  request draw inside arm D's `pickup_by_class` event on a
  `1.0195 GEC` pool. Arm A, on `0.644 GEC`, skips that event and
  proceeds to its next challenge draw.
- The pools had **already parted** before epoch 61. The probe's first
  per-class mass difference is at epoch 50, `Engine_Room`,
  `button_or_dispenser`: a pickup from a `≥ 1 GEC` pool delivered
  `0.061 GEC` from that class in A and `1.138 GEC` in D — the declared
  table doing what it declares.

So the divergence is the `-01` gate behaving correctly on two pools that
the treatment itself had made different: D is above one copy and picks
up, A is below one copy and does not. No deposit is involved.

## 2. The other six diverged seeds (measured)

Same anatomy on every seed. "First parted" is the probe's
`ordering_witness`: the first (epoch, zone, class) at which a per-class
pickup delivery differs between arms. "Gate zone" is the zone whose
pickup event is present in D and absent in A at the first differing
draw (for 8003 and 8008 arm A's next draw is a pickup at a later zone
whose gate is open in both arms, so the gate zone is read from D's
event and the probe's per-zone mass diff).

| seed | first parted: epoch, zone, class | A / D delivered from that class (GEC) | divergence epoch | gate zone | pool A / D at the gate (GEC) | deposits into gate zone that epoch |
|---|---|---|---|---|---|---|
| 8001 | 50, `Engine_Room`, `button_or_dispenser` | 0.061 / 1.14 | 61 | `Engine_Room` | 0.644 / 1.02 | 0.0549 in both |
| 8003 | 19, `SpaFit`, `button_or_dispenser` | 8.47 / 341 | 36 | `PoolDeck` | 0.806 / 26.5 | not in witness |
| 8005 | 37, `KidsClub`, `button_or_dispenser` | 0.071 / 5.30 | 65 | `KidsClub` | 0.765 / 1.36 | none |
| 8007 | 43, `Promenade`, `button_or_dispenser` | 0.025 / 0.417 | 89 | `PhotoShops` | 0.854 / 3.90 | 0.0 in both |
| 8008 | 22, `Reception`, `button_or_dispenser` | 1.10 / 57.0 | 45 | `Reception` | 0.837 / 4.81 | none |
| 8014 | 10, `MainTheater`, `button_or_dispenser` | 0.041 / 0.686 | 83 | `Casino` | 0.543 / 1.03 | 0.0 in both |
| 8017 | 87, `MainTheater`, `button_or_dispenser` | 0.702 / 11.9 | 91 | `Casino` | 0.756 / 1.04 | 0.0 in both |

On all seven seeds:

1. every draw before the first differing draw is identical in context,
   method and argument shape (the probe's lockstep criterion), so no
   earlier deposit — whatever its mass — changed the draw stream;
2. the pools first part at a `button_or_dispenser` pickup from a
   `≥ 1 GEC` pool, i.e. the declared-vs-areal reallocation;
3. at the gate zone D's pool is at or above 1 GEC and A's is below it,
   so D enters `pickup_by_class` and A does not. Every one is the `-01`
   gate firing correctly; the probe's `expected` classification in
   `-01` §6.2 stands.

In 8007, 8014 and 8017 the gate zone differs from the first-parted zone:
the reallocation reaches it through later hand loads and pickups, not
through a deposit draw.

Seeds 8015 and 8018 stay in lockstep through epoch 96 and diverge later;
the 96-epoch probe does not see them and this entry does not classify
them.

## 3. Deposits draw no RNG (inferred, code reading at `89b91ac`)

- `TransmissionEngine._deposit_surface_mass` and
  `PerSurfaceFomiteState.deposit` (`engines/fomite_surfaces.py`) are pure
  arithmetic: they add the mass to the pooled, per-pathogen, cleanable
  and per-class compartments and call no generator.
- In `_pathway_fomite`'s deposit loop the draws per shedder
  (`rng.uniform(SURFACE_CONTACT_FRACTION_RANGE)`,
  `rng.lognormal(HAND_TO_SURFACE_LOGNORMAL)`) are made for every
  non-confined shedder **before** the deposit is computed, and do not
  depend on the pool's contents or on the touch-share mode.
  `_replenish_hand` and the strain-attribution bookkeeping
  (`_deposit_reservoir_strains`) draw nothing.
- The only pool-dependent branch in the fomite pathway is
  `pickup_gate_open(surface_mass)` before pickup.

A deposit therefore cannot by itself create an asymmetric RNG stream
between arms. A deposit-side gate on a sub-copy pool has nothing to
suppress: it could only change the stream by stopping a pickup from a
`≥ 1 GEC` pool, which is the treatment effect the canary is trying to
measure. This is an inference from reading the code; §2 is the
measurement that agrees with it on seven seeds.

## 4. Consequence for the frozen rule (inferred)

The §4.2 `aligned` witness requires equal deposit calls, equal
deposited GEC and equal hand-to-mouth calls over the voyage. At this
cell, on the seven seeds of §2, it is broken by the declared table's own
reallocation. Any pickup from a unit where the two tables share out mass
differently changes the pool left behind. Once one arm's pool crosses
1 GEC and the other's does not, the pickup events differ and the streams
part. The witness therefore counts the treatment effect as
misalignment.

The 10 seeds that stay aligned are the ones where the reallocation never
flips a gate. Five of them credit no fomite host at all (8004, 8009,
8012, 8013, 8016), and one credits two (8006). Conditioning on alignment
selects seeds where the treatment had little or nothing to act on. That
is why every aligned seed shows `H_A == H_D` and why the interpretable n
is about 4–5.

Three consequences follow:

- The aligned fraction is bounded near the measured **10/20** at this
  cell. It cannot be raised by gate repairs: the pickup gate is already
  exact at one copy, and the deposit path draws nothing (§3).
- The frozen §4.1 rule, read under the §4.2 interpretation rule, cannot
  become determinate at `classic_cruise_1900` / `norwalk_only` / n = 20
  through further repairs to the gate.
- The frozen rule is **not** changed here. A rule that scores
  paired-host-set outcomes without requiring stream alignment would be a
  new, separately declared design.

## 5. What changed

- This entry.
- A correction note in `NORO-GATE-FLOOR-01` §6.2 pointing here.
- No engine, constant, test, golden, readout or rule change. No canary
  was re-run. `SURFACE_PICKUP_MIN_GEC` and `SURFACE_RESIDUE_FLOOR_GEC`
  are unchanged. `per_surface` and `declared` stay non-default. No
  absolute dose figure is quoted; the GEC values above are surface-pool
  bookkeeping from the `-01` artifacts, used only to locate the gate
  crossing, and remain subject to the norovirus open ledger's
  withdrawal of dose figures.

## 6. Next decision

The coincidence rule stays **indeterminate** at this cell. The options:

- **(b)** Run the same frozen design at a cell with more fomite-active
  seeds.
- **(c)** Run an AWS block under a newly declared rule that scores
  paired-host-set outcomes without requiring stream alignment.
- **(d)** Stop the touch-share line.
