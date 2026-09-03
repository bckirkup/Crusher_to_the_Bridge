# Consensus tranche 7 — shedding stops when illness stops, and two thirds of the norovirus curve is never emitted

**Status:** Evidence assembled and interpreted, plus one in-tree measurement.
**No pathogen-profile constant, no engine constant and no screen interval
changed by this document**; the change it justifies is specified in §6 and is
queued, not applied.
**Scope:** item #45 — moving immunocompromise off the acquisition multiplier
and onto shedding duration, plus the chronic-shedder importation channel. The
tranche was opened to source that move and found the field it needs does not
exist for *any* host, immunocompromised or not.
**Method:** Consensus MCP searches on norovirus shedding duration in healthy
challenge subjects and on chronic infection in immunocompromised cohorts, each
read back into the shipped parameterisation; then a direct measurement of which
authored shedding-curve days a shipped host actually reaches, driving the real
progression seam rather than reasoning about it
(`telemetry_buffer/observation_model/shedding_clock_check.py`).

The short answer: **the model has one clock where the literature measures two.**
Illness duration and shedding duration are separately measured quantities that
differ by an order of magnitude in healthy adults — 1–2 days of symptoms
against a median 28 days of faecal shedding — and the engine ends shedding when
illness ends. Immunocompromise cannot be moved onto shedding duration until
shedding duration exists as a quantity, so #45 acquires a prerequisite that is
not about immunocompromise at all.

---

## 1. The clock, stated precisely enough to test

`orchestrator_epoch.py` clears an infection at

```python
recovery_day = agent.get_chronic_recovery_day(pid, prof.get("recovery_day", 3))
clearance_day = onset_day + recovery_day
```

and shedding is read from the profile's day-indexed curve on the same onset
axis. So `recovery_day` is doing two jobs: it is the symptomatic duration
(measured, and correct at 3 days for norovirus), and it is also the total
infectious period, because when the infection clears the host stops emitting.
`asymptomatic_shedding_log10` is subject to the same clock: a host that never
presents still uses its drawn incubation as a virtual onset and clears
`recovery_day` after it.

The norovirus profile authors **fifteen** days of shedding — a rise to a
10¹¹ copies/g plateau, then a decay to a 10⁸ tail. With `recovery_day: 3`,
most of that authored curve is unreachable code.

## 2. What the host actually emits, measured

200 hosts driven through the real progression seam at current `main`, one
pathogen each, recording the curve index reached on every epoch that emits:

| | Norovirus (`norwalk_gi`) | SARS-CoV-2 (`sars_cov2_resp`) |
|---|---|---|
| Authored curve days | 15 | 15 |
| `recovery_day` | 3 | 7 |
| Curve indices ever reached | **0, 1, 2** | 0–6 |
| Last shedding day (days since infection) | median **4** (3–6) | median 12 (8–22) |
| Share of the authored symptomatic curve integral emitted | **30.9%** | **99.8%** |
| Share of the asymptomatic curve integral emitted | 75.0% | — |

So the defect is generic in mechanism and almost entirely norovirus in effect.
The COVID curve peaks at day 4 and has decayed by day 7, so its clock truncates
0.2% of the integral and nothing needs to change there. The norovirus curve
peaks at 11.0 on days 2, 3 and 4 and the clock reaches exactly one of those
three peak days: 2.26×10¹¹ of 3.27×10¹¹ copies/g·day — **69.1%** — is authored
and never emitted, including the entire decay limb. The emitted profile is
rise, rise, peak, stop: the model has no post-symptomatic shedding at all.

Two consequences worth stating separately from the arithmetic, because they are
what the missing days would have represented:

- **Convalescent shedding does not exist in this model.** The VSP food-handler
  exclusion rule is written about exactly that population, and post-symptomatic
  hosts are currently non-infectious by construction.
- **Nobody debarks shedding.** On a 7-day voyage a host infected on day 2 is
  clear by day 6, so the fraction of the manifest still excreting at
  debarkation — the quantity that connects one voyage to the next — is
  structurally zero.

