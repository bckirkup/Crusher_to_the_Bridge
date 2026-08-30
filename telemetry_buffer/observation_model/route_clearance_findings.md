# Route-specific pre-establishment clearance: what it does, and what it does not

Tested against the Edison v2 parameter file
(`pre_establishment_clearance_params_v2.json`, `norovirus_gii4`), using the
retained-pool hazard form the acceptance tests assume (PEC-03/PEC-04), with a
separate decaying pool per route.

Harness: `route_clearance_efficiency.py`. N = 40,000 hosts, 7-day horizon,
exposure spread over the first 5 days, hourly steps.

## 1. Route-varying lambda is not the no-op that a single lambda is

A single pathogen-wide clearance rate cannot change infection risk: the
accumulated hazard stays linear in total delivered dose regardless of lambda or
of how the dose is fractionated (`clearance_additivity_findings.md`).

Route-*varying* lambda is a different object. With a per-route pool decaying at
`lambda_j`, a delivery `D_j` accrues total hazard `r_rate * D_j / lambda_j`, so
per-virion infectivity is proportional to `1 / lambda_j`. Clearance therefore
*derives* the route efficiency multiplier instead of assuming it, and the mean
residence time `1 / lambda_j` is what converts a rate into a survival fraction.
No separate portal residence time is needed; the earlier objection that these
rates could not be consumed without a `tau` is answered by the formulation
itself.

## 2. Calibration: the oral route is the reference, and it is not optional

`alpha = 0.111`, `beta = 32.81` were fitted to *administered oral* Norwalk
inoculum, so every loss between mouth and gut epithelium is already inside `r`.
The oral route is therefore the reference and `r_rate = r * lambda_food`. Any
other choice silently multiplies all infectivity by a constant.

Relative per-virion infectivity for norovirus under the v2 rates:

| route | lambda (per h) | efficiency vs oral | grade |
|---|---:|---:|---|
| food | 0.05 | 1.000 | C |
| direct_contact | 0.10 | 0.500 | C |
| fomite | 0.10 | 0.500 | C |
| droplet | 0.70 | 0.071 | C |
| hvac_airborne | 0.70 | 0.071 | C |

Simulation reproduces the closed form `1 - (1 + D_eff / beta)^-alpha` to within
0.7% across every mix and every fractionation tested (the small positive bias is
the within-step convention of delivering dose at the start of the step).

## 3. It changes the fitted dose by an order of magnitude

At a fixed delivered dose of 1000 particles, infection attack rate:

| mix | AR |
|---|---:|
| pure food (reference) | 0.319 |
| emission weights (contact .35 / fomite .30 / food .20 / droplet .10 / HVAC .05) | 0.273 |
| droplet-dominated, as measured at establishment (94% droplet) | 0.147 |
| pure droplet | 0.123 |

Our establishing dose is droplet-dominated, so adopting these rates cuts
effective dose ~6.6x and any previously fitted dose has to rise by about the
same factor. Every fitted dose we have quoted is referenced to efficiency 1.0 on
all routes and does not transfer.

## 4. It does not resolve A2

Dose is our one fitted parameter, so the only fair comparison holds infection
attack rate fixed and asks what happens to ill/infected. Rescaling each mix to
land at AR = 0.318:

| mix | dose needed | ill/infected (n=1) | (n=24) | (n=168) |
|---|---:|---:|---:|---:|
| pure food | 1,000 | 0.424 | 0.315 | 0.314 |
| emission weights | 1,867 | 0.448 | 0.322 | 0.319 |
| droplet-dominated | 9,790 | 0.505 | 0.336 | 0.317 |

At matched attack rate and realistic fractionation, ill/infected moves from
0.315 to 0.336 against a target of 0.59-0.81. That is a 7% relative gain on a
~1.8x miss.

The reason is the same algebra as before: within a route the hazard is still
linear in delivered dose, so re-weighting routes rescales the fitted dose and
almost nothing else. Route-specific clearance is a real correction to *which
virions count* and to *what dose means*; it is not a mechanism that separates
A1 from A2.

## 5. The largest single effect rests on the weakest number, and it is
   portal-mismatched

The 14x droplet discount does more to this model than everything else in the
parameter file combined, and `lambda_droplet = 0.7/h` is grade C, annotated
"respiratory clearance proxy; not primary route". Norovirus does not replicate
in the respiratory tract: aerosolised virus (vomitus plume) deposits in the
oropharynx and is *swallowed*, establishing in the gut. The physically correct
clearance for that route is the oral one, not mucociliary escalator.

If droplet is re-assigned to the oral portal (`lambda ~ 0.05-0.1/h`), the
efficiency spread collapses to at most 2x and the whole change becomes nearly a
no-op for us. So the question to settle before implementing is not the value of
`lambda_droplet` but which portal norovirus droplet exposure terminates at. Two
grade-C numbers differing 14-fold, selected by an unstated portal assumption, is
a fit knob unless that assumption is made explicit and defended.

## 6. `gastric_survival_fraction` and the double-count risk

For norovirus the v2 value is 1.0 (acid-stable), so it is inert for us. The
mechanism separation is nevertheless right, and the double-count it invites
should be recorded now: dose-response constants fitted to *ingested challenge*
doses -- norovirus (Teunis), and equally Campylobacter (Black 1988) and Vibrio
(Cash 1974) -- already contain gastric survival. Applying a
`gastric_survival_fraction` of 0.01-0.1 on top of such a fit would discount the
same loss twice. The fraction is only valid against a dose-response referenced
to the dose *arriving at the epithelium*, or as a *relative* modifier for hosts
whose gastric pH differs from the challenge-study population (the antacid/PPI
case, which is the genuinely new capability it buys).
