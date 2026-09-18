# The emesis source term, sourced against Kirby 2016 and Tung-Thompson 2015

**Status: implemented.** Audit for the environmental-observation objective:
surface and wastewater sampling against realistic limits of detection.
Nothing below was selected by comparison with VSP, A9, MIDRS or Park.

Primary sources, both read as open-access full text from Europe PMC rather
than from an abstract:

- Kirby AE, Streby A, Moe CL. *Vomiting as a Symptom and Transmission Risk in
  Norovirus Illness: Evidence from Human Challenge Studies.* PLoS ONE 2016;
  11(4):e0143759. doi:10.1371/journal.pone.0143759. PMC4845978.
  Tables 1–3 and Results transcribed from the JATS XML.
- Tung-Thompson G, Libera DA, Koch KL, de los Reyes FL, Jaykus L-A.
  *Aerosolization of a Human Norovirus Surrogate, Bacteriophage MS2, during
  Simulated Vomiting.* PLoS ONE 2015; 10(8):e0134277.
  doi:10.1371/journal.pone.0134277. PMC4545942. Tables 1–2 and Results
  transcribed from the JATS XML.

## 1. What Kirby Table 3 actually measures

Verbatim from Table 3 (`Subject Mean Cumulative Shed (GEC) (SEM)`), with the
per-sample titre column beside it:

| Study | Strain | n subj | n samples | % subj ≥1 positive | % positive samples | Sample mean titre, GEC/mL (SEM) | Subject mean cumulative shed, GEC (SEM) |
|---|---|---|---|---|---|---|---|
| 1 | GI.1 Norwalk | 6 | 16 | 50% | 63% | 5.8e5 (2.6e5) | **1.3e8** (9.1e7) |
| 2 | GI.1 Norwalk | 8 | 20 | 75% | 90% | 9.2e5 (3.1e5) | **3.1e8** (1.7e8) |
| All GI | GI.1 | 14 | 36 | 64% | 78% | 8.0e5 (2.2e5) | **2.3e8** (1.0e8) |
| 3 | GII.2 Snow Mountain | 4 (2 excluded, missing samples) | 8 | 25% | 38% | 1.6e5 (4.5e4) | **1.8e7** (1.8e7) |
| 4 | GII.1 Hawaii | 2 (1 excluded, missing volume) | 13 | 100% | 92% | 5.0e3 (2.7e3) | **2.3e5** (ND) |

Results text, verbatim: *"cumulative shedding was calculated by multiplying
the sample virus titer by the sample volume in ml and summing the resulting
value across all positive samples for a subject. Overall, the cumulative
virus shedding per subject was high (**1.8x10⁸ GEC ± 7.8x10⁷**, Norwalk and
Snow Mountain viruses only)."*

Table 2, volume and count: per-subject total emesis volume **658.7 mL** (All
GI, SEM 111.9) and **845.0 mL** (GII.2, SEM 226.7); events per subject
**1–7, mode 1**, and *"32% of subjects only vomiting once."* Weight was used
as a proxy for volume, 1 g = 1 mL.

Two further measured facts that the model did not represent:

- *"Of the subjects who only vomited once, none had detectable virus in
  their emesis sample."* Fig 1 caption: seven subjects vomited once, all
  negative; two vomited twice, both negative.
- Fig 1's title is the finding: *"Subjects With More Vomiting Events Have
  Higher Cumulative Virus Titers."*

## 2. Three compounding defects in the shipped source term

`EMESIS_TOTAL_SHED_GEC_RANGE = (1e5, 1e8)`, log-uniform, drawn once per
illness and partitioned **equally** over an episode count drawn uniform on
1–7.

**(a) The interval's ceiling excluded the paper's own measured means.** 1e8
sat below the overall per-subject cumulative shed (1.8e8), below All GI
(2.3e8) and below study 2 (3.1e8). No draw from the shipped interval could
produce an average GI subject. The interval's arithmetic mean, 1.45e7, was
set to reproduce **one cell** of Table 3 — study 3, GII.2, n=4 after two
exclusions, **SEM equal to the mean**, i.e. a cell whose 95% interval
includes zero and spans more than a decade. That is the weakest number in
the table, and it is also the lowest.

