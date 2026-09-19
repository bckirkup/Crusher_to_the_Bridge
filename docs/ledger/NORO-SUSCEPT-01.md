# NORO-SUSCEPT-01
**Date:** 2026-09-19
**Commit:** 56edddf
**Pathogens:** norwalk_gi
**Status:** closed
**Closed by:** `NORO-SUSCEPT-02` (measured at 9f4cd79)

Analysis only. **No constant is changed by this entry and none is recommended
for change.** Every figure below is either read from a definition site, derived
from one by arithmetic reproducible with
`tools/noro_diag/susceptibility_dose_table.py`, or a recovered diagnostic
supplied by the operator and recorded here because it exists nowhere else in
the repository.

## 1. Recovered diagnostics from the crashed Noro2 session

These are the operator's settled inputs from the crashed session's event
stream. They were not reproduced here and carry no `Measured at` SHA; they are
recorded so they are not lost a second time.

| Quantity | Value |
|---|---|
| 12-seed post-repair runs, classic / expedition | 1,910 / 450 agents, 288 epochs |
| `ever_infected` | equals `imports_epoch0` exactly, every seed |
| `secondaries`, `last_infection_epoch`, `route_counts` | 0, 0, empty |
| `emesis_event_count`, `patch_pickups` | 0, 0 — the emesis pathway was never exercised |
| Sanitary activity in the same runs | 91,105 visits, 668 stool visits, `dose_delivered` 0.109 |
| Forced-challenge trace: `protection` | 0.0 for every host |
| `raw_fomite_in_max` = `raw_fomite_credited_max` | 49,572 GEC (dose credited in full) |
| `raw_fomite_in_sum` | 394,281 GEC over 353,711 accumulate calls |
| `naive_susceptibility_median` | 3.98e-05, individual draws to 1.0e-12 |
| `naive_hazard_sum`, whole run | 0.197 |
| Worked example | agent 1831, dose 17,211 GEC, s = 3.557e-06, hazard 0.0594 |

## 2. The shipped dose-response, quoted at its definition

`data/pathogens/active_profiles.json`, profile `norwalk_gi`:

```json
"dose_response": {"model": "beta_poisson", "alpha": 0.111, "beta": 32.81}
```

The engine does **not** evaluate the population beta-Poisson curve per host. It
draws one persistent frailty per host and exponentiates
(`engines/transmission_core.py`):

```python
        draw = float(
            self.rng.beta(dr.get("alpha", ALPHA), dr.get("beta", BETA)),
        )
        susceptibility = (
            draw * self._beta_poisson_susceptibility_scale(pathogen_id, dr)
        )
        agent.dose_response_susceptibility[pathogen_id] = susceptibility
```

```python
        susceptibility = self._dose_response_susceptibility(agent, pathogen_id)
        return -math.expm1(-susceptibility * effective_dose)
```

Provenance, from `docs/parameter_provenance_register.md` (row
`dose_response.alpha / beta`), class **M (form and value)**, state **declared
and swept**: the pair is the disaggregated GI.1 challenge arm of Teunis 2008
(Teunis's own body text and Table III are **?nr** — paywalled, abstract only;
the attribution is carried at **Sec** on a collaborator bundle). The human GII
evidence maps to **α ∈ [0.072, 0.161]** at fixed β, and the dose axis to
**ID50 ∈ [1.32e3, 1.69e4] gEq**. The live per-agent path has an exact
confluent-hypergeometric N50 of **16,644 copies**. The dose unit is closed:
administered genome copies (gEq/GEC).

## 3. Table 1 — implied susceptibility quantiles and 50%-hazard doses

Beta(0.111, 32.81); mean s = 3.3717e-03; median s = 3.676e-05, which reproduces
the recovered `naive_susceptibility_median` of 3.98e-05. Dose for a 50%
single-epoch hazard is `ln 2 / s`.

