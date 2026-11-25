# COVID-SHED-EVIDENCE-01
**Date:** 2026-11-24
**Commit:** 32861c29d87670b46055a7e67d53429530e29ea8
**Pathogens:** sars_cov2_resp
**Status:** open

**Partial methodology record, not an implementable target shape.** The
requested evidence-class argument and re-denomination analysis are recorded
below. Implementation-ready SARS-CoV-2 emission parameters and numerical
segment bounds are intentionally not supplied. Consequently, the requested
quantitative deliverable remains incomplete. This omission is not a finding
that the literature contains no relevant measurements.

No profile, constant, simulation code, fit, campaign, or held-out status changes
in this entry. GM remains held out; H5 remains held out forever. No simulation
or refit was run. The findings and source limitations of
[COVID-SHED-CURVE-01](COVID-SHED-CURVE-01.md),
[PR #1422](https://github.com/bckirkup/Crusher_to_the_Bridge/pull/1422), are
settled inputs, not re-derived here.

## Evidence-class verdict

**The latent quantity is viable-virus-weighted emission, upstream of recipient
infection probability.** Direct measurements of emitted viable virus are the
closest evidence class. Quantitative upper-respiratory culturable-virus
kinetics are a biological proxy, not a direct measurement of that emission.
RNA kinetics are supplementary assay evidence. Transmission-derived
infectiousness belongs on the outcome side as an external epidemiological
check, not as a drop-in physical-emission curve.

Thus the appropriate methodological combination is **viable-emission evidence
where available, culture kinetics with an explicit proxy assumption, and
transmission-derived profiles as contextual checks**. This does not license a
numerical blend of unlike endpoints or assert that swab culture alone identifies
the model's source term.

### What the implementation establishes

Code locations below refer to the header commit. These are static-code
observations, not measurements of biological emission or simulation outputs.

| Stage | Where read | Consequence for the quantity |
|---|---|---|
| Select the shedding age and curve | `engines/infection_dynamics_bridge.py`, `_shedding_curve_point`, `_shedding_age` | Uses an onset-relative axis; unpresented infections use a virtual onset. The presymptomatic gate and clamped array index are implementation conventions, not measurements. |
| Produce an emission amount | Same file, `get_pathogen_shedding` | Exponentiates the curve after the release offset, applies host/strain multipliers, and converts a daily amount to an epoch amount. It does not directly return a transmission probability. |
| Supply the environment | `orchestrator_epoch.py`, `_deposit_agent_emission` | Adds the emission amount to a mass pool after deposition/confinement factors. |
| Construct respiratory exposure | `engines/transmission_core.py`, `_get_shedders`, `_pathway_droplet`, `_droplet_unit_doses`, `_droplet_target_dose`, `_pathway_hvac_airborne` | Uses shedding to construct concentrations and recipient doses through air volume, inhalation, residence/ventilation, proximity and presence terms. |
| Resolve infection | Same file, `_dose_response`, `_dose_response_susceptibility`, `_dose_response_hazard` and the per-pathogen challenge path | Applies a nonlinear dose-to-probability mapping downstream; host susceptibility persists across exposures. |

**Interpretation, not a unit validation:** these consumers establish the curve's
role as a source term. They do not establish that an inherited RNA-labelled
amount is already calibrated in culturable or human-infectious units. A log
array, release offset and nonlinear dose-response do not themselves identify
that conversion. The name *infectiousness-weighted* must refer here to the
viability/potency of emitted material, not to the probability that a particular
recipient becomes infected.

## Why the nonlinear dose-response matters

A transmission-pair profile describes when successful transmission occurs under
its study's exposure and observation process. Depending on the inference model,
it can retain effects of contact opportunity, symptom-linked behaviour,
isolation, exposure duration, recipient susceptibility, dose-response
nonlinearity, and selection or censoring of observed pairs. It is not generally
an emitted-material rate.

Copying that profile into the source curve and then applying the model's own
exposure process and nonlinear infection probability risks counting these
effects twice. The problem is not that every transmission study literally
applies the same probability function twice: some estimate relative rates or
renewal kernels rather than per-contact probabilities. The general error is
**substituting an outcome-derived kernel for an upstream source term without
establishing an equivalence**. There is no unique reverse conversion from an
aggregate transmission profile to emission without assumptions about those
other processes.

An approximate proportionality can occur in a low-probability regime with
stable exposure and recipient conditions. Neither the presence of a
beta-Poisson profile nor the inspected code establishes that regime for the
relevant contacts. It cannot be assumed merely because a normalized curve is
convenient.

Two further distinctions prevent overclaiming:

- The relationship between RNA and viable virus is separate from the
  relationship between delivered viable material and human infection. Culture
  evidence informs the former biological distinction; it does not already
  include every recipient's in-vivo dose-response.
- A fixed strictly increasing dose-response, applied to an otherwise identical
  exposure at each age, preserves the age ordering of doses and therefore the
  peak location. Nonlinearity alone is not an explanation for every displaced
  peak across papers. Cohort, specimen, symptom definition, sampling and contact
  differences must remain visible.

## Evidence and provenance boundaries

Grades describe suitability for the model quantity and setting, not paper
prestige or agreement with a desired result: A = directly measured in the
target setting; B = analogous-setting measurement; C = inference or declared
assumption. Origin is separate: `R` Results, `Me` Methods, `Sec` secondary.
Figure captions cited below were read as text; no figure was digitized.

| Evidence class/source | What was actually observed or inferred | Where read and retrieval | Permissible role and grade boundary |
|---|---|---|---|
| Zhou et al., *The Lancet Microbe* (2023), [DOI](https://doi.org/10.1016/S2666-5247(23)00101-5) | Challenge-study respiratory and environmental sampling; RNA quantification and recovery of viable virus from some sample types. The paper distinguishes these endpoints. | Consensus full-text retrieval: `Me`, Outcomes; `R`, paragraphs beginning “All 18 infected participants emitted…” and “Viable virus was recovered…”; Figure 2 caption. | Direct emitted-viable-virus observations are closest to the source concept, but the challenge setting is analogous rather than the ship setting (B). Transferring a swab trajectory to emitted viable material is an additional C inference. |
| Zhou et al., same article | Nasal measurements and emissions were associated, but individual trajectories were discordant; symptom burden did not uniquely determine emissions. | `R`, paragraphs beginning “In a correlation analysis…” and “Even for a single individual…”; Figures 2–3 captions, text only. | Supports neither identity of swab titre and emission nor a universal symptom-to-emission mapping. Correlation cannot upgrade the proxy transfer to A. |
| Sender et al., *eLife* (2022), [DOI](https://doi.org/10.7554/eLife.79134) | An inferred unmitigated infectiousness profile, addressing epidemiological and observation biases in transmission data. | Consensus full-text portion: Results, Discussion and Table 1 (“Potential biases…”). Supplementary material was not exhaustively retrieved. | C, inferred population transmission timing. Useful for examining dependence on mitigation and observation assumptions, not a direct physical-emission measurement. |
| Marc et al., *eLife* (2021), [DOI](https://doi.org/10.7554/eLife.69302) | Reconstruction of viral loads and estimation of transmission probabilities from contact data. | Consensus `R` excerpts under “Quantifying the relationship between SARS-CoV-2 viral load and infectiousness”; not a complete full-text audit. | C, model-derived relation involving a probability outcome. It must not be relabelled as a measured emission rate. |
| He, Hakki, Wölfel and Jones evidence already assembled in [COVID-SHED-CURVE-01](COVID-SHED-CURVE-01.md) | Transmission inference, RNA kinetics and culture-related observations have different denominators and clocks. | `Sec` in this entry: the settled ledger's source table and limitations, without new primary-source verification. | Retain the original ledger's origins and caveats. Neither disagreement nor convenience warrants promoting one endpoint to another. |

The Zhou presymptomatic summaries of environmental **RNA** are not automatically
presymptomatic viable-virus emission shares. Similarly, the proportion of people
with a positive culture is not the fraction of total viable material emitted.
A culture-negative sample is assay- and sampling-dependent, not proof of a
universal hard biological cutoff. None of these substitutions is licensed by
normalizing each series to its own peak.

The selection rule is endpoint compatibility, not whether a paper improves an
attack-rate or timing anchor. This is a focused methodological reading, not a
systematic review or a claim that all relevant literature has been exhausted.

## Segment-level disposition: numerical targets not supplied

This table preserves the requested segment distinctions but is **not** a frozen
parameter box and is **not sufficient to implement a replacement curve**. No
numerical interval is adopted, inferred, or recommended by this entry.

| Requested segment | Methodological distinction | Quantitative disposition |
|---|---|---|
| Presymptomatic level/share | Emitted viable-material share, culture-positive participant fraction, RNA area share and transmission-event share are different quantities. | Not supplied. |
| Peak position | Infection time, first detection, symptom onset and peak symptoms are different origins; specimen and emission peaks are not interchangeable. | Not supplied. |
| Onset-to-peak rise | The slope of viable material cannot be inferred directly from an RNA slope or a normalized transmission profile. | Not supplied. |
| Post-peak decay | RNA persistence, loss of culturability and declining population transmission have different endpoints and censoring. | Not supplied. |
| Total infectious period | Culture-detectable duration, emission duration, clinical duration and the tail of a transmission kernel are distinct. | Not supplied. |

## Does one relative-emission shape fail structurally?

**Not established by this review.** The discrepancy between evidence classes is
not a contradiction between measurements of one identical quantity. A
conditional reference emission trajectory remains a coherent modelling
abstraction; it is not automatically an honest representation of every host,
route, variant, immune history or symptom state.

The stronger claim that a universal mean shape reproduces population
infectiousness is unsupported. With nonlinear dose-response, infection
probability averaged over heterogeneous exposures need not equal infection
probability evaluated at their average. A persistent host multiplier can
represent amplitude variation but not every difference in timing or
within-person emission episodes. Zhou's reported discordance makes that
limitation material, without proving that every single-shape approximation is
unusable.

There is also an implementation expressiveness limit already visible in the
settled audit: the current pre-onset gate and index clamp cannot encode an
independent pre-onset trajectory. That is distinct from proving that an
onset-relative emission function is scientifically impossible. This entry
neither changes that representation nor declares it adequate.

## What a later curve change would re-denominate

These are consequences inferred from the dependency path, not re-measured
results. This documentation-only entry changes no numerical baseline.

| Object | Consequence of a later change |
|---|---|
| Emission and delivered dose | Redistributes source material across infection age, presence aboard, activities and recipient exposure. Equal lifetime totals would not guarantee equal delivered doses. |
| COVID transmission scale, including Θ | Earlier fitted or screened values remain conditional on the old source timing and normalization. A non-proportional timing change generally has no single scalar conversion valid across exposure histories; changing unit conventions additionally changes the dose denominator. |
| Founder/index aboard emission | Changes how much source output overlaps embarkation, contact and departure. Earlier aboard fractions, founder yield and takeoff inferences are not transferable without qualification; no direction or magnitude is established here. |
| Generation and serial intervals | Changes the temporal weighting of opportunities for secondary infection; symptom-onset intervals also depend on incubation and observation. Neither interval is identical to the emission curve. |
| Symptom-triggered isolation and testing | Changes which source output overlaps intervention and detection. An emission share is not generally the fraction of infections prevented under nonlinear response and time-varying contact. No fixed benefit follows from a transmission-derived presymptomatic percentage. |
| `shedding_curve_log10` provenance | Shape, normalization, assay units, proxy transfer and time origin require separate justification. C assumptions stay C even when grounded in a well-measured but different biological quantity. |
| Earlier COVID readouts | Remain historical results at their recorded source revision, not measurements of the replacement model. A later implementation would need corresponding provenance and ledger updates; none is performed now. |

**Disposition:** the evidence-class verdict is recorded; the requested
literature-supported numerical target shape remains unfulfilled. No curve
replacement, simulation or campaign is authorized or started by this record.