**(b) Equal partition inverts Kirby Fig 1.** Dividing a count-independent
total by the episode count makes per-episode load fall as 1/K: a 7-episode
host emits one seventh per event of a 1-episode host. Measured: cumulative
shed *rises* with event count, and every 1-event subject was negative. The
model's lowest-emitting events belonged to its sickest hosts.

**(c) The episode count is uniform where the measurement is mode-1
skewed.** `rng.integers(1, 8)` put 14.3% of subjects at one event against a
measured 32%, and had mean 4. Under (b) an inflated count divided the total
further.

**Compounded effect on the quantity observation depends on** — the genome
concentration of the deposit:

| | GEC/mL |
|---|---|
| Model, per-episode load 1.45e7/4 in the drawn volume geometric mean 200 mL | **1.8e4** |
| Measured, cumulative ÷ total volume, All GI (2.3e8 / 658.7 mL) | 3.5e5 |
| Measured, cumulative ÷ total volume, overall (1.8e8 / ~700 mL) | 2.6e5 |
| Measured, cumulative ÷ total volume, GII.2 (1.8e7 / 845 mL) | 2.1e4 |
| Measured, per-sample mean titre of **positive** samples, GII.2 / All GI | 1.6e5 / 8.0e5 |

The model's vomitus was **10–40× more dilute** than measured for anything
but the n=4 GII.2 cell. A swab or a wastewater sample reading it sits one to
one and a half decades low against a real assay's LOD — precisely the
comparison the environmental-observation work exists for.

## 3. The aerosol fraction is correct, and the deposition partition is supported

`EMESIS_AEROSOL_FRACTION_RANGE = (7.2e-7, 2.67e-4)` — **verified, no
change.** Tung-Thompson Table 2 is headed `% Aerosolized`, with a companion
`Log % Aerosolized` column that logs the tabulated number (2.8e-3 → −2.58,
2.7e-2 → −1.72), and the Results text reads *"as a percent of total virus
'vomited' ranged from a low of 7.2 x 10⁻⁵ ... to a high of 2.67 x 10⁻²."*
The shipped range is those percentages converted to fractions. The
per-treatment span is real (pressure 115 → 1,283 mmHg, viscosity, simulated
coughing), so the interval is a condition span, not an uncertainty to be
collapsed.

Two definitional qualifications recorded at the constant rather than
adjusted:

- The fraction is **recovered** MS2 in an SKC Biosampler, so it is a lower
  bound on the aerosolised fraction, not the fraction itself.
- It is **PFU** of a surrogate phage. Applying a PFU-based fraction to a GEC
  load assumes genome and plaque aerosolise in the same proportion; any
  infectivity loss during aerosolisation or sampling makes the true GEC
  fraction higher. Both qualifications point the same way — the shipped
  interval is conservative.

The deposition partition `surface_load = load × (1 − f_aero)` gains direct
support from the same Results text: *"After each vomiting episode, virtually
all of the vomitus solution was deposited at the bottom of the chamber."*

## 4. What the source term is instead — the adopted structure

Kirby's own arithmetic is titre × volume summed over **positive** samples.
Titre is a host property (Table 3 reports per-subject positives-only sample
means); volume varies per episode. Implemented:

**Per illness, drawn once in `draw_emesis_schedule`:**

- **Episode count K** on 1..7 from a truncated geometric,
  `P(K=k) ∝ q^(k−1)`, with `q` solved by bisection from the measured
  single-episode fraction `(1−q)/(1−q⁷) = 0.32`, giving q ≈ 0.708 and
  E[K] ≈ 2.75. The measured input is the 0.32 (`EMESIS_SINGLE_EPISODE_FRACTION`,
  Grade B, Kirby Table 2); q is derived from it — no free shape knob.
- **Host detectability**: a host with `K < EMESIS_DETECTABLE_MIN_EPISODES`
  (= 3) is below the assay LOD, read directly off Fig 1 — of the subjects
  who vomited once (7) or twice (2), every one was virus-negative; every
  subject with ≥3 events was positive. Below-LOD is a censored interval,
  not zero.
