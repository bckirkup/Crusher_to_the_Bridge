# Environmental observation against real limits of detection, v1

Why this change exists: the objective is not to move the attack rate. It is to
be able to state what a surface swab and a wastewater assay would read on this
ship, against the limit of detection a real assay has. That requires three
things the model does not currently have — a surface *density* for a swab to
sample, a physical wastewater stream for an assay to draw from, and an emesis
source term whose concentration is the measured one.

Nothing below was selected by comparison with VSP, A9, MIDRS or Park. Every
value carries its source, unit and evidence grade at the point of use; the two
composite limits of detection are marked as declared inferences with their input
factors enumerated, because no paper reports them for this configuration.

## 1. What is broken

- `TargetedSurfaceSwab` has a real Ct-based cut (`ct <= 38`) but its input is
  `zone_pathogen_mass x microflora.surface_fraction` — a synthetic 0.4 of the
  **airborne** pool. It never reads `surface_pools_by_pathogen`, the pool the
  fomite route actually doses from. Its `swab_area_cm2` is stored and never
  used, so there is no density, and an LOD has nothing to be expressed per.
- `WastewaterSequencingGrid` reads a further 0.1 fraction of that same synthetic
  figure and applies **no limit of detection at all**. No stool, flush or emesis
  mass reaches it: plumbing is unmodelled. Its output is a sequencing
  composition, not a concentration, so it is not the instrument a copies/L LOD
  belongs on.
- The deposited share of a vomiting event outside the high-touch footprint
  (`non_touchable`) and the non-aerosolised share of a flush are written to a
  record or dropped. They are the majority of both events' mass, and they are
  exactly the mass a cleaning stream and a holding tank would carry.

## 2. Surface density and the per-swab limit of detection

**Density denominator, no new constant.** The fomite dose route already treats a
zone's surface pool as spread over `_fomite_surface_area(zone)` — pickup goes as
`mass x hand_area / area`. The swab takes the same denominator, so the quantity
the swab measures and the quantity a host picks up are the same physical field:

```
density_copies_per_cm2 = pool_copies / (high_touch_area_m2 * 1e4)
sampled_copies         = density_copies_per_cm2 * swab_area_cm2
recovered_copies       = sampled_copies * recovery_efficiency
```

**Sampled area.** `SWAB_AREA_CM2 = 100.0` remains, now used rather than stored.
It sits inside the measured practice envelope: Park et al. 2015 sampled 161.3
cm² and 645 cm² coupons with macrofoam.

**Recovery efficiency is area- and material-dependent, and no universal nominal
is sourceable.** Recorded as an interval, swept, not a point:

| Bound | Value | Source |
|---|---|---|
| Low | 0.023 | Park et al. 2015, macrofoam at 645 cm² (2.3%); stainless-steel range 2.2–36.0%, toilet seat 1.2–33.6% |
| High | 0.80 | Lee et al. 2018, cotton/PBS and microdenier polyester/PBS >80% recovery on plastic and stainless steel |

Park et al. 2015, doi:10.1128/aem.01657-15; Lee et al. 2018,
doi:10.1007/s12560-018-9353-5. Both read as full text. The shipped nominal
`SWAB_NOMINAL_EFF = 0.35` is **not changed by this document** and is not a
reading of either paper: it is a Grade C declared value that lies inside the
sourced interval, and it becomes a declared swept axis in the provenance
register rather than a settled number.

**Limit of detection, per swab, in copies — direct, not derived.** Park et al.
2015 reports detection limits for exactly this configuration:

| Surface | LOD | Source location |
|---|---|---|
| Non-porous hard surface (stainless steel) | 10^3.5 RNA copies per swabbed surface | Park 2015, Results |
| Toilet seat | 10^4.0 RNA copies per swabbed surface | Park 2015, Results |

This is a **per-swab copy threshold**, which is what a per-area density
multiplied by a sampled area produces — no elution/reaction chain has to be
invented to reach it. Detection therefore requires recovered copies at or above
the surface's LOD *and* the existing Ct cut. Below-LOD samples keep their
quantitative value and are flagged `censored_below_lod`; a censored reading is
never written back as a physical zero.

