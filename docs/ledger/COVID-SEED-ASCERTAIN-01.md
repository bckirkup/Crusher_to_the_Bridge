# COVID-SEED-ASCERTAIN-01
**Date:** 2026-11-26
**Commit:** 49b1226e
**Pathogens:** sars_cov2_resp
**Status:** closed

Owner decision on the boarding-geometry scoring contract under the zero-inflated
COVID source law.

## Decision

`index_shedding_at_day0` remains an admissibility requirement: an onset-eligible
seed whose day-0 episodic occurrence draw is silent is not a valid Diamond
Princess or Greg Mortimer replay seed for the scored contract.

The reason is ascertainment conditioning, not a claim that a biologically
infected boarding host must emit every day. Diamond Princess and Greg Mortimer
are in the validation record because a transmission process with substantial
source emission was observed; neither ship would have entered the outbreak
record as the epidemiological object being replayed without that process. The
scored seed class is therefore conditional on a shedding index event. A silent
day-0 draw is a possible draw in the source model, but it is outside the
ascertainment-conditioned event class being validated.

## Consequence

`tools/covid_screen_readout_common.py::audit_index_geometry` correctly treats
`index_shedding_at_day0 == false` as a geometry failure. Eligibility alone is
insufficient, and the occurrence draw should not be demoted to a separate
informational field for the DP/GM contract. This is a scoring-contract decision;
it is not fitted to an attack-rate, onset, testing, or outcome anchor. Greg
Mortimer remains held out, and H5 remains held out forever.

No simulation campaign was run for this entry.
