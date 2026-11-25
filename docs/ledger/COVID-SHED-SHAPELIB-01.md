# COVID-SHED-SHAPELIB-01
**Date:** 2026-11-25
**Commit:** a5bbce80
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** a5bbce80

Implementation-ready literature shape library for the SARS-CoV-2 shedding-curve
evidence leg. The machine-readable library is
[`docs/covid/covid_shed_shape_library_01.json`](../covid/covid_shed_shape_library_01.json).
This entry is documentation/input-library data only: **no profile field,
constant, engine behaviour, simulation expected value, campaign, theta, GM, or
H5 status changes.** No fitting or selection against Diamond Princess outcomes
was performed. GM remains held out; H5 remains held out forever.

The target quantity remains the one fixed by
[COVID-SHED-EVIDENCE-01](COVID-SHED-EVIDENCE-01.md): **viable-virus-weighted
emission upstream of contact, exposure, recipient susceptibility, isolation,
and nonlinear infection probability**. The four evidence classes are kept
separate in the library. No unlike endpoints are averaged or blended.
Transmission-derived profiles are validation targets only.

## What is now numeric

| Evidence class | Families produced | Implementation status |
|---|---|---|
| Direct emitted material | `zhou2023_mask_rna_onset_aligned_zero_inflated`; `zhou2023_air_rna_onset_aligned_zero_inflated`; selected digitized individual heterogeneity references for participants 1, 5, 7, 9 and 18 | Candidate source-term evidence, with daily detection probability, conditional positive magnitude, equal-weight normalized shape, and mass-weighted high-emitter-sensitive normalized shape. Emitted RNA, not viable-virus-weighted emission. |
| Viable-virus/culture proxy | `hakki2022_pfu_unvaccinated_pre_alpha_alpha_onset_aligned` with all-symptomatic sensitivity; `killingley2022_ffa_piecewise_axis_bracket`; `woelfel2020_culture_duration_check` | Biological proxy candidate evidence. PFU/culture is not emission; the library preserves that distinction. Killingley is a bracketed piecewise family because full numeric FFA curves were not recovered. |
| RNA-kinetic sensitivity | `jones2021_rna_onset_relative_piecewise_sensitivity`; `kissler2021_rna_first_detectability_parameters` | Sensitivity evidence only. RNA persistence is not viable emission. Kissler is not onset-convertible because symptom-onset timing was not recorded. |
| Outcome-side transmission | He 2020, Ferretti 2020, Casey-Bryars 2021 and Sender 2022 targets | Validation/check targets only. They are explicitly outside the candidate source-term classes because the engine already applies downstream exposure/contact/behaviour and nonlinear dose-response. |

## Zhou 2023 direct emitted-material family

Zhou et al. 2023 human-challenge Figure 2 was digitized from the publisher's
high-resolution figure asset after direct article/supplement access escalation.
The digitization recovered **109 positive exhaled-mask samples** and **63
positive room-air samples**, exactly matching the Results counts. Using the
symptom cells digitized from the same figure, mean per-participant
pre-first-symptom log-AUC shares reproduce **9.57% mask** against the paper's
**10% (SD 26)** with **4 positive participants**, and **8.52% air** against the
paper's **9% (SD 26)** with **2 positive participants**. This is a figure
digitization validation, not access to the underlying participant dataset.

The onset axis is the first nonzero self-reported symptom-score cell digitized
from Zhou Figure 2. It is participant-specific and independent of the inoculation
clock. Participant 18 never reported symptoms and is excluded from
onset-aligned means; participant 18 remains in the library as a heterogeneity
reference. Sampling-time alignment is treated as approximately ±1 day. Negative
onset days are measured rows, not clamped to day zero.

The daily tables intentionally separate three different objects:

1. `detection_probability` — the fraction of observed onset-aligned cases with
   a positive sample that day;
2. `mean_log10_positive` — conditional magnitude among positive samples; and
3. normalized deterministic shape variants — either equal-weighted by case or
   mass-weighted across the cohort.

This separation is required because the direct emission data are strongly
zero-inflated and episodic. Two participants produced **86% of airborne viral
RNA** on three individual timepoints. The mass-weighted cohort mean is therefore
dominated by sparse high-emission bursts and does not represent a typical host;
the equal-weight mean suppresses that dominance but hides the burst structure.
Neither deterministic mean is a replacement for the zero-inflated daily model.
This is measured/digitized heterogeneity, not a hypothesis to be smoothed away.
Zhou's published AUC shares were calculated from log-transformed copy values;
the implementation shapes in the library are instead normalized after
exponentiating digitized log10 values to linear copies. Those normalization
conventions are not interchangeable, so the tabulated normalized presymptomatic
mass shares need not equal the paper's log-AUC shares.

