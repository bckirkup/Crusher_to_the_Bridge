# Emesis deposition: the concentrated mechanism the fomite chain is missing

Authored specification. Every quantity below is taken from a measurement in the
literature. Nothing here is fitted to VSP, to the passenger:crew ratio of 2.9,
or to Park et al. In particular §6 states what the model is expected to predict
*after* this change so the comparison is made against a number written down
beforehand.

## 0. Why this exists

`park_surface_findings.md` recorded a split verdict on the rebuilt fomite chain
(PR #351). Absolute surface contamination landed inside Park et al.'s observed
cruise-ship range in both cabins and public spaces. The *gradient* did not:

| Quantity | Model | Park et al. 2015 |
|---|---:|---:|
| Cabin/public surface concentration ratio | 4.0x | roughly 100-300x |

The finding recorded there was that no occupancy assumption can close this — a
cabin would need ~75x more shedder-hours than a lounge — and that the missing
mechanism is therefore not a bigger version of hand-to-surface transfer but a
*different, concentrated, localised* deposition event. It named vomiting as the
hypothesis and explicitly refused to tune a term to fit.

This document supplies that mechanism with measured numbers.

## 1. What the model currently does with vomiting

Nothing. `"vomiting"` appears in `clinical_presentation.phases[0].features` for
`norwalk_gi` as a descriptive clinical string consumed by the syndromic
modality. It has no effect on emission, deposition, or any environmental pool.

All norovirus environmental release in the model is continuous faecal release:
`environmental_faecal_release_log10_g_per_epoch` (the honest name for the old
`dose_adjustment`), spread across routes by `transmission_route_weights`. That
is a smooth per-epoch trickle. It cannot produce a localised spike, and a
localised spike is what Park measured.

## 2. Measured quantities

| Quantity | Value | Type | Source |
|---|---|---|---|
| Norovirus titre in vomitus, GII | 3.9e4 GEC/mL (mean) | Measured, human challenge | Kirby et al. 2016 |
| Norovirus titre in vomitus, GI | 8.0e5 GEC/mL (mean) | Measured, human challenge | Kirby et al. 2016 |
| Median titre, Norwalk | 4.1e4 GEq/mL | Measured, human challenge | Atmar et al. 2014 |
| Emesis volume per episode | 50-800 mL | **Estimate** (expert opinion; ipecacuanha-induced emesis in non-norovirus patients) | Tung-Thompson et al. 2015; Booth & Frost 2019 |
| Total vomitus shedding per illness | 6.4e5 - 3.0e7 GEC | Measured, dose-escalation challenge | Ge et al. 2023 |
| Cumulative shedding per subject, all episodes | 1.8e8 GEC | Measured | Kirby et al. 2016 |
| Surface deposition area per episode | >= 7.8 m^2 (forward >3 m, lateral 2.6 m) | Measured, simulated emesis ("Vomiting Larry") | Booth 2014; Booth & Frost 2019 |
| Aerosolised fraction of expelled virus | 7.2e-7 to 2.67e-4 | Measured, surrogate (MS2) | Tung-Thompson et al. 2015 |
| Airborne NoV after vomiting | 5-215 copies/m^3 | Measured, outbreak | Alsved et al. 2019; Bonifait et al. 2015 |

The profile's genotypes are GII.4/GII.17/GII.2 (see the `incubation.notes`
field, which already resolves this same GI/GII mismatch in the pathogen_id).
**Use the GII titre, 3.9e4 GEC/mL.** Using the GI figure would be a 20x
overstatement of the mechanism this document is arguing for, which is precisely
the direction we must not err in.

## 3. Two independent measurements agree on episode count

The per-episode quantity (volume x titre) and the per-illness total are measured
by different groups using different methods, and they can be cross-checked.

Per episode, from Kirby's titre and the volume estimate:

```text
50 mL  x 3.9e4 GEC/mL = 2.0e6 GEC
800 mL x 3.9e4 GEC/mL = 3.1e7 GEC
```

Per illness, measured directly by Ge et al.:

```text
6.4e5 - 3.0e7 GEC
```

The per-episode range and the per-illness range overlap almost exactly. A
symptomatic norovirus illness therefore involves **order 1-3 vomiting
episodes**, and this is a consequence of two measurements rather than an
assumption. Kirby's observation that single-episode subjects never had
detectable virus while 57% of multi-episode subjects did is consistent with the
low end being at or below detection.

**Specified:** number of episodes per symptomatic illness ~ DiscreteUniform{1,2,3}.
Evidence grade C (inferred from the intersection of two Grade B measurements,
not directly counted).

**Required cross-check in the implementation's test suite:** the expected total
emitted per illness must fall inside Ge et al.'s measured 6.4e5-3.0e7 GEC. At
2 episodes x median volume, `2 x 200 mL x 3.9e4 = 1.6e7 GEC`, which does. If a
future parameter edit pushes it outside that interval the test must fail.

