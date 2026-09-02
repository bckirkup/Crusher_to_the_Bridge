# Norovirus fit: open ledger

> **Status:** Living

**Live status as of `1329bbf` (#353 merged).** What is currently withdrawn,
what each anchor last measured and *when*, and what is outstanding.

`docs/norovirus/norovirus_model_history.md` is the permanent record of defects and
corrections. This file is the volatile counterpart: it goes stale by design and
must be updated whenever a model change lands. If the head commit below is not
the current head, treat every number here as unverified.

Read this before quoting any dose figure or anchor result.

---

## 1. Currently withdrawn

**Every dose figure in this repository is void.**
`environmental_faecal_release_log10_g_per_epoch` (the old `dose_adjustment`,
still accepted as a legacy alias) was last fitted against a contact layer that no
longer exists: #351 rebuilt the fomite chain, #352 added emesis, and #353
raised the direct-contact kernel about 10x and the shared-surface touch rates
4-10x. A dose fitted before those is not transferable, and no refit has been
run since.

Also withdrawn and not yet replaced:

- **The v4 campaign** and every campaign before it. Each was invalidated by a
  defect found after it ran (§12 of the history).
- **Any claim that the model reproduces VSP attack rates.** Withdrawn at #346
  and not re-established. Expedition's earlier agreement was a cancellation of
  an inflated infection rate against a deflated illness ratio.
- **Route shares.** Last measured before #351/#352/#353, all three of which
  change route magnitudes directly. The often-quoted "droplet carries 94-96% of
  establishing dose" dates from the post-#338 measurement and is stale.
- **The passenger/crew ratio.** Same reason.

**The withdrawal of the `innate_nonsusceptible_fraction` correction is itself
withdrawn for `norwalk_gi`: it was derived from the wrong genogroup.** The
0.00 – 0.16 interval published in #367 used the **GII** row of Teunis et al.
2020, *Epidemics* 32:100401 — Se+ 0.076 against Se− 0.015 per genomic copy, a
~5× reduction, which with Rouphael et al. 2022 (*JID*, GII.2, 4 of 8 Se− ill at
top dose) and Frenck et al. 2012 (*JID*, GII.4, 1 of 17 Se− ill against 13 of 23
Se+) does establish partial susceptibility **to GII**. The same paper's **GI**
row is Se+ 0.28 against Se− **0.00007** — a factor of ~4,000, not ~5 — and
Lindesmith et al. 2003, *Nature Medicine* reports the FUT2 null allele as fully
penetrant in GI.1 challenge: no nonsecretor was infected **at any dose**. For a
GI.1 profile the removed-fraction mechanism is correct and the ceiling is the
non-secretor prevalence itself, ≈0.20. So 0.0 → 0.20 is defensible for the arm
we ship, and the shipped 0.0 is the only value outside the range.

**The open question this exposes is larger than the parameter.** `norwalk_gi` is
GI.1 by name and carries Teunis 2008 GI.1 challenge dose-response, but it is
scored against VSP cruise outbreaks that are predominantly GII.4, and GI is
3.7× more infectious per genome copy in Se+ hosts than GII (0.28 vs 0.076). The
arm is GI-parameterised and GII-validated, and a genogroup switch would move
infectivity and susceptibility in opposite directions — partially cancelling in
the aggregate attack rate. Whether this arm is GI.1 or cruise-realistic GII.4 is
a scope decision and is not settled here. Prevalence is population-specific in
either case (~20% European-ancestry, 29% of the Lindesmith 2003 sample, 19% in
the Rwandan cohort of Munyemana et al. 2025), so the replacement remains an
interval rather than a value. Evidence:
[`../literature/consensus_tranche_2.md`](../literature/consensus_tranche_2.md)
§1–§2; derivation:
[`bounded_sensitivity_and_admissible_region_spec.md`](../proposals/bounded_sensitivity_and_admissible_region_spec.md)
§3.3. No profile JSON is changed by this entry.

## 2. Anchors

Targets, from `telemetry_buffer/observation_model/anchor_measurement_spec.md`:

| | quantity | target |
|---|---|---|
| A1 | ever-ill attack rate, passengers (Wikswo whole-ship cohort) | ~0.154 |
| A2 | ever-ill / infected | 0.68-0.81 (0.59-0.81 GII.4-weighted) |
| A3 | reported / ever-ill (infirmary capture) | 0.60 ± 0.05 |
| A4 | reported passenger attack rate | inside the hull-class IQR |
| A5 | passenger / crew reported attack rate | ~2.9-3.5 |

A5's two figures come from different sources and are both live: the anchor spec
says ~3.5 (7% vs 2%); the VSP 424-outbreak series gives ~2.9 (passenger
5.7-6.9% against crew 2.0-2.4%). Treat the target as a range, not a point.

**"Stable on both sides of the COVID break" was wrong, and is withdrawn.** It
was inferred from A5 rather than measured, and the per-outbreak series
contradicts it: across the break the median crew rate rises by 1.37x
(1.004-1.677, p=0.007) while the passenger median does not move detectably,
so the passenger/crew ratio falls by about a third (A7c = 0.668, 0.532-0.907).
A5 must therefore be quoted per era, not as one era-independent number, and any
fit that reproduces A5 pooled across both arms is reproducing an average of two
different ratios. Measured at `e167e32`; see A7 in
`telemetry_buffer/observation_model/anchor_measurement_spec.md`.

**Last measured values, and this is the part that matters: they are stale.**
All of the following were taken at `d557f39`, immediately after #346 and
*before* #348, #351, #352 and #353 landed. Every one of those changed
transmission. Do not quote these as current model behaviour; they are recorded
so the next measurement has something to compare against.

| | expedition | classic | measured at |
|---|---:|---:|---|
| infection attack rate | 0.407 | 0.465 | `d557f39`, 120 runs, dose 2.0 |
| ill / infected (A2) | 0.341 | 0.364 | `d557f39` |
| reported passenger AR (A4) | 3.48% | 3.89% | `d557f39` |
| A5, ever-ill ratio | 0.94-1.15 across hulls | | pre-#351 |
| A5, reported ratio | 0.85-0.97 across hulls | | pre-#351 |

Status at that measurement: **A4 failed on both hulls** (expedition below the
4.51% floor). **A2 missed by ~1.8x.** **A5 missed by ~3x, in a model that
returns roughly parity.** A1 and A3 were not jointly satisfiable with A2 under
homogeneous exposure — infection attack rate and ill/infected are welded to the
same dose, so they cannot be separated by refitting.

**The four hard-coded VSP class targets are withdrawn.** The triples
`score_anchors.py` carried (expedition 8.56%, 4.51-13.60%; classic 5.59%,
4.46-7.76%; spirit 5.64%, 4.44-7.90%; mega 5.61%, 3.40-7.45%) had no
derivation script and no source note, and do not reproduce from
`telemetry_buffer/observation_model/vsp_outbreak_series.csv` under capacity
bands or under any alternative band edge tried; the expedition class misses by
the widest margin. They are replaced by values recomputed from the series at
runtime, per hull class **and per era**, by
`telemetry_buffer/observation_model/vsp_class_era_scoring.py`, which
`score_anchors.py` now calls (`--vsp-era`, default `pre`). Derivation and
sources: `telemetry_buffer/observation_model/incidence_and_attack_rate_scoring_spec.md`.

VSP passenger attack-rate targets, for A4, as now derived (333 of 428 postings
carry a passenger denominator; the 87 `legacy_pre2004` rows carry none, and the
5 `shutdown` postings are never pooled into either arm):

| hull | era | n | q1 | median | q3 |
|---|---|---:|---:|---:|---:|
| expedition | pre | 34 | 3.70% | 5.07% | 10.18% |
| expedition | post | 18 | 3.31% | 7.24% | 13.51% |
| classic | pre | 174 | 4.18% | 5.46% | 7.70% |
| classic | post | 32 | 4.11% | 5.06% | 6.89% |
| spirit | pre | 50 | 4.31% | 5.42% | 6.67% |
| spirit | post | 13 | 3.53% | 4.73% | 6.35% |
| mega | pre | 4 | — | — | — |
| mega | post | 3 | — | — | — |

**`mega_cruise_5000` has no usable A4 anchor in either era** — four postings
before the 2020 break and three after, against a floor of ten. `score_anchors.py`
reports its A4 verdict as `n/a (insufficient VSP postings)` rather than scoring
it. That is the hull the campaign manifests centre on, so no mega-hull result
may be described as passing or failing A4.

**A8/A9 are now implemented model-side, but the post-COVID arm has no
unconditional incidence observation at all.** The model-side channels are in
`telemetry_buffer/observation_model/score_anchors.py`; their MIDRS constants,
interval targets and fixed hull-to-GRT mapping are in
`telemetry_buffer/observation_model/midrs_incidence_targets.py`, sourced from
`telemetry_buffer/observation_model/midrs_observed_targets.md`. A8 aggregates
reported cases and travel-days over every run, including non-take-off runs. A9
applies the VSP 3% passenger-or-crew rule to eligible voyages and reports
ineligible runs separately. A truth-only arm emits an explicit no-reporting
sentinel rather than a false zero.

The only published MIDRS incidence analysis is MMWR Surveill Summ 2021;70(6),
covering 2006-2019; a search of CDC's VSP data pages, MMWR and the
peer-reviewed literature found nothing after it. So the post-2020
health-practice configuration changes exactly the channel we have no post-2020
observation for. A pre-arm A8 match plus a post-arm A4 match is the most that
can honestly be claimed until a post-2020 MIDRS analysis exists.

The MIDRS source record carries three conflicts that must remain attached to
the implementation. First, the MMWR Results prose labels 26.7 and 29.2 as
mega and super-mega **crew** rates, but Table 2 identifies those as passenger
rates; the crew values are 14.7 and 16.0, with the crew maximum 19.8 on
extra-large ships. Second, the reported "80.6% of the 252 ships were extra
large" is actually 30,039/37,258 voyage reports; the per-ship size distribution
is unpublished. Third, MMWR counts 156 investigated passenger outbreaks,
whereas `telemetry_buffer/observation_model/vsp_outbreak_series.csv` contains
208 posted outbreaks over the same period. A9 therefore reports an interval
spanning those definitions rather than silently mixing them.

**Open defect: `HULL_CAPACITY` is a total-agent complement, not a passenger
complement.** The role split used by the model is authoritative in
`orchestrator_init.py::role_group_for_agent`: on the expedition reprobe
summary `..._dose12_..._s503`, `cumulative_ever_infected_passenger = 107` and
`infection_attack_rate_passenger = 0.338608`, giving
`round(107 / 0.338608) = 316`; the corresponding crew values are 40 and
0.298507, giving 134. Thus 316 passengers plus 134 crew equals the
`num_agents = 450` total. `HULL_CAPACITY["expedition_cruise_450"] = 450`
therefore denotes the total complement, not the passenger denominator.
`BAND_EDGES` in `telemetry_buffer/observation_model/vsp_class_era_scoring.py`
are geometric means of those total complements while binning observed
passenger counts (`pax_total`), so the A4 class bins inherit this offset.
The A4 targets merged in #360 are affected and remain unrepaired; recutting
them is a separate decision. A8's passenger and crew denominators instead
come from the role-derived complements emitted in each run summary and do
not use `HULL_CAPACITY`, so A8/A9 are unaffected.

## 3. Out-of-sample checks

**Park et al. (2015)** — surface swabs during a shipboard outbreak; nothing was
ever fitted to it. Observed 80-31,217 copies/swab in sick passengers' cabins,
16-113 in public spaces, a gradient of roughly 100-300x.

| | #351 (hand chain) | #352 (+ emesis) | #353 (+ measured contact) | #355 (+ cleaning) |
|---|---:|---:|---:|---:|
| cabin, confined | 1,434 | 1,434 | 5,571 | 4,120 |
| public, 60 shedder-h/day | 356.9 | 356.9 | 384.9 | 368.0 |
| cabin/public gradient | 4.02x | 4.02x | 14.5x | 11.2x |
| shedder-hour asymmetry needed for 100x | 75x | 75x | 29.3x | 29.3x |

Levels sit inside the observed ranges across 1.5 orders of magnitude, from
independently sourced constants. The **gradient still fails**. A single emesis
episode reaches Park's level (1,047-31,400 copies/swab at Park's stated
recovery) but carries no intrinsic cabin/public gradient — the touchable-area
factor and the per-area concentration cancel exactly. The residual is *where*
people vomit, and reaching 100x needs 98.5-99.7% of episodes in the host's own
cabin. That fraction is unmeasured, is not a model parameter, and reading it off
Park's gradient would be fitting. Refused. Harness:
`telemetry_buffer/observation_model/park_surface_check.py`.

