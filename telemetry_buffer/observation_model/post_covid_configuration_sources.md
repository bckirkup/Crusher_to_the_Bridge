# Post-2020 operational and design configuration: what is sourceable

Companion to `vsp_covid_discontinuity_design.md`. That document says the
post-2020 arm runs at the pre-2020 fitted dose with an *independently sourced*
operational configuration, and that A7c is therefore a prediction rather than a
second fit. This document is the source audit behind that promise: what the
industry and the literature actually document, what it implies for each
transmission route in the model, and — the larger half — what they do not
document at all.

Nothing here is a fitted quantity and nothing here was selected because it
reproduces A7. Several of these entries push the prediction the wrong way, and
they are kept for that reason.

**Where an entry here can now land (#9).** `non_pharmaceutical_interventions` in
`crusher_labs/config.yaml` takes a named measure with a source, a per-role
coverage, a compliance and a per-route surviving fraction, applied per host
between route efficiency and gastric survival. It ships empty: the shape is
commented out with magnitudes written `XXX`, and #10 owns whether any entry
below survives sourcing into a number. Two constraints the interface enforces
rather than assumes. **Who does it and what it does are separate arms** — in
§2.2, being actively reminded at the buffet door sets coverage, while the
soap-versus-rub gap sets the route multiplier, and one hygiene multiplier cannot
carry both. **A measure's routes
are the transmission routes, not the ship's plant**: filtration and surface
cleaning are already parameterised as ship configuration, so an air- or
surface-side change belongs there and would be double-counted here.

## 1. The identifiability problem this exists to answer

Interventions divide into two classes with completely different visibility in
the VSP series, because every A7 statistic is conditional on VSP posting a
voyage:

- **Takeoff-preventing.** Stops an introduction from becoming an outbreak at
  all. The voyage is never posted, so it leaves *no trace in any A7 statistic*.
  The effect lands entirely in the annual posting count, which is the one
  series with no voyage denominator (A7e, descriptive, never scored).
- **Magnitude-capping.** The outbreak happens and is posted; the intervention
  limits how far it runs. This is what A7a-A7d can see.

A7c is therefore a **lower bound on total NPI effect**, and a flat A7a is not
evidence that NPIs did nothing. An intervention that halved the number of
outbreaks while leaving the survivors' shape untouched scores A7c = 1.0
exactly. This is a limitation of the observation, not of the model: the model
can report both, but only the capping half is scoreable against VSP without a
denominator.

Recovering the takeoff half needs a voyage denominator from outside VSP
(published passenger volumes and ships in service by year). That is a separate
anchor on outbreak *incidence* and is not attempted here.

## 2. Sourced, quantified, and consumable by the model

### 2.1 HVAC filtration: MERV 8 → MERV 13, and ≥6 air changes per hour

Healthy Sail Panel, Recommendations 29-31 (Royal Caribbean Group / Norwegian
Cruise Line Holdings expert panel, 2020-09-21). Recommendation 31 asks all
operators to upgrade to MERV 13, and states the filtration difference
explicitly: MERV 8 is 30% efficient over 3.0-10.0 µm, MERV 13 is 90% efficient
over 0.3-1 µm. Recommendation 30 adds maximised air changes, ≥6 ACH in
occupied spaces and 6-12 ACH at negative pressure with 100% exhaust for medical
isolation rooms.

Supported by a tracer study the Panel cites: DNA-barcoded 1 µm microsphere
release aboard *Oasis of the Seas* (University of Nebraska Medical Center /
National Strategic Research Institute), finding no significant transport into
adjacent spaces on the same air handling unit and non-detection within an hour,
attributed to MERV 13 plus ≥6 ACH. **Unpublished as cited**, so grade it as
industry-reported, not peer-reviewed.

Route this touches: the HVAC pathway only. For norovirus that pathway is
aerosolised vomitus, so this is a **magnitude-capping** intervention acting
specifically on the mechanism behind large events — not on the median voyage.

### 2.2 Hand hygiene: alcohol rub is *weaker* than soap against norovirus

This is the entry that matters most, and it points the opposite way to the
intuition that a publicised hygiene push must lower norovirus.

Healthy Sail Panel Recommendations 25-28 specify the intervention as
alcohol-based hand rub at 60-95% alcohol, with stations placed at venue
entrances and lifts. Against norovirus specifically:

- Tuladhar et al. 2015 (*J Hosp Infect*), finger-pad tests: 30 s of soap and
  water removed >3.0 ± 0.4 log10 infectious MNV1 versus 2.8 ± 1.5 log10 for
  alcohol rub, and on genomic copies the gap is wide — soap removed >5 log10
  MNV1, >6 log10 GI.4 and 4 log10 GII.4, while propanol rub achieved >1.2,
  >2.6 and >3.3 log10 respectively. Non-enveloped virus; alcohol is poorly
  matched to it.
- Liu et al. 2009 (*Appl Environ Microbiol*), Norwalk virus on finger pads,
  same direction.
- Eggers et al. 2023 (*J Hosp Infect*): ethanol formulations can reduce MNV
  titre in 30 s, but an ethanol/propan-2-ol product was significantly worse
  than the 70% ethanol reference — efficacy is formulation-specific, not
  generic to "hand sanitiser".

So the documented post-2020 hand-hygiene intensification is expected to be
**near-null for norovirus** even where compliance rose, and the model should be
configured that way rather than given a generic hygiene multiplier.

Compliance itself is not improvable by assertion either. Bánsághi et al. 2025
(*Open Res Europe*) ran a four-arm intervention aboard *Celestyal Olympia*:
surface disinfection spray, hand-hygiene monitoring, and training. None
produced measurable behavioural change; observed usage was 7.6 soap and 1.6
hand-rub doses per person per day, and the authors conclude compliance is
determined by dispenser placement and by whether passengers are actively
reminded. That last clause is the only support found for the
steward-at-the-door mechanism, and it is qualitative.

### 2.3 Increased population susceptibility — pushing the other way

Two fitted community models find susceptibility rose materially through
2020-2021 because exposure stopped, with post-restriction incidence projected
at or above pre-pandemic levels: O'Reilly et al. 2021 (*BMC Medicine*,
England) and Lappe et al. 2023 (*BMC Infect Dis*, US), the latter projecting
>2-fold community incidence at full contact resumption.

