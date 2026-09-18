# AERO-NEAR-02
**Date:** 2026-09-18
**Commit:** 9c1ed81
**Pathogens:** all
**Status:** measured
**Measured at:** 7d8b0d2

## Defect

The former continuous near-field route used a retained-fraction and assumed
unit-volume parameterisation. It could not identify the near/far exchange, and
the model had no per-meal seating unit for buffet or crew-mess diners.

## Declaration

The shipped declaration is `transmission.near_field_air.mode: two_box`, with
interzonal airflow β = 204 m³/h and neighbouring-table ratio ρ = 0.43.
β is a declared swept axis from 24–1,140 m³/h, not a fitted campaign constant.
The far-field pool and its mass are unchanged. Buffet and crew-mess diners are
dealt into random tables at every meal epoch, with cabin bookings kept
together, on-duty service staff excluded, and the default table size applied.
Fixed MDR and specialty seating is unchanged.

β is Keil et al. 2017 (DOI 10.1080/15459624.2017.1334903), Grade B,
Origin: Abstract + Results. ρ is the 0.40–0.47 analogous-setting envelope in
Li et al. 2021, Table 3, Grade B, Origin: T3. Background air-speed and
near-field extent context are recorded in `docs/near_field_air_spec.md` §11.
Serving-line queue exposure and cruise-dining-table β remain open omissions.

The COVID change detector moved from `(81, 42, 217, 88, 11)` to
`(64, 8, 217, 67, 36)` on CPython 3.11 and to
`(51, 8, 217, 51, 32)` on local CPython 3.12. These moves are attributed to
the default β near-field dose and the additional RNG consumption from
per-meal buffet/crew-mess table dealing. The CPython 3.11 reading was read
from the CI job (fast tier, 3.11) on this branch.

## Measurement (Measured at 7d8b0d2)

Both diagnostic cells were re-run at `7d8b0d2` with the AERO-NEAR-02 default
on the enforced SOP-017 order (QUAR-ORDER-01), `mega_cruise_5000`, full
32-day horizon, `sars_cov2_resp`. `de83182` (the cabin-mate near-field term
below) postdates the measurement; it touches `Cabin_Corridor` pairs only, so
the dining figures stand and the totals are historical at that SHA.

**Burning cell** (seed `20200206`, Θ = 3.16e7): **2 infections** (0.1%), both
droplet in `Cabin_Corridor` on days 7 and 19; no dining infection anywhere.
QUAR-ORDER-01 measured 2,182 on this cell. The per-meal table deal consumes
RNG, so this is a different trajectory of the same seed, not a suppressed copy
of the old one: the Windjammer meal epochs on days 12–15 (403–419 occupants,
24 per day) held no shedder, and the day-13/14 Windjammer burst did not recur.

**Intermediate cell** (seed `20200210`, Θ = 1e9): **1,390 infections** (37.5%;
QUAR-ORDER-01 measured 10). Infections by day — 4: 1, 13: 8, 15: 74, 16: 4,
17: 16, 18: 16, 19: 276, 20: 207, 21: 263, 22: 263, 23: 65, 24: 63, 25: 29,
26: 16, 27: 11, 28: 13, 29: 16, 30: 26, 31: 23. Route: droplet 1,186,
`hvac_airborne` 204. Zone type: Dining 977, `Cabin_Corridor` 338, Free 75.
Target status: unconfined crew 1,045, confined passengers 303, unconfined
passengers 42. Dining by venue: `Crew_Mess_Main` 607, `CrewMess_Fwd` 345,
`MainDining_L` 20, five venues at 1 each, `Windjammer` 0. Days 12–15 dining
infections: `MainDining_L` 20, every other venue 0.

**The roomful-at-once archetype is still present, and it is the far field, not
the near field.** `Crew_Mess_Main`, epoch 476 (day 19): 242 occupants, 2
shedders, pool mass 1.30e-5, **140 infections**. 139 of the 140 received the
identical dose 1.110e-9 (Θ·dose ≈ 1.1, so P ≈ 0.67 for every occupant of the
well-mixed 2,100 m³ pool); the maximum was 1.13e-8, ≈10× — the same-table
near-field excess, matching the declared gain ratio
(1/204 − 1/2,100)/(1/2,100) ≈ 9.3. The near field adds a local ring on top of
the pool; it does not change what the pool does to a roomful of hosts with
identical susceptibility on the Θ arm. The next structural items are host
frailty provenance (`docs/covid/covid_open_ledger.md` §3) and crew-mess
seating structure (below).

**Windjammer 100× pool-mass jump (QUAR-ORDER-01 trace, 2.16e-4 → 2.16e-2 at
1 → 2 shedders): not re-traced.** The trajectory that produced it did not
recur in either cell, and neither cell had a Windjammer shedder on days 12–15,
so the dump instrumented for it recorded nothing. It stays open.

## Seating persistence (open null)

The per-meal deal is independent across meals; the only persistent unit is the
cabin booking. Literature pass (2026-09-18, Consensus): Read et al. 2008
(J. R. Soc. Interface, Abstract) — casual conversational encounters are
predominantly irregular and well captured by random mixing, close contacts
stable; Pung et al. 2023 (temporal contact
patterns and superspreader prediction, Abstract) — in
workplaces and schools retained contacts are dominated by the same department,
and no-repetition models overestimate unique contacts by 20–70%. No cruise
buffet or crew-mess seating measurement was found. The passenger buffet deal
(strangers as casual contacts, booking as the stable core) is consistent with
Read 2008; the crew mess is a workplace and likely retains department
structure, which the model does not declare. A persistence axis is not
introduced until sourced; nothing here may be set against the attack rate.

## Follow-up in `de83182`

A confined shedder's near-field emission to a **cabin-mate** is no longer
scaled by the confinement isolation factor (the pair shares the stateroom;
this matches `_cabin_pair_contact_factor`, which already returns 1.0 for
cabin-mates on the contact route). `Cabin_Corridor` pairs only; no new
constant. The CPython 3.12 detector tuple was unchanged by it.
