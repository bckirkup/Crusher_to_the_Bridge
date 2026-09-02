# Edison's norovirus sourcing bundle and influenza parameter bundle: review

Status: received and reviewed. Nothing adopted, no constant changed.
Received 2026-08-30 as `norovirus_parameter_sourcing_bundle.md` (Edison's,
canonical SHA `a684d1c6`) and `influenza_parameters_bundle.json`.
Companion to `edison_v3_spec_review.md` and `edison_provenance_request.md`
(Q1–Q7 answered in part here), and to
`../../telemetry_buffer/observation_model/route_weight_measurement_findings.md`,
which is what the influenza dose-response bears on.

`a684d1c6` is the #367 merge, 14 commits behind current `main`, so the bundle
predates tranches 2–4 (#371–#373) and the Morris screen (#368). Every shipped
norovirus value in its table nevertheless matches HEAD exactly, so it is not
reviewing a stale tree — the overlap with our tranches is independent
convergence, not copying, and it agrees with tranche 3 on the point that
matters: the shipped dose-response comes from a GI.1 inoculum.

## 1. The real win: two Korkin-era rows are now traced

`dose_response` α=0.111/β=32.81 and `illness_probability` η=0.508/γ=0.095 are
traced to Teunis et al. 2008, Tables III and V, **the 8fIIa inoculum,
secretor-positive volunteers only, "nonaggregation" row**. Both were "inherited
from `Person.java`, origin unknown" in `norovirus_parameter_freedom_audit.md`.
That is the largest single provenance gain since the audit began, and it answers
Edison Q1 and Q2 from the literature rather than from the Java.

It also brings two conditions with it that the profile does not currently carry:

**The dose-response is conditioned on secretor-positive hosts.** This changes
the argument for task #21 from an interval argument to a mechanism argument. A
dose-response fitted on Se+ volunteers only describes the Se+ subpopulation, so
the profile needs *some* separate treatment of Se− hosts — a removed fraction is
the coherent implementation if and only if Se− hosts are absolutely protected.
For GII they are not (Teunis 2020: Se− infection risk 0.015 against Se+ 0.076;
Rouphael's GII.2 challenge infected 4 of 8 Se− at top dose), so the coherent
implementation is a second host class at reduced susceptibility, with the Se+
class taking the Teunis parameters unchanged. The shipped `0.0` is not merely
outside the interval — it silently applies an Se+-conditional curve to the whole
population.

**The fit assumes no aggregation despite evidence the inoculum was
aggregated.** Edison notes Teunis's preferred aggregation-aware fit gives
different parameters, so the honest object is a model-selection interval rather
than `[lo, hi]`. That is the same conclusion tranche 4 reached from Liu 2026,
which found aggregation parameters "function as an effective fitting parameter
rather than a directly measured property". Two independent routes to it.

## 2. Correction: the ID50 arithmetic does not show a unit mismatch

Bundle §1 states an implied ID50 of "~18 RT-qPCR genome copies" and concludes
from the profile's `dose_reference_log10 = 4.23` (16,871) that "model units are
NOT the same as the Teunis dose units". The shipped parameters do not imply 18.

Solved directly on the shipped α=0.111, β=32.81:

| quantity | exact beta-frailty `1 - 1F1(α; α+β; -D)` | classic `1-(1+D/β)^-α` |
|---|---:|---:|
| ID50 | 16,644 copies | 16,871 copies |
| P(infection) at D = 18 | 0.0475 | 0.0474 |

`dose_reference_log10 = 4.23` is 16,871 — the classic-approximation ID50 of the
shipped dose-response to four figures. So the model unit and the Teunis unit
agree, and `dose_reference_log10` is *derived from the dose-response*, not
independent evidence about units; the freedom audit already listed it as "1
derived from its own N50". The unit incoherence in this arm is real but it lives
in §7 (`dose_adjustment` as grams of stool), not here.

Hypothesis for where 18 comes from, not verified: 18 is plausibly Teunis's ID50
in *aggregates* rather than genome copies, in which case 16,644 / 18 ≈ 925
genome copies per infectious aggregate — which would be a usable copies-to-
aggregate bridge and worth a targeted check of Table III. Recorded as an open
question for Edison, not as a finding.

## 3. Correction: §6 sources a real measurement onto the wrong key

Grove et al. 2015 (n=150 transfers, 80 participants, MNV) surface→hand 24% and
hand→surface 0.6% is a Grade A measurement we should have. The bundle proposes
it against `contact_transfer_fraction = 1.0`, "wrong by 4× ... and 170×". Both
halves of that mapping are wrong in a way worth being precise about, because
this is the largest lever in the arm:

- **`contact_transfer_fraction` is not a surface→hand efficiency.** It is the
  person-to-person multiplier on the *direct-contact* pathway
  (`transmission_core.py` `_pathway_direct_contact`, default 1.0) — no surface
  is involved. Its sourced screen interval is 0.06–0.50, i.e. it is already not
  shipped at 1.0 in the bounded box (`bounded_screen.py`), and task #22 tracks
  it against a ~0.25 anchor.
- **Surface→hand already exists and is already sourced.** #351's fomite
  re-derivation replaced the lumped constants with a measured chain:
  `SURFACE_TO_HAND_LOGNORMAL = (-2.1, 1.4)`, median 0.12, mean 0.33, cited to
  Julian et al. 2010, Grade B (`fomite_food_rederivation.md`). Grove's 24% mean
  sits inside that distribution, so it **corroborates the shipped chain and
  narrows it** — it does not correct a 4× error. The lumped
  `FOMITE_TRANSFER_FRACTION`/`FOMITE_PICKUP_PROBABILITY` the criticism seems
  aimed at are retained only as deprecated import stubs and are not on the
  dose path.
- **The 0.6% hand→surface figure sources a key the bundle's own table leaves
  blank.** Deposition back onto surfaces is `surface_deposition_fraction =
  1e-4` (inherited from `ViralParticle.java`, listed as unsourced, Edison Q4).
  Grove's 0.006 is 60× larger. That is the actionable half of §6, and it lands
  on the fomite *source* term rather than on its pickup term.

Why the precision matters rather than being pedantry: the route measurement
landing alongside this review finds direct contact carrying 97–98% of delivered
dose mass and ~44% of establishment, so a mis-assigned 4× on
`contact_transfer_fraction` would be the single biggest unforced parameter move
available in the model. Elasticity is compressive — an 8.3× dose range buys
2.1–3.0× establishment — but that is luck, not licence.

## 4. Surface decay: the bundle's interval invalidates our screen box

The bundle reads the field's convention correctly (a per-day fractional loss:
`_surface_survival` passes it to `SimClock.decay_per_epoch`), so shipped 0.25 is
a 57.8 h half-life, 2–6× slower than MNV-1 on stainless steel, and its
recommended interval is `surface_decay_per_day ∈ [0.49, 0.84]` from Kim et al.
2014's 0.31–0.79 log10/day at 30–50% RH.

The Morris screen swept that factor over **0.10–0.60** (`bounded_screen.py`).
The two intervals overlap only in 0.49–0.60, and the shipped value sits outside
the sourced one. So the screen box for this factor is wrong low, and it has to
be re-cut before the admissible-region search (#37) — that search is a
statement about the sourced box, and a box that excludes most of the sourced
interval cannot support it. Recorded against #35/#36. The screen's finding for
this factor was "no effect above the noise floor", so re-cutting it upward is
not choosing a favourable direction; it is testing a range we never tested.

Second-order and unresolved: Kim is MNV-1 on steel at 25 °C and 30–50 % RH.
Ship cabins and public spaces are neither that RH nor only steel, and the
per-zone-class work in #358 found the schedule was not the binding uncertainty.
The interval should be entered as a surrogate-derived one (Grade B/C), not as a
norovirus measurement.

## 5. Airborne decay and shedding duration: agree, with one distinction

The airborne null result is confirmed independently — there is no norovirus
airborne inactivation measurement, so the shipped 1.1 h is a SARS-CoV-2 borrow
that cannot be repaired by searching harder (tranche 1 reached the same null).
Their Lin & Marr inference that a non-enveloped virus should persist *longer*
than 1.1 h is Grade D and points the shipped value in the conservative
direction, which is worth saying explicitly rather than leaving as a bare null.

On shedding duration the bundle says 2–4 weeks, "NOT 3 days", against
`recovery_day = 3`. The distinction to keep: `recovery_day` is symptomatic
duration from onset and it also terminates infectiousness in this engine
(`infection_dynamics_bridge.py` clears a resident lineage at
`days_elapsed >= recovery_day`), while the 2–4 weeks is RT-PCR positivity.
RNA positivity is not infectiousness, so the bundle's framing overstates the
case. What is true and structural: **the model cannot represent
post-symptomatic shedding at all**, so any transmission from convalescent
passengers is outside its support — which is a scope statement for the ledger,
not a parameter to move.

## 6. Influenza: a directly measured per-route efficiency, which is the object
   task #25 has been arguing about

The influenza bundle contains the measurement that settles the *form* of the
route-weight question, and I did not expect it to come from the flu arm.

Memoli 2015's H1N1 challenge gives α=0.407, β=201 in TCID50 **intranasal**;
Alford 1966 gives an aerosol ID50 of 0.6–3 TCID50 via 1–3 µm particles. Solving
the intranasal curve (exact beta-frailty and the classic approximation agree to
0.1%):

| quantity | value |
|---|---:|
| intranasal ID50, Memoli α=0.407 β=201 | 902 TCID50 |
| aerosol ID50, Alford | 0.6–3 TCID50 |
| **aerosol : intranasal potency per TCID50** | **300–1,500× (2.5–3.2 log10)** |

Three consequences.

**Route efficiency is a real per-portal physical quantity, measurable, and
therefore not a normalised share.** A quantity spanning 2.5–3.2 log10 between
two portals of the same pathogen cannot be a set of numbers summing to one.
This is evidence for the resolution of task #25 — independent per-virion
efficiencies — and against the sanity checker's warning that
`transmission_route_weights` should sum to 1.0. It also confirms the finding in
the route measurement doc that `transmission_route_weights` and Edison's
pre-establishment clearance layer are two parameterisations of one object;
influenza shows what that object is when it is measured instead of assumed.

**Our route multipliers and the v2 clearance rates both point the opposite way
from the one pathogen where the ratio is measured.** The norovirus profile
penalises aerosol against contact (droplet 0.10 against direct contact 0.35) and
the v2 clearance rates penalise it harder (0.071 against 0.500); influenza's
measured ratio favours the aerosol portal by two to three orders. This does
**not** transfer to norovirus — norovirus's portal is enteric and inhaled virus
must be swallowed, which is exactly the open question in
`route_clearance_findings.md` §5 — but it means the direction of the
discrimination is a per-pathogen empirical question, and neither our weights nor
the clearance rates have earned it.

**Correction I owe: influenza is not a single-unit-system arm.** I said earlier
in this session that flu gives emission and dose-response in one unit system,
"rather than bridged". It does not. The bundle's emission is Yan 2018's
3.8×10⁴ **RNA copies** per 30-minute fine-aerosol sample; Memoli and Alford are
in **TCID50**. The bridge is unavoidable, and its material is Yan's culturable
fraction (infectious virus recovered from 39% of fine-aerosol samples) plus a
copies-per-TCID50 ratio — not a free conversion factor. The flu arm has the same
units problem as COVID; what it has that COVID lacks is a measured emission
*rate* and a route-resolved denominator.

## 7. Influenza: one verified defect and two interval notes

**`surface_decay_per_day: 4.8` is in the wrong units and fails silently.** The
note reads "equivalent to loss of ~4.8 log10/day", but the field is a per-day
*fractional* loss, and `SimClock.decay_per_epoch` clamps with
`decay = min(1.0, decay)`. A value of 4.8 therefore becomes 1.0 — total loss
every epoch — and the influenza fomite pool is annihilated as fast as it is
deposited, with no error raised. Their own norovirus bundle uses the fractional
convention correctly, so the two bundles disagree about the same field.

Underneath the unit slip is a real engine limitation the flu arm exposes:
Greatorex 2011's ~1.5 h half-life is 0.98 as a per-day fractional loss, so any
sub-daily surface half-life saturates this parameterisation. Influenza cannot be
given a defensible surface decay until the field is a rate rather than a daily
fraction. Recorded as an open engine question, not repaired here.

**`airborne_half_life_hours: 1.0` with range 0.05–1.8.** The range's lower end
is the 3–5 minute half-life at 40–70% RH — which is the RH band of a ventilated
ship interior — so the point estimate sits at the persistent end of its own
range, while Kormuth 2018's mucus protection is the reason not to take 3 minutes
either. This has to enter as an interval; as a point value it is a choice.

**`asymptomatic_fraction: 0.33` (Carrat 2008, 0.26–0.42)** is usable and its
"independent of dose" note is worth keeping, but it is pooled from challenge
studies in healthy adults, so it is a Grade B estimate for a cruise population
with a different age structure. The bundle does not address
`base_susceptibility = 0.65`, which is the flu arm's largest freedom: prior
immunity has to come from season- and route-specific seroprevalence or
vaccination coverage, or it becomes the arm's fitted knob.

## 8. What is adopted

Nothing. Actions this review generates, all as tasks rather than edits:

1. Re-cut the `surface_decay_per_day` screen interval to the sourced range
   before #37, and grade it as surrogate-derived (#35/#36).
2. Task #21 gains a mechanism argument: the Teunis fit is Se+-conditional, so
   the fix is a reduced-susceptibility class, not a removed fraction.
3. Source `surface_deposition_fraction` from Grove's hand→surface 0.6% rather
   than leaving Edison Q4 open — 60× above the inherited 1e-4.
4. Narrow, do not replace, the surface→hand chain with Grove alongside Julian.
5. Ask Edison whether §1's ID50 of 18 is in aggregates, which would give a
   ~925 copies-per-aggregate bridge.
6. Fix `surface_decay_per_day` in the influenza bundle before any of it is
   loaded, and decide whether the field becomes a rate.
7. Enter the influenza airborne half-life and asymptomatic fraction as
   intervals when the arm is activated.
