# AERO-SPLIT-01: partition the droplet emission into near-field, far-field and settled shares

> **Status:** **Implemented, on by default (`partition`)** — `transmission.droplet_field_split`
> in `engines/transmission_core.py`; `mode: off` is the labelled pre-change
> well-mixed baseline in which the whole continuous share still enters the zone
> pool and no proximity draw exists. No constant is fitted: `far_field_share`
> ships the midpoint of a declared, grade-C interval and is meant to be swept,
> never tuned to a scored record.

## 1. The defect

Before this item the droplet pathway deposited `emitted ×
DROPLET_AEROSOL_FRACTION` into the zone's well-mixed aerosol pool, so every
susceptible co-occupant of a venue inhaled the same far-field dose. A single
shedder's reach was bounded only by venue occupancy — ~850 dosed hosts per day
in promenade/buffet/dining venues — and the AERO-NEAR-02 near field was an
excess on top of that pool, an add-on rather than a bound. The measured
signature (assay-1 §2a) was ~68% of transmission events landing in days 0–2 in
public zones, ~99% by the droplet pathway.

## 2. The partition

`emitted → { near-field share, far-field share, settled share }`, declared per
run as

```yaml
transmission:
  droplet_field_split:
    mode: partition        # partition | off
    far_field_share: 0.175 # fraction of continuous emission reaching the zone pool
    settled_share: 0.0     # fraction deposited ballistically, never inhaled
```

`near_field_share = 1 − far_field_share − settled_share`. The far-field share
alone enters the zone pool (and, from there, HVAC transport and the swab
channel); the settled share leaves the inhaled budget entirely; the near-field
share is delivered only to a partner-bounded set, as a plume concentration
`near_share / (β·T)` in the near-field volume — not as an excess over the far
field. A host outside every ring inhales only the pool share; a partner in a
ring inhales the pool share **plus** the plume term, so the near field is a
partition of the emitted mass, not an add-on over the whole emission.

`mode: off` reproduces the pre-partition tree exactly: the pool carries the
full continuous share and `_proximity_shedder_ids` is never drawn, so no new
consumption lands on `engine.rng` and an `off` run is bit-identical to the
pre-change code. The partition itself does draw on `engine.rng`, so an
on-vs-off paired contrast is the intended physics plus the stream reordering
the new draw induces (RNG-FRAILTY-STREAM-01 applies); the labelled baseline is
what keeps the contrast honest.

The partition requires the near field to carry the near share: with
`near_field_air.mode: off` the spray has nowhere else to go, so such a run
keeps the whole pool (the `near_field_on` guard folds the partition back to
`pool_share = 1.0`) — the A5-style all-air-off bound is preserved verbatim.
`emesis_conditioned` arms keep their refusal through `_near_field_admits` —
the partition changes nothing about norovirus gating.

## 3. The partner bound

The near-field ring now has three membership rules: cabin-mate (Cabin_Corridor
only), same dealt meal table, and **proximity partner** — a per-target draw
from the zone's activity contact sample (`_sample_contact_partners` driven by
`_activity_contact_draw`, the same sourced per-activity rates per hour as
CONTACT-ARCH-01, Pung 2022), capped by `n_occupants`. The proximity draw is a
fresh sample of the same distribution rather than the contact pathway's own
sample, so the two pathways' partner sets stay statistically independent of
each other. Physically: a person near a talker for part of an epoch sits
in the breathing-zone plume; the room beyond the conversational set receives
only the dilute share that survives into room air.

## 4. Constant and sourcing

| Parameter | Value | Source | Grade |
|---|---|---|---|
| `far_field_share` default | **0.175**, midpoint of declared interval [0.05, 0.30] | composite | C |
| `settled_share` default | 0.0 (a declared sink, unexercised) | — | — |
| near-field exchange β | reuses `interzonal_airflow_m3_per_hour` 204 m³/h | Keil 2017 (AERO-NEAR-02) | B |
| partner count per epoch | reuses `activity_contacts` rates per hour | Pung 2022 (CONTACT-ARCH-01) | B |

The interval is a composite bound, not a measurement: the room-reachable tail
of a *droplet-mode* spray is a small fraction of the emitted dose — the ≤5 µm
fine band that dominates exhaled copy counts (85–90%, Coleman 2022 DOI
10.1093/cid/ciab691; Alsved 2022 DOI 10.1080/23744235.2022.2140822) rides the
airborne reservoir route, while coarse ballistic spray settles within ~1.5–2 m
(Xie 2007 DOI 10.1111/j.1600-0668.2007.00469.x) and only initially ≤~15 µm
droplets contribute to long-range airborne exposure (Li 2021 DOI
10.1111/ina.12946). The interval is declared so a successor sweep can post the
contrast across [0.05, 0.30]; the shipped midpoint is not a fit to the record.

## 5. What moves

Every figure whose mechanism was the unbounded room pool — the Θ-1e9-plus
voyage burns, the stage-2 ~17.7× onset overproduction, the day-0–2 public-zone
event mass, all droplet route shares — is superseded pending remeasurement on
the partition tree. Contact, fomite and cabin-mate addback channels are
unchanged (the addback restores the pool-scale share only). The labelled `off`
baseline and the probe `tools/covid_droplet_split_probe.py` carry the paired
evidence.
