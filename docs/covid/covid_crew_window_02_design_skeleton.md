# CREW-WINDOW-02 design skeleton — fractional / activity-scoped crew duty

Status: **draft skeleton for owner review — not a design, not frozen, no
cells may run against this file.** It exists to put the follow-on arm
families on paper so the owner can steer the arm definitions before a
design is written and frozen. `covid_crew_window_01_design.md` is the
format this file imitates; a real CREW-WINDOW-02 design lands only after
the open decisions below are answered.

## Question

CREW-WINDOW-01 measured the bracket but found no interpolation
(240/240 cells at `ea9550ef`, `covid_crew_window_01_readout.md`):

| arm (20 seeds, takeoff-conditional medians) | Θ1e6 | Θ7.9e6 |
|---|---:|---:|
| `D0_declared` — SOP-017, all crew exempt and working | 601 | 739 |
| `EXEMPT_ENGMED` / `EXEMPT_ESSENTIAL` | 18 | 70 |
| record-informed band | **150–350** |  |

Post-landing resolution (PR #923): the cliff is the hull's class
vocabulary, not an attenuation function — `diamond_princess_2020`
instantiates only `passenger_general` + `crew_general`, so every
exempt-subset arm confined the entire crew identically and the
ENGMED/ESSENTIAL bit-identity was forced by construction. The record's
"essential service continued" distinction lives **inside** `crew_general`'s
duty mix, which this hull does not currently subdivide.

Question for the next leg: **which interior point between the corners —
zero crew working vs the whole crew working — lands the during-window
median inside [150, 350]?**

## What the engine actually offers (verified against the tree, 2026-10-05)

- Crew carry a `work_zone` (one posting per agent), but `crew_general`
  declares no `duty_zone` — on this hull every crew work posting is a
  **uniform-random draw over the 34 Free+Dining zones**
  (`engines/infection_dynamics_bridge.py` `_resolve_class_zones`). There
  is no activity taxonomy inside the class: the day template is a flat
  `Work`-token schedule (`CREW_SCHEDULE`), and "what this crew member
  does" is fully encoded by which zone the lottery gave them.
- Confinement gating is `agent_class in exempt_classes`
  (`orchestrator_epoch.py` `confine_all_agents`/`confine_agents`) —
  binary, class-keyed, no fractional or zone-keyed variant today.
  The dict-agent projection those paths read (`AGENT_OPTIONAL_FIELDS`
  passthrough in `telemetry_buffer/fields.py` →
  `engine_payload_to_schema`) does NOT currently carry `work_zone` —
  the zone gate needs that field added to the passthrough (one-line,
  presence-checked) or evaluated against `engine.agents` upstream.
- `engines/crew_duty_exclusion.py` (VSP §4.4.1.1.1) is symptom-timed and
  measured null on this channel — not the tool for this leg.
- R3 meal delivery to confined passengers exists
  (`_caregiver_service_epoch`) and draws its steward uniformly from
  **unconfined** crew (`_draw_service_responder`; the
  `service_function_classes` grammar is declared but no shipped
  population populates it). Consequence measured in CW-01 without being
  named: the ALLHANDS-corner arms also killed cabin meal delivery — real
  DP kept delivering — so the 18/70 corners over-shoot the record in both
  directions at once. Any arm that confines a subset leaves deliveries
  running through the still-working remainder.
- On the mega hull, 10 of the 34 work-assignable zones read essential in
  the record's sense (galleys, Engine_Room_Aft/EngControl, Bridge,
  Medical_Center, Central_Stores, Laundry_Main, WasteTreat, crew messes);
  24 read hospitality/retail/dining-floor. Dining venues are the
  contested members — on the real ship their staff were redeployed to
  cabin meal delivery, so both a WIDE (dining included, ~53% expected
  exempt) and a NARROW (dining excluded, ~29% expected exempt) reading
  exist. These expected shares are arithmetic over a uniform lottery,
  not sourced fractions — declared Grade C.

## Candidate arm families (owner picks)

### A. Zone-essential exemption — `EXEMPT_ZONES` (record-shaped, small engine delta)

New protocol modifier beside `exempt_classes` — e.g.
`exempt_work_zones` (or `nonessential_work_zones`): an agent in an
exempt class is confined anyway when its posted `work_zone` is not on
the order's essential-zone list. On this hull that turns the flat
"all crew work" into "only crew posted to essential zones work" —
the record's shape expressed on the vocabulary the ship already has.

- `EXEMPT_ZONE_NARROW`: essential = galleys + engine/bridge + medical +
  stores/laundry/waste + crew mess (10/34 → ~29% keep working).
- `EXEMPT_ZONE_WIDE`: + dining venues (18/34 → ~53% keep working).

Pros: two interior points between the corners with zero new classes and
no RNG-stream restructuring at spawn (the zone draw already exists); R3
deliveries continue through the still-working subset — record-faithful.
Cons: the underlying uniform lottery is itself unsourced; the arm is a
probe of *how much* duty has to stop, and the realized exempt share is
emergent (must be witnessed — see audit).

### B. Headcount-fraction exemption — `EXEMPT_FRAC` (count-scoped, smallest delta)

`exempt_classes` gains a fractional form — e.g.
`exempt_fraction: {"crew_general": f}` — a sticky per-agent draw at
order activation; the exempt f keep working, the rest confine. Ladder
f ∈ {0.25, 0.5, 0.75} straddles the corner gap directly.

