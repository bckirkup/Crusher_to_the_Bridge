# AERO-NEAR-01: a near-field air compartment over the seating unit and the cabin

> **Status:** **Implemented, off by default** — `transmission.near_field_air`
> in `engines/transmission_core.py`, with `retained_fraction` 0 (and an absent
> block) taking the pre-change well-mixed code path. §§1–7 below are the
> requirement as sourced; **§10 records what landed and how it differs from
> the requirement**. No constant is adopted and no value is fitted: the §6
> sourcing tranche ([tranche 36](literature/consensus_tranche_36_near_field_air.md))
> licenses the *structure*, bounds the two rings of §5, and returns **∅ null**
> on the one magnitude the structure needs (the near-field effective volume,
> equivalently the near/far exchange rate), so that ships as declared geometry
> plus a swept axis. Filed for every active pathogen arm, not for norovirus
> alone.

## 1. The defect

`TransmissionCore._pathway_droplet` is the only short-range inhalation route.
Per zone and epoch it sums `DROPLET_AEROSOL_FRACTION` (0.05) of every shedder's
emission into one pool, divides by the zone's declared `volume_m3`, and gives
every susceptible in the room `concentration × inhaled_air_volume × vent_factor`
(`engines/transmission_core.py`, `_pathway_droplet`). The dose is identical for
every occupant and carries no notion of distance, seat, or table. The HVAC
route (`_pathway_hvac_airborne`) is the far field between zones and is not at
issue.

So the model has no sub-room air compartment at any parameter value. Two
consequences follow from the hulls' own declarations
(`data/platforms/expedition_cruise_450/spatial_layout.json`):

| unit | actual air volume | volume the dose is divided by |
|------|------------------:|------------------------------:|
| passenger cabin (2 berths, ~12 m²) | ~30 m³ | 600 m³ (`PC_*` corridor, 12 cabins) |
| crew cabin (2–3 berths, ~7.5 m²) | ~20 m³ | 450 m³ (`CC_*` corridor) |
| dining table of 6 at ~1 m | expiratory near field | 1,050 m³ (`MainDining`) |

`BERTH-01` made the cabin the direct-contact unit and gave it its own fomite
pool; it did **not** give it its own air. `_cabin_mate_droplet_addback` only
restores the confinement attenuation between cabin mates, and does so at the
corridor volume. `DINE-PARTY-01` made the table the direct-contact pool at a
meal; the table's air is still the room's. Both repairs therefore left the
inhalation route exactly as well-mixed as before, over a 15–30× larger volume
than the unit the person actually shares air with.

This is the defect archetype recorded in `model-parameter-provenance`: a small
number of high-exposure pairs replaced by a room average. No rescaling of
`DROPLET_AEROSOL_FRACTION`, `droplet_scalar` or `route_efficiency_multipliers`
can express it, because those move every occupant together.

## 2. Why it is pathogen-general

The route matters differently per arm, and the structure must serve all of
them:

- **SARS-CoV-2** (`sars_cov2_resp`, `airborne_emission_fraction` 0.76): the
  dominant route is inhalation, and the restaurant record is explicitly a
  *table and adjacent-table* record. The Guangzhou air-conditioned restaurant
  cluster (Lu et al. 2020; Li et al. 2021 tracer/CFD reanalysis) infected
  diners at the index table and at the two tables in the same recirculating
  air stream, with none at tables outside it; the Jin 2022 / Zhang 2021 video
  studies cited for `DINE-PARTY-01` are the same setting's close-contact and
  surface record. A well-mixed dining room cannot produce that pattern.
  Now retrieved and quantified in
  [tranche 36](literature/consensus_tranche_36_near_field_air.md) §2:
  31.25% at the immediate neighbouring tables against 0% remote, 45.45% inside
  the recirculating air-conditioning zone against 0% outside it.
- **Influenza** (`influenza_a`, inactive; see
  `proposals/influenza_arm_activation_plan.md`): same physics as SARS-CoV-2 with a
  different emission spectrum; the arm must not activate onto a route that
  cannot represent seating.
