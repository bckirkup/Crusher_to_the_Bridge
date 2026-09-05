# The fleet-emergence ruling: fleet statistics are a likelihood, and what that costs

> **Status:** Decision record, 2026-09-04. It settles open decision 5 of
> [`bayesian_inference_design.md`](bayesian_inference_design.md) §9 and adds one
> prohibition that document did not carry. **Nothing here is implemented, no
> value is adopted, no register row is re-graded, and no interval is narrowed.**
> Every number it quotes is re-read from the
> [provenance register](../parameter_provenance_register.md) or the
> [norovirus ledger](../norovirus/norovirus_open_ledger.md) and is cited to the
> row it came from. Its purpose is to record what the ruling forbids, what it
> makes load-bearing, and — because the question was asked in the same
> breath — how many degrees of freedom the fleet observable can actually carry.

## 0. The ruling

> "I think the fleet statistics should emerge from our parameters; that is, the
> number of ships of each class that have notable and recorded outbreaks against
> a background of ship traffic."

and the frame it has to serve:

> "a model that effectively 'can' represent the observed VSP data for norovirus
> for the various pathogens **without changing the ship and crew models**, using
> something that approximates the operational state of the ships pre and post
> COVID".

Read operationally, that is one requirement and three prohibitions.

**The requirement.** The class-level outbreak counts are a *generated* quantity.
The chain that produces them — traffic volume and its class composition,
boarding prevalence, the pathogen's natural history, the transmission
mechanisms, the operational state of the era, the detection and reporting
process, and VSP's own posting rule — runs forward, and the counts fall out of
the end of it. They are compared against the observed series, not matched to it
by a knob that exists for that purpose.

**Prohibition 1: no fleet knob.** No parameter may exist whose function is to
set the number of posted outbreaks. This is the ruling's plain content.

**Prohibition 2: no parameter indexed by hull class.** This is the teeth of
"without changing the ship and crew models", and it is stronger than it looks.
The class contrast in the observed series — expedition against classic against
spirit against mega — must be produced by what already differs between the
platforms: geometry, zone volumes, HVAC topology, complement, schedules, and the
contact structure they imply. A class-keyed multiplier would reproduce the
contrast while explaining nothing, and it would do so by the exact mechanism
this whole audit road exists to prevent: one free parameter per scored number.

**Prohibition 3: era differences enter through one shared operational-state
vector.** Pre- and post-COVID may differ, but they differ in the *same* declared
list of operational quantities for every class — cleaning schedule and coverage,
medical-operations configuration, screening, and the prior-immunity shift — not
in a per-class or per-era re-parameterisation of the physics. The pathogen's
constants do not know what year it is.

## 1. What it settles, and the bookkeeping it triggers

§9.5 asked whether the fleet aggregates are prior or likelihood in the first
fit; §3 permits either and forbids both. **The ruling picks likelihood.** Fleet
statistics cannot simultaneously be the thing the model generates and the
external evidence constraining a parameter that generates it.

The consequence is mechanical, and it runs the opposite way from the
loosening §3 derived for an N=1 fit. Under §3's rule — *every fit declares the
data entering its likelihood; a datum entering that likelihood is barred from
that fit's prior* — declaring the VSP posting series as likelihood bars from
that fit's prior:

| Row | Why it is now barred |
|---|---|
| A4, the per-class per-era posted passenger attack-rate quantiles | Derived from the same 428-posting series (`vsp_class_era_scoring.py`), recomputed per class and era at runtime |
| A9, the posting rate under the 3% rule | The observable itself |
| A7c, the passenger/crew shift across the break (0.668, 0.532–0.907) | Same series, same rows |
| A8, MIDRS class-level incidence | Enters if the likelihood includes unconditional incidence; see §3 |

And it withdraws, *for this fit only*, the specific loosening §3 recorded: the
cabin-localization bound `f ≤ 0.18–0.45` and the other-outbreak attack rates
(Wikswo, Chimonas, Mouchtouri) were readmitted as priors on the grounds that
fleet aggregates are external to a single voyage. Once the fleet aggregate *is*
the likelihood, that argument is spent for any row derived from it. Wikswo,
Chimonas and Mouchtouri are separate outbreak cohorts rather than the posting
series, so they are not barred by the letter of the rule — **but whether any of
those cohorts is also a row in the VSP series is a fact, not a judgement, and it
has not been checked.** It must be checked before the first fit; an overlapping
cohort is the same datum on both sides.

Nothing here bars those rows from a *different* fit. §3's per-fit bookkeeping is
the whole point: the N=1 voyage fit and the fleet-count fit are two fits, and
the same row may be prior in one and likelihood in the other. What is forbidden
is quietly running one design and reporting the other's admissions.

## 2. The observable, stated precisely enough to be blocked

"The number of ships of each class that have notable and recorded outbreaks
against a background of ship traffic" is a rate with a numerator and a
denominator, and only one of them exists.

