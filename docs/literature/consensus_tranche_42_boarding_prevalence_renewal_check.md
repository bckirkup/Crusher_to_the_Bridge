# Tranche 42 — the boarding prevalence renewal check

**Read first:** this tranche is a *consistency check*, not a refit. It asks
whether the adopted boarding prevalence, the engine's representable window,
and adult community incidence are mutually consistent under the renewal
identity prevalence = incidence × mean detectable duration. The finding is
that three separately sourced quantities cannot all be right; no constant
moved, none was fitted, and nothing here proposes a candidate value.

**Register rows fed / supersession.** Feeds the register rows for the boarding
axis intervals `PASSENGER_PREVALENCE_INTERVAL` / `CREW_PREVALENCE_INTERVAL`
(`picard_framework/runs/mega_cruise_campaign/boarding_axis.py`) and the open
ledger's §4 item 33, which records the retraction of two claims in
[`../norovirus/introduction_mechanism_ab.md`](../norovirus/introduction_mechanism_ab.md)
that this check exposed. It **moves no constant and adopts none.**

**Retrieval.** Consensus MCP `search` with `include_full_text_chunks: true`.
Each number below names the paper section it was read from.

**Status:** Evidence assembled, arithmetic reproduced below and checkable —
findings A/B/C stand as stated; both repairs are now implemented as
selectable, default-off modes (§6) and unmeasured.

---

## 1. Sources and the numbers read

**Atmar et al. 2008**, "Norwalk Virus Shedding after Experimental Human
Infection", *Emerg Infect Dis*, DOI 10.3201/eid1410.080117. Read from
**Results** (full-text chunk): RT-PCR-detectable shedding first detected at a
median 36 h (range 18–110 h) post-inoculation and **lasted a median of 28 days
(range 13–56)**; antigen-ELISA detectable from median 42 h and **last detected
10 days (median 7 days)**; clinical illness lasted **1–2 days**; median peak
95×10⁹ genome copies/g (range 0.5–1,640×10⁹). n = 16 challenged, 11 met the
clinical-gastroenteritis definition. Grade A for duration-of-detectability;
note it is GI.1 challenge in adults, not a community prevalent sample.

**O'Brien et al. 2016**, *J Infect Dis*, DOI 10.1093/infdis/jiv411. Read from
**Table 1** (full-text chunk, rendered markdown): community norovirus-associated
IID incidence, cases/1,000 person-years — <1 y 178.2; 1–5 y 137.3; 5–15 y 59.6;
**15–64 y 39.0 (31.3–48.7)**; **≥65 y 27.7 (19.6–39.1)**; ≥5 y 37.6 (31.5–44.7).

**Tam et al. 2011**, *Gut* (IID2), DOI 10.1136/gut.2011.238386. Read from
**Results**: all-ages norovirus community incidence **47 cases/1,000
person-years**, 2.1 GP consultations/1,000 py; 4,658 person-years of follow-up.

**Circularity check.** Both incidence sources are UK community cohorts with no
cruise, VSP, MIDRS or A-anchor content, so the cross-check in finding C is
independent of everything the model is scored against.

## 2. Finding A — the adopted prevalence and the engine's window are not the same quantity

The adopted interval is RT-PCR stool RNA positivity in a person reporting no
diarrhoea (tranche 10). Atmar puts RNA detectability at a median **28 days**
while the high-load, antigen-detectable phase ends by day 7–10 and illness
lasts 1–2 days. `norwalk_gi` ships `shedding_duration_days` 15, so in a
stationary prevalent sample — where days-since-infection is approximately
uniform over the detectable duration — only about **15/28 ≈ 54%** of an
RNA-positive cohort is in any state the engine can represent, and the engine
currently places the whole prevalence inside the 15-day window.

## 3. Finding B — the boarding age draw is concentrated on the high-shedding days, not the tail

`engines/initiation.py` `_state_window` draws a convalescent import's age
uniformly over `[recovery_day, shedding_duration_days]` = 3–15 days since
infection; with the profile's incubation median 1.2 d that is 1.8–13.8 days
post onset, which **spans the symptomatic curve's own peak**
(`shedding_curve_log10` = 11.0 at post-onset days 2–4). Quantified against the
shipped curves and `environmental_faecal_release_log10_g_per_epoch` 4.0, with
the shipped split (0.29 / 0.04):

- engine mean per-import shedding **1.77×10¹⁰** (log10 10.25)
- the same composition with age drawn uniformly over Atmar's 28-day detectable
  window (hosts past day 15 contributing nothing): **8.77×10⁹** (log10 9.94)
- ratio **2.02×**
- for scale, the mean shedding of a full-course symptomatic host over its 15
  days is 2.18×10¹⁰, so **each import is 81% as infectious on average as a
  fully symptomatic index case** while being invisible to surveillance
  (ledger item 33(a)).

Derivation, reproduced before writing the figures above:

```python
import numpy as np
S=[7.75,9.0,11.0,11.0,11.0,10.0,10.0,9.5,9.0,9.0,8.0,8.0,8.0,8.0,8.0]
A=[7.75,9.5,10.5,10.0,9.0,8.0,7.75,7.75,7.75,7.75,7.75,7.75,7.75,7.75,7.75]
inc=1.2
shed=lambda age,c: 10**c[int(min(max(round(age-inc),0),14))]
conv=np.mean([shed(a,S) for a in np.linspace(3,15,10001)])
nev=np.mean([shed(a,A) for a in np.linspace(0,15,10001)])
pres=np.mean([shed(a,S) for a in np.linspace(0,1.2,1001)])
f=0.29
eng=f*nev+(1-f)*0.04*pres+(1-f)*0.96*conv
st=np.mean([f*(shed(a,A) if a<=15 else 0.0)+(1-f)*(shed(a,S) if a<=15 else 0.0)
            for a in np.linspace(0,28,20001)])
print(eng, st, eng/st, np.mean([shed(a,S) for a in np.linspace(0,15,10001)]))
```

Output: `1.7694e10  8.7651e9  2.019  2.1786e10` — engine 1.77×10¹⁰,
stationary 8.77×10⁹, ratio 2.02, full-course symptomatic 2.18×10¹⁰.

## 4. Finding C — the renewal-identity cross-check

prevalence = incidence × mean detectable duration. Converting adult community
*cases* to *infections* with the engine's own two named regimes and
multiplying by Atmar's 28 days:

- adult-challenge regime (`never_symptomatic_fraction` 0.29):
  ≥65 y → 0.30%; 15–64 y → 0.42%
- community-cohort regime (0.635):
  ≥65 y → 0.58%; 15–64 y → 0.82%
- full corner set (duration 13/28/56 d × both regimes × both adult bands):
  **0.14%–1.64%**

The adopted passenger interval **[2.5%, 4.0%]** lies above every corner —
roughly 4–10× the central value and 1.5× above the most favourable one. The
crew interval [0.7%, 3.0%] straddles it. So three separately sourced
quantities (the asymptomatic screening prevalence of tranche 10, Atmar's
28-day detectable duration, and the adult community incidence) are **mutually
inconsistent; at most two of the three can be right.**

Three admissible resolutions exist; none is chosen here:

1. the screening series (Kobayashi 2021, Qi 2018, Jeong 2021 food handlers)
   are setting-, season- and country-selected and may not be a
   general-population embarkation rate;
2. community cohorts count IID cases, so asymptomatic infections are missing
   from the numerator and dividing by (1 − never-symptomatic) may not recover
   them;
3. long-duration shedders — the profile's own `chronic_shedder_fraction` and
   `chronic_shedding_duration_days` — can lift the mean *detectable* duration
   well above 28 days without lifting the mean *infectious* duration,
   inflating prevalence without proportionate transmission.

A coincidence, stated explicitly and **not** as confirmation: every one of
these corrections lowers boarding's imported infectious pressure, which is
also the direction A9 wants. The derivation uses no cruise observable, and
**no constant is changed on the strength of it in this change.**

## 5. The open question

Unresolved: whether the boarding block should take a renewal-derived import
rate (incidence × model-representable duration) in place of a screening
prevalence, and whether "convalescent" is the right state for an RNA-positive
asymptomatic sample at all given finding B.

## 6. What was implemented

Both repairs now exist as selectable, default-off modes; nothing shipped
moved and neither arm has been measured.

- **A2, `rate_mode: renewal`.** The boarding block carries
  `renewal.case_incidence_per_1000_py` per role and
  `renewal.detectable_duration_days`, and `engines/initiation.py` derives the
  per-person prevalence under the finding-C identity — case incidence
  divided by `1 − never_symptomatic_fraction` to recover infections, times
  duration/365.25. At 39.0 / 0.29 / 28 it derives **0.004208 ≈ 0.42%**. A
  block carrying both `renewal` and `prevalence` is a load error.
- **B2, `age_draw: stationary_detectable`.** The infection-age draw keeps
  `_draw_state` first, then widens only the `never_symptomatic` and
  `convalescent` high edges to `max(incubation + shedding duration,
  detectable_duration_days)` — detectable duration is read from the profile
  (`norwalk_gi` now ships 28, Atmar 2008; origin mismatch between
  from-infection and from-incubation indexing is recorded at the definition,
  not harmonised). A host whose age lands past `incubation +
  shedding_duration` boards as `cleared`: counted in
  `BoardingReport.composition`, never passed to `infect_with_pathogen`, inert
  to transmission, and excluded from `drawn_by_role` so the realised
  introduction count stays a count of infectious hosts. The
  `_select_prevalent` length-bias weight is unchanged
  (it is strictly detectable duration under the stationary model; changing
  it was scoped out).
- **Defaults.** `rate_mode` omitted → `screening_prevalence`; `age_draw`
  omitted → `engine_window`; both reproduce the pre-change draw bit-for-bit,
  pinned by a labelled change-detector test. The open question of §5 is
  thereby made measurable rather than decided.
