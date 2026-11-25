# COVID-SHED-CURVE-01
**Date:** 2026-11-24
**Commit:** 5e9365fe
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 5e9365fe

Is the shape of the `sars_cov2_resp` shedding curve — presymptomatic window,
rise, peak position relative to symptom onset, post-peak decay, total period —
supported by the literature the profile cites or should cite? Audit only:
**no curve, profile field or constant is changed by this entry.**

**Verdict: the curve is unsupported by its own citation (He et al. 2020) in
its presymptomatic and onset-to-peak segments, contested in its peak position,
and supported only in its total period. This is a structural finding that
affects every COVID arm**, because every arm emits through this one array.

| Segment | Verdict |
|---|---|
| A. Presymptomatic window — duration (2.0 d) | **partially supported** (citation stale) |
| A. Presymptomatic window — level (10⁻⁶ of peak) | **unsupported** |
| B. Onset-to-peak rise (10⁻⁶ at onset, ×100/day) | **unsupported** |
| C. Peak position (onset +4 d) | **partially supported** (viral-load evidence for, the cited transmission evidence against) |
| D. Post-peak decay | **partially supported** (direction yes, rate no) |
| E. Total period (15 d; ~5 d effective) | **supported** |

Settled input, not re-derived: `COVID-INDEX-CLOCK-01` (PR #1421, open at the
time of writing, not yet on `main`) — the clock is honest; the presymptomatic
window emits `shedding_curve_log10[0]`.

## 1. Authored and assembled curve (measured)

`data/pathogens/active_profiles.json`, `sars_cov2_resp`:
`shedding_curve_log10 = [3.0, 5.0, 7.0, 8.5, 9.0, 8.5, 7.5, 6.5, 5.5, 4.5,
3.5, 3.0, 2.5, 2.0, 2.0]`; `asymptomatic_shedding_log10` identical;
`presymptomatic_shedding_days` 2.0; `shedding_duration_days` 15;
incubation median 5.8 d. `environmental_release_log10_per_day` (1.93) and the
host/strain multipliers scale level, not shape.

The engine (`KorkinAgent._shedding_curve_point`, `_shedding_age` in
`engines/infection_dynamics_bridge.py`) emits nothing earlier than 2.0 d
before onset, clamps negative day indices to entry 0, and then reads one
entry per whole day since onset. Assembled curve, relative to peak, from
`python3 tools/diag/covid_shed_curve_shape.py` (reads the profile only; daily
sums, one emitter, no multipliers):

| Day since onset | −2 | −1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11–14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| log10 relative emission | −6 | −6 | −6 | −4 | −2 | −0.5 | **0** | −0.5 | −1.5 | −2.5 | −3.5 | −4.5 | −5.5 | −6 … −7 |
| Share of total emission | 6.0e-7 | 6.0e-7 | 6.0e-7 | 6.0e-5 | 6.0e-3 | 0.19 | **0.60** | 0.19 | 0.019 | 1.9e-3 | 1.9e-4 | 1.9e-5 | 1.9e-6 | <1e-6 |

Derived: share before onset **1.2e-6**; share on onset day and the next
6.0e-5; share before onset +2 d (when the DP index leaves) **6.1e-5**; share in
the first 7 d after onset 0.998; share after day 9 2.8e-6; days within 1 / 2
log10 of peak 3 / 5; mean rise onset→peak 1.5 log10/day (2.0 for the first two
steps, i.e. the ×100/day ramp); mean decay peak→end −0.70 log10/day, steepest
−1.0 log10/day (days 5–10).

## 2. Audit table

Grades per `.agents/skills/model-parameter-provenance/SKILL.md` (no source here
is a ship measurement, so nothing is A). Origin codes: R Results, Ab abstract
only, Sec secondary, F·leg figure legend, `?nr` not retrieved. All retrieval
was through the Consensus index with full-text excerpts; "Ab" means the number
was seen only in the abstract or summary.