**Measured:** plotted sample positivity and log10 E-gene RNA magnitudes;
symptom-score cells; published validation counts and presymptomatic shares.
**Inferred:** numeric heights from figure digitization, onset alignment within
about ±1 day, exponentiation from log10 to linear copies, normalization.
**Hypothesis:** any use of these curves as viable-virus-weighted emission.

## Hakki 2022 culture-proxy family

The authors' public analysis repository was recovered despite the article's
data-availability language implying request-based access. It contains
`Data/trajectories.RDS`/`trajectories.csv` and `Data/symptoms.RDS`. The public
`day` column is zero-based, while the authors' R analysis uses one-based
`which()` indices; the library therefore uses `day + 1 - contact_onset` as the
onset-relative day. That transform reproduces the paper's median onset-to-PFU
peak interval of **3 days**. The published **7/35 (20%)** presymptomatic
culture-positive fraction is recovered only when onset-day rows are included in
presymptomatic counting (`day + 1 - contact_onset <= 0`); strictly negative rows
give **5/35**. That boundary is part of the approximately ±1-day onset-axis
uncertainty and is encoded explicitly in the library. NaN PFU rows are censored
missing observations, not zeros. This is an implementation-critical indexing and
boundary check, not a refit.

The principal Hakki family is restricted to unvaccinated pre-alpha/alpha cases
with definitive onset (`n=13`) because that is the closest retrieved subset to
the ancestral COVID setting. A larger all-symptomatic sensitivity table (`n=38`,
mixed variant and vaccination composition) is included but not preferred for
Diamond Princess. Hakki remains a swab-PFU/culture shape. It is not emitted
material, and its very low presymptomatic normalized mass must not be read as
evidence against direct emitted-RNA presymptomatic mass.

**Measured:** authors' machine-readable PFU and symptom-onset data.
**Inferred:** treating `pfu <= 1` as nondetect because the authors' analysis
uses `pfu > 1`; subset selection; normalization. **Hypothesis:** transfer from
swab culture kinetics to emission.

## Killingley 2022 and Wölfel 2020 culture-proxy support

Killingley's full individual viable-virus curves were not recovered as numeric
source data. The library therefore supplies only a bracketed piecewise family:
throat/nose FFA first-quantification, approximate FFA peak positions, median
positive durations, individual duration envelope, and latest viable detection.
Because symptom onset is reported only as **2–4 days post-inoculation**, the
library provides early/central/late axis-shift variants rather than pretending
one participant-aligned onset axis exists. The `-5` log10 relative starting
floor is a declared assay-floor sensitivity, not a measured emission floor.
The piecewise tail offset explicitly borrows Hakki's infectious-virus decline
(−1.13 log10/day) over about six days; it is labelled as cross-study culture-
proxy inference, not a Killingley measured slope.

Wölfel remains a duration/tail check only: peak throat RNA on illness day 4,
no isolates after illness day 8, and a wide probit threshold interval. It is
not converted into a candidate curve.

## Jones 2021 and Kissler 2021 RNA sensitivity families

Jones supplies the only onset-relative RNA sensitivity family here: onset of
shedding to peak **4.31 days (95% CI 4.04–4.60)**, peak viral load about
**10^8.1 copies/swab**, hospitalized-case peak **1–3 days before symptom
onset**, and post-peak slope **−0.168 log10/day (95% CI −0.171 to −0.165)**.
The piecewise variants use early/central/late peak positions at onset −3, −2
and −1 days. The starting point is a declared assay-floor sensitivity at −5
log10 relative to peak, not a measured emission floor. This family is useful
for sensitivity to rapid presymptomatic RNA rise and slow RNA tail; it is not a
viable-emission source term.

Kissler supplies acute-infection proliferation/clearance parameters on a first
PCR-detectability axis: mean proliferation **3.3 d**, clearance **8.5 d**,
total acute shedding **11.7 d**, proliferation slope **+1.5 log10 copies/mL/day**,
and clearance slope **−0.6 log10 copies/mL/day**. It is not onset-aligned
because onset timing was not recorded. The library says so rather than inventing
an onset transfer.

## Implementation-state tree check