Routine cleaning (#355) moves the gradient the **wrong way**, from 14.5x to
11.2x, and the reason is instructive: a daily pass over 37% of objects competes
with continuous removal by hand pickup, so it multiplies the time-averaged pool
by 0.74 in a quiet cabin (loss 0.029/h) but only 0.96 in a busy public zone
(loss 0.33/h), where pickup already clears surfaces faster than housekeeping
can. Real ships clean cabins and public spaces on different schedules with
different products; the model does not, because nothing measured says how. The
gradient shortfall is therefore not a cleaning gap — it remains §4's sick-host
movement problem. Measured at the #355 head with
`ROUTINE_CLEANING_COVERAGE=0.37`, 1.29 log10/pass, one pass/day.

**The COVID discontinuity** is the better instrument, is now measured, and is
not yet scored. It is a *difference*, so errors common to both arms cancel —
which is what this effort needs, having spent its length finding errors that
cancel in levels. #355 supplies the NPI lever it needs (routine coverage and
per-event log10 are separately configurable, and outbreak response is a
distinct mechanism), but one schedule still applies to every zone class, so the
passenger-facing asymmetry cannot yet be expressed.

Two limits on the instrument, from
`telemetry_buffer/observation_model/post_covid_configuration_sources.md`. Every
A7 statistic is conditional on VSP posting, so an intervention that stops an
introduction from taking off is *invisible* to all of them — it prevents the
posting rather than shrinking it, and pre-boarding screening and denial of
boarding are exactly that kind. A7c is therefore a lower bound on NPI effect,
and a flat A7a is not evidence that NPIs did nothing. Second, the post-2020 arm
carries two changes with opposite signs: the NPI change, and a susceptibility
rise from two years of interrupted exposure (O'Reilly 2021, Lappe 2023, the
latter projecting >2-fold community incidence at full contact resumption).
Prior immunity must be set from those sources, or the NPI configuration
silently absorbs the immunity effect. Also note the industry's own hand-hygiene
push was alcohol-rub-centric, and alcohol rub is measurably weaker than soap
against norovirus (Tuladhar 2015), so it is expected to be near-null here.

