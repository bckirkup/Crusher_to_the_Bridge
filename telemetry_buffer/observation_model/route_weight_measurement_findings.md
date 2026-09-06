# What `transmission_route_weights` actually does, measured on the realised dose stream

Status: measurement. Nothing here is adopted and no constant is changed by it.
No quantity below was chosen against an anchor; all of them are read out of
instrumented runs at `e8b2b95`.

Harness: `route_weight_attenuation.py` (instrumented run, one JSON record per
nonzero exposure event) and `route_weight_attribution.py` (attribution and
elasticity over those records), output in
`route_weight_attenuation_out.txt`. Runs: `active_profiles` bundle, 240 epochs,
`expedition_cruise_450` at seeds 500/501/502 and `classic_cruise_1900` at seed
500.

This measurement replaces the route-share entry withdrawn in
`docs/norovirus/norovirus_open_ledger.md` §1 ("Route shares. Last measured
before #351/#352/#353 ... The often-quoted 'droplet carries 94-96% of
establishing dose' ... is stale"). It also retires the premise of
`route_clearance_findings.md` §3.

## 0. What had to be fixed before any number was trustworthy

`active_profiles.json` gives **both** `norwalk_gi` and `sars_cov2_resp`
`initial_infected: 1`, and `_apply_route_weights` fires once per pathogen with
that pathogen's own weight set. An accumulator that is not keyed by pathogen
therefore blends the two dose streams: the first pass of this measurement
reported a droplet post/pre ratio of 0.120 on the 1900 hull against a profile
weight of 0.10, which is the norovirus 0.10 and the COVID 0.30 mixed in the
proportion the two arms happened to deliver. Keyed per pathogen, every observed
post/pre ratio equals the profile weight exactly, which is what validates the
instrumentation.

Any future diagnostic that aggregates pathway dose across a multi-pathogen
bundle inherits this defect.

## 1. Mass share and establishment share are different objects, and they
   disagree by a factor of about 3.5

The route weights are applied to dose *mass*. What the model scores is
*establishment*, drawn per host as `r ~ Beta(alpha, beta)` with
`P = 1 - exp(-r D)`, whose expectation is
`E_r[1 - exp(-rD)] = 1 - 1F1(alpha; alpha+beta; -D)` exactly. Because that
function is concave, a route delivering a large dose to few hosts buys far less
establishment per particle than a route delivering small doses to many.

`norwalk_gi`, post-weight, credited across pathways in proportion to the dose
each delivered into the same exposure event:

| run | direct contact | fomite | droplet | food | HVAC |
|---|---:|---:|---:|---:|---:|
| 450 s500 mass | 0.9728 | 0.0242 | 0.0029 | 0.0000 | 0.0000 |
| 450 s500 **establishment** | 0.4182 | 0.4250 | 0.1530 | 0.0030 | 0.0008 |
| 450 s502 mass | 0.9674 | 0.0311 | 0.0015 | 0.0000 | 0.0000 |
| 450 s502 **establishment** | 0.4406 | 0.4790 | 0.0786 | 0.0014 | 0.0004 |
| 1900 s500 mass | 0.9814 | 0.0147 | 0.0038 | 0.0001 | 0.0000 |
| 1900 s500 **establishment** | 0.4581 | 0.3054 | 0.2307 | 0.0053 | 0.0006 |

Direct contact carries 97-98% of the delivered mass and about 44% of the
establishment. Fomite carries 1.5-3% of the mass and 31-48% of the
establishment. Quoting either number as "the route share" without saying which
object it is will be wrong by a factor of 3.5 on direct contact and by a factor
of 20 on fomite.

## 2. Droplet dominance is gone, and this is a real change rather than a
   change of statistic

`a5_role_asymmetry_diagnosis.md` measured droplet at 94-95% of establishments
with fomite "numerically extinct" (0.13 particles per classic voyage against
7.0e7 for droplet). At `e8b2b95` the fomite pool delivers 7.5e4 particles on
the same hull and droplet is a 8-23% minority of establishment.

The comparison is not confounded by the two documents using different
statistics. The dominant-route-of-the-largest-exposures statistic, which is
closest to what the old single-shedder probe reported, agrees:

| run | direct contact | fomite | droplet | food |
|---|---:|---:|---:|---:|
| 450 s500 | 226 | 66 | 0 | 0 |
| 450 s501 | 25 | 132 | 0 | 0 |
| 450 s502 | 235 | 59 | 0 | 0 |
| 1900 s500 | 493 | 511 | 35 | 6 |

(dominant pathway among the top 1% of exposure events)

Droplet is the dominant pathway in 35 of 1,045 such events on the classic hull
and in none at all on the expedition hull. The inversion is consistent with
#351 (fomite chain re-derived), #352 (emesis) and #353 (contact kernel and
touch rates raised), which is where the ledger already attributes the
withdrawal.