| Quantile | Susceptibility | Dose for 50% host hazard (GEC) |
|---:|---:|---:|
| 1% | 1.815e-20 | 3.82e+19 |
| 5% | 3.597e-14 | 1.93e+13 |
| 10% | 1.853e-11 | 3.74e+10 |
| 25% | 7.127e-08 | 9.73e+06 |
| **50%** | **3.676e-05** | **1.886e+04** |
| 75% | 1.477e-03 | 4.69e+02 |
| **90%** | **9.445e-03** | **7.34e+01** |
| 95% | 1.955e-02 | 3.55e+01 |
| 99% | 5.036e-02 | 1.38e+01 |
| 99.9% | 1.015e-01 | 6.83e+00 |

**Against the recovered delivered fomite doses of 1.5e4 to 5e4 GEC:**

- The **median** host's 50%-hazard dose, 18,860 GEC, lies **inside** the
  delivered range. At 15,000 GEC the median host's hazard is 0.424; at 50,000
  it is 0.841.
- The **90th-percentile** host needs 73 GEC, i.e. 200–680× less than the
  delivered doses.
- The closed-form population N50 is 16,871 GEC (1.3% above the live path's
  16,644), also inside the delivered range.

**The median host is therefore not unchallengeable at realistic fomite load.**
The inverted-DOSE-FRAIL-01 hypothesis is not supported in magnitude by this
table: the frailty distribution puts the median host's threshold in the middle
of the doses actually delivered, not one to two orders above them.

## 4. Which side is out by the one-to-two orders — neither, on this evidence

### 4a. The dose-response pair cannot supply the discrepancy

α = 0.111 lies inside the sourced interval [0.072, 0.161] and within 3% of its
geometric centre. Moving α to the interval's *top* at fixed β takes the
population N50 from 16,871 to 2,398 GEC — a factor of **7.0, less than one
order**. The full sourced dose-axis span [1.32e3, 1.69e4] gEq is **1.1 orders
end to end**, and the register records it as a distance between studies of two
different genogroups rather than a measurement of one quantity: Rouphael 2022's
GII.2 ID50 of 5.1e5 sits ≈30× *above* 16,644 while Atmar 2014's GI.1 HID50 of
1,320–2,800 gEq sits 5.9–12.6× *below* it — opposite directions. There is no
admissible move of this pair that is worth two orders, and no interior
preference in the interval is supported.

### 4b. The dose chain reproduces the only shipboard measurement there is

The pickup chain is `density × hand_area × used_fraction × transfer_efficiency`
(`_fomite_pickup_request_for_area`), then the mouth leg. With the shipped
distributions at their medians — hand area 490 cm², `SURFACE_CONTACT_FRACTION`
0.129, surface→hand lognormal(-2.1, 1.4) median 0.122, `MOUTH_CONTACT_FRACTION`
0.01, `HAND_TO_MOUTH_NORMAL` mean 0.339 — one touch-and-mouth pair delivers
**density × 2.61e-02 GEC**. The recovered trace's mean of 1.11 GEC per
accumulate call therefore implies a touch-weighted surface density of ≈42
GEC/cm².

Park et al. 2015 (doi:10.1128/aem.01657-15) is the out-of-sample check and
nothing was fitted to it: 80–31,217 copies/swab in sick passengers' cabins,
16–113 in public spaces (Grade **A** for the measurement, **B** as shipboard
analogue for the LOD row; recorded in
`docs/norovirus/environmental_observation_v1.md` §2). At the shipped swab area
and the sourced recovery interval [0.023, 0.80] that is ≈0.2 to 1.4e4 GEC/cm².
The repository's own recorded prediction against it is 1,434 copies/swab in
sick cabins and 59 in public spaces, both inside the observed ranges
(`docs/norovirus/norovirus_open_ledger.md` §3). **The surface end of the chain
is not one to two orders low; it is inside the only shipboard measurement.**

Sustaining the median host's 18,860 GEC over the trace's ≈185 accumulate calls
per agent needs ≈3,905 GEC/cm² — which is *also* inside Park's sick-cabin
range, and far above his public-space range. The shipped chain and the shipped
dose-response together therefore say: a host living in a symptomatic case's
cabin is challengeable; an ordinary passenger touching public surfaces is not.
That is the shape of shipboard norovirus epidemiology, not a defect.

### 4c. Emesis titre is, if anything, high — and it never fired

`EMESIS_TITRE_GEC_PER_ML_RANGE = (1.6e5, 8.0e5)` with
`EMESIS_VOLUME_ML_RANGE = (50.0, 800.0)` gives 8e6–6.4e8 GEC per episode. The
independent retrieval this pass (Consensus, abstract only — origin **Ab**):

