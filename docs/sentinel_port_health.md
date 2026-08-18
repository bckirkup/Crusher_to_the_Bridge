# Port public health surveillance

What a port's *own* public health system observes, independently of any ship.

| Item | Value |
|---|---|
| Model | `picard_framework/analysis/sentinel/port_health.py` |
| Profile libraries | `picard_framework/analysis/sentinel/port_profiles.py` + `data/port_surveillance_<region>.json` |
| Ledger generation / ablation / CLI | `picard_framework/analysis/sentinel/port_ledger.py` |
| Schemas | `schemas/port_surveillance.schema.json` (profiles), `schemas/port_surveillance_ledger.schema.json` (generated data) |
| Tests | `tests/test_port_health_surveillance.py` |

## Why

The sentinel estimator infers a per-port hazard `λ_p` from ship data. Nothing in
the ship's own observations can validate that number — the ship is both the
instrument and the subject. A port authority is the independent view: the same
community prevalence that infects a passenger ashore also drives the port's
syndromic reports and its municipal sewage. So

```
corr(inferred λ_p, port observed signal)
```

is a validation where the port has surveillance, and where it does not, the
absence *is* the value proposition: the ship is the only pathogen-level
instrument calling at Cozumel, Costa Maya, or Ketchikan.

## Universal generation, analysis-time ablation

**Every port generates every channel, every day, regardless of capability.**
`generate_port_signals` never returns `None`. A port with no municipal WBE
programme still gets a `wbe_gc_per_l_observed`: the sewage exists whether or not
anyone samples it, and the counterfactual is precisely what quantifies the gap
("what would Cozumel have seen running what Miami runs").

Capability is metadata carried next to the signals (`wbe_capable`,
`syndromic_capable`, `lab_capable`, `genotyping_capable`, `reports_to`,
`reporting_threshold`). Suppression happens later, at fleet-analysis time:

```python
from picard_framework.analysis.sentinel.port_ledger import ablate_ledger

realistic     = ablate_ledger(ledger)                                  # what these ports run
wbe_only      = ablate_ledger(ledger, channels=["wbe"])                # single-channel arm
no_port_data  = ablate_ledger(ledger, channels=[])                     # ship-only arm
counterfactual = ablate_ledger(ledger, respect_capability=False)       # if everyone had everything
```

Two independent switches, because they answer different questions: `channels` is
the analyst's ablation, `respect_capability` is the realism filter. An ablation
is a *view* — the generated ledger is never edited, so all four arms above come
from one generation run and are directly comparable.

Truth columns (`true_community_prevalence`, `true_incidence_per_100k_day`,
`true_ww_gc_per_l`) are never ablated: they are the comparison target and were
never observable in the first place.

## The chain from truth to signal

```
prevalence          = λ_p / hazard_per_prevalence_hour
incidence/100k/day  = prevalence / infectious_days * 1e5
true cases          = Poisson(incidence * population)
reported cases      = Binomial(true cases, syndromic_coverage)      [+ delay]
lab confirmed       = Binomial(reported cases, lab_confirmation_fraction)
gc/L                = prevalence * gc_per_person_day / municipal_l_per_person_day
observed gc/L       = 10 ** (log10(gc/L) + Normal(0, wbe_log10_noise_sd))
wbe detected        = observed gc/L >= wbe_lod_gc_per_l
```

`PrevalenceLink` holds every constant in that chain in one object, because the
whole validation argument rests on the port side and the ship side sharing one
latent prevalence. Defaults:

| Constant | Value | Note |
|---|---|---|
| `hazard_per_prevalence_hour` | 0.1 | ~2 community contacts/hour ashore × ~5% per contact |
| `infectious_days` | 2.0 | norovirus infectious duration |
| `gc_per_person_day` | 1e10 | shared with the shipboard assay layer |
| `municipal_l_per_person_day` | 200 | vs 30 L/person/day of shipboard blackwater |

Two consequences worth stating:

- The scan's hazard ladder (1e-4 … 0.015 per person-hour) maps to **0.1% … 15%**
  community prevalence — background to frank outbreak.
- The municipal denominator is ~7× the shipboard one, so a port needs a much
  lower LOD than a ship to see the same prevalence. A ship's holding tank is a
  *concentrator*.