## 4. What the model must not do with this

- **The emesis load must not pass through `environmental_faecal_release_log10_g_per_epoch`.**
  It is an independently measured absolute count of genome copies. Routing it
  through the one fitted parameter in the model would destroy the only property
  that makes it worth having.
- **The emesis load must not be scaled by `host_shedding_multiplier` or
  `shedding_variance_log10`.** Ge et al.'s 6.4e5-3.0e7 range *is* inter-host
  variation, measured. Applying our lognormal heterogeneity on top would count
  the same dispersion twice.
- **No parameter here may be adjusted toward Park's gradient, toward 2.9, or
  toward any VSP attack rate.** §6 fixes the prediction in advance.

## 5. Specification

### 5.1 Eligibility

A host emits an emesis event in an epoch only if all hold:

1. it is infected with the pathogen and `IllnessStatus.SYMPTOMATIC`;
2. the pathogen profile lists `"vomiting"` among the features of the clinical
   phase covering the host's current days-since-onset.

Condition (2) reuses the existing `clinical_presentation.phases` data rather
than adding a new invented severity vector. For `norwalk_gi` this makes the
acute phase (dpi 0-2) emetic and the resolving phase not, which matches the
profile as already written.

### 5.2 Event timing

Episodes are drawn once per illness, at the transition into symptomatic status,
as a count `E ~ DiscreteUniform{1,2,3}` and are then scheduled uniformly at
random over the emetic window. Drawing the schedule once per illness rather
than sampling a per-epoch hazard keeps the total conserved and keeps the result
independent of epoch size, which the timestep-invariance guards require.

### 5.3 Emitted load per episode

```text
volume_mL      ~ LogUniform(50, 800)
titre_per_mL   = EMESIS_TITRE_GEC_PER_ML          # 3.9e4, GII, Kirby 2016
episode_load   = volume_mL * titre_per_mL          # genome copies
```

Log-uniform rather than uniform because the range spans more than an order of
magnitude and the underlying quantity is a positive scale variable; a uniform
draw would put the mass at the top of a range whose upper bound is itself an
estimate.

### 5.4 Partition of the emitted load

```text
aerosol_fraction ~ LogUniform(7.2e-7, 2.67e-4)     # Tung-Thompson 2015
surface_load     = episode_load * (1 - aerosol_fraction)
aerosol_load     = episode_load * aerosol_fraction
```

`aerosol_load` is **deferred and not implemented in this change** — see §7. It
is below 0.03% of the episode by measurement, so omitting it cannot inflate the
mechanism, and the airborne route is already the model's dominant and
most-suspect pathway. Compute it, record it in the deposition record for the
route ledger, and route nothing to the airborne reservoir yet.

### 5.5 Geometry: what reaches touchable surface

Booth measured deposition over >= 7.8 m^2. Our fomite pool is a *high-touch*
surface pool with a much smaller area (`HIGH_TOUCH_AREA_M2`, 1.5 m^2 in a
cabin). Emesis lands mostly on floors and large surfaces, and only the part
intersecting touchable surface can enter the hand chain.

```text
EMESIS_DEPOSITION_AREA_M2 = 7.8
touchable_fraction = min(1.0, high_touch_area_m2 / EMESIS_DEPOSITION_AREA_M2)
pool_gain = surface_load * touchable_fraction
```

This assumes the deposit is spread uniformly over its footprint and that
high-touch surface is distributed within that footprint in proportion to its
area. That is a **declared geometric assumption, Grade C**, and it is
deliberately the conservative choice: it discards 81% of the deposit in a
cabin. Do not remove it to make a number larger.

The remainder (`surface_load - pool_gain`) is deposited on non-touchable
surface. It is not tracked; record it in the deposition record so the
conservation test can assert that the parts sum to `episode_load`.

### 5.6 Destination

`pool_gain` is added to the surface pool of the zone the host occupies at that
epoch, through the same accounting the fomite pathway already uses
(`surface_pools_by_pathogen`, the strain reservoir, and the strain composition
ledger). It is then picked up by the existing, unmodified fomite pathway and
receives the `fomite` route weight exactly once, in `_apply_route_weights`, as
everything else does. **Add no new route and no second weighting.**

