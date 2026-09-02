# Consensus sourcing, tranche 4

**Status:** evidence discovery. Nothing here is adopted; no constant, profile
field or engine path is changed by this document. Candidate values become model
values only through `model-parameter-provenance`, with a unit check and an
evidence grade, and never by being quoted here.

Companions: [`parameter_sourcing_bundle.md`](parameter_sourcing_bundle.md)
(tranche 1), [`consensus_tranche_2.md`](consensus_tranche_2.md) (tranche 2, §1–§2
superseded), [`consensus_tranche_3.md`](consensus_tranche_3.md) (tranche 3).

Two targets. First, the emesis discrepancy tranche 3 opened and could not close
from abstracts — Kirby et al. 2016 against Ge et al. 2023, "1–2.4 orders apart"
on total emesis shedding, against the screen's **second-ranked** factor. Second,
the SARS-CoV-2 emission scale and dose-response denominator, which task #30
requires to be re-sourced *together in one unit system* because their ratio is
all the model can see.

Both were resolved by reading primary texts. The emesis one dissolves; the COVID
one produces, for the first time, a candidate pair in the same units.

---

## 1. Kirby vs Ge: there is no discrepancy, and our shipped titre is from the abstract

Tranche 3 compared two headline figures and read a conflict. The primary texts
say they are two different summaries of one right-skewed distribution.

### 1a. What each paper actually computed

Both compute total emesis shedding the same way — titre × sample volume, summed
over a subject's samples — so the arithmetic is not in dispute.