| # | Quantity (unit) | Authored / assembled | Literature | Declared interval | Grade · Origin |
|---|---|---|---|---|---|
| A1 | Start of infectiousness (d before onset) | 2.0, citing "approximately 2.3 d" | He 2020 **corrected**: 12.3 (95% CI 5.9–17.0); the 2.3 (0.8–3.0) figure is the pre-correction value | not declarable as a start time; use A2 | C (fitted to 77 pairs) · R, Author Correction |
| A2 | Share of transmission earlier than 3 d before onset | 0 (gated out) | He 2020 corrected: 9%; 1% before −5 d; <0.1% before −7 d | [0.01, 0.09] lost to a 2–3 d window | C · R |
| A3 | Presymptomatic share (fraction of total) | **1.2e-6** of emission | He 2020: 0.44 (0.30–0.57) of transmission; 0.37–0.48 in sensitivity runs. Ferretti 2020: 0.41 (0.31–0.50) strictly presymptomatic, plus 0.35 (0.26–0.45) on onset day or the next. Casey-Bryars 2021: 0.459 (0.429–0.490) to 0.691 (0.662–0.719) across contexts | **[0.30, 0.69]** of transmission | He C · R; Ferretti C · Ab (preprint); Casey-Bryars C · Sec |
| A4 | Hosts shedding infectious virus before onset (fraction of cases) | 1.0, at 10⁻⁶ of peak | Hakki 2022: 7/35 (0.20) culture-positive, 24/38 (0.63) PCR-positive before onset | — (a case fraction, not an emission share) | B · Ab |
| B1 | Viral load on day of onset relative to peak (log10) | **−6** | He 2020: throat-swab load highest at onset, then monotonic decline. Wölfel 2020 (n=9): earliest swabs day 1; every swab days 1–5 positive, mean 6.76×10⁵ against a maximum 7.11×10⁸ copies/swab | no number retrieved; qualitatively within ~3 log10 of peak | B · R (He, Wölfel) |
| B2 | Rise rate to peak (log10/day) | 2.0 then 1.5, 0.5 | Jones 2021: 4.31 d (4.04–4.60) from onset of shedding to peak of 8.1 log10 copies/swab; Kissler 2021: 3.3 d (2.5–4.2) from first detectability to peak. Neither is on the symptom-onset axis | `?nr` on the onset axis | B · R (Jones); B · Ab (Kissler) |
| C1 | Peak infectiousness (d since onset) | **+4** | He 2020 corrected: 0 (−0.9 to +0.9); sensitivity runs −2 to +1. Casey-Bryars 2021: mean transmission time −2.6 to +1.4 across contexts | **[−2, +1]** | C · R; C · Sec |
| C2 | Peak upper-respiratory viral load (d since onset) | **+4** | Hakki 2022: onset a median 3 d before peak RNA (IQR 3–5, n=38) and peak infectious virus (IQR 3–6, n=35). Wölfel 2020: maximum on day 4. Stankiewicz Karita 2022: mild symptoms start within 1 d of peak, moderate/severe 2 d **after** peak. He 2020: highest at onset. Benefield 2020 (pooled, preprint): peaks before onset. Çevik 2020: first week of illness | **[−2, +5]** | Hakki B · Ab; Wölfel B · Ab/R; Stankiewicz Karita B · Ab; Benefield C · Ab; Çevik Sec |
| D1 | RNA decline after peak (log10/day) | −0.70 mean, −1.0 steepest | Jones 2021: −0.168 (−0.171, −0.165), 4,344 subjects | [−0.171, −0.165] for RNA per swab | B · R |
| D2 | Infectiousness within 7 d of onset | 0.998 of emission inside 7 d | He 2020: "declined quickly within 7 days". Hakki 2022: 22/34 (0.65) still culture-positive at day 5, 8/34 (0.24) at day 7. Oordt-Speets 2024: culture positivity 44–50% days −1 to 5, 28% day 7, 11% day 9 | — (probabilities of culture, not relative emission) | He C · R; Hakki B · Ab; Oordt-Speets Sec |
| E1 | RNA-positive duration (d) | 15 | Çevik 2020: 17.0 (15.5–18.6), 43 studies, 3,229 individuals | [15.5, 18.6] | Sec · Ab |
| E2 | Infectious duration (d) | 5 d within 2 log10 of peak; 2.8e-6 of emission after day 9 | Hakki 2022: median 5 (IQR 3–7). Wölfel 2020: <5% isolation success by day 9.78 (8.45–21.78). Çevik 2020: no live virus beyond day 9 | [3, 7] median duration; end by day ~9–10 | Hakki B · Ab; Wölfel B · F·leg; Çevik Sec |

