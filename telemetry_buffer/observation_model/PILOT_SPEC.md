# Post-confinement-fix ladder pilot (spec)

Purpose: relocate the dose ladder and test whether containment bites, on the
corrected model (PR #340: emission-side confinement + norovirus sigma 1.0),
under the take-off-conditioned endpoint we will fit against VSP.

Run on the `devin/1788019043-confinement-emission` code, not on main.

## Cells

| factor | values |
|---|---|
| hull | `expedition_cruise_450`, `classic_cruise_1900` |
| response branch | `none_response`, `syndromic_comp85` |
| `dose_adjustment` | 2.0, 2.5, 3.0 |
| seeds | 940-949 (10, held out from 950-959 and 960-969) |
| `initial_infected` | 1 on **both** hulls (primary arm; no per-capita seeding here) |
| epochs | 168 hourly |

120 runs. No pathogen-profile edits: sigma comes from the branch's
`active_profiles.json` (1.0). No changes to `engines/`, shipped profiles,
production manifests, or campaign code. Artifacts under
`telemetry_buffer/v4_results/postfix_pilot/`.

## Endpoint

VSP records exist only for voyages that produced a reportable outbreak, so the
comparable statistic is conditioned on take-off, defined as peak prevalence
>= 10 infected. Report both, and never pool `initial_infected` arms.

Per (hull, branch, dose) cell:

1. take-off count out of 10;
2. reported passenger case rate: median and quartiles **conditional on
   take-off**;
3. same, marginal over all 10 seeds (for reference only);
4. ever-ill passenger rate, median conditional on take-off;
5. infection attack rate, median conditional on take-off;
6. reported / ever-ill ratio, per cell (surveillance capture check);
7. quarantine person-epochs, median (0 expected on `none_response`);
8. peak prevalence, median.

## What the pilot has to answer

- **Ladder**: at which dose does the take-off-conditioned reported median cross
  the VSP class median (expedition 8.56%, classic 5.59%), and does one dose
  bracket both hulls within the grid?
- **Containment**: on `syndromic_comp85` versus `none_response` at matched
  (hull, dose, seed), does ever-ill fall now, and by how much on classic
  relative to expedition? Pre-fix, classic/spirit/mega spent 38k-150k
  quarantine person-epochs for no reduction.
- **Surveillance capture**: the sigma pilot's reported/ever-ill ratio was ~0.18
  on both hulls with surveillance off. If it is still ~0.18 with
  `syndromic_comp85` on, reporting is capturing far less than
  `sick_call_probability_per_day` = 0.70 implies over a 2-3 day illness, and
  that is a defect to chase before any fit.