## Alert levels

`normal`, `elevated`, `outbreak`, `unknown`. Escalation runs on the **reported**
rate, so a low-ascertainment port escalates later than a high-ascertainment one
at identical true prevalence — that asymmetry is a finding, not something to
normalize away. Defaults: elevated ≥ 50/100k/day, outbreak ≥ 200/100k/day.

Municipal WBE escalates on **concentration**, not on detection
(`wbe_elevated_gc_per_l`, default 1e6 gc/L ≈ 2% prevalence): at municipal
dilution a qPCR assay detects background norovirus every single day, so
"detected" carries no alerting information.

A port with every channel ablated reads `unknown`, never `normal` — an
uninstrumented port has no evidence of quiet, only an absence of evidence.

## Reporting pathways

`CDC_VSP`, `CARPHA`, `ECDC`, `WHO_IHR`, `local_only`.

| Pathway | Modelled as |
|---|---|
| CDC Vessel Sanitation Program | US homeports; 3% AGE reporting threshold, arrival screening |
| CARPHA Regional Tourism Health | Caribbean; syndromic only, **no** wastewater |
| EU SHIPSAN / ECDC | European ports; syndromic *and* municipal WBE, short delays |
| WHO IHR | Ports whose notifications run through the international pathway |
| local_only | No external reporting; the signal stops at the municipality |

## Port profile libraries

Four cruise theatres, as data rather than code:

| Region | Ports | Character |
|---|---|---|
| `caribbean` | USMIA, MXCZM, MXCTM, KYGEC, BSBGI, BSNAS, PRSJU, JMOCJ | The surveillance desert: CARPHA syndromic reporting, almost no WBE |
| `mediterranean` | ESPMI, GRPIR, ITCIV, FRMRS, HRDBV, TRIST | ECDC coordination, EU sewage sentinel WBE |
| `nordic` | DKCPH, NOOSL, SESTO, DEKEL, ISREY | Best instrumented: 1–2 day delays, high coverage, low LODs |
| `alaska` | USSEA, USJNU, USKTN, USSIT, CAVAN | US pathways, tiny catchments — the noisiest Poisson regime |

The four ports of `sentinel_ww_ops_scan_v1` (USMIA, MXCZM, MXCTM, KYGEC) are all
profiled. A port called by an itinerary but absent from every library gets a
local-only authority from `capability_or_default` rather than a hole in the
ledger, so ledger coverage never depends on profile completeness.

## Generating a ledger

From explicit hazards:

```bash
python3 -m picard_framework.analysis.sentinel.port_ledger \
  --hazard USMIA=0.0001 --hazard MXCZM=0.001 --hazard KYGEC=0.0001 \
  --pathogen norovirus --days 7 --seed 501 \
  --channels syndromic,wbe --out tmp_port_health_out
```

writes `port_surveillance_ledger.json` (the full generation), the ablated
`port_surveillance_analysis.json`, and `port_signal_table.json` (per-port
summaries a hazard correlation consumes).

From a voyage itinerary, reusing the hazards the simulation actually applied:

```python
from picard_framework.analysis.sentinel.port_ledger import ledger_from_itinerary

ledger = ledger_from_itinerary(voyage["itinerary"], pathogen="norovirus", seed=501)
```

`hazards_from_itinerary` collapses repeated calls at one port (the home port is
called twice) to a single hazard, since the hazard is a property of the community
and not of the visit.

Each port draws from its own RNG stream keyed by UN-LOCODE, so adding a port to
an itinerary cannot renumber another port's draws.

## Limitations

- **Flat community prevalence.** A port's prevalence is constant across the
  window because the campaign's port hazards are themselves constant per port.
  Inventing a community epidemic curve here would put structure in the port
  signal that the ship-side truth does not have.
- **No feedback onto the ship.** Arrival screening and departure health
  certificates are recorded as capability metadata; they do not (yet) alter
  boarding or the ship's own observations.
- **`hazard_per_prevalence_hour` is an assumption, not a measurement.** Every
  correlation between an inferred hazard and a port signal inherits it. It is
  stated as one named constant precisely so a reviewer can move it.
- **Signals are per-day.** Sub-daily port dynamics are out of scope; the ship's
  epoch grid is finer than the port's reporting grid, which is realistic.