**Grade.** Recovery interval **A** (direct measurement, same matrix and
quantity). Per-swab LOD **A** for stainless steel and toilet seat, **B** as an
analogue for other shipboard hard surfaces. Nominal recovery **C**, declared.

## 3. A blackwater holding tank, and a copies/L assay

The wastewater sequencing grid is left alone. A concentration assay is a
different instrument and gets its own one, reading a physical tank.

**The tank.** Ship-level blackwater pool holding, per pathogen, a copy count and
a volume in litres, drained as a continuously-stirred tank.

| Quantity | Value | Source | Grade |
|---|---|---|---|
| Blackwater generation | 31.8 L/person/day (8.4 gal), range 4.2–102 L (1.1–27 gal) | EPA 842-R-07-005 (2008) §2, survey of 29 Alaska cruise ships | B — direct measurement of the right vessel class, EPA cautions the rates were not independently confirmed, hence the range is swept |
| Flush volume | 1.14 L (0.3 gal) vacuum; 3.8 L (1 gal) one gravity system | same | B |
| Holding residence time | 62 h average, range 0.5–170 h | same | B |

Volume accrues as `complement x rate x day_fraction_per_epoch` and is drained at
`epoch_hours / residence_hours`, so the steady-state inventory is
`rate x residence` and the concentration does not depend on the flush count —
flush volume is recorded but not added on top of the per-capita rate, which
already contains it (0.3 gal x ~6 voids/day = 1.8 gal/person/day, inside 8.4).

**Copies in.** Two streams that are currently dropped:

- the non-aerosolised share of every flush, `10^stool_titre x FLUSH_STOOL_MASS_G
  x (1 - f_aero)` — the same bowl deposit the flush route already computes, whose
  aerosol share alone reaches the air;
- the drain share of a vomiting event's cleanup: the deposited mass outside the
  high-touch footprint. Routed at a declared fraction of 1.0 (all cleaned-up
  vomitus enters the sewage stream), Grade D declared, deliberately not a free
  parameter.

**Limit of detection, copies/L — a declared inference, factors enumerated.** No
paper reports a raw-wastewater LOD for this workflow. Alex-Sanders et al. 2023
(doi:10.1016/j.jviromet.2023.114804) reports the **assay** LOD in the eluate:
0.519 gc/µL GI and 1.369 gc/µL GII (LOQ 3.837 / 11.68). Converting that to a raw
concentration requires four declared workflow factors, and the composite is an
inference, not a reading:

```
LOD_raw = LOD_eluate (gc/uL) * elution_volume (uL)
          / (sample_volume (L) * concentration_recovery)
        = 1.369 * 100 / (0.1 * 0.25)
        = 5.5e3 copies/L  (3.74 log10)
```

with sample volume 0.1 L, elution 100 µL and concentration recovery 0.25, each
declared Grade C and each a swept axis. Reported as
`lod_copies_per_litre` alongside the quantitative concentration; below-LOD
samples are flagged, never zeroed. Inhibition up to ~32% (same paper) is
recorded at the constant, not applied as a hidden multiplier.

**Two independent checks the derivation was not fitted to.** Measured raw
municipal sewage runs 5.2–7.9 log10 copies/L (Jahne et al. 2020,
doi:10.1016/j.watres.2019.115213; Fumian et al. 2019,
doi:10.1016/j.envint.2018.11.054, GII median ~6.4 log10) — comfortably above a
3.74 log10 LOD, matching those studies' near-total quantifiability. And a
one-shedder ship: 1e11 copies/g stool x 107 g into 500 x 31.8 L/day gives ~8.8
log10 copies/L at the day's inflow, against ~7.8 log10 for the same shedder
diluted into a municipality's 300 L/person/day at the same 1/500 prevalence.
Same order, from opposite directions. Ahmed et al. 2020
(doi:10.1093/jtm/taaa116) and 2023 (doi:10.1016/j.scitotenv.2023.165007) find
transport-vessel wastewater sits *near* the LOD with infrequent GII detection,
which is the regime a small complement and a short residence time put this tank
in — so the model should produce marginal detections on a quiet ship, and that
is a prediction to check rather than a target to hit.