Reads were scoped to the COVID shedding ledgers/docs, the one active profile
entry, and the specific engine lines implementing shedding age. At the header
commit, `engines/infection_dynamics_bridge.py` resolves the curve array index
with `min(max(curve_index, 0), len(curve) - 1)`. Thus negative onset-relative
ages inside the declared presymptomatic window are clamped to curve entry 0 in
the active engine. This confirms the implementation-state claim carried by
[COVID-SHED-CURVE-01](COVID-SHED-CURVE-01.md); the present library does not
alter it. The active `sars_cov2_resp` profile still carries the same 15-entry
`shedding_curve_log10`, `presymptomatic_shedding_days: 2.0`, and the unchanged
release offset; `active_profiles.json` was not edited.

## Relation to COVID-SHED-INTERVALS-01

No material correction to [COVID-SHED-INTERVALS-01](COVID-SHED-INTERVALS-01.md)
is forced by the retrieval in this entry. The numeric work extends it in two
ways:

- Zhou time resolution is now digitized rather than represented only by
  aggregate presymptomatic AUC shares; and
- Hakki PFU kinetics are now computed from the authors' public machine-readable
  trajectories rather than only read as published medians/proportions.

The Hakki public data repository is a retrieval improvement, not a biological
correction. The axis transform reproduces the published values rather than
contradicting them.

## What remains blocked

1. Zhou's underlying individual participant data are access-controlled by
   written approved request/data-access agreement. Time-resolved curves are
   recovered only by figure digitization; exact nondigitized values remain
   blocked.
2. Zhou does not report a viable-only time-resolved emitted-material AUC or
   curve. Culture-positive mask swabs are visually indicated in Figure 2, but
   overlapping symbols/annotations prevented a validated automated digitization
   of those fill states. Exact time-resolved viable mask emission remains
   blocked; direct emitted evidence here is RNA emission with viability caveats.
3. No retrieved source directly measures emitted viable virus densely enough
   to report an onset-day rise slope or post-peak emission decay slope.
4. Killingley full numeric individual FFA trajectories/source data were not
   recovered; only the bracketed published timing/duration family is encoded.
5. Kissler cannot be onset-aligned from the paper because symptom-onset timing
   was not recorded.

These are blocked reads/evidence gaps, not null results and not licence to
invent curves.

## Owner decision required before implementation

The single blocking owner decision is: **choose the endpoint priority and
representation for a future source term — Zhou direct emitted RNA with explicit
zero-inflated host heterogeneity, Hakki/Killingley culture-proxy PFU kinetics,
or a declared hybrid proxy-transfer rule.** This must be decided before engine
implementation because the evidence classes are noncommensurate and may not be
silently averaged or blended.

## Sources

- Zhou et al., *The Lancet Microbe* 2023, “Viral emissions into the air and
  environment after SARS-CoV-2 human challenge”, DOI
  [10.1016/S2666-5247(23)00101-5](https://doi.org/10.1016/S2666-5247(23)00101-5).
- Hakki et al., *The Lancet Respiratory Medicine* 2022, “Onset and window of
  SARS-CoV-2 infectiousness and temporal correlation with symptom onset”,
  DOI [10.1016/S2213-2600(22)00226-0](https://doi.org/10.1016/S2213-2600(22)00226-0);
  authors' public data repository
  [SARS-CoV-2-viral-shedding-dynamics](https://github.com/HPRURespMed/SARS-CoV-2-viral-shedding-dynamics).
- Killingley et al., *Nature Medicine* 2022, “Safety, tolerability and viral
  kinetics during SARS-CoV-2 human challenge in young adults”, DOI
  [10.1038/s41591-022-01780-9](https://doi.org/10.1038/s41591-022-01780-9).
- Wölfel et al., *Nature* 2020, “Virological assessment of hospitalized
  patients with COVID-2019”, DOI
  [10.1038/s41586-020-2196-x](https://doi.org/10.1038/s41586-020-2196-x).
- Jones et al., *Science* 2021, “Estimating infectiousness throughout
  SARS-CoV-2 infection course”, DOI
  [10.1126/science.abi5273](https://doi.org/10.1126/science.abi5273).
- Kissler et al., *PLoS Biology* 2021, “Viral dynamics of acute SARS-CoV-2
  infection and applications to diagnostic and public health strategies”, DOI
  [10.1371/journal.pbio.3001333](https://doi.org/10.1371/journal.pbio.3001333);
  public posterior data in the authors' `CtTrajectories` repository.
- He et al., *Nature Medicine* 2020, DOI
  [10.1038/s41591-020-0869-5](https://doi.org/10.1038/s41591-020-0869-5), and
  Author Correction DOI
  [10.1038/s41591-020-1016-z](https://doi.org/10.1038/s41591-020-1016-z).
- Casey-Bryars et al., *BMJ Open* 2021, DOI
  [10.1136/bmjopen-2020-041240](https://doi.org/10.1136/bmjopen-2020-041240).