## 3. What is measured in healthy hosts

| Source | Setting | Illness duration | Shedding duration | Magnitude |
|---|---|---|---|---|
| Atmar et al. 2008, *Emerg Infect Dis* | GI.1 Norwalk human challenge, 16 subjects, 11 with gastroenteritis | **1–2 days** | RT-PCR first detected 18 h, lasting median **28 days** post-inoculation (range **13–56**); antigen ELISA median 7 days | median peak **95×10⁹** copies/g (range 0.5–1,640×10⁹) |
| Kirby et al. 2014, *J Med Virol* | GI.1 Norwalk and GII.2 Snow Mountain challenge; all stools to day 7, representative stools to day 35 | — | both genogroups shed **up to 3 weeks after resolution of symptoms**; long durations more common with GI.1 | GI.1 titres ≈ **2 logs above** GII.2 |
| Cheng et al. 2021, *Medicine* | 77 hospitalised children, GII.4 / GII.4 Sydney / GII.P16-GII.2 | — | load rises days 2–9 from onset, irregular plateau, declines after day 9, **most shedding ceased by day 15** | highest in GII.4 Sydney, lowest in non-GII.4 |
| Ge et al. 2023, *Emerg Infect Dis* | Bayesian re-analysis of GI.1 challenge, dose 4.8–4,800 RT-PCR units | symptom onset 1.5→0.8 d with dose | shedding onset 1.4→0.8 d, peak 2.3→1.5 d | cumulative faecal total **4.5×10¹¹–3.4×10¹²** genome copies |

Three things follow that the shipped arm does not express.

**The two durations are different measurements.** Atmar reports them in the same
16 subjects: symptoms 1–2 days, RT-PCR shedding a median of 28 days. Our
`recovery_day: 3` is a defensible *illness* duration and an indefensible
*infectious* duration, and the field is used as both.

**The authored curve is roughly the right shape for the wrong reason.** Cheng's
GII cohort — plateau to day 9, decline, most ceased by day 15 — is close to the
15-day curve already in the profile. The curve does not need to be authored; it
needs to be *reachable*.

