# Phase 1 options memo — droplet near-field/far-field split (COVID arm)

**Status:** design memo — produced by the Phase-1 survey session; direction
pending. See `docs/ledger/SENS-ASSAY-V2.md` (stood-down note) for why the
well-mixed-room reach is the operative problem.

**Scope:** survey only; no implementation. Decision needed before Phase 2.

## 1. What the survey found

- `near_field_air` **is active** in the COVID spec: `crusher_labs/config.yaml` declares no
  `near_field_air` block, so the shipped default `mode: two_box` applies (assay-1's
  A3 `near_field_off` is the labelled baseline, and it measured inert, +0.6%).
- `_droplet_unit_doses` (engines/transmission_core.py ~L5108) deposits
  `emitted × DROPLET_AEROSOL_FRACTION (0.05, unsourced)` into the zone pool and gives
  **every susceptible co-occupant** `concentration × inhaled(0.6 m³/epoch) × droplet_scalar
  × vent × confinement`. Reach is bounded only by epoch occupancy — one shedder in
  promenade/buffet/dining venues (V = 2,100–42,000 m³, caps 700–2,500) doses ~850/day.
  The same deposit also lands in `aerosol_pools`, feeding HVAC drift.
- The existing near field (`_near_field_droplet_dose`, ~L3886) is a **difference-of-
  concentrations excess** for table parties, neighbour tables (ρ=0.43), and cabin-mates
  in Cabin_Corridor — an add-on, not a bound. β=204 m³/h (Keil 2017, Grade B) is already
  declared; flushed volume per 1-h epoch is 204 m³.
- Partner-bounded machinery already exists and is switched on: `contact_mode:
  per_partner_contact` + `activity_contacts` (CONTACT-ARCH-01, sourced rates per
  activity/role, hypergeometric partner sampling in `_sample_contact_partners`).
  The contact draw IS the partner bound the droplet route lacks.
- The B10 design note already names this residual: "a sparse-contact-graph
  counterfactual needs engine surgery (a contact network), not overrides."
- Conserved-side wiring to respect: the aerosol pool feeds HVAC drift and surface-swab
  telemetry; `_cabin_mate_droplet_addback` is a declared full-dose unconfineable channel;
  `_near_field_admits`/`_droplet_emission_fraction` refuse `emesis_conditioned` arms
  (norovirus) — do not reopen that gate.

## 2. Candidate architectures

### Option 1 — Emission partition at the source (recommended)

Split each shedder's continuous emission at generation: **near-field share** delivered
only to partner-bounded co-occupants through an extended `_near_field_unit` ring set;
**far-field share** = only the fraction physically able to remain airborne and room-mix;
the remainder settles ballistically (can route to surface deposition or decay).

- **Mechanism:** `emitted → {f_near to partners via two-box β, f_far to zone pool,
  f_settled to surfaces/decay}`. Far-field pool keeps well-mixed form but carries a
  physically small share. Near-field rings: table/cabin-mate (w=1), neighbour table (ρ),
  plus a new ring — **proximity partners in open venues**, drawn per shedder-epoch and
  bounded by the activity contact rate (partners/hour) of the zone — i.e., the people
  who could actually be inside the exhaled jet.
- **Constants + sourcing:**
  - `f_far`: Li et al. 2021 (Indoor Air, DOI 10.1111/ina.12946) — long-range route
    involves only droplets with final diameter ≤5 µm (initial ≤~15 µm). Apply that cut
    to a declared exhaled-size distribution (Morawska 2009 BLO modes / Johnson 2011) →
    interval for the copy share in the airborne band. Grade B/C, sweepable, NOT tuned
    to 197.
  - Near-field per-partner dose: existing β=204 m³/h (Keil 2017, Grade B) — no new
    magnitude needed; Wei et al. 2023 (Build Environ 109973) gives an out-of-sample
    check: face-to-face talking intake fraction ≤~5%, ~0.37% at 15° off-axis.
  - Partner bound: existing `activity_contacts` rates — already sourced; no new
    constant. A POLYMOD "contact" is by definition a ≥3-word conversation or touch, i.e.
    inside the near field.
- **Expected reach bound:** shedder reach ≈ partner draws (~5–40 distinct/day) at
  two-box concentration + room-wide far field at `f_far/0.05` of today's dose.
  Plausibly 5–20× drop in total events; day-0–2 share should fall with it.
- **Risks:** `f_far` is the soft constant — must ship as a declared interval, not a
  tuned value. New partner draws in the droplet path disturb the RNG stream → requires
  the labelled off-baseline and the null contrast (off vs pre-change bit-identical),
  then on-vs-off read on paired seeds. Partner-draw direction (shedder-centric exposed
  set vs target-centric draw) is a design choice — reusing the target-side contact draw
  is cheapest and already sourced.

### Option 2 — Ventilation/removal-limited far field only

No partner extension. The room pool receives only emission that survives settling + ACH
removal within the epoch; standing concentration = `G/(V·(ACH+settling))`.

- **Constants:** per-zone ACH (partially sourced for DP cabins — Kosako/Almilaji ~30%
  fresh-air, Grade C; public-venue ACH is a declaration), droplet settling rate by size
  band (Xie 2007/Wei 2023, Grade B).
- **Bound:** similar far-field suppression to Option 1's `f_far`, but **no concentrated
  near-field** — cabin-mate/table exposure falls back to diluted room dose, which
  contradicts the Li-2021 restaurant record the near-field spec exists to honour.
- **Risk:** needs zone-ACH declarations the hull doesn't carry; likely overshoots the
  other way (A5 collapsed takeoff at 3/20 when shared air went to zero — a far field
  shrunk without a near field is a weaker version of that arm).

### Option 3 — Pure contact-graph droplet route

Delete the room pool for continuous droplet emission: near-field partners only, no
far-field residual (HVAC drift keeps whatever the airborne share deposits).

- **Bound:** hardest — reach = partner count (~13–40/day) → the largest event-count
  reduction.
- **Risk:** likely reproduces A5's takeoff collapse in softer form; abandons the real
  far field entirely (the DP record does show distributed/late transmission). Basically
  Option 1 with `f_far = 0` — better expressed as the floor of Option 1's sweep interval
  than as a separate architecture.

### Option 4 — Extend AERO-NEAR-02 rings only (no far-field change)

Add crew-work-department / promenade-group rings to `_near_field_unit`; far field
untouched. **Cannot bound reach** — the excess term only adds dose. A3 already measured
this family as inert. Listed for completeness; not viable.

## 3. Mechanics shared by Options 1–3 (invariants to protect)

- Conservation: near + far + settled = emitted; drift route reads the far-field pool.
- `emesis_conditioned` arms stay refused (`_near_field_admits`, zero continuous share).
- Cabin-mate full-dose addback: keep as declared unconfineable channel, or map to the
  near-field share — a design decision to surface in the PR.
- Validation per repo rules: feature-flagged `transmission.droplet_field_split`
  (labelled `off` baseline → null contrast must be bit-identical), `ruff` + `sonar_guard`
  + fast-tier pytest, then the `QuarantineAttributionLedger` epoch_observer probe on ≥2
  paired seeds at Θ 4.22e10 reporting day-0–2 share and total event count vs main.
- Reporting: direction only, never tuned to 197.
