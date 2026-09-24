# NORO-TOUCH-SHARE-01
**Date:** 2026-09-24
**Commit:** e64bb00
**Pathogens:** norwalk_gi
**Status:** declared

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

*Not yet run.*
