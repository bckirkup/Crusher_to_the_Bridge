# NORO-FOMITE-DISAGG-01
**Date:** 2026-09-22
**Commit:** 6594c6e
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 622f99f

Per-item-class fomite surface representation (option B of
`../proposals/fomite_surface_disaggregation_spec.md`) shipped as a labelled,
default-off arm, gated on its neutrality identity (spec §3.4). §§0–5 are the
frozen design and acceptance gate, written **before** the identity block ran;
§6 is filled only from the measured block. Every dose quantity here is a
paired ratio or difference against a withdrawn baseline
(`../norovirus/norovirus_open_ledger.md` §1) and is relative/derived, never a
dose result.

## 0. Settled inputs (quoted, not re-derived)

- **`NORO-TRANSFER-PRODUCT-01`** (`bd462c5`): per-touch dose is exactly
  `1/A`; the areal denominator `HIGH_TOUCH_AREA_M2` is the single unsourced
  term carrying the route's magnitude.
- **`NORO-HIGH-TOUCH-AREA-01`** + `g0.25` canary (`25eaa17`): whole-voyage
  dose does not scale with `A` and is not resolvable at n = 20.
- **`NORO-HIGH-TOUCH-DEFINITION-01`** (`97b6af7`): `ITEM_AREA_M2` and
  `ZONE_ITEM_SETS` (three readings `hardware`/`shared`/`broad`). This entry
  **promotes those tables to engine inputs** (moved verbatim to
  `engines/fomite_surfaces.py`; the envelope tool re-imports them) and adds
  no item, area or count.
- **`NORO-HIGH-TOUCH-SWEEP-01`** hardware canary (`06b3239`, seeds
  8000–8019): galley measures the conservation cap at small `A`; remaining
  arms skipped in favour of this deliverable. `HIGH_TOUCH_AREA_M2` is a
  lumping parameter with no literature referent (`∅nr`/`∅lit`, registered
  twice, not re-retrieved).
- **Untouched:** `HIGH_TOUCH_AREA_M2`, `SANITARY_HIGH_TOUCH_AREA_M2_PER_WC`,
  `ROUTINE_CLEANING_COVERAGE`, every physical constant; no numeric touch
  share is declared or adopted (Jin/Zhang/Ackerley are the next session).

## 1. The seam (as shipped in PR1)

`transmission.fomite_representation: pooled | per_surface`, default `pooled`.
Absent or `pooled` runs the pre-change code with no extra RNG draw (every hook
is an attribute guard, `self._per_surface is None`). Under `per_surface`:

| key | values | default | meaning |
|---|---|---|---|
| `fomite_touch_share` | `areal` / `declared` | `areal` | `areal`: share ∝ `count × area_each`; `declared`: hook reading `fomite_touch_share_table` (zone class → item class → share, sums to 1); a class absent from the table falls back to `areal`. Table may be empty/unset. **No numeric table exists in-tree.** |
| `fomite_area_basis` | `shipped` / `derived` | `shipped` | `shipped`: per-item areas scaled so the unit roll-up equals the pooled `_fomite_surface_area` (identity case). `derived`: roll-up = `Σ count × area_each` from the item tables. |
| `fomite_item_reading` | `shared` / `hardware` / `broad` | `shared` | which fixed item set enumerates a unit. |
| `surface_cleaning.routine_coverage_by_item_class` | item class → [0, 1] | unset | per-class routine coverage; a class not listed takes the zone's `ROUTINE_CLEANING_COVERAGE`, so the touch-weighted mean recovers the pooled coverage exactly. |

State is keyed `(unit_key, pathogen_id, item_class)` (`PerSurfaceFomiteState`).
Deposition splits by touch share; pickup per class is
`contacts × (used × hand / (count_c × area_c)) × eff × mass_c × share_c`,
capped at `mass_c`, with per-class over-demand scaling; decay and
disinfection are uniform; routine cleaning is per class. Time-dependent
terms are unchanged (`_fomite_surface_contacts` through `SimClock`).

