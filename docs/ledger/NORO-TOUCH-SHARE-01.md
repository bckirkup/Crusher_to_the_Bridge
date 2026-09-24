# NORO-TOUCH-SHARE-01
**Date:** 2026-09-24
**Commit:** e7ab09f
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 3a54ad3

A numeric, provenance-backed `fomite_touch_share: declared` table for the
`per_surface` fomite arm (`shared` item reading), wired through
`tools/noro_diag/per_host_dose_challenge.py`, and one 20-paired-seed local
canary reading out *who* is credited fomite mass, not how much. §§0–4 are
frozen before any cell runs; §5 is filled only from the measured block.
Every dose quantity is a paired ratio or share against a withdrawn baseline
(`../norovirus/norovirus_open_ledger.md` §1) — relative/derived, never a
dose result. Nothing is adopted: `pooled` stays the default; no physical
constant, `HIGH_TOUCH_AREA_M2` or `SANITARY_HIGH_TOUCH_AREA_M2_PER_WC` moves.

## 0. Settled inputs (quoted, not re-derived)

- **`NORO-FOMITE-DISAGG-01`** (#664, measured `622f99f`):
  `per_surface + areal + shipped` is an algebraic re-expression of `pooled`
  (host-by-host ≤ 2.3e-14 rel, 20 seeds × 288 epochs). `declared` exists as
  a hook reading `fomite_touch_share_table`; no numeric table was in-tree.
  Its §6.5 is the hypothesis tested here.
- **`NORO-HIGH-TOUCH-AREA-01`, `NORO-HIGH-TOUCH-SWEEP-01`:** whole-voyage
  fomite dose is design-limited at n = 20; galley measures the conservation
  cap. Whole-voyage scaling is therefore a secondary here, never a gate.
- **Per-occupant item groups** (`table_top_per_seat`, `chair_touched`,
  `small_panel`, `tableware_per_seat`) are not enumerated at unit
  resolution; `derived` area basis is not used. Shares are declared only
  over `shared_fixed` classes.
- **Literature:** `../literature/consensus_tranche_46_touch_behaviour.md`
  (Jin 2022, Zhang 2018/2021/2024, Ackerley 2025, Lei 2017, Carling 2009,
  Huslage 2010, Cheng 2015, Yuan 2024). New retrieval this session is
  tranche 47 (`../literature/consensus_tranche_47_touch_shares.md`).
- **Nulls (not re-retrieved):** summed high-touch area per zone class
  `∅nr`/`∅lit`. No source retrieved here contradicts it.

## 1. Mechanism under test

In `engines/fomite_surfaces.py` the touch share enters twice: a deposit to a
unit is split across item classes by share, and each class's pickup request
is `contacts · used_fraction · hand_area / (count·area_c) · η · mass_c ·
share_c`. Under `areal` (`share_c = count·area_c / A`) the two cancel and the
class requests sum to the pooled request. Under `declared` they do not: a
class with declared share `s_c` above its areal share `a_c` holds more of
the deposited mass *and* is picked from harder, so its request scales as
`s_c²/a_c` relative to areal. This is the shipped hook's behaviour, not a
change made here; it is what makes a concentrated table a *coincidence*
change (which touchers meet which class) rather than a rescaling.

## 2. Provenance — the declared table

Data file: `data/config/fomite_touch_share_declared.json` (schema
`schemas/fomite_touch_share_declared.schema.json`). Every share is an
**observed group share (Grade B, analogous setting) × shipped areal share
within the group (Grade C, this repository's geometry)**. Touches were
counted in both sources (not touchers, not contact episodes).

### 2.1 `dining` — Jin et al. 2022 (restaurant, CCTV, 41,042 touches)

| Study class | Counted (touches/person·h, Results, full text) | Engine class | Share (central) | Interval | Areal reference |
|---|---|---|---|---|---|
| T — table's object for public use | diners 38.5, staff 245.8 | `utensil` | **0.5678** | [0.4507, 0.8995] | 0.6394 |
| R — restaurant public/common objects | diners 4.3, staff 299.6 | `button_or_dispenser` | 0.2299 | R-group 0.4322 × areal split | 0.1918 |
| R | | `tap_set` | 0.1533 | | 0.1279 |
| R | | `door_lever` | 0.0490 | | 0.0409 |

Central `T` share = (81·38.5 + 18·245.8)/(81·42.8 + 18·545.4) = 0.5678,
headcount-weighted over the 81 visible diners and 18 staff in the
observation; interval bounds are the staff-only and diner-only T shares.
`PT` (personal place setting), `PP`, `M`, `H`, `B` are not shared surfaces
and are excluded; `table_top_per_seat`/`chair_touched` are per-occupant and
not enumerated. **Note:** the declared dining table is close to areal
(largest move `utensil` −0.07); little coincidence change is predicted from
dining alone.

### 2.2 `public` — Ackerley et al. 2025 (hotel lobby, 30 h, 627 touches, 13 fomites)

| Study fomite | Counted (% of all touches, Results) | Engine class | Share (central) | Interval | Areal reference |
|---|---|---|---|---|---|
| elevator button | 32% | `button_or_dispenser` | **0.4103** | [0.4103, 1.0] | 0.0242 |
| front-desk counter, countertops, tables, seating, computer equipment | 22% (counter) + part of 46% | — no class in public `shared_fixed` — | excluded, renormalised out | | |
| doors | part of 46% (split `?nr`) | `door_lever` | 0.0038 | residual 0.5897 × areal split | 0.0062 |
| luggage cart handle | part of 46% (split `?nr`) | `grab_rail_m` | 0.5860 | | 0.9696 |

Central `button_or_dispenser` = 32/(100 − 22) = 0.4103: the retrieved
elevator-button share renormalised over touches not on the unmapped
counter. The per-fomite split of the remaining 46% (which includes a credit
card reader and a sanitizer pump that would also map to
`button_or_dispenser`) is **`?nr`** — the full-text table is not indexed —
so the central is the lower bound and the upper bound is unconstrained. This
is the one class where the declared table moves far from areal (×17), and
where any coincidence change is predicted to appear.

### 2.3 Areal fallback (no observed analogue — nothing invented)

| Zone class | Why it stays on `areal` |
|---|---|
| `cabin` | Yuan 2024 is an all-surface dormitory rate (cellphone, keyboard, mouse, own desk); Lei 2017 enumerates aircraft-seat surfaces without touch counts. No shared-surface touch share for a sleeping unit was retrieved. |
| `crew_mess` | Jin 2022 staff are servers working a dining room, not crew eating in a self-service mess. |
| `sanitary` | Carling 2009 counts 30.6 objects per shipboard public restroom but reports no touches; Abney 2024 is a QMRA over assumed contact sequences. |
| `galley` | No per-surface touch observation among commercial food handlers retrieved; Kirchner 2023 codes first-7 touches in a home-kitchen study without per-surface shares. |

No source giving per-class touch shares for a cruise/shipboard setting was
retrieved (would have upgraded the grade; report-immediately condition not
triggered).

## 3. Wiring

- `data/config/fomite_touch_share_declared.json` — `shares` block is exactly
  the `transmission.fomite_touch_share_table` shape; `provenance` and
  `areal_fallback` blocks are documentation validated by schema.
- `engines/fomite_surfaces.load_declared_share_table(path)` reads the file,
  checks `item_reading`, returns `shares`.
- `parse_per_surface_config` additionally requires each declared zone
  class's item set to equal the engine's `unit_item_counts(zone, reading,
  1)` set — a class present in the unit inventory but absent from the table
  previously received share 0.0 silently (mass loss); it is now a
  `ValueError`. Zone classes absent from the table fall back to `areal`
  whole, as before.
- `tools/noro_diag/per_host_dose_challenge.py`: `--fomite-touch-share
  {areal,declared}`, `--fomite-touch-share-table <path under repo>`;
  resolved values echoed and a dropped override is a `RuntimeError`. New
  per-class witness (`fomite_by_class`: requested, delivered, calls,
  capped calls, distinct hosts) and per-host `fomite_delivered_by_class`,
  reconstructed exactly in the delivery wrapper from the engine's uniform
  per-class scale (no engine hook, no RNG draw).
- Identity preserved: `pooled` default bit-identical; `per_surface + areal`
  bit-identical to #664 (table inert under `areal`, tested).

## 4. Coincidence readout — frozen before any cell runs

**Cell.** `classic_cruise_1900`, `norwalk_gi`, 288 epochs, paired seeds
8000–8019 (20), arms `A = per_surface+areal+shipped`,
`D = per_surface+declared+shipped` with the §2 table. Local only; this is
the last local-scale block.

**Credited quantity.** Per host, fomite mass delivered to hands over the
voyage (`hosts[].fomite_delivered_by_class`, summed) — the only per-host
quantity attributable to an item class. Whole-voyage credited-scaled dose
(`credited_scaled_gec`) is a secondary.

**Primary statistics (per seed unless stated).**
1. `n_hosts_A`, `n_hosts_D`: distinct hosts with nonzero fomite-delivered mass.
2. `jaccard`: |H_A ∩ H_D| / |H_A ∪ H_D| over those host sets.
3. Concentration per arm: Gini of per-host fomite-delivered share and
   top-decile share.
4. Per (zone class, item class) per arm: share of delivered mass (of the
   ship total, and of that zone class's total); distinct hosts credited
   from that class; capped-call share (`capped_calls / calls`).

**Secondary (distributional only, no pass/fail).** Whole-voyage
`sum(fomite_delivered) D/A`, `sum(credited_scaled) D/A`, secondaries D − A,
all reported as median and [min, max] over seeds.

**Admissibility rule.** The declared table *changes coincidence* if, over
the 20 seeds, (a) median `jaccard` < 0.90 **and** (b) in ≥ 15 seeds the
`public.button_or_dispenser` share of the *public zone class's* delivered
mass exceeds its areal-arm share by > 0.10 absolute (the within-zone share,
because public-zone mass is a small fraction of the ship total and a
ship-total share could never move by 0.10). It is *inert* if H_A == H_D on all 20 seeds
(stop and report). Otherwise *indeterminate at n = 20* (report; a larger
block is a later AWS decision). Predicted direction: `button_or_dispenser`
share of delivered mass rises and `grab_rail_m` falls in `public`; dining
classes move little.

**Cap diagnostic.** Any declared class with capped-call share > 10% in arm
D is reported immediately; its delivered share then measures the
conservation cap, not the touch share.

**Stop conditions.** `areal` arm not bit-identical to #664 → implementation
defect, stop. Inert → design finding, stop. Cap > 10% → report.

Readout tool: `tools/noro_diag/touch_share_coincidence_readout.py`
(deterministic JSON + table; `_safe_path` for the output).

## 5. Measured

Cell as frozen in §4, run locally: arms A and D, seeds 8000–8019, 288
epochs, `classic_cruise_1900`, `norwalk_gi`, `per_surface + shipped`, the
§2 table (`data/config/fomite_touch_share_declared.json`). Engine and CLI
at `3a54ad3` (the only later commits before merge, `2266431`/`6f3c0ca`,
touch table-path canonicalisation, the readout tool and tests — no
numeric path); readout tool at `6f3c0ca`. Readout:
`../norovirus/noro_touch_share_01/touch_share_coincidence_per_surface_declared.json`
(sorted, deterministic; 20/20 seeds in both arms).

### 5.1 Stop conditions (measured)

| Condition | Result |
|---|---|
| `areal` arm bit-identical to #664 | **Holds.** `deliver_calls`, `hand_to_mouth_calls` and secondaries equal the #664 §6.2 table on all 20 seeds (0 mismatches). |
| Any declared class capped-call share > 10% in D | **None.** Max capped share over all declared classes and seeds: `dining.*` 0.002, `public.*` 0.000 (`crew_mess.*` 0.010, areal fallback). |
| Host sets identical on every seed (inert) | **No.** Identical on 2/20 (8001, 8015). |
| Cruise/shipboard per-class source; exact-area null contradicted | Neither occurred (§2). |

### 5.2 Primary statistics (per seed)

| seed | n_A | n_D | jaccard | gini_A | gini_D | top10_A | top10_D | focus gain | dep_A | dep_D | aligned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 8000 | 445 | 386 | 0.8385 | 0.9269 | 0.9934 | 0.9336 | 1.0000 | 0.3890 | 27 | 26 | no |
| 8001 | 245 | 245 | 1.0000 | 0.9959 | 0.9959 | 1.0000 | 1.0000 | 0.3927 | 14 | 14 | yes |
| 8002 | 580 | 637 | 0.7638 | 0.8571 | 0.8851 | 0.7693 | 0.8414 | 0.4075 | 45 | 59 | no |
| 8003 | 634 | 531 | 0.8375 | 0.8432 | 0.9981 | 0.7115 | 1.0000 | 0.3872 | 22 | 14 | no |
| 8004 | 761 | 4 | 0.0039 | 0.7596 | 0.4970 | 0.6004 | 0.5819 | −0.0242 | 12 | 10 | no |
| 8005 | 702 | 760 | 0.6101 | 0.9177 | 0.8496 | 0.8892 | 0.7332 | 0.5710 | 62 | 52 | no |
| 8006 | 527 | 533 | 0.9887 | 0.8481 | 0.8489 | 0.7579 | 0.7629 | 0.3881 | 21 | 21 | yes |
| 8007 | 657 | 650 | 0.9773 | 0.8171 | 0.9086 | 0.6606 | 0.8309 | 0.3890 | 58 | 49 | no |
| 8008 | 712 | 455 | 0.6231 | 0.8738 | 0.8689 | 0.7985 | 0.7572 | 0.4658 | 34 | 28 | no |
| 8009 | 942 | 1111 | 0.7502 | 0.9722 | 0.9675 | 0.9990 | 0.9659 | 0.8045 | 70 | 87 | no |
| 8010 | 253 | 1 | 0.0040 | 0.7268 | 0.0000 | 0.6173 | 1.0000 | −0.0242 | 4 | 8 | no |
| 8011 | 468 | 473 | 0.9852 | 0.8355 | 0.6743 | 0.6933 | 0.4577 | 0.4087 | 33 | 43 | no |
| 8012 | 634 | 647 | 0.9799 | 0.8389 | 0.8527 | 0.6810 | 0.7171 | 0.4785 | 32 | 47 | no |
| 8013 | 331 | 215 | 0.6012 | 0.9950 | 0.9587 | 0.9971 | 0.9991 | 0.8262 | 26 | 23 | no |
| 8014 | 898 | 798 | 0.8824 | 0.6877 | 0.7940 | 0.5366 | 0.6831 | 0.3915 | 33 | 39 | no |
| 8015 | 1 | 1 | 1.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 6 | 6 | yes |
| 8016 | 374 | 462 | 0.8095 | 0.8607 | 0.8860 | 0.7941 | 0.8296 | 0.3888 | 12 | 23 | no |
| 8017 | 3 | 4 | 0.7500 | 0.0788 | 0.7500 | 0.4020 | 1.0000 | 0.0000 | 2 | 4 | no |
| 8018 | 695 | 659 | 0.7292 | 0.9254 | 0.7749 | 0.8761 | 0.6587 | 0.4605 | 35 | 23 | no |
| 8019 | 508 | 347 | 0.5602 | 0.7907 | 0.7242 | 0.6596 | 0.5541 | 0.4698 | 22 | 26 | no |

`focus gain` = within-`public` delivered share of `button_or_dispenser`,
D − A. `dep_*` = `surface_deposit_calls`; `aligned` = equal deposit calls
and deposited GEC within 1e-9 (the event-stream witness added at `6f3c0ca`
after seed 8000 showed divergent events).

Aggregate, median [min, max] over 20 seeds:

| statistic | A (areal) | D (declared) |
|---|---|---|
| distinct credited hosts | 553.5 [1, 942] | 467.5 [1, 1111] |
| Gini of per-host fomite-delivered share | 0.846 [0.000, 0.996] | 0.851 [0.000, 0.998] |
| top-decile share | 0.764 [0.402, 1.000] | 0.830 [0.458, 1.000] |
| `surface_deposit_calls` | 26.5 [2, 70] | 24.5 [4, 87] |
| `hand_to_mouth_calls` | 4934.5 [58, 22228] | 11836.5 [80, 26389] |
| jaccard(H_A, H_D) | 0.787 [0.004, 1.000] | |
| focus gain | 0.392 [−0.024, 0.826] | |
| seeds with focus gain > 0.10 | 16 / 20 | |
| seeds with deposit events aligned | 3 / 20 (8001, 8006, 8015) | |

Per (zone class, item class), median over seeds of within-zone delivered
share A → D, and distinct hosts credited A → D (capped share max in D):

| class | zone share A → D | hosts A → D | cap D |
|---|---|---|---|
| `public.button_or_dispenser` | 0.0242 → **0.4243** | 322 → 246 | 0.000 |
| `public.grab_rail_m` | 0.9696 → 0.5377 | 322 → 284 | 0.000 |
| `public.door_lever` | 0.0062 → 0.0034 | 322 → 284 | 0.000 |
| `dining.utensil` | 0.6394 → 0.5678 | 227 → 179 | 0.000 |
| `dining.button_or_dispenser` | 0.1918 → 0.2299 | 227 → 179 | 0.002 |
| `dining.tap_set` | 0.1279 → 0.1533 | 227 → 179 | 0.002 |
| `dining.door_lever` | 0.0409 → 0.0490 | 227 → 179 | 0.002 |
| `cabin.*`, `crew_mess.*`, `galley.*` (areal fallback) | unchanged within zone | cabin 4 → 4, crew_mess 108 → 98, galley 76 → 72 | ≤ 0.010 |

In D the within-zone delivered shares of the declared zones equal the §2
table to four decimals on the median seed: with no capping, delivered share
tracks requested share, so criterion (b) is met by construction wherever
any public-zone mass is delivered at all (the four seeds at 0.00/−0.02 —
8004, 8010, 8015, 8017 — have essentially no public-zone delivery).

### 5.3 Secondary (distributional only; relative/paired against a withdrawn baseline)

| statistic | median [min, max] over seeds |
|---|---|
| `sum(fomite_delivered)` D/A | 0.489 [1.7e−72, 6.8e+80] |
| `sum(credited_scaled)` D/A | 1.24 [0.0079, 5.1e+04] |
| secondaries D − A | 0 [0, 1] (8008, 8009: +1) |
| runtime D/A | 0.989 [0.977, 1.013]; A median 593 s/seed |

The extreme ratios come from seeds whose whole-voyage deposited mass is
1e−81 … 1e−20 GEC in one arm (8001, 8003, 8015, 8017): these are numerically
empty voyages, not dose results, and are reported only because the rule
says report the distribution.

### 5.4 Verdict under the frozen rule

**`changes_coincidence`**: median jaccard 0.787 < 0.90 **and** focus gain
> 0.10 on 16 ≥ 15 seeds. Predicted direction confirmed
(`button_or_dispenser` up, `grab_rail_m` down in `public`; dining moves
little).

### 5.5 Inferred (not measured)

1. **The rule fired, but not through the mechanism §1 predicted.** Deposit
   event streams stayed aligned on only 3/20 seeds, and on those three the
   credited-host sets are identical or nearly so (jaccard 1.000, 0.989,
   1.000). Where the arms met the same deposits, re-weighting the share
   within a zone changed *how much* each host received from each class,
   not *who* received it — which follows from the delivery wrapper's
   construction (every host in the zone is credited every class in
   proportion to a common per-class scale). The jaccard < 0.90 on the other
   17 seeds is therefore carried by downstream divergence of the voyage —
   different hand loads → different hand-to-mouth events
   (`hand_to_mouth_calls` median 4.9k → 11.8k) → different infections,
   shedding and deposits — not by direct reallocation among touchers.
2. The §4 rule did not anticipate this; criterion (a) cannot separate
   direct coincidence from dynamical divergence. The event-alignment column
   is the discriminator and should be part of the rule in any successor.
3. Concentration (Gini, top-decile) moves in the predicted direction only
   weakly (medians +0.005, +0.07) and inconsistently across seeds.

### 5.6 Hypothesis and next decision

**Hypothesis (one cell, n = 20, untested):** the D-arm divergence is
legitimate dynamics (concentrating share on `button_or_dispenser` raises
some hosts' hand load across an infection threshold) rather than
RNG-stream disruption through a `<= 0` cap/empty gate on a floating-point
residue (the `NORO-FOMITE-DISAGG-01` §6.1 archetype). The doubling of
`hand_to_mouth_calls` with fewer deposits is the observation that would
distinguish them and is unexplained here.

**Next decision (for the operator, not taken here):** either
(i) accept `changes_coincidence` as "the declared table changes the voyage,
and therefore who is credited", and take a larger block to AWS with the
alignment column in the rule; or (ii) first run a two-seed epoch-lockstep
probe (8001 aligned vs 8000 diverged) locating the first epoch at which the
arms' RNG states differ, to rule the §6.1 archetype in or out before any
larger block. Nothing is adopted either way: `pooled` remains the default,
`declared` remains a diagnostic arm.

### 5.7 Void

Nothing previously measured is voided: the #664 identity re-measured here
unchanged; `NORO-HIGH-TOUCH-AREA-01`/`-SWEEP-01` are untouched.