Pros: mechanically simplest; the ladder reads the dose-response of
working-crew count head-on. Cons: a random fraction is *not* the
record's essential-service distinction — if it lands the band, the
winning f still has to be interpreted back into which duties ran (the
Zone arms skip that indirection). Still worth carrying as the semantics-
free control.

### C. Duty-mix subclassing — `CREW_DUTY_MIX` (structural; probably a separate stage)

Split DP's `crew_general` 1,045 into sourced subclasses
(`crew_service`, `crew_hotel`, `crew_engineering`, `crew_medical`, …)
each carrying `duty_zone`, a real schedule template, and a
`berth_group`; populate `service_function_classes` so R3 draws stewards
from the service class; then `exempt_classes` exempts the essential
subset and the CW-01 grammar becomes live on this hull.

Pros: the real model improvement — makes the four-class protocol
vocabulary mean something on DP, fixes the uniform-lottery posting, and
every exemption reading becomes expressible by name. Cons: changes agent
spawn → RNG stream moves → golden/attribution repins; the subclass
fractions are only partially sourceable (deck-3 restaurant cluster,
department counts), the rest declared; heavier than an arm — this is
the "if A/B land, build C for the committed configuration" path, not a
cell in this grid.

## Cells, seeds, pairing (sketch)

`{Θ1e6, Θ7.9e6}` × `{D0_declared, EXEMPT_ZONE_NARROW, EXEMPT_ZONE_WIDE,
EXEMPT_FRAC_25, EXEMPT_FRAC_50, EXEMPT_FRAC_75}` × 20 seeds = 240 cells
on the verbatim replay contract — same grammar as CW-01. If owner picks
one family only: `{D0, NARROW, WIDE}` or `{D0, FRAC25/50/75}` = 120
cells. Canary: the middle-expected-share arm @7.9e6 (ZONE_WIDE or
FRAC_50) — it lands furthest from both corners and reads the realized
exempt share immediately.

## Admissibility and verdict grammar (sketch — freeze before cells run)

Same grammar as CW-01: CHANNEL-LANDED / UNDER-ATTENUATED /
OVER-ATTENUATED / UNMOVED vs `infections_during_quarantine` median in
[150, 350], before-phase seed-paired unmoved, crew share moving toward
0.29. `D0_declared` is the pairing baseline and clause-scored row; all
other arms non-scoring probes.

## Audit invariants (sketch — adds the CW-01 gap fix)

- CW-01's invariant checked the **declared** `exempt_classes` set and
  missed that the named classes carried no agents. New required witness:
  **realized exempt headcount** — every cell echoes
  `confined_crew_count` / `working_crew_count` (and on ZONE arms the
  realized exempt share by posted zone). An arm whose realized working
  share is 0 or 1 is an ALLHANDS/D0 equivalent and reported as such.
- R3 reach witness on every confining arm: `service_deliveries` per
  cell — a fraction arm that starves the steward draw to zero is a
  different mechanism than the record.
- Carry over CW-01's window/index/propensity/delivery invariants
  unchanged.

## Report immediately if

Any realized-share witness contradicts the declared arm; any arm lands
the band with before-mass unmoved (CHANNEL-LANDED — stop); the ZONE arms'
realized exempt share departs materially from the lottery expectation
(zone-posting distribution is not uniform in practice — report what it
is).

## Non-goals

- No fitting: fractions and zone lists are declared arms; whichever lands
  is a magnitude to source afterward, not a constant to adopt.
- Passenger-side under-delivery (F13/F14, D2 cabin witness) stays a
  separate leg — crew share is reported, not scored.
- If the whole fractional axis skips the band: the suspect leaves this
  channel — dating/ascertainment (map D1–D3) or the phase residual F8 —
  and that is the readout's conclusion, not a new arm.

## Required deltas before cells run (sketch)

1. `protocols.json`: modifier for the ZONE arm
   (`exempt_work_zones`/`nonessential_work_zones`) and/or fractional
   `exempt_classes` — semantics fixed here before implementation.
2. `orchestrator_epoch.py`: apply the zone/fraction gate inside the
   existing confinement paths (enforced + voluntary); confined
   exempt-classed agents take the same cabin-bound path as passengers.
   ZONE arms need `work_zone` on the confinement dicts — add it to
   `AGENT_OPTIONAL_FIELDS` (presence-checked passthrough) or evaluate
   the gate against `engine.agents`.
3. Payload echoes: realized `confined_crew_count` /
   `working_crew_count`, realized exempt share by zone on ZONE arms,
   `service_deliveries` count per cell.
4. Campaign registration under `campaigns/covid/crew_window_02/` and a
   design JSON carrying the frozen admissibility verbatim.

## Open decisions for the owner

1. Which family runs: A (zone-essential), B (fraction ladder), or A+B
   on one grid (recommended — A is the record shape, B is the semantic
   control; 240 cells).
2. Dining venues essential or not — the NARROW/WIDE pair exists because
   the record supports both readings; running both costs nothing extra.
3. Whether C (duty-mix subclassing) is queued as the next structural
   stage regardless of outcome, or only if a fractional arm lands.
4. Whether this leg runs before or after the D2 passenger-cabin witness
   — they are independent; D2 answers the share defect's other half.