**Numerator — available.** Posted outbreaks, class- and era-resolved, from
`telemetry_buffer/observation_model/vsp_outbreak_series.csv` (428 postings,
`e167e32`). The rows carrying a passenger denominator, by class and era:
expedition 34 / 18, classic 174 / 32, spirit 50 / 13, mega 4 / 3. The
87 `legacy_pre2004` rows carry no denominator and the 5 `shutdown` postings
pool into neither arm.

**Denominator — blocked, and blocked by definition rather than by effort.** The
register's own row (§3.1, external voyage denominator, task #13) records:
Freeland 2016's 4,404–4,808 VSP-report voyages per year for 2008–2014
(Σ 32,084; of which 3–21 d and >100 pax, 3,964–4,387/yr, Σ 29,107) at **Grade
M, transcription unverified** — the sourcing unit could not re-open the table,
the paper's own per-1,000-voyage rates do not reproduce from those counts for
5 of 7 years, and its text says 133 where its table says 132. Jenkins 2021 gives
37,258 unduplicated voyage reports for 2006–2019 as a **single total, not
year-resolved**, and not reconcilable with Freeland in the same unit. Neither is
resolved by hull class. There is no denominator at all for 2004–2007, 2015–2019,
or 2022–2026. And the definitional blocker survives all of that: our numerator
is *posted* outbreaks, while every CDC denominator pairs with *investigated*
ones.

**So the ruling promotes #13 from a nice-to-have to a prerequisite, and it lands
on the worst-sourced row in the register.** That is a cost of the decision, not
an argument against it; a design whose observable is a rate cannot condition on
the numerator alone. Note what the ruling displaces: the COVID-discontinuity
design deliberately scores only statistics *conditional on posting* precisely
"so the missing voyage denominator never enters"
(`vsp_covid_discontinuity_design.md`, and the ledger §3). That evasion is no
longer available for the fleet fit.

**The factorisation that makes the first fit possible anyway.** The rate
factors into two observables with very different sourcing needs:

1. **Absolute posting rate** (postings per 1,000 qualifying voyages per era).
   Needs the absolute denominator. Blocked on #13, and absent for the post-COVID
   era entirely.
2. **Class composition of postings** (given a posting, which class it is on — a
   multinomial over classes). Needs only the **relative class shares of
   traffic**, not the absolute count. Which is exactly the question "how many
   ships of each class have recorded outbreaks", with the unknown total
   cancelled.

Recommendation, and it is a recommendation rather than a decision because it
belongs with the summary-statistic vector (§9.2): **the first fit conditions on
(2) plus the voyage-level observation streams, and holds (1) as a
posterior-predictive check to be run when #13 clears.** The class-share
observable is far better conditioned, it is the part of the ruling that carries
the class contrast, and it does not require us to adopt a Grade M transcription
as the exposure of a likelihood. A relative-traffic-share prior still has to be
sourced from fleet registry or capacity data, and it is a *denominator* rather
than a physical constant, so a wide prior over it marginalised out is legitimate
where a fitted physical constant would not be — but it may not be set to
whatever makes the shares come out right, and its provenance goes in the
register like anything else.

## 3. The post-COVID arm is thinner than the pre arm, and the ruling does not fix that

Three holes, all already recorded, all now on the critical path:

- **No post-2020 unconditional incidence observation exists.** The only
  published MIDRS analysis covers 2006–2019 (MMWR SS 2021;70(6)); a search of
  CDC's data pages, MMWR and the literature found nothing after it. So A8 has no
  post arm, and the operational-state changes the ruling most wants to represent
  are changes to the channel we have no post-2020 observation for. A pre-arm A8
  match plus a post-arm A4 match remains the most that can honestly be claimed.
- **`mega_cruise_5000` has no usable class anchor in either era** — 4 postings
  pre-break and 3 post, against a floor of 10 — and it is the hull the campaign
  manifests centre on. No mega-class result may be reported as passing or
  failing the class comparison. Under the ruling this becomes a statement about
  the *likelihood*: the mega cell contributes almost no information, so a
  posterior that appears to constrain mega behaviour is reporting its prior.
- **The era contrast is a tail collapse, not a level drop.** The withdrawn
  "~15–20% drop, p=0.032" is gone: rebuilt, the passenger median moves 5.39% →
  4.91% (ratio 0.912, 0.788–1.182, p=0.26). What actually moves is the crew
  median (×1.37, 1.004–1.677, p=0.007), the passenger/crew ratio (A7c = 0.668;
  0.736 with fleet composition held), and the upper tail — on 1000+ passenger
  ships, 11 of 226 pre-2020 postings exceed 15% of passengers ill against 0 of
  48 post-2020, maximum 25.2% → 13.5%. About half the crew rise is fleet
  composition rather than behaviour.

The last point is the one that interacts with the ruling most usefully. A
tail-collapse and a composition shift are exactly the kind of statistic that an
emergent fleet model produces and a fitted class rate cannot: the composition
half comes out of the traffic and class mix for free, which is a real advantage
of the decision. It also sets the compute floor, which the discontinuity design
already fixes: detecting an effect of that size needs **hundreds of posted
simulated voyages per configuration, and the design fixes 1,000** — posted, not
run, so the run count is that divided by the posting probability.

## 4. Degrees of freedom: how many, and in what windows