**The curve's magnitude is GI.1-shaped, and this one has a direction.** Our peak
of 11.0 log10 copies/g is Atmar's GI.1 median peak (95×10⁹ = 10^10.98) to two
decimal places, while Kirby measures GII.2 about two logs below GI.1 in the same
challenge design. So the emission side carries the same genogroup mismatch as
the dose axis did in tranche 6 — but where the GII dose-response interval turned
out to *contain* the shipped GI.1 value, this discrepancy is directional and
large. It is **not adoptable**: emission scale and dose-response enter the model
as a product (#366), so a −2 log emission correction applied alone would be
absorbed into a quantity we have not identified. Declared here, queued as its
own item, and explicitly not applied.

## 4. What is measured in immunocompromised hosts

This is the evidence #45 was opened to find, and it is about duration and
infectiousness — not about acquisition.

| Source | Cohort | Chronic shedding duration | Notes |
|---|---|---|---|
| van Beek et al. 2017, *Clin Microbiol Infect* | **2,182** solid-organ recipients, retrospectively tested | median **218 days** (range **32–1,164**) | 101/2,182 (**4.6%**) infected; **23/101 (22.8%)** became chronic; heart, kidney and lung recipients |
| van Beek et al. 2017, *J Infect Dis* | 16 immunocompromised patients, 65 samples, whole-genome sequenced | mean **352 days** (range 76–716) | distinct within-host GII.4 variants in 3/13; a candidate reservoir for emerging strains |
| Davis et al. 2020, *Viruses* | 1,140 paediatric patients over 6 years | 20 chronic cases, **37 to >418 days** | **continuous shedding of infectious virus confirmed for the first time**, by HIE assay; longer in males and in those with diarrhoea |
| Chaimongkol et al. 2024, *J Infect Dis* | 88 immunocompromised NIH patients, 448 stools, 2010–2022 | 39 patients with documented chronic infection | shedding **10⁴–10¹¹** genome copies/g; GII.4 variants predominant (51/88, 57.9%); GI and GII both present |
| Schorn et al. 2010, *Clin Infect Dis* | kidney-transplant recipients | 97–898 days | immune-driven within-host evolution |
| Green 2014, *Clin Microbiol Infect* | review | weeks to years | **mechanisms of persistence not known** |

And the acquisition side, restated because it is the reason #45 exists: nothing
found in this tranche or the last measures the relative risk of *acquiring*
norovirus while immunocompromised. The shipped `immunocompromised_multiplier:
2.0` has no source, and Wave 1 made it bite harder by composing it
multiplicatively instead of overwriting. It is an assumption sitting on the one
quantity the literature does not measure, while three independent cohorts
measure the quantity next to it.

Two further readings that matter for the mechanism rather than the value:

- **Chronic shedders are infectious, not merely PCR-positive.** Davis 2020 is
  the citation that licenses treating them as a transmission source at all; the
  older literature could only report genome copies.
- **The magnitude is 7 logs wide** (Chaimongkol: 10⁴–10¹¹). There is no point
  value to adopt, so chronic magnitude is a swept axis or nothing.
- **218 days against a 7–14 day voyage** means the relevant immunocompromised
  host is not someone who acquires norovirus more easily on board. It is
  someone who **boards already shedding** — an importation channel, which is
  also the first evidence-based statement available about who brings norovirus
  aboard, against an index case currently seeded by fiat.

## 5. Prevalence, carried forward from tranche 6's queue

Recorded here so the interval lives with the mechanism it belongs to:
`immunocompromised_fraction: 0.05` is bounded to roughly **[0.02, 0.074]** —
Harpaz et al. 2016 (NHIS, 2.7% of US adults, 2013), Martinson et al. 2024
(6.6%, 2021, and 7.4% in 2022), and the one measurement in our own setting,
Lopez-Gigosos et al. 2020 (24 of 1,196 international travellers screened at a
travel clinic, **2.0%**). The width is population and era, not uncertainty,
which makes it an era-aware interval rather than a point — the same treatment
the NPI sets get.

## 6. What this licenses, and what it does not

**The prerequisite, and it is not immunocompromise-specific.** Separate the
shedding clock from the illness clock for every host:

- illness clears at `onset + recovery_day` — **unchanged**, so every
  symptomatic-duration, emesis-schedule, reporting and VSP observation window
  keeps its current behaviour and its Atmar-consistent 1–2 day basis;
- infection and shedding clear at `onset + shedding_duration_days`, a new
  profile field.

Shipped value **15 days**, which is the authored curve's own length and is
sourced by Cheng 2021 for GII (most shedding ceased by day 15); screen interval
**[12, 30]**, spanning Cheng's 15 to Atmar's 28-day median and Kirby's three
weeks past symptom resolution. The interval is wide because the duration is
genogroup- and population-dependent, and adopting Atmar's GI.1 median as a GII
point value would repeat the mistake tranche 6 was written to catch.

**No curve value is authored or changed by this.** The change activates a tail
that is already in the profile — it adds a field, not a number, which is the
cleanest form this correction could take.

**It will move every norovirus golden number, and the direction is known.**
Strictly more infectious host-days per infection, so attack rate rises; by how
much is unmeasured until the change lands and is not predicted here. That move
is attributable to one line of the diff, which is the standard the scope rules
set. It also re-invalidates the Morris screen, which was already invalid.

**Then #45 splits into three, in this order:**

1. **Withdraw** `immunocompromised_multiplier` from susceptibility. No measured
   basis, wrong quantity. Not silently repurposed — withdrawn on the record.
2. **Immunocompromise as duration**: an extension of `shedding_duration_days`,
   which is where the measurement is (218-day median, 32–1,164). Bounded by
   `immunocompromised_fraction` ∈ [0.02, 0.074] × chronic fraction 22.8%.
3. **Chronic magnitude and importation**: shedding level swept over the measured
   10⁴–10¹¹ rather than adopted, and a boarding-prevalence channel for hosts who
   embark already shedding. Neither is a point value in any source; both are
   axes.

**Not licensed by this document:** any change to `recovery_day`; any change to
an authored curve value; the −2 log GII emission correction (§3, blocked by the
emission × dose-response product); any chronic-shedder point prevalence; and any
re-run of the screen before the mechanism is stable.

## 7. Sources

- Atmar, R. L. *et al.* (2008) *Emerg Infect Dis* 14(10):1553 — Norwalk virus
  shedding after experimental human infection; 16 subjects, illness 1–2 days,
  RT-PCR shedding median 28 days (13–56), median peak 95×10⁹ copies/g. Grade
  **A** for GI.1 challenge, **B** as a GII duration.
- Kirby, A. E. *et al.* (2014) *J Med Virol* 86(12):2055 — GI.1 and GII.2
  challenge shedding dynamics to day 35; shedding up to 3 weeks past symptom
  resolution; GI.1 titres ≈2 logs above GII.2. Grade **A** for the genogroup
  comparison. First report of GII shedding dynamics in experimental infection.
- Cheng, H.-Y. *et al.* (2021) *Medicine* 100(15):e25123 — 77 hospitalised
  children, GII.4 / GII.4 Sydney / GII.P16-GII.2; rise days 2–9, decline after
  day 9, most ceased by day 15. Grade **B** (paediatric, hospitalised).
- Ge, Y. *et al.* (2023) *Emerg Infect Dis* 29(7) — dose effect on kinetics;
  cumulative faecal total 4.5×10¹¹–3.4×10¹² genome copies. Grade **B**
  (secondary Bayesian analysis).
- van Beek, J. *et al.* (2017) *Clin Microbiol Infect* 23(4):265 — 2,182 solid
  organ recipients; 4.6% infected, 22.8% chronic, median shedding 218 days
  (32–1,164). Grade **A** for chronic duration in SOT.
- van Beek, J. *et al.* (2017) *J Infect Dis* 216(9):1132 — 16 immunocompromised
  patients, mean shedding 352 days (76–716); within-host GII.4 divergence.
  Grade **B** (selected samples).
- Davis, A. E. *et al.* (2020) *Viruses* 12(6):619 — 1,140 paediatric patients,
  20 chronic infections 37 to >418 days; **infectious** virus shed continuously,
  confirmed by HIE assay. Grade **A** for infectiousness of chronic shedding.
- Chaimongkol, N. *et al.* (2024) *J Infect Dis* — 88 immunocompromised
  patients, 448 stools; chronic shedding 10⁴–10¹¹ copies/g; GII.4 predominant
  (57.9%). Grade **A** for the magnitude interval.
- Schorn, R. *et al.* (2010) *Clin Infect Dis* 51(3):307 — chronic norovirus
  after kidney transplantation, 97–898 days. Grade **B** (case series).
- Green, K. Y. (2014) *Clin Microbiol Infect* 20(8):717 — norovirus infection in
  immunocompromised hosts; persistence mechanisms unknown. Grade **B**
  (review), cited for the absence, not for a value.
- Harpaz, R. *et al.* (2016) *JAMA* 316(23):2547; Martinson, M. L. and Lapham, J.
  (2024) *JAMA* 331(10):880 — US adult immunosuppression prevalence 2.7% (2013),
  6.6% (2021), 7.4% (2022). Grade **B** (self-report).
- Lopez-Gigosos, R. M. *et al.* (2020) — 1,196 international travellers screened
  at a travel clinic, 24 (2.0%) immunocompromised. Grade **B**, and the only
  measurement in a travel population.
- Liu, P. *et al.* (2020) *J Med Virol* — 158 challenge subjects across five
  trials; shedding duration differed 11.0 vs 5.0 days between two inocula of the
  *same* GI.1 virus. Read but **not used** as an interval endpoint: it bounds
  inoculum-to-inoculum variation, not host duration.