`a5_role_asymmetry_diagnosis.md` §"Where the parity comes from" and
`dose_accumulation_defect.md`'s "the droplet pathway, which carries 94-95% of
establishments" are therefore both stale as descriptions of current behaviour.
The A5 *conclusion* — that the routes carrying role structure deliver too
little — needs re-testing rather than assuming, because the routes now
delivering establishment are direct contact and fomite, which are exactly the
role-structured ones.

## 3. The weights are not a scalar on the dose axis: they re-rank the routes

Realised mass attenuation `sum(w_r D_r) / sum(D_r)` is 0.31-0.35 across all
four runs — which is just `w_direct_contact = 0.35`, because direct contact
carries almost all the mass. Realised *establishment* attenuation is different,
and so is the ordering it produces:

| run | S, unit weights | S, shipped weights | ratio |
|---|---:|---:|---:|
| 450 s500 | 845.32 | 425.05 | 0.503 |
| 450 s501 | 17.39 | 8.96 | 0.515 |
| 450 s502 | 745.46 | 373.04 | 0.500 |
| 1900 s500 | 683.17 | 251.07 | 0.368 |

Under unit weights on the 1900 hull, droplet holds 55% of establishment and
direct contact 22%; under the shipped weights that becomes 23% and 46%. The
weights therefore do two things at once — they halve total establishment and
they invert the top route — and neither is visible in the mass shares. The
"one multiplicative attenuation" reading I would have taken from the mass table
is wrong.

`S` sums `P(establish | D_i)` over every exposure event, including exposures of
agents already infected or recovered, so its level is an upper bound on
establishments and only its ratios are meaningful. (Very small doses produce
`hyp1f1` round-off at the 1e-16 level, occasionally negative; irrelevant at
these magnitudes.)

## 4. The clearance layer is not the order-of-magnitude change §3 claimed —
   because it is the same object as the route weights, applied twice

`route_clearance_findings.md` §3 concluded "our establishing dose is
droplet-dominated, so adopting these rates cuts effective dose ~6.6x". That
premise no longer holds, and on the current establishment mix the effect
reverses sign relative to the shipped weights, because the v2 rates are *more*
generous than the profile weights on the routes that now dominate (direct
contact 0.500 against 0.35, fomite 0.500 against 0.30, food 1.000 against 0.20)
and more punitive only on droplet and HVAC:

| multiplier set applied to the same unit-weight stream | 450 s500 | 450 s501 | 450 s502 | 1900 s500 |
|---|---:|---:|---:|---:|
| unit (no route weights) | 1.000 | 1.000 | 1.000 | 1.000 |
| shipped route weights | 0.503 | 0.515 | 0.500 | 0.368 |
| clearance-derived, v2 rates | 0.574 | 0.685 | 0.588 | 0.409 |
| clearance, droplet re-assigned to the oral portal | 0.743 | 0.688 | 0.719 | 0.675 |

Relative to the shipped weights the clearance layer is a factor of 1.11-1.33
(1.33-1.84 with droplet re-assigned), not 6.6. And relative to unit weights it
lands in the same band the shipped weights already occupy, which is the
substantive finding: **`transmission_route_weights` and route-specific
pre-establishment clearance are two parameterisations of one quantity —
per-virion route efficiency.** Adopting clearance while the weights remain in
place applies route discrimination twice, with the two sets disagreeing on
direction for direct contact, fomite and food.

That makes the clearance-adoption question a special case of task #25 rather
than an independent decision, and it strengthens the third condition in
`docs/literature/edison_v3_spec_review.md`: the layer cannot be screened as
intervals against a profile that is already discriminating by route.

The portal question in `route_clearance_findings.md` §5 survives intact and is
now the larger of the two effects: re-assigning droplet to the oral portal
moves the clearance multiplier by 1.22-1.65x on the three runs where the
outbreak took off (and by 1.00x on the one that did not, where droplet
delivered nothing to re-assign).

## 5. Dose elasticity is strongly compressive, which is why the Morris screen
   found what it found

`S(s) = sum_i P(establish | s * D_i)` over the shipped-weight stream, `s`
multiplying every exposure:

| s | 450 s500 | 1900 s500 |
|---:|---:|---:|
| 0.060 | 0.242 | 0.223 |
| 0.125 | 0.359 | 0.328 |
| 0.250 | 0.514 | 0.473 |
| 0.500 | 0.723 | 0.686 |
| 1.000 | 1.000 | 1.000 |
| 2.000 | 1.356 | 1.462 |
| 4.000 | 1.804 | 2.126 |
| 8.000 | 2.354 | 3.055 |

