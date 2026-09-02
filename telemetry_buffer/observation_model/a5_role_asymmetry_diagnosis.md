# A5: why the model cannot produce a passenger:crew asymmetry

Status note: the route mix has been re-measured at `e8b2b95` in
[`route_weight_measurement_findings.md`](route_weight_measurement_findings.md);
droplet is no longer dominant, so the droplet share quoted below is stale. The
analysis is kept as the record of the state it diagnosed.

VSP reports passenger attack rates of 5.7–6.9% against crew 2.0–2.4%, a ratio of
about 2.9 that is stable on both sides of the COVID break. The model returns
roughly parity. This note records where that parity comes from. It is a
diagnosis only: no model constant is changed here.

## What the model actually produces

Post-#346 matched-seed pilot, natural-history arm (`none_response`), pooled over
seeds. Crew denominators are recovered from the passenger denominator and the
run's agent count.

| Hull | Dose | Runs | Reported AR, pax | Reported AR, crew | Ratio | Ever-ill, pax | Ever-ill, crew | Ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| classic_cruise_1900 | 2.0 | 9 | 3.62% | 3.59% | 1.01 | 22.86% | 24.28% | 0.94 |
| classic_cruise_1900 | 2.5 | 8 | 2.62% | 1.90% | 1.38 | 14.82% | 12.85% | 1.15 |
| classic_cruise_1900 | 3.0 | 8 | 1.92% | 1.81% | 1.06 | 11.19% | 11.39% | 0.98 |
| expedition_cruise_450 | 2.0 | 9 | 4.92% | 4.31% | 1.14 | 26.13% | 22.64% | 1.15 |
| expedition_cruise_450 | 2.5 | 7 | 3.80% | 1.71% | 2.23 | 17.86% | 17.38% | 1.03 |
| expedition_cruise_450 | 3.0 | 5 | 2.97% | 1.49% | 1.99 | 15.95% | 9.85% | 1.62 |

The ever-ill columns matter more than the reported ones. **The asymmetry is
absent at the illness level, not just at the reporting level**, so A5 is not an
observation-layer defect. The surveillance code is if anything biased the other
way: `_agent_is_crew` gates an optional proactive crew screening pass that can
only add crew reports, and no role appears anywhere in the sick-call probability.

## Where the parity comes from

Establishment is almost entirely by one well-mixed, room-level route.
Single-shedder route probe, dominant-route attribution of infections:

| Hull | direct_contact | droplet | hvac_airborne | fomite | food |
|---|---:|---:|---:|---:|---:|
| expedition_cruise_450 | 22 | 343 | 0 | 0 | 1 |
| classic_cruise_1900 | 57 | 1484 | 0 | 0 | 0 |
| spirit_cruise_3000 | 144 | 2761 | 2 | 0 | 11 |
| mega_cruise_5000 | 379 | 8273 | 8 | 0 | 87 |

Droplet is a per-zone aerosol pool sampled through an inhaled air volume. Every
susceptible occupant of a zone draws from the same pool on the same terms. It
carries no information about who you touched, which mess you ate in, or whose
cabin you share. **The routes that do carry role structure — fomite, food, and
to a lesser extent direct contact — are the ones delivering almost nothing.**

Fomite is not merely small; it is numerically extinct. Total fomite dose over a
full classic voyage is 0.13 particles against 7.0e7 for droplet. The cause is
arithmetic, in two places:

1. Emission split. `SURFACE_DEPOSITION_FRACTION = 1e-4` and
   `FOOD_DEPOSITION_FRACTION_PER_EPOCH = 1e-4` against
   `DROPLET_AEROSOL_FRACTION = 0.05` — a 500× handicap at the source. The
   surface constant's comment cites a Java particle *survival duration*
   (86 400 steps), which is not a deposition fraction; the constant appears to
   be mislabelled rather than sourced.
2. Pickup. `_fomite_pickup_request` spreads the zone's surface mass uniformly
   over `zone_volume / DECK_HEIGHT_M`, i.e. the zone's whole deck footprint, and
   then samples a single 2e-4 m² fingerpad from it. For a 1000 m³ zone that is
   400 m² of "touchable" area and a per-touch fraction of 5e-9, times a 0.01
   transfer fraction and a 0.10 per-epoch touch probability.

Multiplying through, fomite delivers about 5e-14 of a shedder's output per
susceptible per epoch against droplet's ~3e-5: a factor of 6e8, which is the gap
the probe measures.

Both steps of (2) look wrong independently of any calibration. Norovirus deposits
on touched surfaces — handrails, tongs, flush handles, tabletops — whose area is
order 1–10 m², not on the whole deck; dividing by floor area assumes the
contamination lands where nobody puts a hand. And 0.1 touch-events per epoch is
two to three orders below observed hand-to-surface contact rates. There is also
no hand-to-mouth step at all: picked-up mass is credited directly as ingested
dose, which is a separate error in the opposite direction.

## Why this is the A5 mechanism and not a side issue

The model does contain role structure. Crew have their own berthing zones,
their own schedules (`CREW_SCHEDULE`, `GALLEY_CREW_SCHEDULE`, and the rest),
they are pushed to the crew mess for meals, they are excluded from passenger
dining venues, and `crew_contact_multiplier = 2.0` doubles their contact rate in
service zones. That structure is entirely expressed through *who you are near
and what you touch*. With 94–96% of establishing dose arriving through a
well-mixed aerosol pool, none of it can reach the attack rate. What survives is
the contact multiplier, which pushes crew *above* passengers — which is what the
ever-ill columns show.

So the model is, for transmission purposes, a set of well-mixed rooms with a
schedule decoration. That is enough to reproduce a hull-size gradient and an
epidemic curve; it is not enough to reproduce a role asymmetry, and it would not
be enough to reproduce a venue-specific or a food-handler-mediated outbreak
either.

## What this does not establish

Restoring fomite and food to plausible magnitudes is necessary for A5, not
demonstrably sufficient. Nothing here shows that the resulting asymmetry would
be 2.9 rather than 1.3 or 6. The real-world ratio also has candidate causes this
model does not represent at all, chiefly standing crew immunity from repeated
seasonal exposure — `immune_ratio` is applied uniformly across roles, which for
a resident population against a weekly-turnover one is an assumption, not a
finding. Crew presenteeism and mandatory occupational reporting push in opposite
directions on the observation side and are both absent.

The right sequence is: fix the route magnitudes on physical grounds and with
sources, re-measure the ratio, and only then ask what residual needs a role-
specific immunity or reporting assumption. Fitting the route constants to 2.9
would be the same mistake as fitting clearance to A2.

## Relation to the route-clearance result

This compounds with §9c. Route-specific pre-establishment clearance discounts
droplet by up to 14× relative to ingestion, which shifts establishment toward
exactly the concentrated, role-structured routes that are currently extinct. The
two corrections act on the same defect from opposite ends: one says droplet is
over-credited per virion, the other says fomite and food deliver essentially no
virions to credit. Neither is meaningful without the other.
