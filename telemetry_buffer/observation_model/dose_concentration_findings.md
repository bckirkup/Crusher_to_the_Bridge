# The shipped exposure stream is already maximally patchy, and that is why the variance arms were null

Status: **measurement of the shipped model** (VARIANCE-INV-01), taken at
`dose_concentration_readout.py` on the current tree. No constant is adopted,
narrowed or proposed here, and nothing below is a calibration target. Every
number is a property of one instrumented voyage
(`expedition_cruise_450`, 168 epochs, seed 500), read at the establishment draw
itself — `TransmissionCore._dose_response_hazard` — not from a route
accounting layer.

## 1. Why this was measured

Four independent findings had the same shape: the release scalar is a switch and
not a gradient (#497), the environmental release is a rare-event distribution
collapsed to one number (#498), the hand load is intermittent rather than
routine (#502, 18/71 rinses), and every mean-field contact and topology arm
returned a null while the same arms read +15 pp inside a transmitting stratum
(#499). The natural conclusion — *the missing mechanism is variance itself* —
is testable before any distribution is built, because a mean-preserving
dispersion can only change establishments where the dose-response is curved.
So the question asked here is not "is the model patchy enough" but "is the
model in a regime where patchiness can do anything at all".

Two quantities answer it:

- **Curvature utilisation**, `sum(1 - exp(-sD)) / sum(sD)` over the realised
  stream. At 1.0 every draw is in the linear limit, where establishment is
  exactly proportional to dose and *any* mean-preserving redistribution is
  provably inert. Far below 1.0 the stream is saturating, i.e. dose is being
  spent on hosts already certain to be infected.
- **Concentration** (Gini, Lorenz top-shares) of effective dose per
  host-epoch, per route, and per `(epoch, zone)` cell, plus how many hosts
  share a heavy cell.

## 2. The dose-scale sweep: there is no regime where dispersion is informative

`environmental_faecal_release_log10_g_per_epoch` swept over the campaign
interval's live span, norovirus channel:

| `adj` | curvature utilisation | share of draws with `sD` in [0.01, 10] | share `sD ≥ 1` | hazard from `sD ≥ 1` |
|---:|---:|---:|---:|---:|
| 4 | 0.0130 | 0.0186 | 0.0018 | 0.49 |
| 6 | 0.2883 | 0.0024 | 0.0002 | 0.49 |
| 7 | 0.6132 | 0.0009 | 0.0001 | 0.60 |
| 8 | 0.9935 | 0.0003 | 0.0000 | 0.00 |
| 10 | 0.9994 | 0.0000 | 0.0000 | 0.00 |
| 12 | 0.9994 | 0.0000 | 0.0000 | 0.00 |

The sweep passes straight from a saturating regime to the linear limit with
nothing in between: at `adj = 4` the curved part of the dose-response absorbs
98.7% of the delivered dose without producing an infection, and by `adj = 8` the
whole stream is linear to four decimal places. In **no** cell of the sweep does
more than 1.9% of the exposure stream sit in the band where a dose-response is
informative at all; at the switch itself (`adj ≈ 7`, #497) it is 0.09%.

This is a sufficient explanation for the nulls. A mean-preserving dispersion —
the zone sigma, a hand point process, a tail index on per-event release, a
lognormal on transfer — cannot move establishments in the linear limit by
construction, and in the saturating regime it moves them *down* by concentrating
dose that is already wasted. Both regimes are inert for the same reason from
opposite sides, and the model has no third regime.

## 3. Where the patchiness already is

Gini of effective dose per host-epoch, `adj = 4`:

| stream | n host-epochs | total dose | Gini | top 1% share |
|---|---:|---:|---:|---:|
| all | 35,929 | 9.43e6 | 0.997 | 0.988 |
| direct contact | 2,992 | 9.40e6 | 0.969 | 0.565 |
| fomite | 14,884 | 2.28e4 | 0.989 | 0.858 |
| droplet | 32,690 | 9.43e3 | 0.905 | 0.260 |
| food | 4,432 | 2.79 | 0.868 | 0.263 |
| HVAC airborne | 1,739 | 0.90 | 0.984 | 0.881 |

Nothing here is mean-field. Every route's delivered dose has a Gini between
0.87 and 0.999, and the top 1% of host-epochs carry 98.8% of all effective
dose. Whatever the model's defect is, **it is not an absence of dispersion in
delivered dose.**

## 4. What the realised allocation costs

Same run, comparing the stream as delivered against the same total `sD` spread
flat over the same host-epochs:

| route | n | sum `sD` | establishments as delivered | flat | ratio | utilisation |
|---|---:|---:|---:|---:|---:|---:|
| direct contact | 2,992 | 8,914 | 95.0 | 2,839.9 | 0.034 | 0.011 |
| fomite | 14,884 | 14.2 | 10.8 | 14.2 | 0.762 | 0.762 |
| droplet | 32,690 | 11.0 | 10.4 | 11.0 | 0.944 | 0.943 |
| food | 4,432 | 0.0146 | 0.015 | 0.015 | 1.000 | 1.000 |
| HVAC airborne | 1,739 | 0.00034 | 0.000 | 0.000 | 1.000 | 1.000 |

Three of five routes are in the linear limit to three decimal places: for food
and HVAC the allocation of dose is arithmetically irrelevant, and droplet is
within 6% of irrelevant. One route has curvature, and it is spending 97% of its
own potential: direct contact delivers 95 establishments where the same mass
spread evenly would deliver 2,840.

## 5. The one curved channel is saturated and solitary

Per-route `sD` distribution, `adj = 4`:

| route | median `sD` | p90 | max | share ≥ 0.01 | share ≥ 1 |
|---|---:|---:|---:|---:|---:|
| direct contact | 9.9e-6 | 0.023 | 6,809 | 0.156 | 0.020 |
| fomite | 1.3e-10 | 2.7e-6 | 1.57 | 0.0066 | 0.0003 |
| droplet | 3.6e-8 | 4.0e-5 | 0.335 | 0.0041 | 0.0000 |
| food | 2.9e-11 | 1.4e-7 | 0.0020 | 0.0000 | 0.0000 |

Sixty of 35,929 draws are at `sD ≥ 1`, and they fall in 59 distinct
`(epoch, zone)` cells — at most two in any one cell. So the model's transmission
is a sequence of **isolated near-certainties**: a susceptible who meets a
shedding partner under `per_partner_contact` receives a dose three orders of
magnitude past the certainty threshold, and no second host shares it. The
`(epoch, zone)` cells that carry the dose *are* crowded (top 1% of cells average
18.1 exposed hosts against 12.9 overall, 9.4% single-host cells), but the
saturating draws inside them are not shared, because the mass goes to the
partner and not to the cell.

Under that structure the epidemic is **contact-count-limited, not
dose-limited** — the infection count is the number of susceptible–shedder
contacts, and the dose magnitude is irrelevant over three logs on either side.
That is consistent with the whole record: contact-count arms moved the readout
(+15 pp inside a transmitting stratum, #499), while every dose-side, topology
and dispersion arm was a null.

## 6. What this rules out, and what it does not

Ruled out as an explanation for the anchor misses, on this evidence:

- **More marginal variance anywhere.** In the linear limit it is inert; in the
  saturating one it reduces establishments. This applies to the zone sigma, the
  proposed hand point process (HAND-EVENT-01 §3), a per-event release tail, and
  the existing transfer lognormals alike — none of them can be the missing
  mechanism *while the stream stays in these two regimes*. HAND-EVENT-01 is not
  withdrawn; it is a fidelity repair to a measured process (Liu's occupancy),
  and it must be expected to leave the anchors where they are.
- **"The model is mean-field."** It is not, on any route.

Not ruled out, and now the better-posed questions:

- **The per-contact dose of `direct_contact`.** A single contact with a shedder
  delivering `sD` up to 6.8e3 is the reason the channel is saturated and the
  reason 97% of its mass is wasted. That is a *level* question about the
  contact transfer term, which is sourced separately from the environmental
  release scalar and was never swept beside it.
- **Coincidence rather than magnitude.** The quantity a variance mechanism
  would have to change is the *number of hosts* a patch reaches at `sD ≈ 1`,
  not the spread of the magnitudes. The engine's pools cannot express that: the
  surface, food and air pools are one scalar per zone per pathogen, so a
  concentrated event is smeared over the zone footprint on arrival (#498), and
  the only within-zone structure is a per-host-epoch multiplier that is
  redrawn independently and therefore correlates nothing.
- **The anchors A5 and A9 are untouched by all of this**, as the stratification
  already showed; nothing here is evidence about either, and no value in this
  document may be read into a parameter.

## 7. The variance inventory: what is drawn, at what level, and from what

Every stochastic term the faecal/hand/contact chain passes through, read off the
shipped code. "Level" is what the draw is a property of, and it is the column
that decides whether a term can create a *shared* patch: only a draw held at the
host, the event or the pool can correlate two exposures; one redrawn per
host-epoch is independent noise by construction.

| term | site | level | dispersion sourced? | mean-preserving? |
|---|---|---|---|---|
| host shedding multiplier `10^N(0, σ)` | `draw_shedding_multiplier` | **persistent per host** | `shedding_variance_log10` is a declaration (1.0 / 1.2), not a measured σ | no (lognormal raises the mean) |
| shedding curve over illness | `natural_history` | persistent per host-illness | yes (Atmar/Teunis) | — |
| emesis episode load | `_emesis_episode_load` | per event, log-uniform **collapsed to its mean** | range Grade C, ledger-void | the draw is not taken |
| environmental release scalar | `environmental_faecal_release_log10_g_per_epoch` | **no draw at all** — one scalar | void (#497, #498) | — |
| hand load ceiling | `HAND_LOAD_LOG10_GEC` | **no draw** — a deterministic decay-and-reset | conditional positive mean misused as a ceiling (#502, ledger 25) | — |
| defecation events | `stool_events_per_day` | per epoch, Bernoulli | rate sourced (tranche 32); amplitude has no dispersion | — |
| surface→hand transfer | `SURFACE_TO_HAND_LOGNORMAL` | **per pickup** (host-epoch) | yes, lognormal fitted to transfer studies | no |
| hand→surface transfer | `HAND_TO_SURFACE_LOGNORMAL` | per deposition | yes | no |
| hand→mouth fraction | `HAND_TO_MOUTH_NORMAL` | per contact | yes, truncated to [0,1] | approx. |
| mouth contacts/hour | `EATING_/NON_EATING_MOUTH_CONTACTS_PER_HOUR` | per host-epoch, normal | yes | yes |
| hand area, surface contact fraction | `HAND_AREA_CM2_RANGE`, `SURFACE_CONTACT_FRACTION_RANGE` | per pickup, uniform | yes | yes |
| hand hygiene efficacy | `HAND_HYGIENE_EFFICACY_LOG10` | per wash, clipped normal | yes | yes |
| within-zone exposure factor | `_zone_exposure_factor` | **per host-epoch**, mean-1 lognormal | σ by zone type is a declaration | yes, by construction |
| contact count | `_activity_contact_draw` / Poisson | per host-epoch | rates per activity declared per run | yes |
| partner identity | `_pathway_direct_contact` | per contact | structural | — |
| dose-response susceptibility | `_dose_response_susceptibility` | **persistent per host/pathogen** | yes (Teunis beta) | — |
| surface / food / air pool | `surface_pools*`, `food_pools` | **one scalar per zone per pathogen** — no within-zone state | — | — |

Three things fall out of the table, and they are the whole finding restated
structurally:

1. **The two terms with no draw at all are the two the ledger calls void** —
   the environmental release scalar and the hand load. Every term that *is*
   drawn is drawn from something sourced. The model's missing variance is not
   spread thinly across the chain; it is concentrated in exactly the places
   where the level is a fitted constant.
2. **Almost everything that is drawn is drawn at the host-epoch.** Only three
   terms are persistent or shared: the host shedding multiplier, the host
   susceptibility, and the shedding curve. The within-zone multiplier — the one
   term whose name suggests spatial structure — is redrawn independently per
   host-epoch and so cannot make one hotspot reach two hosts.
3. **The pools have no internal geometry.** A concentrated arrival is divided by
   the zone footprint on deposition, so no draw anywhere downstream can
   recover it. This is the concentrated-event-into-well-mixed-pool archetype
   again, and it is why §6's coincidence question cannot currently be asked of
   the engine at all.

## 8. Reproducing

```bash
python3 telemetry_buffer/observation_model/dose_concentration_readout.py \
  168 450 expedition_cruise_450 500 [adj]
# or re-report a saved stream without re-simulating:
python3 telemetry_buffer/observation_model/dose_concentration_readout.py \
  <exposures json>
```

The harness monkey-patches two `TransmissionCore` methods in-process to record
the establishment draw; it changes no profile on disk, and the optional `adj`
argument is a run-spec override for the diagnostic only.