An 8.3x range in delivered dose (0.06-0.5; measured here through the retired
`contact_transfer_fraction`, which multiplied the direct-contact pathway dose
from the same position as `route_efficiency_multipliers["direct_contact"]` and
is now refused at load - the same 8.3x is reachable through the surviving
owner, so the dose-to-establishment result below stands and only its label
changes, #22) buys 2.1-3.0x in
establishment, and establishment is bounded above by the susceptible pool well
before that. This is the mechanical reason the direct-contact dose factor cleared
nothing above the noise floor in the Morris screen
(`docs/norovirus/bounded_screen_results.md`): the factor moves total dose by
almost an order of magnitude and the establishment channel absorbs most of it.

Establishment is concentrated in the tail of the exposure distribution — the
top 1% of exposure events carry 28-32% of `S` on the 450 hull and 68% on the
1900 hull, and everything below the median carries under 0.05% everywhere. A
parameter that raises the whole exposure distribution multiplicatively is
therefore cheap; one that changes the tail is not.

## 6. Secondary: the same instrumentation quantifies the COVID emission defect

`sars_cov2_resp` is seeded in the same runs, so its dose stream is measured
here too. For a respiratory pathogen, direct contact carries 92-96% of
delivered mass while droplet carries 4-8% — and droplet nevertheless carries
24% (450 s502) and 72% (1900 s500) of establishment, against 36% and 82% under
unit weights. Fomite and HVAC deliver an establishment share that rounds to
exactly zero on both hulls.

Total establishment over a whole voyage is 6.6 (450 s502) and 23.7 (1900 s500)
against norovirus's 251-425 on the same runs, and the arm's total delivered
mass varies from 10.9 particles (450 s500) to 6.4e4 (450 s502) across seeds.
That is the `environmental_faecal_release_log10_g_per_epoch` division by 1,000
of `docs/covid/covid_parameter_provenance_audit.md` §"emission scale", measured
rather than argued, and it is one more reason task #30 has to re-source the
emission scale and `beta` together.

## 7. What this does not settle

- Whether the weights *should* be independent multipliers, normalised shares,
  or per-virion efficiencies derived from a clearance rate. This is task #25
  and it is an architectural decision, not a measurement.
- Whether the sanity checker's warning that the weights should sum to 1.0 is
  wrong or the semantics are. On the evidence here the warning is describing a
  different model than the engine implements: the weights are applied as
  independent multipliers and their sum has no interpretation.
- Any literature route share. Nothing in this document is evidence about how
  norovirus is transmitted on real ships; it is a description of what this code
  currently does.
- The absolute level of any attack rate. `S` is not an attack rate.

## 8. Post-`FOOD-ARCH-01` food share, measured under boarding

Measurement, adopted nothing. Harness as above, one run: `active_profiles`,
168 epochs, 450 agents on `mega_cruise_5000`, seed 7, after the hand-mediated
food route landed (contacts × per-contact transfer × hand load, with depletion).

| pathway | pre-weight dose | share | post-weight share |
|---|---|---|---|
| direct_contact | 3.399e+07 | 0.9970 | 0.9979 |
| fomite | 7.30e+04 | 0.0021 | 0.0018 |
| droplet | 2.972e+04 | 0.0009 | 0.0002 |
| hvac_airborne | 529.5 | ~0 | ~0 |
| food | 6.11 | 2e-7 | 1e-7 |

This is the direction nobody predicted. The withdrawn pre-repair figure had the
food route at 93–99.9% of delivered dose; bounded by a hand load whose ceiling
is 10^3.86 GEC and divided per head across a dining zone's occupants, it now
delivers ~1e-7 of it. The route did not move by a chosen magnitude — the shipped
contact rate is the retired constant's own composition read backwards — so the
collapse is the removal of the whole-emission coupling, not a new value: the old
form scaled the deposit with each shedder's entire per-epoch emission and with
`environmental_faecal_release_log10_g_per_epoch`, the box's one Grade D axis,
while a hand load saturates.

Against the one external, non-circular check
(Mouchtouri et al. 2024: food the sole mode in 7.3% of cruise outbreaks, food
involved in 32% counting mixed modes) the model now sits far **below** the
check, having sat far above it. That is recorded as a discrepancy, not a target:
no food parameter may be selected to close it. The two candidate structural
causes are the per-head division of a well-mixed pool (a communal serving is not
well mixed over an entire dining zone) and the null contact rate, and both are
open in `docs/parameter_provenance_register.md`.