**Implementation state (this section now exists).**
`engines/wastewater_plumbing.py` carries the constants above and
`BlackwaterHoldingTank`, the CSTR pool: `complement × l_per_person_day ×
day_fraction_per_epoch` of inflow per epoch, then discharge at
`min(1, epoch_hours / residence_hours)` applied to volume and per-pathogen
copies alike. `transmission.blackwater_plumbing` (default `false`; `true`
for the EPA nominals, or a dict overriding the three ctor kwargs) builds
the tank on `TransmissionCore` and routes the two copy streams: the bowl
deposit's non-aerosolised share `bowl × (1 − f_aero)` for every resolved
defecation venue — independent of `flush_aerosol_fraction`, including the
cabin-compartment venue — and each emesis event's `non_touchable ×
emesis_drain_capture_fraction`. The tank discharges at the same epoch
boundary where `drain_emesis_aerosol`/`drain_flush_aerosol` run, so the
assay reads the post-discharge state. `WastewaterHoldingTankAssay`
(`crusher_labs/observation_core.py`, `observation.wastewater_assay_mode:
holding_tank`, default `none`) applies the composite LOD above and records
`observation_engine.wastewater_holding_tank` each epoch. v1 limitations,
declared: the assay is not routed through the `InstrumentTurnaroundQueue`
(no declared TAT entry); no decay is applied over the holding time; the
graywater sequencing grid is untouched; and the emesis capture reaches only
the `non_touchable` cleanup share — the touchable footprint still feeds the
fomite pool only. Unresolved cross-check, deliberately not reconciled:
EPA's 8.4 gal/person/day average embeds far more than the mechanistic
0.3 gal × ~6 voids ≈ 1.8 gal that `FLUSH_VOLUME_L` implies.

## 4. The emesis source term

Derived separately and in full against Kirby et al. 2016 (doi:10.1371/journal.
pone.0143759, Tables 1–3 and Results from the Europe PMC JATS XML). Summary of
what changes and why, since the concentration it produces is the quantity both
observers turn on:

- the shipped interval's ceiling (1e8 GEC) sits **below** the paper's own
  per-subject cumulative shed (1.8e8 overall, 2.3e8 All GI, 3.1e8 study 2);
- equal partition of a count-independent total makes per-episode load fall as
  1/K, inverting Kirby Fig 1 ("Subjects With More Vomiting Events Have Higher
  Cumulative Virus Titers");
- the episode count is drawn uniform on 1–7 where the measurement is mode-1 with
  32% of subjects vomiting once.

Replacement structure: **per-episode volume x per-episode titre x per-episode
positivity**, which is Kirby's own arithmetic (titre x volume summed over
positive samples) run generatively. Checked against the paper's numbers per
genogroup, it reproduces the measured per-subject cumulative shed inside its own
standard errors — All GI 4.1e8 predicted vs 2.3e8 (SEM 1.0e8), GII.2 5.1e7 vs
1.8e7 (SEM 1.8e7) — so the per-subject total stops being a fitted input and
becomes a validated output. Positivity is not cosmetic: Ge et al. 2023
(doi:10.3201/eid2907.230117) states the challenge assays' own LODs (1.5e4 GEC/g
immunomagnetic-capture RT-PCR, 4.0e7 GEC/g qRT-PCR), so a "negative" emesis
sample is a censored interval, not a zero — the same censoring the two observers
need.

`EMESIS_AEROSOL_FRACTION_RANGE = (7.2e-7, 2.67e-4)` is **verified and
unchanged**: Tung-Thompson et al. 2015 Table 2 is a percent column and the
shipped range is that percent converted. Two definitional qualifications are
recorded at the constant rather than adjusted for — the fraction is *recovered*
MS2 in a Biosampler (a lower bound) and it is PFU of a surrogate phage applied
to a GEC load. Both point the same way: the shipped interval is conservative.
It is not narrowed, and no decade of it is selected.

## 5. Sequencing and default state

The surface swab's rewiring changes an observation the decision layer reads, so
it ships behind `observation.surface_swab_source` with the legacy
airborne-fraction path as the default, and is measured as a matched arm before
any default flips. The holding tank and its assay are **additive** and ship
behind `transmission.blackwater_plumbing` (default `false`) and
`observation.wastewater_assay_mode` (default `none`): they read mass that was
dropped on the floor and remove nothing from any existing pool, so no dose and
no golden moves — which is also why a null in the infection outcome would say
nothing about whether they are right.