Open item (not a deviation from the spec's algebra, but from its inventory):
per-occupant item groups (`*_per_occupant`) are **not** enumerated in the
engine because `TransmissionCore` has no per-unit `max_occupancy`. Under
`shipped` basis this is immaterial (areas rescale to the pooled total); under
`derived` it under-counts dining/crew-mess/public furniture. Plumbing
occupancy is a follow-up, not this deliverable.

## 2. Identity to be measured (frozen)

Paired seeds 8000–8019, 288 epochs, `classic_cruise_1900`, `norwalk_gi`,
1,910 agents, `pooled` vs `per_surface` + `areal` + `shipped`, run locally via
`tools/noro_diag/per_host_dose_challenge.py --fomite-representation`.

Statistics, per seed, from the per-seed dumps:

| statistic | source field | tolerance |
|---|---|---|
| whole-voyage credited dose (relative) | `reconciliation.sum_credited_raw_gec` | `rel ≤ 1e-9` |
| fomite pickups (hand→mouth calls, hand load seen, delivered mass to hands) | `fomite.hand_to_mouth_calls`, `fomite.hand_load_seen_gec`, `fomite.mass_delivered_to_hands_gec` (the per-class delivery is witnessed by the PR3 wrapper on `_deliver_fomite_requests_by_class`; the pooled `surface_to_hand.pool` rows are by construction empty in the arm and are not compared) | exact / `rel ≤ 1e-9` |
| hand→surface deposition total | `fomite.surface_deposit_calls`, `fomite.surface_mass_deposited_gec` | exact / `rel ≤ 1e-9` |
| swab-density denominator | `zone_high_touch_area_cm2` per zone (unit test) | exact |
| emesis patch area | `EmesisPatch.high_touch_area_m2` (unit test) | exact |
| infections / attack rate | `transmission.attack_rate`, `run_history` | exact |
| RNG stream | `rng.bit_generator.state` after a short paired run (unit test) | exact |

**Verdict rule:** identity holds iff every statistic is within tolerance on
all 20 seeds. A single seed outside tolerance is an implementation defect
(spec §3.4), not a model difference, and is fixed before anything else is
interpreted.

## 3. Runtime envelope (frozen)

Wall-clock ratio `per_surface / pooled`, median over the 20 paired seeds,
compared against spec §4's 1.5–4×. Above 4× is reported immediately.

## 4. Default-path proof (frozen)

Two independent pieces of evidence, both required:

1. Byte-identical `per_host_dose_challenge` dump (seed 8105, 24 epochs) at
   the PR1 base and head, ignoring only the `arm_tag` string.
2. Unit test: `fomite_representation` absent vs `pooled` yields identical
   surface state and identical `rng.bit_generator.state`.

## 5. Non-goals

No numeric touch shares; no `declared` arm run; no `derived`-basis run; no
cleaning-policy study; no fitting to VSP, Park, attack rates or the
passenger/crew ratio; the 2020 door retrofit is a consistency bound only; no
A4/Yuan-2024 work; no campaign or array job.

## 6. Measured

**Measured at `622f99f`** (PR #660 head at run time; the later `3530b5a`
only extracts a shared roll-up helper with identical arithmetic), seeds
8000–8019, 288 epochs, `classic_cruise_1900`, `norwalk_gi`, 1,910 agents,
both arms run locally and concurrently on a 2-vCPU VM. Dumps:
`../norovirus/noro_fomite_disagg_01/classic_cruise_1900/` (40 files);
readout: `../norovirus/noro_fomite_disagg_01/fomite_disagg_identity_per_surface_areal.json`
(`tools/noro_diag/fomite_disagg_identity_readout.py`).

### 6.1 Two defects found and fixed before the block (measured)

Both were found by an epoch-by-epoch lockstep probe on seeds 8000/8001 after
the first block attempt (`14f98c2`) diverged in exact counts by 11–30 %.

1. **Cap gate — labelled default-path change (Benjamin, option 1).** A pool
   whose demand exceeded its supply was left at `previous − delivered`,
   which lands on `0.0` or ~1e-22 GEC by rounding luck; a positive residue
   made `_pathway_fomite` draw pickup RNG for a de-facto empty zone next
   epoch. Per-class arithmetic cannot reproduce that residue bitwise, so the
   288-epoch identity was unattainable by construction. Fix (`bd87ce9`,
   `a71fa3d`): `delivered_total := surface_mass` when `scale < 1.0`, in
   `_deliver_fomite_requests`, the pooled sanitary loop and the per-class
   path. Per-target doses unchanged. **This is the only default-path
   behaviour change in the deliverable**; the full fast tier (5,788 tests)
   moved no golden or neutrality test, so the shipped stream is affected
   only on seeds where a residue was positive at a cap event (seed 8001:
   `MainDining_L` epoch 9). §4 item 1 is therefore superseded: the default
   path is proven neutral by §4 item 2 (unit RNG-state identity) plus the
   unmoved fast tier, not by a byte-identical dump across the cap fix.
2. **Outbreak disinfection — arm-only.** `_disinfect_zone` (SOP-003) had no
   per-class mirror: pooled set `cleanable := old_cleanable × cf` while the
   arm only received the total retention, so class cleanables drifted and
   the next routine pass removed a different amount (seed 8001: first
   mismatch epoch 26 `Engine_Room`, pool split epoch 27). Fix (`622f99f`):
   `PerSurfaceFomiteState.disinfect` + `_disinfect_zone_by_class`.

After both, lockstep on 8000 and 8001 × 288 epochs: RNG state bit-identical
every epoch, worst relative pool difference ≲ 4e-15.

### 6.2 Identity (measured) — **holds on all 20 seeds**

| statistic | tolerance | worst rel. diff (seed) |
|---|---|---|
| `reconciliation.sum_credited_raw_gec` | 1e-9 | 3.9e-16 (8010) |
| `reconciliation.sum_credited_scaled_gec` | 1e-9 | 4.0e-16 (8010) |
| `reconciliation.sum_evaluated_hazard` | 1e-9 | 3.5e-16 (8012) |
| `fomite_witness.surface_deposit_calls` | exact | 0 |
| `fomite_witness.surface_mass_deposited_gec` | 1e-9 | 0 |
| `fomite_witness.deliver_calls` | exact | 0 |
| `fomite_witness.mass_delivered_to_hands_gec` | 1e-9 | 5.3e-16 (8015) |
| `fomite_witness.hand_to_mouth_calls` | exact | 0 |
| `fomite_witness.hand_load_seen_gec` | 1e-9 | 4.1e-16 (8004) |
| `fomite_witness.hand_to_mouth_dose_gec` | 1e-9 | 3.2e-16 (8009) |
| `joint.hosts_credited_any_dose`, `transmission.secondaries/imports/attack_rate` | exact | 0 |
| `hosts[].credited_scaled_gec` (host by host) | 1e-9 | 2.3e-14 (8014) |

Swab-density denominator, emesis patch area and the paired RNG stream are
covered by the unit identities in `tests/test_fomite_per_surface.py`
(20 tests) as frozen in §2.

Per seed (pooled = arm on every row; secondaries are near zero because every
dose figure is withdrawn — ledger §1 — so the identity's weight is carried by
the dose vectors and event counts, not by infections):

| seed | secondaries | deliver_calls | hand_to_mouth_calls | runtime ratio |
|---|---|---|---|---|
| 8000 | 0 | 1022 | 1036 | 1.121 |
| 8001 | 0 | 993 | 10959 | 1.138 |
| 8002 | 0 | 2216 | 6810 | 1.120 |
| 8003 | 0 | 443 | 4583 | 1.127 |
| 8004 | 0 | 647 | 6375 | 1.127 |
| 8005 | 0 | 1470 | 22228 | 1.157 |
| 8006 | 0 | 763 | 2095 | 1.102 |
| 8007 | 0 | 2233 | 8221 | 1.140 |
| 8008 | 0 | 549 | 2003 | 1.119 |
| 8009 | 0 | 2212 | 4215 | 1.148 |
| 8010 | 0 | 261 | 488 | 1.127 |
| 8011 | 0 | 342 | 4890 | 1.090 |
| 8012 | 0 | 941 | 15961 | 1.125 |
| 8013 | 0 | 844 | 6699 | 1.127 |
| 8014 | 0 | 806 | 10377 | 1.211 |
| 8015 | 0 | 257 | 66 | 1.208 |
| 8016 | 2 | 760 | 793 | 1.077 |
| 8017 | 0 | 514 | 58 | 1.105 |
| 8018 | 1 | 961 | 12793 | 1.051 |
| 8019 | 0 | 1583 | 4979 | 1.105 |

### 6.3 Runtime (measured)

`per_surface / pooled` wall-clock per seed: median **1.126** [1.051, 1.211];
totals 17,413 s vs 15,474 s. **Below** spec §4's 1.5–4× envelope. Inferred:
the arm's extra cost is one dict loop per zone-epoch over ≤ 10 item
classes, dwarfed by the per-agent contact work, so §4's envelope was
conservative; not a report-immediately condition (only > 4× is).

### 6.4 Status of the arm

`per_surface` + `areal` + `shipped` is a proven algebraic re-expression of
`pooled` (measured, 20 seeds × 288 epochs). It carries per-class state,
per-class cleaning coverage and per-class outbreak disinfection, and exposes
`fomite_touch_share: declared` with an empty table. Nothing in this entry
changes a physical constant or declares a touch share.

### 6.5 Decision for the next session (hypothesis, not measured)

Whether to declare graded touch shares (Jin/Zhang/Ackerley) so the arm
departs from pooled. Under `areal` the arm is inert by construction; any
signal requires a non-uniform `declared` table (or the `derived` area basis
plus per-occupant inventory, see §1 open item). Given `NORO-HIGH-TOUCH-AREA-01`
(whole-voyage dose does not scale with `A` at n = 20), the hypothesis to
test first is whether concentrating touch share on a few high-traffic
classes changes *which hosts* are credited (coincidence, patchiness brief
§3), not whether it moves the whole-voyage total. Sourcing the shares is a
provenance deliverable with its own ledger; this session did not start it.