The honest answer has three parts: what the ruling freezes, what the literature
pins, and what is left — and then a count of how much the fleet observable can
actually identify, which is the binding constraint and is smaller than the
free list.

### 4.1 Frozen by the ruling (zero degrees of freedom)

Ship geometry, zone volumes and adjacency, HVAC topology and AHU membership,
crew complement and schedules, the contact structure they generate, and the
class composition of the fleet. Plus, by prohibitions 2 and 3: any per-class
parameter, and any per-era parameter outside the declared operational-state
vector.

### 4.2 Free quantities, and their sourced windows

From the register §5, unchanged by this document:

| Arm | Free | Windows recorded in the register |
|---|---|---|
| Norovirus | 6 route-efficiency multipliers, cabin-localization `f`, `airborne_emission_fraction`, one reporting-probability scale | `surface_decay_log10_per_day` [0.067, 0.79]; `hand_to_surface_drying_multiplier` [0.008, 1.0]; `secretor_negative_relative_susceptibility` [0.04, 0.83]; `shedding_duration_days` [12, 30]; α [0.072, 0.161] at β = 32.81; GII peak [7.0, 9.1] log10 copies/g; boarding prevalence, passengers [0.025, 0.040] and crew [0.007, 0.030]; cleaning frequency cabin 0.33–1.0/day, public 1.0–12.0/day, dining/galley/crew_mess 1.0–6.0/day, with coverages 0.336–0.600, 0.292–0.454, 0.292–0.600 |
| SARS-CoV-2 | 1 identifiable composite `(emission × route)/β` (`transfer` was a fourth name for the same position and is retired, #22), 6 route multipliers, a 5-state severity vector, the testing-campaign replica, `airborne_emission_fraction` | The composite is one degree of freedom wearing three parameters' clothing; β sweeps the Killingley-to-Zhang & Wang span. Blocked on #43, the copies conversion |
| Influenza | `base_susceptibility`, plus everything in §3.3 | Not active. Must come from seroprevalence or vaccination coverage for the specific season and route |

One was removed by *measurement* rather than by sourcing, and it is the
precedent for how this list shrinks: the norovirus dose knob is measured inert
above release 8 (a 14-log10 change is byte-identical). `contact_transfer_fraction`
was the second example here, on the grounds that it cleared no noise floor across
its sourced interval; **that reading is withdrawn (#22)** — it stood in the same
position of the same product as `route_efficiency_multipliers["direct_contact"]`,
so the screen ranged half of a product, and the field is removed by retirement
and refused at load rather than by measurement. The count of free parameters
above is unchanged: the route multipliers already carried the axis. Influenza's
dose-dependent illness form (R3) removes a third by deletion — Carrat's endpoint
is flat across 4.2 logs, so the form is refuted and `eta` already equals the
measured fraction rounded.

### 4.3 What the fleet observable can carry

Counting the informative summaries the ruling's observable actually contains,
per era: the class-composition multinomial over the three usable classes
(2 free cells), the per-class posted attack-rate location and spread (~6),
the passenger/crew ratio (1), and the absolute posting rate (1, blocked). Call
it ~9 per era, ~18 across both — before accounting for the fact that the era
pair shares its structure by prohibition 3, so the era contrast contributes
1–2 numbers (A7c and the tail collapse) rather than a second independent set.
The cells are counts and quantiles with real sampling noise, and two of the
eight class-era cells (mega) are unusable.

Against that, the norovirus free list is 9 named quantities, of which
identifiability already collapses several: the six route multipliers duplicate
Edison's clearance layer and are not separately identifiable from it (#25), and
emission scale enters strictly as a product with dose-response (#47, #366).

**So the working expectation is order 5 identifiable composites for the
norovirus arm from the fleet observable, not 9** — roughly: one
emission × dose-response product, one or two route composites, `f`, and one
reporting scale. Everything beyond that must be pinned by literature prior or
frozen by §4.1, and any posterior that appears to resolve more than that is
reporting its prior, which §7's prior-sensitivity step is there to expose.

**This is a prediction, not a result, and it is exactly what #36 and #37 exist
to measure.** #36 (the recut Morris screen) says which of the free quantities
clears the noise floor at all; #37, recast by
[`bayesian_inference_design.md`](bayesian_inference_design.md) §4 from a box
search to posterior mass in the admissible set, says whether the surviving set
can reach the anchors jointly. The final count of degrees of freedom and the
width of their windows are *posterior* quantities: prior-to-posterior
contraction is the direct answer to how many knobs are left and how much of what
the model claims comes from the data rather than from us. Committing a number
now would be the same error as fitting one.

## 5. What this decision does not do

It does not select the summary-statistic vector (§9.2), does not decide emulator
versus ABM in the loop (§9.1), and does not decide what goes hierarchical
(§9.3). It does not re-grade #13 or adopt any denominator. It does not authorise
a fit: the ordering is unchanged — the field repairs R2–R5 land, then #36, then
#37, with nothing structural inserted between the screen and the gate. And it
does not license a class-resolved traffic prior chosen to make the class shares
come out right; that would be prohibition 1 wearing a denominator's clothing.