| Source | Measurement | Grade |
|---|---|---|
| Kirby et al. 2016, PLoS ONE, doi:10.1371/journal.pone.0143759, Abstract Results | mean emesis titre **8.0e5 GEC/mL (GI)** and **3.9e4 GEC/mL (GII)**, p = 0.02; average subject shed **1.7e8 GEC** in emesis | B, origin Ab (human challenge adults; GII.2 standing in for GII.4) |
| Atmar et al. 2014, J Infect Dis, doi:10.1093/infdis/jit620, Abstract Results | norovirus in 15/27 (56%) vomitus samples, **median 41,000 gEq/mL** (GI.1) | B, origin Ab |

The shipped range's upper bound is Kirby's **GI** mean. This profile declares
GII genotypes, and Kirby's GII mean is 3.9e4 GEC/mL — **4 to 20× below the
shipped range**, as is Atmar's measured median of 4.1e4. The emesis titre is
not a candidate for a missing one to two orders in the upward direction; the
open question it raises points the other way and is left to
`EMESIS-FOOTPRINT-01` and ledger item 13. Note only that one vomiting host's
per-illness emesis output (1.7e8 GEC, Kirby) is **430×** the entire recovered
voyage's mouth-credited fomite dose of 3.94e5 GEC, and that
`emesis_event_count = 0` in every diagnostic run: the pathway that carries most
of the real dose was inert in the runs the conclusion is being drawn from.

### 4d. The delivered dose in aggregate is not small — the arithmetic that matters

The recovered numbers do not describe a model that delivers too little dose:

| Derived quantity | Value |
|---|---|
| Mean per-host credited dose, 394,281 / 1,910 | **206.4 GEC** |
| Shipped population response at 206.4 GEC | **0.1977** |
| Expected infections if that dose were spread evenly over 1,910 hosts | **≈378** |
| Expected summed hazard if dose allocation were independent of the frailty draw, `E[s] × ΣD` | **1,329** |
| Dose-weighted mean susceptibility implied by the observed `naive_hazard_sum`, 0.197 / 394,281 | **4.996e-07** |
| That against the shipped mean (3.372e-03) and median (3.676e-05) | **6,750× and 73.6× below** |

Scaling the worked example is the same story in one line: agent 1831's own
susceptibility, 3.557e-06 — already 10× sub-median — applied to the whole
credited dose gives a summed hazard of **1.40, seven times the observed 0.197**.

Monte Carlo over the number of hosts sharing the 394,281 GEC
(`tools/noro_diag/susceptibility_dose_table.py`, 20,000 replicates, seed 8105):

| Hosts sharing the dose | Median summed hazard | P(sum ≤ 0.197) |
|---:|---:|---:|
| 1 | 1.00 | 0.314 |
| 2 | 1.04 | 0.116 |
| 5 | 3.00 | 0.0066 |
| 10 | 5.45 | 0.0001 |
| 50 | 22.8 | 0.0000 |
| 200 | 73.5 | 0.0000 |
| 1,910 | 379.5 | 0.0000 |

**This is the finding.** A summed naive hazard of 0.197 against 394,281 GEC of
credited dose is an ordinary draw only if the dose effectively reached **one or
two hosts**. It is already a 1-in-150 outcome at five hosts and numerically
impossible at ten. But the accumulator made 353,711 calls across 1,910 agents
over 288 epochs — ≈185 calls per agent — and the recovered per-host maximum of
49,572 GEC is only 12.6% of the total, which by itself requires at least eight
hosts to hold the rest. **The credited dose and the evaluated hazard are not
being taken over the same host set.** That is a plumbing question, not a
parameter question, and it is not one the recovered numbers can close.

## 5. Code path shared with DOSE-FRAIL-01 — verified, and the analogy does not carry

Verified rather than assumed. Both pathogens resolve susceptibility through the
same seam, `TransmissionCore._dose_response_susceptibility` →
`_dose_response_hazard`, called from `_resolve_pathogen_challenge`. There is no
norovirus-specific branch.