The two caveats that blocked it are now handled by construction rather than by
correction, per `telemetry_buffer/observation_model/vsp_covid_discontinuity_design.md`: score only statistics
conditional on posting, so the missing voyage denominator never enters; and run
VSP's own posting rule over simulated voyages, so both arms are truncated
identically. The reporting-intensity confound is cancelled by taking the
passenger shift over the crew shift.

**The "~15-20% drop, p=0.032" figure is withdrawn.** It was read off
`docs/norovirus/vsp_covid_discontinuity.png`, whose per-outbreak table was never in the
repository. Rebuilt from CDC-hosted pages (`telemetry_buffer/observation_model/vsp_outbreak_series.csv`, 428
postings, `e167e32`), the passenger median moves 5.39% → 4.91%, a ratio of
0.912 (0.788-1.182, p=0.26) — no detectable level drop. The discontinuity is
real but it is not that: the crew median rises, the passenger/crew ratio falls
by a third (A7c = 0.668, p<0.001, and 0.736 with fleet composition held), and
what disappears from the passenger distribution is its upper tail — on ships
carrying 1000+ passengers, 11 of 226 pre-2020 postings exceeded 15% of
passengers ill and 0 of 48 post-2020 do, the maximum falling 25.2% → 13.5%.
About half the crew rise is composition, not behaviour: small expedition
vessels, several below VSP's own 100-passenger criterion, are posted post-2020.
Detecting an effect of this size needs hundreds of posted simulated voyages per
configuration; the design fixes 1,000.