The post-2020 arm therefore carries **two** changes, not one: an NPI change and
an immunity change with opposite signs. The model represents prior immunity
(`ImmuneHistory`), so this must be set from these sources rather than left at
the pre-2020 value — otherwise the NPI configuration absorbs the immunity
effect and A7c stops being a clean test of anything.

## 3. Sourced but qualitative — configuration shape only, no magnitude

- **Isolation capacity and layout.** Post-2020 newbuilds and refits place
  blocks of convertible cabins adjacent to the medical centre and use the
  structural Main Vertical Zones as containment boundaries (Musio-Sale et al.,
  NAV 2022). A CONTAM-based multi-zone study of an in-service passenger ship
  concludes isolation rooms should be ≥5% of occupancy (*Buildings* 13:2350,
  2023). Magnitude-capping, and specifically tail-capping: capacity binds only
  in large outbreaks.
- **Buffet service.** Self-service replaced by staff-assisted serving lines.
  Norovirus-relevant on the shared-utensil fomite route and plausibly both
  takeoff-preventing and capping. No efficacy measurement found.
- **Touchless fittings, zoned crew/passenger separation, cleanable
  materials.** Direction is clear, magnitude is unmeasured. Trade-press
  sourcing only.
- **Pre-boarding screening and denial of boarding.** Squarely
  takeoff-preventing, hence invisible to A7 by §1. Note Neri et al. 2008 and
  Wikswo et al. 2011 both record ill passengers boarding pre-COVID, so the
  baseline this acts against is real.

