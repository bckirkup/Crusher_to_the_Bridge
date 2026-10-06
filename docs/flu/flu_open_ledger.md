# Influenza-A fit: open ledger

> **Status:** Living. Head commit of record: `ee39d64d`. If that is not the
> current head, treat every number here as unverified.

What is currently withdrawn on the `influenza_a` arm, what the last
measurement of record is, and what is outstanding. The permanent defect and
measurement record is `docs/ledger/` (entries tagged `influenza_a` or `all`);
the scored observables live in `data/observation/flu_fit_targets.json`;
readouts live in `docs/flu/`.

Read this before quoting any SAR, presentation, or route-share figure for
the flu arm.

---

## 1. Currently withdrawn

**CABIN-OCC-01 + ROOM-AIR-01 (ledger entries tagged `all`): every
airborne-route dose figure on any hull that declares AHU rates, and every
confined-cabinmate figure, moves at `1b9d37ca`.** Room-pool inhalation routes
now dose the epoch-mean of a pool exchanging at the zone's declared
`ach × hvac_duty` (plus the stateroom bathroom-exhaust adder), and cabin-mate
plume/addback/confined-contact channels gate on time-partitioned
co-presence. Confined-SAR figures measured before that SHA — including the
FLU-RHYTHM-01 census at `07d9856c` and the FLU-PRESENT-RESCORE-01 paired
readout at `232292f2` — are historical on airborne and confined channels.

**HOST-AGE-02 + HOST-AGE-03 (declared 2026-10-05): presentation and severity
draws on `influenza_a` are age-graded as of these merges.** The arm now
carries `symptomatic_fraction_by_age_band` (Hoy 2022's ladder) and
`severity_model.base_probabilities_by_age_band` (CDC 2023-24 per-age severe
shares), shipped default-ON. Any flu figure conditioned on the presentation
or severity draws and measured on the flat draws is historical on an
age-structured hull; `presentation_age_mode: "flat"` and
`severity_age_mode: "flat"` are the labelled baselines for attribution, and
`FLU-PRESENT-RESCORE-01`'s "flag inert on this surface" finding still stands
on the mechanism it measured.

**CAREGIVER-SVC-01 (landed 2026-10-06): the R3 service channel now carries a
door-drop contact discount, `transmission.caregiver.service.contact_factor`
U[0.05,0.3] default-ON — every caregiver dose figure below is historical on
the un-discounted channel** (`contact_factor: 1.0` is the labelled baseline).
This is the fix for the serviced-quarantine crew bridge the FLU-VIS-01
attribution measured (§4 of that readout): on the paired 8-seed probe
(`ca775a0b`) the factor collapses the bridge sub-channel (median onboard
36→~7 on exp `r200_dec`), and a second confinement-mediated channel — a
passenger/droplet wave persisting at f=0 on a subset of seeds, candidate
confined-cabinmate pooling — is open as a separate attribution. Ledger:
`docs/ledger/CAREGIVER-SVC-01.md`.

## 2. Measurement status (pointers, not quotes)

| Entry | Status | Measured at | Surface |
|-------|--------|-------------|---------|
| FLU-DOSE-01 | measured | `f280e348` | delivered-dose chain |
| FLU-DELIVERY-01 | measured | `201835b2` | dose delivery stages; `k` sourced interval |
| FLU-RHYTHM-01 | measured | `07d9856c` | conditioned-cell confined SAR vs floor band |
| FLU-PRESENT-RESCORE-01 | measured | `232292f2` | F1 verdict **IN** at n=4 seeds; F5 check 0.18 vs ~0.08 |
| FLU-SOCIAL-01 | measured | `8c03e9d7` | social-layer readout |
| FLU-OPEN-01 | measured | `7f4702ef` | open-voyage census on all four classes; F5 above frame = declared observation vector |
| FLU-VIS-01 | measured | `ca775a0b` | observation-layer sweep (report scale × eligibility) on the open voyage; reporting saturates — big-hull Ward gap is incidence, not visibility |

Numbers are quoted from the entries above at their `Measured at` SHAs, never
from this page.