## 4. Outstanding

Roughly in dependency order.

1. **Zone-differentiated cleaning schedules — swept, bounds sourced, no cell
   adopted.** #355 closed the "nothing cleans surfaces" gap — routine
   housekeeping is a discrete pass over the measured 37% of objects it reaches,
   and outbreak-response hypochlorite is a separate, stronger, SOP-triggered
   mechanism. A search found no measured cleaning-frequency schedule
   differentiated by zone class in an accommodation or passenger-vessel
   setting. The opt-in schedule is therefore swept inside the bounds documented
   in
   [`cleaning_schedule_sweep_spec.md`](../../telemetry_buffer/observation_model/cleaning_schedule_sweep_spec.md):
   cabin frequency 0.33–1.0/day, public 1.0–12.0/day, dining/galley/crew_mess
   1.0–6.0/day; cabin coverage 0.336–0.600, public 0.292–0.454, and
   dining/galley/crew_mess 0.292–0.600. No sweep cell may be adopted as a
   parameter value or default.

   Carling et al.'s Grade A 37% measurement is specifically from public
   restrooms on cruise ships, not cabins. Applying it to cabins is an
   unsourced extension, not evidence of a cabin schedule. The shipped model
   retains its uniform default; the schedule sweep exposes this uncertainty
   without fitting it to an anchor. Its hand-only gradient envelope is
   8.6635–18.5054x, against 11.1977x for the shipped default: that is a
   bound on schedule leverage (at most 1.6526x upward), not a test of Park
   reachability, because the hand-transfer channel was already shown
   unreachable at any occupancy. The Park comparison is instead made with
   the emesis-inclusive calculation, swept over the separate, unmeasured
   cabin-localization fraction f; at f=0.99, 78 of 81 schedule cells reach
   Park's 100–300x range, and at f=1.00 all 81 do. f is not a schedule
   parameter and no value is selected. Note that the premise has changed:
   crew rates did *not* hold still across the break, they rose (A7b), so a
   configuration that leaves the crew arm untouched now contradicts the data
   rather than matching it.
