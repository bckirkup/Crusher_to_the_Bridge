# CONTACT-ARCH-01 — a host's contact draw is a property of the unit the ship's architecture and schedule put it in, not of the day

> **Status:** Implemented, off by default — `transmission.activity_contacts`
> in `engines/transmission_core.py`. With the block absent or `enabled: false`
> every run is bit-identical to the uniform POLYMOD draw it replaces, on the
> same RNG path. **No rate is adopted**: enabling the block requires every
> activity's per-hour rate to be declared by the run, and the declared values
> are swept axes with the provenance of
> [tranche 37](literature/consensus_tranche_37_contact_architecture.md).
> The block is a design arm of the bounded gate (`--activity-contacts`, §4a);
> the first matched expedition campaign is submitted and its readout and the
> §6 checks are to be recorded here before anything is read against them.

## 1. The defect

In the shipped `per_partner_contact` mode every susceptible host, in every
mixing unit, in every epoch, draws

```
n_contacts ~ Poisson(13.4 / 24 × voyage_contact_multiplier)
```

and receives the full per-epoch shedding of each sampled partner. The 13.4 is
Mossong 2008's pooled European diary mean of *distinct persons per day*. Three
things follow, none of them a magnitude problem:

1. **Role-blind.** A waiter on a ten-hour shift and a passenger asleep draw the
   same count. The cruise sensor record has passengers at twice the crew's
   distinct close contacts (Pung 2022); unbubbled institutional records have the
   mobile working roles at 1.3–2.2× a resident's (Duval 2018).
2. **Activity-blind.** Nine `Sleep` hours carry 37.5% of the day's draw against
   a measured ~6% of contacts at night (Vanhems 2013); a one-hour sitting and a
   two-hour sitting yield the same expected count, against per-visit saturation
   (Pung Fig. 2).
3. **Architecture-inert.** The zone decides *who* can be sampled and never *how
   many*. This is why `BERTH-01`, `DINE-SEG-01`, `SEAT-01/02`, `DINE-PARTY-01`
   and `CONTACT-SCALE-01` — five reallocations of partners — were nulls or
   near-nulls on the crew arm: the aggregate draw they reallocated never moved.

Mossong's own location split (home 23%, work 21%, leisure 16%, travel 3%) says
13.4 is a *sum over settings of very different intensity*. The repair is to
derive it.

## 2. The structure

```
schedule token + zone type + mixing unit + duty state
    → contact activity            (one of eight)
    → declared rate per hour       (number, or per-role mapping)
    → clock conversion, voyage multiplier
    → Poisson draw, capped by the unit's eligible pool  (unchanged sampler)
```

The **contact activity** is resolved per target, per mixing unit, per epoch,
from state the engine already holds — nothing new is assigned to an agent:

| Activity | Resolved when | Unit the draw lands in |
|---|---|---|
| `cabin` | the mixing unit is a cabin compartment of a `Cabin_Corridor`, or the schedule token is `Sleep` in any other zone | the cabin (`BERTH-01`) |
| `corridor` | the mixing unit is a `Cabin_Corridor`'s hallway residual | the corridor, cabin mates excluded |
| `work_service` | `_on_service_duty`: a food employee, on `Work`, in its own service zone | the venue floor |
| `work_other` | schedule token `Work`, anywhere else | the work zone |
| `dining_table` | a `Dining` zone that is the target's own venue and the target has a table party | table party + floor by `dining_party_contact_share` (`DINE-PARTY-01`) |
| `dining_venue` | any other presence in a `Dining` zone (buffet, crew mess, a diner away from its venue) | the venue |
| `leisure` | schedule token `Free` outside a `Dining` zone | the leisure zone |
| `other` | anything unresolved (a `Meal` token outside a `Dining` zone, an empty schedule) | the zone |