Sources: He et al., *Nat Med* 2020, doi:10.1038/s41591-020-0869-5 and its
Author Correction doi:10.1038/s41591-020-1016-z; Jones et al., *Science* 2021,
doi:10.1126/science.abi5273; Wölfel et al., *Nature* 2020,
doi:10.1038/s41586-020-2196-x; Hakki et al., *Lancet Respir Med* 2022 (ATACCC
cohort; pre-alpha, alpha and delta); Stankiewicz Karita et al., *JAMA Netw
Open* 2022, doi:10.1001/jamanetworkopen.2021.42796; Kissler et al., *PLoS
Biol* 2021; Casey-Bryars et al., *BMJ Open* 2021,
doi:10.1136/bmjopen-2020-041240; Ferretti et al., SSRN 2020,
doi:10.2139/ssrn.3716879; Benefield et al., medRxiv 2020,
doi:10.1101/2020.09.28.20202028; Çevik et al., *Lancet Microbe* 2020,
doi:10.1016/S2666-5247(20)30172-5; Oordt-Speets et al., *J Glob Health* 2024,
doi:10.7189/jogh.14.05005.

## 3. The three literature questions

**(a) What He et al. 2020 reports.** Throat-swab viral load was highest at
symptom onset. The fitted infectiousness profile (77 transmission pairs), as
corrected in August 2020, starts 12.3 d before onset, peaks at onset and
puts 44% of transmission before onset. The profile's
`presymptomatic_shedding_notes` quotes "approximately 2.3 days", the value the
authors withdrew. The abstract still indexed for the paper shows a 25–69%
interval for the presymptomatic share; the body text read here gives 30–57%.

**(b) Other sources.** Transmission-pair analyses agree with He: a third to
two thirds of transmission is presymptomatic and the mean transmission time
sits between about 2.6 d before and 1.4 d after onset. Viral-load cohorts
split: Hakki 2022 (daily culture, n=57) and Wölfel 2020 (n=9) put the peak
3–4 d **after** onset; He 2020, Stankiewicz Karita 2022 and Benefield 2020 put
it at or before onset. Jones 2021's 4.31 d is measured from onset of
shedding, not from symptom onset, and cannot be read as an onset-axis peak.
Hakki 2022 is the one cohort that argues against heavy presymptomatic
shedding (20% of cases culture-positive before onset) — and it still does
not support a 10⁻⁶ level.

**(c) Declared intervals.** Presymptomatic share of transmission
**[0.30, 0.69]** (He's lower confidence bound to Casey-Bryars' highest
context). Peak position **[−2, +5] d** for upper-respiratory viral load, of
which **[−2, +1] d** is the transmission-derived sub-interval. The two
evidence classes do not overlap above +1 d; the authored +4 d lies inside
the first and outside the second. Caveat (inference): the share is measured
on transmission, which includes post-onset behaviour change; the emission
share of an unisolated host could be lower than 0.30, and no retrieved source
bounds it directly. Nothing retrieved bounds it anywhere near 1.2e-6.

## 4. Per-segment reasoning