- **Norovirus** (`norwalk_gi`, `airborne_emission_mode: emesis_conditioned`):
  inhalation is episodic — the aerosol pool is fed only by vomiting events
  (`emesis_aerosol_fraction_range` 7.2e-7 to 2.67e-4 per episode). The unit
  that matters is whoever shares air with the vomiting host at that moment,
  which is the table (Marks 2000: attack rate falling with distance from the
  vomiting table, in a single room) or the cabin. Whether the arm carries
  material dose through this route at all is a measurement to make, not to
  assume; the cabin-volume error is 20× regardless.

## 3. The seating unit is an operator lever

`SEAT-02` and `DINE-PARTY-01` made the sitting count, venue occupancy bound and
`dining_table_size` per-venue declarations that a cruise operator actually
controls (open vs fixed seating, table size, sittings, spacing between tables).
Once the air route reads the same declarations, those become the levers of an
NPI whose effect the model can score — the reason the requirement is filed now
rather than after the next reprise. Today the declarations reach direct contact
and (through occupancy) the fomite pool, and the inhalation route ignores them.

## 4. Required structure

A two-compartment near-field / far-field form (Nicas & Jones 2009; Cheng /
Chen "close-contact" formulations), per zone and epoch:

1. **Far field** — exactly today's term: zone pool ÷ `volume_m3` × inhaled
   volume × `vent_factor`. Unchanged code path.
2. **Near field** — an additional term for each susceptible from the shedders
   in its **co-located unit**:
   - at a meal in a table-service venue: the table party present
     (`dining_party_ids ∩ present`), plus, as a second ring, the *adjacent
     tables* (§5);
   - at night in a cabin: `cabin_mate_ids`;
   - elsewhere: none (near field off; buffet queues are recorded as a
     later item, see §7).
   The near-field emission is the same shedder emission already computed;
   the unit's effective volume is derived from declared geometry (cabin
   `volume_m3` when a cabin compartment is declared, otherwise a declared
   per-berth or per-seat volume), and the exchange rate between near and far
   field is one declared parameter, **swept, not fitted**.
3. **Conservation.** Emission is not created: what enters the near field is
   the same mass that today enters the zone pool, partitioned. Total inhaled
   dose summed over the room may rise relative to today only because
   occupants near the source breathe a higher concentration than the room
   average, never because more virus is emitted.
4. **Off switch.** `transmission.near_field_air: off` (the default until the
   sourcing tranche has run) must be bit-identical to the current tree,
   checked by test on at least one hull for both arms.
5. **Pathogen-general.** The structure reads the arm's existing emission
   (`airborne_emission_fraction` or the emesis-conditioned pool) and adds no
   per-pathogen constant of its own.

## 5. Adjacent-table topology

`DINE-PARTY-01` deals tables but gives them no positions. Adjacency requires
one further declaration per table-service venue: a table graph (grid or list of
neighbour pairs) or, minimally, a declared number of neighbouring tables and
the rule that consecutively dealt tables are neighbours. The record supports
two rings (same table; tables sharing the air stream) and nothing finer; a
continuous distance kernel would be invented. Tranche 36 §2 bounds the rings
from Li 2021's Table 3 (**CFD exposure**, index table = 1): same air stream
**0.76–1.04**, same HVAC zone but downstream **0.40–0.47**, remote tables
**0.04–0.23** — an envelope for the ordering test of §8, not a value, and
measured in a room at 0.9 L/s/person. Spacing between tables — the
operator's second lever — enters as the neighbour ring's near/far exchange
rate, not as a fitted distance. Buffet venues have no fixed tables and are
out of scope for adjacency; their seating half, if any, is a separate item.

## 6. Sourcing tranche — **run**, in [tranche 36](literature/consensus_tranche_36_near_field_air.md)

Consensus was **exhausted for the period**, so every row was retrieved by the
approved open-full-text fallback (Europe PMC `fullTextXML`; the Cambridge Core
open PDF for the one paper PMC holds only as a scan). A blocked read is not a
null result. Answers, in the order asked:

