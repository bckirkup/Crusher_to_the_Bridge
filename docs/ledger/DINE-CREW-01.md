# DINE-CREW-01
**Date:** 2026-09-18
**Commit:** 1ede284
**Pathogens:** all
**Status:** open

## Change

Crew-mess booking groups are now dealt into per-meal tables within department
(`agent.work_zone`), while buffet groups retain the existing whole-sitting
shuffle. Cabin booking groups remain together, and the venue far-field pool is
untouched, so the AERO-NEAR-02 roomful-at-once burst is expected to persist.

## Evidence and declared nulls

Kakimoto et al. 2020, MMWR 69(11), DOI 10.15585/mmwr.mm6911e2, reported that
15 of the first 20 Diamond Princess crew cases were food-service (245/1,068
crew), including a deck 3 cluster and cases in the same occupational group.
This is recorded as an ANCHOR against which the model is scored, not as a
source for the dealing rule.

Pung et al. 2022, Nat Commun, DOI 10.1038/s41467-022-29522-y, provides Grade B
evidence (Results section and Table 2 weighted degree 8.3 for crew versus 13.9
for passengers) that crew contacts cluster by department. The crew-mess
department deal is a structural declaration based on that evidence; no
numeric constant is introduced.

Shift and break structure is not modelled: departments are spread over the
three sittings by the existing sitting rotation. The mess venue remains a
capacity-weighted draw, and no cruise crew-mess seating observation was found
in searches of Consensus and the Europe PMC full text of Pung et al. 2022.
The AERO-NEAR-02 intermediate-cell numbers measured at `7d8b0d2` are
superseded pending remeasurement.