- **A. Presymptomatic window.** A 2-day window is a defensible truncation
  (it drops at most ~9% of transmission by He's corrected fit, and Hakki
  supports a short window), but its stated source figure is withdrawn. The
  level is not sourced anywhere: the window re-uses curve entry 0, so two
  presymptomatic days carry 1.2e-6 of emission against a declared
  [0.30, 0.69] of transmission.
- **B. Rise.** The onset day sits 6 log10 below peak and the next day 4
  below. He's and Wölfel's swabs at days 0–1 are at or near their maxima.
  No retrieved source reports a ×100/day rise *after* symptom onset.
- **C. Peak position.** Supported by Hakki and Wölfel, contradicted by the
  profile's own citation. The register row
  (`docs/parameter_provenance_register.md`, "`shedding_curve_log10` (shape)",
  C → B, peak index [2, 6]) rests on Killingley 2022 — 5 d after
  **inoculation**, a different axis — and Pan 2020 (not re-retrieved here).
  That grade should be read as contested until re-audited on the onset axis.
- **D. Decay.** Direction and the "mostly over within a week" behaviour
  match. The rate is 4–6× steeper than Jones' measured RNA decline; the curve
  is declared as an RNA concentration, so on its own terms the tail is too
  steep, while as an infectious-virus curve it is within what culture data
  allow.
- **E. Total period.** 15 d against a pooled 17.0 d (15.5–18.6) of RNA
  positivity; effective emission of ~5 d against a measured median 5 d
  infectious window.

## 5. Where the shape came from (measured from git; intent is inferred)

The array was authored in `10b6dd29` (2026-05-24) and has not changed. The
engine then indexed it by day **post-infection**. `d3947c7f` (2026-08-28,
"Anchor pathogen shedding to symptom onset") re-indexed every curve from
symptom onset and added the presymptomatic window, without shifting this
array. `docs/pathogen_notes.md` still reads "Peak viral load near symptom
onset (days 4-6)". On the old axis index 4 is 1.8 d before onset at the
5.8 d median incubation; on the current axis it is 4 d after. Inference: the
array describes a post-infection course and has been read on the onset axis
since `d3947c7f`. Not shown: that the original author intended either axis.

## 6. Decision relevance (inference, no cell run)

The DP index leaves at onset +2 d (`COVID-INDEX-CLOCK-01`). Under the
authored curve it emits 6.1e-5 of its lifetime total before leaving, almost
all of it on its last day aboard. Under any curve inside the declared
intervals the index would emit a large fraction of its total while aboard,
including the first voyage days. The founder-class shortfall recorded in
`docs/covid/covid_dp_union_01_readout.md` is therefore conditional on this
curve.

## 7. What a correction would re-denominate (not implemented here)

A later, owner-approved leg that moved the curve would re-denominate
(inferred from which quantities read the curve; none re-measured):

- every Θ fitted or screened on a COVID arm (the emission-timing weight
  inside the dose product changes, so no old Θ converts by one factor);
- index-seeded founder yield and takeoff on DP, and the aboard-emission
  split `COVID-INDEX-CLOCK-01` measured;
- generation and serial intervals, hence onset-curve timing on every arm;
- the measured effect of any onset-triggered control (isolation, sick-call
  testing), which today removes ~all emission and under the literature shape
  would remove roughly half;
- the register grade for `shedding_curve_log10` (shape).

Not a proposal for a value: the candidate shapes differ between the
transmission-derived and viral-load-derived classes, and choosing between
them is an owner decision made before any arm is scored.

## 8. Limits

- Literature numbers were read from index excerpts; origins marked Ab were
  not confirmed in Results. Pan 2020 and Killingley 2022 were not
  re-retrieved. He's fitted profile parameters were not retrieved, so the
  literature curve is compared at tabulated points, not as a full curve.
- Cohorts span ancestral to delta; the profile targets the ancestral arm.
- Section 1 is deterministic arithmetic on the profile; no simulation ran,
  no test or golden moved.