1. **Answered, Grade B.** Parhizkar 2022 (27 m³ chamber, ~3 ACH, VOC breath
   tracer at 0.76/1.52/2.28 m against the exhaust as the volume average):
   **~36–44% above the other distances in the first 20 min**, decaying to
   **~18% / ~11% / ~7.5% above the volume average** by the end of the 60-minute
   trials. Licenses the two-compartment form and its time-dependence; bounds
   the steady-state seated enhancement at tens of percent, not decades;
   refuses a distance kernel.
2. **Answered, two rings and no more.** Li 2021: attack rate **31.25%** at the
   immediate neighbouring tables against **0%** remote, **45.45%** in the ABC
   air-conditioning zone against **0%** outside it; measured ethane nearly flat
   (1.00/0.92/0.96 at TA/TB/TC, 0.55–0.86 elsewhere), with the order-of-magnitude
   separation appearing only in the **CFD** droplet-nuclei exposure column.
3. **Answered for SARS-CoV-2, ∅ null for influenza.** Sharing a bedroom:
   **aOR 2.99 (1.35–6.71)** (Brown 2023, n = 943) and **×4.5** from
   **aOR 0.22 (0.10–0.41)** for *not* sharing (Sun 2023, Costa Rica) —
   converging with the cruise cabin-mate **RR 3.0 / aOR 3.27** of tranche 35.
   The influenza household literature does not stratify by sleeping
   compartment. These are infection odds over three routes the cabin already
   has, so they are the **post-repair check**, not a parameter.
4. **Null, and the null narrows the arm.** Norovirus airborne material is
   **emesis-conditioned** (Alsved 2020: 21/86 samples, 10/26 patients, **OR
   8.1** within 3 h of vomiting, 5–215 copies/m³); the 2024 review lists
   respiratory emission, toilet-flush aerosol, diarrhoea aerosolisation and
   airborne infectivity as unresolved. The only distance gradient in the record
   is Marks 2000's attack rate by table around a vomiting diner —
   **91 / 71 / 56 / 50 / 40 / 25%**, trend P ≈ 0.0007 — which becomes the
   norovirus out-of-sample check for this change.

**The magnitude is still absent.** No study measures a near-field effective
volume or exchange rate for a table or a bedroom, so the exchange parameter
ships as a declared swept axis with the volume derived from declared geometry
(`cabin_size` + MLC floor areas; `dining_table_size` + seated spacing).

The original questions, retained:

1. Near-field / far-field concentration ratio versus distance for exhaled
   aerosol at seated conversational distance (~1 m) and at 2–3 m, indoor,
   mechanically ventilated — the measured quantity, not a model's assumption.
2. The Guangzhou restaurant cluster's tracer and CFD reanalyses: which tables
   received what fraction of the index table's exhaled tracer, so the two-ring
   structure of §5 is bounded by measurement.
3. Cabin- or bedroom-scale shared-air transmission: household bedroom-sharing
   secondary attack rates for SARS-CoV-2 and influenza relative to same-house
   non-bedroom contacts, as the cabin analogue.
4. Whether any norovirus outbreak record supports inhalation beyond the
   emesis-episode pathway already modelled. A null here narrows the norovirus
   arm to cabins and vomiting tables and is a finding, not a failure.

Every number is recorded with grade, origin (table, figure, text) and page,
and enters the register as an interval or a swept axis. Nothing may be chosen
against A5, A9, posting frequency, an attack-rate band, or a COVID trajectory
anchor.

## 7. Out of scope, recorded

- Buffet queue near field (a moving line at ~0.5 m, rotating partners).
- The **emesis** pool's near field, which is norovirus's only licensed airborne
  pathway (§6 question 4) and an episodic, event-conditioned term rather than
  the continuous one this item adds — so `norwalk_gi` takes no near field here
  (§10).
- Service-surface / utensil fomite class for buffets (the fomite half of
  the service-model question, not yet filed as its own item).
- Per-venue exhaust/recirculation in Contam; the far field stays as declared.
- Any change to `DROPLET_AEROSOL_FRACTION` or the arms' emission fractions.

## 8. Tests the change must carry

- `near_field_air: off` bit-identical to the pre-change tree (both arms).
- Emission conservation: room-summed emitted mass unchanged by the switch.
- Graded sensitivity: a table mate's inhaled dose rises monotonically with
  the near-field exchange parameter; a non-party diner's does not.