The branch *inside* that seam differs by declared model, and that is the whole
of DOSE-FRAIL-01: the COVID Θ fit arm declared `{"model": "exponential",
"k": Θ}`, and the exponential branch returns `k` itself, giving every host one
identical susceptibility. `norwalk_gi` declares `beta_poisson`, takes the
`rng.beta` branch, and carries full per-host frailty — the recovered draws
spanning 1.0e-12 to the median 3.98e-05 are that branch working. The two arms
share the code path; norovirus never enters the defective branch. The inverted
form of the defect — frailty so dispersed that the typical host is
unchallengeable — is **refuted by §3**: the median host's threshold sits inside
the delivered dose range.

What the seam *does* contribute is second-order and worth recording: frailty is
frozen per host for the voyage, so repeated small doses to a low-draw host are
permanently wasted rather than independently resampled. At the mean per-host
dose of 206 GEC that costs a factor of ≈2.5 against a fresh draw per epoch
(0.198 frozen against 1 − exp(−E[s]·D) = 0.50), not orders of magnitude.

## 6. Recommendation

**Change nothing.** Neither the dose-response pair nor any dose-chain constant
is indicted by this arithmetic:

- α = 0.111 is inside its sourced interval and its most extreme admissible move
  is worth 7×, not 100× (§4a).
- The fomite chain's surface end reproduces Park 2015 out of sample (§4b), and
  the emesis titre is high for GII rather than low (§4c).
- The delivered dose in aggregate implies ≈378 expected infections if it were
  spread over the complement; the shortfall is in *allocation*, not magnitude
  (§4d).

The next session's paired-seed measurement (8105/8106, per the
`stochastic-attribution` skill) should be the **joint distribution of credited
dose and drawn susceptibility per host**, not a parameter sweep. Specifically:
dump `(agent_id, Σ credited dose over the voyage, dose_response_susceptibility,
infection state at each crediting epoch)` for every agent, and answer:

1. How many hosts hold 90% of the 394,281 GEC? §4d says the hazard sum implies
   one or two; the call count and the 12.6% maximum say at least eight. Those
   cannot both be right.
2. Is dose being credited to hosts that are never challenged — already
   infected, recovered, secretor-negative (`secretor_negative_fraction` 0.20 at
   relative susceptibility 0.20), or shedders excluded at the challenge?
3. Does the challenge read the same dose the accumulator records, or a
   per-epoch residue of it?
4. Why is `emesis_event_count` 0 when `clinical_presentation.symptom_axis_prob\
abilities.vomiting` is 0.72 and `severity_model` puts 75% of infections in a
   symptomatic class? An imported index case should draw an emesis schedule
   through `draw_emesis_schedule` (`engines/initiation.py:1518`). Confirm it
   fires before any conclusion is drawn from a run in which it did not.

Only if (1)–(3) come back clean is there a case that the expectation itself is
wrong, and at that point the admissible move is α within [0.072, 0.161] with β
held fixed, as a swept axis — not a refit, and never chosen against VSP.

## Resolution

`NORO-SUSCEPT-02` measured (1)–(4) on paired seeds 8105/8106, classic hull, 288
epochs, and closes this entry. Measured there: 106 and 48 hosts hold 90% of the
credited dose; zero hosts and zero GEC are credited to a host that is never
challenged; the challenge reads the same per-epoch dose the accumulator
credited, and Σ credited dose reconciles with Σ evaluated hazard exactly over
the same host set; the emesis pathway fires end-to-end to a patch pickup that
delivers mass to a host's hands.

The §1 recovered figures were never reproduced and carry no `Measured at` SHA.
The measured credited dose at the same seam, same hull, same epoch count is
0.101 GEC (seed 8105) against the recovered 394,281 GEC — five to six orders of
magnitude apart, the size of the fomite transfer chain below hand load.
**`raw_fomite_in_sum` = 394,281 GEC, `raw_fomite_in_max` = 49,572 GEC and
`naive_hazard_sum` = 0.197 are void as credited-dose and hazard figures and
must not be quoted; see `NORO-SUSCEPT-02` §d.** Nothing in §2–§4 of this entry
is indicted: the dose-response pair, the frailty draw and the arithmetic are
unchanged and were reproduced by the measurement.