A confined host emits into its cabin. Confinement attenuation
(`confinement_emission_attenuation`, PR #340) applies to continuous faecal
release, not to vomiting: a confined host still vomits the same amount, it
simply does so in its cabin. Do **not** apply the attenuation to this term, and
add a test that asserts it is not applied.

## 6. Prediction, written down before it is measured

After implementation, `park_surface_check.py` must be re-run unchanged except
for the added emesis term. Predicted, from the constants above:

At the Ge et al. upper total (3.0e7 GEC per illness), in a cabin:

```text
3.0e7 * (1.5 / 7.8) / 1.5 m^2 * 0.0645 m^2  =  2.5e5 copies per swab
```

At the Ge et al. lower total (6.4e5 GEC):

```text
6.4e5 * (1.5 / 7.8) / 1.5 m^2 * 0.0645 m^2  =  5.3e3 copies per swab
```

Park's reported cabin values are 80-31,217 copies per swab at a stated recovery
of 1.2-36%, so the surface loads implied by Park's measurements are roughly
2.2e2 to 2.6e6 copies per swab area. The predicted interval 5.3e3-2.5e5 sits
inside that, and the hand-chain-only prediction of 1,434 sits near its bottom.

**The claim to test is the gradient, not the level.** Public spaces receive
emesis only at whatever rate people vomit in them, which is far below the rate
in the cabin of a confined sick passenger. The predicted cabin/public ratio
should therefore move from 4.0x into the 10^2-10^3 band. If it lands inside
Park's 100-300x that is a genuine out-of-sample success for a mechanism no part
of which was fitted to Park. If it overshoots by an order of magnitude, that is
information about the episode count or the geometry, and it must be reported as
a miss and **not** corrected by adjusting these constants.

## 7. Explicitly out of scope

- The aerosol fraction's onward transport (§5.4). Computed and recorded, not
  routed.
- Faecal deposition from diarrhoea, and toilet-flush aerosol. Both are real and
  both are localised; neither is specified here.
- The food pathway, unchanged since before PR #351.
- Cleaning and disinfection of surface pools. The model has surface decay
  (`surface_decay_per_day`, 0.25/day for norovirus) but no cleaning events at
  all. Routine cleaning is 1-2 log10 per event and outbreak hypochlorite 4-5
  log10 (Tuladhar et al. 2012; Reynolds et al. 2021; Spitzer et al. 2025, the
  last being the only field hospitality measurement, at 1.57 log10). This is a
  separate change and is the natural lever for the post-COVID NPI
  discontinuity.
- The shared-surface contact rates `PUBLIC_SURFACE_CONTACTS_PER_HOUR = 6.0` and
  `CABIN_SURFACE_CONTACTS_PER_HOUR = 2.0`, declared Grade C in PR #351, are now
  known to be low by 4-10x against behavioural-observation measurements (hotel
  lobby 21/h, restaurant diners 42.8/h on shared surfaces, airport manual
  check-in 55.8/h, dormitory primary surfaces 10.4-25.4/h; Ackerley et al. 2023,
  Jin et al. 2022, Zhuang et al. 2023, Yuan et al. 2024). Correcting them is a
  separate change, kept separate so that its effect on route share is
  measurable independently of this one.

## 8. A gap that is the field's, not ours

`HIGH_TOUCH_AREA_M2` was declared Grade C in PR #351 for want of a source. A
20-paper review confirms that **no study has ever measured the total area of
high-touch surface per room in square metres** for hotel rooms, cruise cabins,
lounges, or dining rooms. Touch counts exist in abundance; the denominator they
would be normalised against does not exist. The table stays a declared
assumption permanently, and that should be recorded rather than quietly carried.

## 9. Sources

- Alsved, M. et al. (2019). Sources of Airborne Norovirus in Hospital Outbreaks. *Clinical Infectious Diseases* 70, 2023-2028.
- Atmar, R. et al. (2014). Determination of the 50% human infectious dose for Norwalk virus. *J Infect Dis* 209(7), 1016-22.
- Bonifait, L. et al. (2015). Detection and quantification of airborne norovirus during outbreaks in healthcare facilities. *Clin Infect Dis* 61(3), 299-304.
- Booth, M. C. (2014). Vomiting Larry: a simulated vomiting system for assessing environmental contamination from projectile vomiting related to norovirus infection. *J Infection Prevention* 15, 176-180.
- Booth, M. C. & Frost, G. (2019). Potential distribution of viable norovirus after simulated vomiting. *J Hospital Infection* 102(3), 304-310.
- Ge, Y. et al. (2023). Effect of Norovirus Inoculum Dose on Virus Kinetics, Shedding, and Symptoms. *Emerging Infectious Diseases* 29, 1349-1356.
- Kirby, A., Streby, A. & Moe, C. (2016). Vomiting as a Symptom and Transmission Risk in Norovirus Illness: Evidence from Human Challenge Studies. *PLoS ONE* 11.
- Tung-Thompson, G. et al. (2015). Aerosolization of a Human Norovirus Surrogate, Bacteriophage MS2, during Simulated Vomiting. *PLoS ONE* 10.
- Park, G. W. et al. (2015). Emergence of norovirus surface contamination on cruise ships (surface swab survey used as the out-of-sample check).