- Cabin: two cabin mates' night dose is independent of the number of other
  cabins on the corridor when near field is on.
- Adjacency: dose ordering same table ≥ neighbour table ≥ far table, for
  any admissible parameter.
- No golden values.

## 9. Sequence

After the `DINE-PARTY-01` matched reprise is recorded (Batch `14dfa232`). The
sourcing tranche (§6) precedes implementation; implementation ships off by
default. What the implementation then changed about this sequence: because the
continuous near field admits only continuously emitting arms (§10), a norovirus
κ sweep is a null by construction, so the measurement is a `sars_cov2_resp`
campaign and the restaurant pattern is its out-of-sample structural check.
Norovirus reaches this route only through the emesis pool item of §7.

## 10. What landed

`transmission.near_field_air`, read in `TransmissionCore` and applied inside
`_pathway_droplet`; `tests/test_near_field_air.py` carries the §8 list.

```yaml
transmission:
  near_field_air:
    retained_fraction: 0.0      # κ, the swept axis; 0 = the well-mixed route
    neighbour_table_ratio: 0.0  # ρ, the second dining ring
    cabin_berth_volume_m3: null # declared geometry, required when κ > 0
    table_seat_volume_m3: null  #   ditto; there is no measured default
```

For a susceptible `t` and a shedder `s` in the same zone and epoch, with `m`
the aerosol mass `s` already emits into this zone's pool
(`emission × DROPLET_AEROSOL_FRACTION`, unchanged), the near field adds

```text
near(t) = Σ_s  κ · w(t,s) · m_s · (1/V_unit(t) − 1/V_zone) · inhaled × droplet_scalar × vent × confinement
```

with the same three multipliers the far-field term already carries, and

- `V_unit` = `cabin_berth_volume_m3 × berths` in a `Cabin_Corridor` for a cabin
  mate; `table_seat_volume_m3 × seats` in the target's dining zone for a seated
  party; nothing anywhere else, so a corridor neighbour, a buffet queue and a
  crew-mess diner stay far field only;
- `w = 1` at the same table or in the same cabin, `w = ρ` at a neighbouring
  table, `0` beyond — the two rings of §5 and no third;
- **adjacency is declared, not a distance kernel.** `assign_dining_parties`
  deals a sitting into consecutive tables and records
  `KorkinAgent.dining_table_index`; consecutive indices within one zone and one
  sitting are the neighbour pair. `-1` (unseated, buffet, crew mess) has no
  neighbour.

Four things worth reading twice, because they differ from a naïve reading of
§4:

1. **The far field is untouched, and that is the conservation statement.** The
   zone pool keeps the *whole* emitted mass, as in the nested Nicas–Jones form
   where the near field sits inside the far field and drains into it; the near
   field is the *difference* of the two concentrations, so no emission is
   created, the drift route reads the same pool as before, and the room-summed
   inhaled dose rises only because near partners breathe above the room
   average.
2. **The term vanishes when the unit is not smaller than the room** (`gain ≤ 0`),
   so a declared geometry larger than the zone cannot reduce anyone's dose
   below today's — the change is one-sided by construction.
3. **Norovirus is excluded, and by its own emission mode.** `_near_field_admits`
   refuses `airborne_emission_mode: emesis_conditioned`, because §6 question 4
   returned no support for *continuous* norovirus respiratory emission; the
   arm's licensed airborne pathway is the emesis pool, whose near field is a
   separate item (§7). So a norovirus campaign over κ is a **null by
   construction**: this change is measurable on the `sars_cov2_resp` arm, and
   Marks 2000's by-table gradient remains its out-of-sample check.
4. **Both magnitudes are swept, neither is chosen.** κ and ρ are design fields
   of the bounded gate (`Design`, `build_run_spec`, `--near-field-*` on the gate
   CLI and the Batch entrypoint), and a κ = 0 arm writes no `transmission`
   override at all, so the control arm is the shipped model. Turning the near
   field on without declaring both unit volumes is a load error rather than a
   defaulted geometry.
