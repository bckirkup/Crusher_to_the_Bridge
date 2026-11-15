# NORO-HAND-CASCADE-01-MEAL-SECONDARY
**Date:** 2026-11-15
**Commit:** 08fbe720
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 893cc54d

## Question

Does the provisioned-lot pan cohort convert into secondary transmission during
the same meal-service span? The live hypothesis was that pan mass diluted across
many takers is converted into rare large secondary exposure/infection bursts
during the initial meal service events, and that this conversion is currently
underestimated.

## Method

`tools/noro_diag/meal_secondary_probe.py` runs the five posted
`fl_exp_12d_sens_p06_paxv` seeds on `expedition_cruise_450` / `norwalk_gi` under
`growth_chain_census` with `payload_profile="full"`. It buckets hazards,
acquisitions, challengeable pickups, hand contacts, unit-epoch acquired mass and
food-venue acquired rows by:

- `before_cs`: epoch before the provisioned-lot common-source span;
- `cs_span_pre_q`: inside the span and before first quarantine;
- `cs_span_post_q`: inside the span and after first quarantine;
- `after_cs`: after the span.

The provisioned-lot span is the min/max `start_epoch`/`end_epoch` over
`common_source.events` with `source_kind="provisioned_lot"`. Secondary
acquisitions are acquisition rows whose dominant pathway is not
`common_source_food`. Acquired-source exposure proxies are challengeable pickup
rows with `source_acquired_share > 0`, `unit_epochs.mass_acquired`, and
`hand_contacts` whose donor had an earlier `common_source_food` acquisition.
First symptom and first quarantine epochs come from the voyage timeseries. The
recorded rows were produced by the equivalent inline aggregation at `b3a4db7a`
(engine `893cc54d`) under `PYTHONHASHSEED=1`; `git diff 893cc54d..08fbe720` in
the scoped transmission/pathogen/platform/campaign paths touches only
`engines/contamx_transport.py`.

## Measured

| seed | CS span | first symptom | first quarantine | acquisitions | secondary acquisitions pre-Q / in-span post-Q / after-span |
|---:|---:|---:|---:|---:|---:|
| 8073 | 16-82 | 37 | 50 | 95 | 0 / 5 / 9 |
| 8038 | 10-67 | 30 | 35 | 115 | 1 / 9 / 11 |
| 8046 | 7-14 | 19 | 24 | 89 | 0 / 0 / 22 |
| 8047 | 10-44 | 28 | 40 | 71 | 1 / 0 / 13 |
| 8077 | 10-13 | 4 | 24 | 59 | 0 / 0 / 14 |

Aggregate secondary acquisitions by bucket/pathway:

| bucket | pathways |
|---|---|
| `cs_span_pre_q` | caregiver 2 |
| `cs_span_post_q` | fomite 9, caregiver 3, food 2 |
| `after_cs` | fomite 43, caregiver 24, emesis_aerosol 2 |

Acquired-source exposure proxies, summed over the five seeds:

| proxy | `cs_span_pre_q` | `cs_span_post_q` | `after_cs` | after / pre |
|---|---:|---:|---:|---:|
| challengeable pickup acquired dose, GEC | 188.2 | 96,305.6 | 3,738,562.9 | ~19,868x |
| `unit_epochs.mass_acquired`, GEC | 23,951.2 | 359,656.2 | 31,828,697.4 | ~1,329x |
| hand-contact dose | 4.07 | 2,365.89 | 23,065.90 | ~5,663x |

Hazard rows classified as `secondary_conversion` match the acquisition counts:
2 pre-quarantine, 14 post-quarantine-but-in-span, and 69 after-span, with summed
effective dose 7,739.1 / 32,442.7 / 199,536.5 GEC respectively. The
`exposed_no_acq` hazard rows carry large summed effective dose during the pan
span but are not route-resolved secondary conversions and mostly do not
establish infection.

Two code facts bound the mechanism. For `provisioned_lot` pans,
`_cs_pan_deposit` sets `per_serving = lot_titre_gec_per_g * serving_mass_g` and
pan mass as `per_serving * pan_servings`; demand is cohort take-share capped by
object `servings_remaining`/extent, so taker count does not dilute the per-serving
titre. Separately, `_resolve_pathogen_challenge` runs after all pathway doses
are accumulated for the epoch, so a host infected by a pan cannot become a
source later in the same epoch.

## Inferred

The hypothesis that the missing VSP tail is same-meal conversion of diluted pan
mass is not supported on these posted cells. Before first quarantine there are
only two secondary acquisitions, both caregiver, and the acquired-source surface,
fomite-pickup and contact proxies are negligible. The large acquired-source
exposure mass appears only after the provisioned-lot span, when newly infected
hosts are shedding/depositing and quarantine is already active. The pan span is
also bounded: seeds 8046 and 8077 have spans ending before first quarantine, so
there is no in-span post-quarantine window at all.

## Hypothesis / next

The rare-but-larger posted tail is more likely controlled by post-burst
secondary timing and amplification than by same-meal secondary chaining or pan
mass/dilution: earlier presymptomatic shedding or deposition amplitude, faster
quarantine onset/compliance, or food-service secondary routes after the initial
lot burst. Do not pursue per-contact geometry during the pan itself as the
missing tail without a new measurement that acquired-source mass is large
before first quarantine.
