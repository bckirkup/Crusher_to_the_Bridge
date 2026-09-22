# NORO-FOMITE-DISAGG-01
**Date:** 2026-09-22
**Commit:** (PR1 head; filled at merge)
**Pathogens:** norwalk_gi
**Status:** declared

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

Not yet run. Filled in PR3 with `Measured at` (bare SHA), per-seed table,
verdict per §2, wall-clock ratio per §3.