Claims found only as marketing copy and **not** used: "100% fresh air", "HEPA
standardised across cabins", real-time air-quality monitoring. No vessel-class
specification or measurement was located for any of them.

## 4. What this predicts, before any simulation

Assembled from the above with nothing fitted: alcohol-centric hand hygiene is
near-null for norovirus (§2.2) and rising susceptibility pushes rates up
(§2.3), so the median posted attack rate should move little; HVAC filtration
and isolation capacity act on large events (§2.1, §3), so the upper tail should
contract; and the strongest interventions are takeoff-preventing and therefore
invisible here (§1).

Flat A7a with a contracted tail is what the measurement shows. That agreement
is worth exactly as much as the independence of the sources above and no more —
it was assembled after the measurement was taken, so it is a consistency check
and an explanation, **not** a successful prediction. The honest test is whether
a configuration built only from §2 reproduces A7c = 0.668 (0.532-0.907) when
run at the pre-2020 dose, and that has not been run.

## 4a. Where the configuration now lives (#10)

`era_configuration_sets.py` is the executable half of this audit: the pre-2020
and post-2020 lever sets, each entry carrying the span it is swept over, its
grade and its origin. Three properties of it are worth stating here because
they are what §2 licenses and no more.

**Every lever is a span, and no era has a default coordinate.**
`era_config_patch(era, coordinates)` refuses to build an arm unless the caller
states a position in [0, 1] for every swept lever, so neither arm can acquire a
point value by omission. Ten coordinates are required for the post arm, one for
the pre arm.

**The buffet prompt is four levers per arm, twice.** §2.2's two arms — "would
you like to wash your hands" and "would you like sanitiser" — are separate
measures, each split into coverage (who is reminded), compliance (who acts),
`removal_log10` (what the act removes: the only sourced part) and `hand_share`
(how much of the host's hand-mediated dose passes through the washed state,
which nothing measures). With `hand_share` at 0 the route multiplier is exactly
1.0, so the unsourced lever cannot manufacture a reduction on its own.

**Two findings, neither of them a knob.** First, §2.2's soap-versus-rub gap is
a gap in *genomic copies*; on infectious MNV1 Tuladhar's own intervals overlap
(soap >3.0 ± 0.4 against rub 2.8 ± 1.5), so both arms are carried at their
infectious-titre spans — the weaker separation — and the wide genomic gap is
recorded but unused. Second, §2.1's figures put MERV 8 at 30% and MERV 13 at
90%, which makes the shipped `hvac.filter_efficiency` of 0.50 — whose comment
labels it `MERV-13` — a value inside **neither** era: above any pre-2020
filter, below the post-2020 one it is named after, and carried by an arm whose
anchors are overwhelmingly pre-2020. The value is not changed here; #11 sweeps
the era spans and the register row records the mismatch.

Recommendation 30's ≥6 ACH is quantified and still does not enter: the native
transport has no air-change term, so the post arm is configured *without*
ventilation, along with the four §3 mechanisms and the cleaning schedule of §5.
All six are declared as `unrepresented` levers rather than dropped, so #11
cannot report that the post-2020 configuration was applied while silently
meaning two thirds of it was.

## 5. Still missing

- Per-zone-class cleaning frequency and coverage. The Healthy Sail Panel says
  to "consider areas of the ship that require a higher frequency" and gives no
  frequency, no coverage and no per-zone schedule; §2 of the ledger's open
  items is unresolved by this audit. Do not invent one.
- Any measured efficacy for buffet service change, touchless fittings, or
  crew/passenger zoning.
- A voyage denominator, without which the takeoff channel (§1) cannot be
  scored.
- Crew-side operational changes specifically. A7b says crew rates rose; no
  source found here explains that, and roughly half of it is fleet
  composition rather than behaviour.