Role enters three ways, in this order of preference: **through the schedule**
(crew `Work` hours are passengers' `Free` hours), **through the duty state**
(`work_service` is crew by construction), and only where a setting's evidence
distinguishes the roles, **through a per-role rate** (`{passenger: x, crew: y}`
on one activity — the crew mess against a passenger buffet is the case in
point). Nothing else about a host changes its rate.

Occupancy does **not** enter the rate. Shirreff 2024 measures the aggregate as
frequency-dependent; occupancy enters through the eligible pool (the draw is
capped by it, as today) and through the class-directed exponent φ
(`CONTACT-SCALE-01`), which composes with this change unchanged.

## 3. Configuration

```yaml
transmission:
  contact_mode: per_partner_contact
  activity_contacts:
    enabled: true
    rates_per_hour:           # distinct partners per hour, per activity
      cabin: 0.3
      corridor: 0.2
      work_service: 3.5
      work_other: 1.5
      dining_table: 3.0
      dining_venue: {passenger: 3.0, crew: 2.0}
      leisure: 2.0
      other: 0.5
```

Rules, enforced at load:

- The block is optional. Absent, or `enabled: false`, the uniform draw runs
  on exactly its old path (`_draw_contact_multiplier`'s final branch), with no
  extra RNG.
- `enabled: true` requires **all eight** activities to be declared. There is
  no engine default for any of them, because none is measured for this
  setting; a run that enables the block and omits one fails at load.
- Each rate is a finite number in `[0, 30]` per hour, or a mapping from role
  (`passenger`, `crew`) to such numbers covering both roles. `30/h` is a
  refusal band (Duval's individual maximum is 47.3/day), not a plausible value.
- The values above are **illustrative of the shape only**. They are not a
  default, not a recommendation, and do not appear in the tree.
- The block is read only under `per_partner_contact`; a run that enables it
  under any other `contact_mode` is refused at load.

## 4. What is sourced, and how it should be swept

From tranche 37, per activity — each a declared interval, midpoint stated,
role split only where measured:

| Activity | Evidence | Interval to declare | Grade |
|---|---|---|---|
| `dining_table`, `dining_venue` | Pung Fig. 2a: close contacts plateau at 3 (IQR 2–5) after ≥1 h in an F&B location; 71% of passenger close contacts are F&B | 2–5 per sitting-hour | A setting / B state |
| `leisure` | Pung Fig. 2c: 2 (1–3) at 30–60 min, 4 (2–7) at ≥2 h in sports; entertainment 16% of contacts | 1–3 per hour, saturating | A/B |
| `work_service` | Jiang 2017b: 2.9–5.0 contact episodes/h for working roles whose task is contact; Duval: porters/physicians 1.3–2.2× residents per day | 2.9–5.0 per hour (upper analogue) | B |
| `work_other` | Jiang 2017a: work-block contacts ~3× a community adult's; Pung crew total 10/day under bubbles over a ~10 h shift | 0.5–2 per hour | B/C |
| `cabin` | ∅ per hour. Bounded by the pool (1–3 mates) and Vanhems's night share (~6% of contacts over ~9 h) | 0–0.5 per hour; the pool caps it | C |
| `corridor` | Mossong "travel" 3% of 13.4 ≈ 0.4/day | 0–0.5 per hour | C |
| `other` | ∅ | declare 0 or the leisure interval | C |

The sweep axis is the vector of eight rates over these intervals. A first
campaign should hold role splits at 1 (no per-role mapping) so that any
crew:passenger difference in the readout is **produced by the schedule and the
architecture**, which is the point of the change; a per-role mapping on
`dining_venue` is a second arm.

### 4a. The design arm

`admissible_region.py --activity-contacts 'cabin=<r>,corridor=<r>,...'` carries
one complete eight-rate declaration on a `Design`, the way φ (#487) and κ
carry theirs; the shard entrypoint forwards the string as the Batch parameter
`activity_contacts` (`off` is the control, because a Batch parameter cannot be
empty). Absent, the design writes no `transmission` override and the run is
the uniform 13.4 draw on its old RNG path — the paired control for the same
grid, design seed and seed base. Present, `build_run_spec` writes
`contact_mode: per_partner_contact` and an `enabled` block whose
`rates_per_hour` lists every activity, scalar across roles; a partial,
duplicated or malformed declaration is refused before the grid runs. A rate is
a scalar on purpose: the arm has no per-role field, so the first campaign's
role splits are 1 by construction and a crew:passenger difference in its
readout is the schedule's.

The first campaign brackets the §4 vector rather than sampling it: three arms
at the interval lows, midpoints and highs (`other` = 0, then the leisure
midpoint and high), each matched run-for-run to the uniform control over the
13-factor `expedition_sensitivity` box (256 Sobol' points × 6 seeds, design
seed 17, seed base 500 — the grid of the three-arm and φ campaigns). Three
corners of an eight-dimensional interval box are a finite sample of it and
are reported as one; a Sobol' sweep of the eight rates as factors is a
different grid and a later campaign if the bracket resolves anything.

## 5. What this change does not do

- It does not move `POLYMOD_CONTACTS_PER_DAY`, which remains the reference and
  the control arm.
- It does not change partner sampling, table parties, cabin compartments,
  hallway residuals, φ, or any dose term. The `direct_contact` partner still
  receives the partner's full per-epoch shedding; the register's grading of
  that semantics stands.
- It does not implement per-visit saturation. With one-hour seat-turns
  (`SEAT-02`) the dining visit *is* an hour, so the per-hour rate and the
  per-visit plateau coincide there; leisure blocks of two to four `Free` hours
  do not saturate under a constant per-hour rate. A dwell-tracking saturating
  form is `CONTACT-ARCH-02` if the first readout shows it matters.
- It does not touch `density_dependent`, `heterogeneous_zone_dose` or
  `legacy`.

## 6. Checks, recorded before the first campaign

Out-of-sample, **not targets**:

1. **Per-role daily totals.** Summing each class's expected draw over its
   schedule on each hull gives a per-role contacts/day. Pung's medians are
   **20** (passenger) and **10** (crew) close contacts under COVID-era
   operations; Mossong's **13.4** is the general-population reference. The
   model's totals are reported against both. A total far outside 5–40 is a
   declaration error; a crew:passenger ratio is reported, never adjusted.
2. **Night share.** The expected share of a host's contacts in `Sleep` hours,
   reported against Vanhems's 5.9%.
3. **Setting share.** The share of passenger contacts drawn in `Dining` zones,
   reported against Pung's 71%.
4. **A5 and the posting rate** are read as before. Tranche 37's finding that
   the instrumented crew made half the passengers' contacts means this change
   is expected, if anything, to move A5 **away** from 4.3. That is the result
   to report if it occurs.

## 7. Validation

- Uniform control: with the block absent, the fast tier's goldens are
  unmoved and a matched run is bit-identical (`tests/test_contact_architecture.py`).
- Activity resolution: every row of the §2 table has a test.
- Load rules: missing activity, out-of-band rate, malformed role mapping and
  a non-`per_partner_contact` mode are refused with a message naming the key.
- Graded sensitivity: raising one activity's rate raises the expected draw in
  that activity's units and nowhere else.