2. **Refit the common dose** against VSP class targets. The contact layer
   (#353) and cleaning (#355) are now in place, so this is next. One common
   dose-response across all four hull classes; no hull-specific pathogen
   biology, ever.
3. **Re-measure route shares and the passenger/crew ratio** on the refitted
   model. Expect #353 to push A5 *further* from 2.9 — crew work the highest
   touch-rate zones and their berthing is already ~3x denser than passengers'.
   If it does, that is a finding about what is still missing.
4. **Score the v4-successor campaign** against VSP class targets, per era,
   and never on the mega hull's A4.
5. **A8/A9 observation follow-up.** Model-side aggregation and the sourced
   MIDRS target tables are implemented in
   `telemetry_buffer/observation_model/score_anchors.py` and
   `telemetry_buffer/observation_model/midrs_incidence_targets.py`. The
   post-arm observation remains unavailable, and A10 duration trajectories are
   still Proposed.
6. **Cabin-level environmental compartments.** The finest mixing compartment is
   `Cabin_Corridor`: ~37 people in 800 m³ where reality is 2 people in ~40 m³
   (crew 3). `cabin_size` and `cabin_mate_ids` exist but only exempt a mate from
   confinement attenuation. Building this would raise crew rates — away from the
   anchor — so build it honestly and do not expect it to help. No cruise
   platform has four-berth cabins; crew are three.
7. **Aerosol portal efficiency.** #352 computes and records the emesis aerosol
   load but does not route it into the airborne reservoir. The direction is
   settled (norovirus establishes enterically; inhalation is delivery-to-gut via
   swallowing, so the respiratory clearance proxy is the wrong quantity) but the
   magnitude is not: the 10-30% figure is deposition in mouth/nose/trachea and
   is explicitly **not** an intestinal-delivery fraction.
8. **Sick-host movement and a bathroom destination.** The Park gradient needs
   it; see §3.
9. **AWS daughter session: CONTAM vs native accumulation comparison.** Deferred.
10. **Provenance queue, re-ordered by the bounded screen.** Measured in
    [`bounded_screen_results.md`](bounded_screen_results.md) §7.
    `innate_nonsusceptible_fraction` moves to the front on consequence: it is
    the top-ranked factor while carrying the mechanism §1 withdraws.
    `contact_transfer_fraction` drops down it — across its whole sourced
    interval it moves no scored output above the measured noise floor, so the
    shipped value is still wrong but it is not an exposure. Emesis titre
    becomes a first-order provenance target, which it was not before.

## 5. Held fixed by assumption

Live Grade C liabilities. Any of these could move the reported rate; the system
is over-determined only *given* them. Full list in §10 of the history document.

- Route weights (contact 0.35, fomite 0.30, food 0.20, droplet 0.10, HVAC 0.05)
  — assumed, not traced to a source. **The largest single unsourced input.**
- `HIGH_TOUCH_AREA_M2` — per-room high-touch area in m² has never been measured
  by anybody. Permanent Grade C; the gap is the field's, not ours.
- Fraction of emesis episodes occurring in the host's own cabin — swept, never
  asserted.
- Confinement attenuation factor 0.05.
- Secretor-status non-susceptibility. Not a held-fixed 20% ceiling: the profile
  the campaign runs ships 0.0, no attack-rate ceiling is observed (0.013–0.326
  across the override arms), and §1 withdraws 0.2 as the correction target. The
  live liability is that the mechanism is a removed fraction at all, where the
  evidence is partial susceptibility.
- `airborne_half_life_hours` = 1.1 is cited to van Doremalen et al. 2020, which
  measured **SARS-CoV-2**, and is the identical value carried by the COVID
  profile. A search for a norovirus airborne decay measurement returned a null
  result (see
  [`../literature/parameter_sourcing_bundle.md`](../literature/parameter_sourcing_bundle.md)
  §2.3), so this is a cross-pathogen borrow presented as a citation, not a
  sourced value. Treat as Grade C until it is declared or bounded by deposition
  physics.
- `surface_decay_per_day` = 0.25 has no source. It implies 0.125 log10/day,
  slower than the MNV-1-on-stainless-steel surrogate measurement (≥0.29
  log10/day, Leblanc et al. 2019), and the gap inflates the fomite reservoir.
  No human-norovirus dry-surface infectivity decay measurement exists; any
  adopted interval is Grade B at best and must state its medium.
- Uniform `immune_ratio` across a resident crew and a weekly-turnover passenger
  cohort — an assumption that bears directly on A5.
- Crew presenteeism and mandatory occupational reporting: absent in both
  directions.
- `OUTBREAK_CLEANING_COVERAGE` 0.58 — no shipboard measurement exists. Carried
  over from a 34%→53% supervision-and-feedback effect in two hospitals
  (Murphy 2011) applied to Carling's 37%. Sweep it; never assert it.
- Log10 additivity of the two-step outbreak procedure (detergent preclean then
  hypochlorite, 1.29 + 3.0 = 4.29). The field reports two-step efficacy that
  way; nobody measured the composition.
- Uniform routine cleaning remains the shipped default. One pass per day is the
  denominator of Carling's "cleaned on a daily basis", not a measured
  per-zone-class schedule. The optional per-zone-class schedule is swept inside
  sourced bounds; no sweep cell may be adopted as a parameter value.
- Newly deposited surface mass is split into cleaned and missed shares in
  proportion to coverage, i.e. shedders touch reached and missed objects alike.
  Untested; if soiling concentrates on the objects housekeeping skips, the
  missed reservoir is larger than modelled.

## 6. Maintaining this file

Update it in the same PR as any change that invalidates something here. The
failure mode this file exists to prevent is a future session reading a stale
dose figure from a doc and building on it in good faith — so a ledger that is
quietly out of date is worse than no ledger. Date-stamp every measurement with
the commit it was taken at.
