# AERO-SPLIT-01
**Date:** 2026-09-24
**Commit:** e20008d
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** e20008d

Continuous droplet emission is partitioned at source:
`far_field_share` (0.175, midpoint of the declared [0.05, 0.30] interval,
Grade C, swept-never-fitted) of each emitted spray still enters the zone's
well-mixed pool; the near share reaches a partner-bounded proximity ring at
the AERO-NEAR-02 two-box plume concentration, the ring bounded by the
CONTACT-ARCH-01 activity contact rates (`docs/droplet_field_split_spec.md`,
`transmission.droplet_field_split`, default `partition`, labelled
pre-change baseline `mode: off` which draws no proximity partners on the
shared stream and is bit-identical to the pre-change engine). The defect it
closes is the unbounded far field: under the pre-change architecture every
co-occupant of a venue inhaled `emitted x fraction/volume x inhaled`, so one
shedder in promenade/buffet/dining venues dosed ~850 people/day and the
declared Diamond Princess replay at the fleet-admissible Θ 4.22e10
overproduced recorded onsets ~17.7x with attack ~0.96 vs the record's ~0.19.

Paired-seed probe (`tools/covid_droplet_split_probe.py`, the
`QuarantineAttributionLedger` epoch-observer pattern, declared replay cell
`diamond_princess_2020` Θ 4.22e10, infection_age 3.3, imports 1; `off` vs
`partition` on the same seeds):

| seed | mode | events | day-0-2 share | day-0-5 share | confined | pathways |
|------|------|--------|---------------|---------------|----------|----------|
| 20200205 | off | 3574 | 68.7% | 78.9% | 203 | droplet 3537, hvac 37 |
| 20200205 | partition | 3561 | 57.1% | 73.0% | 200 | droplet 3272, hvac 287, contact 2 |
| 20200206 | off | 3548 | 0.1% | 0.1% | 213 | droplet 3540, hvac 8 |
| 20200206 | partition | 1675 | 0.1% | 0.2% | 628 | droplet 1161, hvac 514 |

Reading: the bound is real — a shedder's droplet reach is now its contact
rate (~2 partners/h in dining venues) plus a 17.5% room share, not the
whole room. On the seed that develops the early public-venue takeoff the
spike survives anyway (57.1% day-0-2): the plume term is ~40-850x more
concentrated per partner than the old pool share, each ring member infects
with near-certainty at this Θ, and ~2 partners/h x a few venue-hours still
branches faster than 1 until the susceptible pool thins. On the seed with
no takeoff under either mode the sustained phase halves (3548 -> 1675) and
the residual concentrates in crew venues (Crew_Mess_Main 569,
CrewMess_Fwd 216) and confinement exposure (628 vs 213 events) — the crew
mess is 2100 m3 serving ~1045 crew in 3 sittings, so even 17.5% of a
shedder-hour there is ~3.5x the promenade's old full-pool concentration.
HVAC's share rises under partition (287 and 514 events vs 37 and 8) because
the aerosol pool — which still carries the far share — is what drifts.

The partition is therefore a real reach bound, not a fit: the ~17.7x
overproduction at Θ 4.22e10 is not reachable by reach-bounding alone when
the takeoff ignites, and nothing here was tuned to 197. Follow-ons tracked
in `docs/covid/covid_open_ledger.md` §3: re-run the declared replay at the
fleet-admissible Θs, stand assay-2 back up, and run the declared
far-field-share sweep.