- **Host titre**, drawn log-uniform once per illness:
  - detectable: `EMESIS_TITRE_GEC_PER_ML_RANGE = (1.6e5, 8.0e5)` — Kirby
    Table 3 positives-only sample means, GII.2 1.6e5 to All GI 8.0e5,
    declared as genotype uncertainty spanning the two strains the paper's
    Results decline to distinguish (p = 0.36); the 2-subject GII.1 Hawaii
    pilot is excluded from this span exactly as the paper excludes it from
    every genogroup comparison. Grade B, surrogate genotype (no GII.4
    emesis measurement exists).
  - censored: `EMESIS_CENSORED_TITRE_GEC_PER_ML_RANGE = (5.0e3, 1.5e4)` —
    upper bound is Ge et al. 2023's stated challenge-study assay LOD,
    1.5e4 GEC/g by immunomagnetic-capture RT-PCR
    (doi:10.3201/eid2907.230117), with Kirby's 1 g = 1 mL proxy; lower
    bound is the lowest emesis titre the literature measures at all, the
    Hawaii pilot's 5.0e3 GEC/mL. Grade C declared inference, bounded by two
    measured numbers. The Hawaii pilot is excluded from the detectable
    span above but anchors this floor — "lowest titre ever measured" is a
    different claim than "genogroup-typical titre", and the two are
    consistent.
- The titre is stored per pathogen on the agent
  (`emesis_titre_gec_per_ml_by_pathogen`) with the censoring flag
  (`emesis_censored_below_lod_by_pathogen`).

**Per episode, at emission time in `_emit_emesis`:** volume log-uniform on
`EMESIS_VOLUME_ML_RANGE = (50.0, 800.0)` (unchanged);
`episode_load = volume_ml × host_titre`; the aerosol/deposited split and
`pool_gain`/`non_touchable` arithmetic are unchanged, including the
blackwater-tank credit. `titre_gec_per_ml` on the record is now the input,
not a derived diagnostic, and each record carries `censored_below_lod`.
`EMESIS_TOTAL_SHED_GEC_RANGE` is retired entirely — no fallback, because a
fallback keeps the equal-partition defect reachable; the no-draw fallback
for harnesses that write a schedule directly is the log-uniform mean of the
detectable titre interval and consumes no RNG.

**The validation checks this reproduces** (recorded, not fitted): with
E[volume] = (800−50)/ln(16) ≈ 270 mL and E[K] ≈ 2.75, per-subject total
volume ≈ 738 mL against measured 658.7 mL (SEM 111.9, All GI) and 845.0 mL
(SEM 226.7, GII.2) — inside both SEMs; simulated ≈ 730 mL. With
P(K≥3) ≈ 0.453, E[K|K≥3] ≈ 4.35 and mean detectable titre 3.98e5, the
per-subject cumulative shed averaged over all subjects (censored ones
contribute their below-LOD mass) is ≈ 2.1e8 against Kirby's measured
overall 1.8e8 ± 7.8e7 and All GI 2.3e8 ± 1.0e8 — simulated ≈ 2.0e8, within
one SEM of both, with no fitted total. The per-subject total is a validated
output, and Fig 1's relation holds by construction instead of being
inverted.

**Declared limitations:**

- Titre is host-level; no within-subject titre variation is represented.
- The detectability threshold is a step at K = 3 read off Fig 1's n ≈ 22;
  the alternative — episode-level positivity — is not modelled.
- % positive samples (78% GI) and % subjects positive (64% GI) cannot both
  be reproduced by independent per-episode draws; that is itself evidence
  positivity is a host property, which is why the censoring sits at the
  illness level.

## 5. The finding that matters more than the source term

Neither observation channel reads the pool emesis deposits into — recorded
at audit time:

- `TargetedSurfaceSwab` was wired with a real Ct-based LOD but read
  `zone_pathogen_mass × microflora.surface_fraction` — a synthetic 0.4 of
  the **airborne** pool — never `surface_pools`.
- `WastewaterSequencingGrid` read `zone_surface × greywater_fraction` with
  no limit of detection at all; no excreta mass reached it.
- `non_touchable` — the deposited share outside the high-touch footprint —
  was written to the per-event record and read by nothing.

Slices 1 and 2 of the environmental-observability work (shipped behind
`observation.surface_swab_source: surface_pool_density` and
`transmission.blackwater_plumbing` + `observation.wastewater_assay_mode`)
now route the real deposited mass to a swab with a per-cm² LOD and to a
blackwater holding tank with a copies/L assay — see
`environmental_observation_v1.md`. This slice is what those observers read.