| | Kirby et al. 2016, *PLoS ONE* ([10.1371/journal.pone.0143759](https://doi.org/10.1371/journal.pone.0143759)) | Ge et al. 2023, *EID* ([10.3201/eid2907.230117](https://doi.org/10.3201/eid2907.230117)) |
|---|---|---|
| Strains | GI.1 Norwalk (2 trials), GII.2 Snow Mountain, GII.1 Hawaii (2-subject pilot) | **GI.1 Norwalk only** (NCT00138476, Atmar dose-ranging) |
| Subjects contributing emesis | 22 subjects, 57 archived samples | 11 subjects, 26 vomit samples |
| Statistic reported | arithmetic mean of cumulative shed, **over positive samples only** | posterior mean by inoculum dose, Bayesian mixed-effects |
| Doses | oyster-borne and stored groundwater; **active dose unknown**, upper limit only | 4.8 / 48 / 4,800 RT-PCR units, known |

Kirby's per-subject cumulative shed, from its Table 3 rather than its abstract:

| Study | strain | sample mean titre (GEC/mL) | subject mean cumulative shed (GEC) |
|---|---|---|---|
| 1 | GI.1 Norwalk | 5.8 × 10⁵ | 1.3 × 10⁸ (SEM 9.1 × 10⁷) |
| 2 | GI.1 Norwalk | 9.2 × 10⁵ | 3.1 × 10⁸ (SEM 1.7 × 10⁸) |
| **All GI** | GI.1 | **8.0 × 10⁵** | **2.3 × 10⁸** (SEM 1.0 × 10⁸) |
| 3 | **GII.2 Snow Mountain** | **1.6 × 10⁵** | **1.8 × 10⁷** (SEM 1.8 × 10⁷) |
| 4 | GII.1 Hawaii (n=2 pilot) | 5.0 × 10³ | 2.3 × 10⁵ |

### 1b. The reconciliation

Compare like with like and the gap closes:

- **GII.2 against Ge's top dose:** 1.8 × 10⁷ (Kirby study 3) against 3.0 × 10⁷
  (Ge, 4,800 units). A factor of 1.7 — inside one SEM of Kirby's own estimate.
- **The remaining GI/GII spread is internal to Kirby** (2.3 × 10⁸ against
  1.8 × 10⁷), i.e. a genogroup contrast measured within one study, not a
  disagreement between studies.
- **Mean against median on a heavy tail.** Atmar et al. 2008 (*JID*,
  [10.1086/528818](https://doi.org/10.1086/528818)) reports the vomitus titre for
  the same GI.1 trial family Ge re-analyses: virus in 15 of 27 (56%) samples at a
  **median 4.1 × 10⁴ gEq/mL**. Kirby's GI **mean** is 8.0 × 10⁵ — 20× the median
  of the same quantity in the same genogroup. Kirby's Fig 1 shows why: cumulative
  titre rises with the number of vomiting events, 7 subjects who vomited once had
  no detectable virus at all, and the mean is taken over positives.

So the honest object is a log-scale distribution spanning roughly **10⁵ – 10⁸ GEC
per symptomatic subject**, not two competing point measurements, and tranche 3's
"1–2.4 orders apart" was a mean/median plus genogroup artefact of comparing
abstracts. This is a resolution, not a new number: no value is adopted here.

### 1c. A defect this exposed in the shipped constant

`engines/transmission_core.py`:

```python
# GII mean titre from Kirby et al. 2016; measured, evidence grade B.
EMESIS_TITRE_GEC_PER_ML = 3.9e4
```

3.9 × 10⁴ is Kirby's **abstract** figure for "GII viruses", which pools GII.2
Snow Mountain with the **2-subject GII.1 Hawaii pilot** at 5.0 × 10³. The paper's
own Results *excludes* Hawaii from every genogroup comparison ("due to the small
sample size … the data was not included when comparing results between
genogroups") and reports the GII.2 sample mean titre as **1.6 × 10⁵ GEC/mL**,
with **no significant GI/GII difference** (8.0 × 10⁵ vs 1.6 × 10⁵, p = 0.36) —
against the abstract's p = 0.02, which is the pooled-with-Hawaii test.

For an arm whose genotypes are GII.4 / GII.17 / GII.2 (tranche 3 §1), the
applicable measured value is the GII.2 one, **4.1× the shipped constant**, and
the shipped constant descends from a headline that the paper's own analysis
section sets aside. Two further mismatches against the same paper:

| shipped | measured (Kirby Tables 2–3) |
|---|---|
| `EMESIS_EPISODES_RANGE = (1, 3)` | 1–7 events per subject, mode 1, 32% of subjects vomiting once |
| `EMESIS_VOLUME_ML_RANGE = (50, 800)` per episode, log-uniform → ≈200–600 mL per subject | mean **658.7 mL** per subject (GI), **845.0 mL** (GII.2), 1,439 mL (GII.1 pilot) |

Compounded, the emesis pathway's total per illness sits roughly an order of
magnitude below the measured per-subject cumulative shed — on the factor the
Morris screen ranked **second**. Queued as its own change under
`model-parameter-provenance` (task added), not made here: the titre is a Grade B
constant on a heavy-tailed distribution and the right repair is probably a
distribution plus a corrected episode count, not a swapped point value.

### 1d. An independent check the emesis pathway has never been held to

Alsved et al. 2019, *CID* ([10.1093/cid/ciz584](https://doi.org/10.1093/cid/ciz584)):
air sampled repeatedly beside **26 hospital norovirus patients**, 21 of 86 samples
positive from 10 patients, **5–215 copies/m³**, RNA in both <0.95 µm and >4.51 µm
particles, and positivity strongly associated with vomiting in the previous 3 h
(OR 8.1, p = 0.04). That is a measured airborne concentration in a real outbreak
setting — the quantity `EMESIS_AEROSOL_FRACTION_RANGE` (7.2 × 10⁻⁷ – 2.67 × 10⁻⁴,
Tung-Thompson surrogate) implies. It is a **check**, not a source: using it to
choose the aerosol fraction would be fitting, and its usable form is a comparison
of simulated airborne concentration against 5–215 copies/m³ in a cabin-scale
volume after an emesis event. Note it does **not** repair the standing null on
norovirus airborne *decay* (tranche 1) — a concentration is not a decay rate.

---

## 2. SARS-CoV-2 emission and dose-response, in one unit system (task #30)

#366 established that the COVID arm's emission scale and β are identifiable only
as a ratio, so one of them must be fixed externally **in units the other shares**.
Both halves now have candidates in RNA copies.

### 2a. Emission, measured as a rate

| Source | What was measured | Value | Grade note |
|---|---|---|---|
| Lane et al. 2023, medRxiv ([10.1101/2023.09.06.23295138](https://doi.org/10.1101/2023.09.06.23295138)) | exhaled RNA copies/min, natural breathing, **312 breath specimens** collected multiple times daily | mean **80 copies/min** days 1–8 from onset; individual spikes >800/min; steep drop after day 8, near-LOD to day 20 | direct measurement of the model's quantity; **preprint**, mixed variants/vaccination |
| Coleman et al. 2021, *CID* ([10.1093/cid/ciab691](https://doi.org/10.1093/cid/ciab691)) | G-II sampler, coarse (>5 µm) and fine (≤5 µm), 30 min breathing / 15 min talking / 15 min singing | **63–5,821 N-gene copies per activity per participant** (≈2–200 copies/min); 85% of load in fine aerosol; 94% from talking and singing; 2 of 22 patients = 52% of total load | peer-reviewed, route-resolved; cultures negative |
| Ma et al. 2020, *CID* ([10.1093/cid/ciaa1283](https://doi.org/10.1093/cid/ciaa1283)) | exhaled breath **condensate**, 35 subjects | **10³–10⁵ copies/min** | 1–3 orders above the aerosol-sampler figures; **method-driven, not a variant effect** |
| Alsved et al. 2023, *Sci Rep* ([10.1038/s41598-023-47829-8](https://doi.org/10.1038/s41598-023-47829-8)) | **culturable** exhaled virus, 3 subjects, singing | **4 / 36 / 127 TCID50 s⁻¹** | the only infectious-units emission rate; needs a copies↔TCID50 bridge |

The method spread (EBC vs aerosol sampler) is the honest interval, and it is
wider than any between-study variance inside either method. Two consequences for
us: the emission term must enter as an interval spanning ≈10⁰–10⁵ copies/min, and
the *activity* dependence (94% of load from talking/singing) is a route-weight
statement, not an emission-scale one.

### 2b. The denominator, in copies

Zhang & Wang et al. 2020, *CID* ([10.1093/cid/ciaa1675](https://doi.org/10.1093/cid/ciaa1675)):
an exponential dose-response deduced for coronaviruses, **k ≈ 6.4 × 10⁴ – 9.8 ×
10⁵ virus copies**, i.e. per-copy infection risk 10⁻⁶ – 10⁻⁵.

This is the pairing #366 asked for — a denominator quoted in the same units as
§2a's emission. Three caveats that keep it Grade C, and they are the reason it
must be *declared* rather than presented as measurement:

1. It is **deduced**, not challenged: an a-priori murine dose-response combined
   with a meta-analysis of observed infection risk and exhaled-shedding data. No
   human challenge fixes k.
2. Its own inputs include exhaled shedding, so pairing it with §2a is not fully
   independent — the shared input must be recorded when the pair is adopted.
3. It is an **exponential** relation; the engine's establishment step is
   beta-frailty (tranche 3 / #370), so adoption needs an explicit mapping, not a
   substitution of β.

With the pair fixed, the emission scale stops being a free composite: it becomes a
quantity comparable against §2a's measured interval, and the Diamond Princess fit
(task #34) becomes a test of that interval rather than a search over it.

---

## 3. Nulls and standing gaps

- **No emesis titre measurement exists for GII.4.** Kirby's GII data are GII.2
  and GII.1; no GII.4 human challenge model has archived emesis quantified. Our
  arm's dominant genotype therefore has *no* direct emission measurement, and
  GII.2 is the closest available surrogate. Kirby's own 2016 statement that
  "there is no data available for the more common GII noroviruses" is now only
  partly retired — by GII.2, not by GII.4.
- **Norovirus airborne decay:** still no measurement (tranche 1). Unchanged.
- **Stool mass per illness:** still no distribution (tranche 3). Unchanged; Ge's
  total-copies measurement remains the route around it rather than a fill.
- **No human-challenge k for SARS-CoV-2.** §2b is the best available and it is
  deduced.

## 4. Repository changes in this document

Documentation only:

- this file;
- [`README.md`](README.md) index row;
- [`../norovirus/norovirus_open_ledger.md`](../norovirus/norovirus_open_ledger.md)
  — the emesis entry, because §1c invalidates the provenance recorded at the
  shipped constant;
- [`../covid/covid_parameter_provenance_audit.md`](../covid/covid_parameter_provenance_audit.md)
  — a pointer to §2, which is the pair that audit said was missing.

No constant, profile field, engine path or test changed.
