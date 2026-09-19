# NORO-DIAG-RECOVER-01
**Date:** 2026-09-19
**Commit:** 0f66954
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 46e103e

## Provenance

The numbers below were run in Devin session `40c2e15ce4b84e349b19094ec443984a`
("Crusher Noro2") on a working tree at or after `46e103e` (the merge of #607,
outbreak-disinfection metering), in the hours before that session crashed.
The session's VM did not come back, so the `noro_diag` scripts and the raw
output files are lost. What survives is the completed shell output recorded
in the session event stream, transcribed here verbatim. The exact tree the
diagnostics ran on cannot be re-verified; treat `Measured at` as a lower
bound, not a reproducible pin. Any successor must re-run before quoting these
as current.

## 1. Post-repair diagnostics: no secondary transmission on any route

Classic cruise diagnostic (`fl_norovirus_classic_cruise_1900`, dose rung 4,
`rung-reportable`, n = 1,910 agents, 288 hourly epochs, syndromic compliance
0.65 where marked):

```text
run_id,seed,num_agents,num_epochs,imports_epoch0,ever_infected,secondaries,last_infection_epoch,route_counts,route_dose_share,trigger_status
..._n1910_ep288_syndromic_comp65_s8000,8000,1910,288,4,4,0,0,{},{},ALERT
..._n1910_ep288_syndromic_comp65_s8001,8001,1910,288,5,5,0,0,{},{},ALERT
..._n1910_ep288_syndromic_comp65_s8002,8002,1910,288,5,5,0,0,{},{},ALERT
..._n1910_ep288_s8003,8003,1910,288,7,7,0,0,{},{},ALERT
```

On every seed `ever_infected == imports_epoch0`, `secondaries == 0`,
`last_infection_epoch == 0`, and `route_counts == {}`. The route attribution
dictionary is empty, not fomite-zero-others-nonzero: **nothing transmitted on
any route** after the disinfection-metering repair. This rules out the
working hypothesis that the blocker was fomite-specific.

Expedition-platform diagnostics (n = 450, 288 epochs):

```text
{'n_agents': 450, 'ever_infected': 0, 'emesis_event_count': 0, 'patch_pickups': 0, 'patch_pickup_mass': 0}
{'n_agents': 450, 'ever_infected': 1, 'emesis_event_count': 0, 'patch_pickups': 0, 'patch_pickup_mass': 0}
{'n_agents': 450, 'ever_infected': 2, 'emesis_event_count': 0, 'patch_pickups': 0, 'patch_pickup_mass': 0}
```

`emesis_event_count == 0` on every run. These runs therefore **did not test
the emesis / `EmesisPatch` pathway at all** (`EMESIS-FOOTPRINT-01`); they are
not evidence for or against it.

Sanitary-activity trace from the same batch: ~91,105 sanitary visits, 668
stool visits, 6,276 distinct dose recipients, `dose_delivered` 0.109 (units
as printed by the diagnostic; the script is lost). Dose *is* being delivered
to the sanitary route; recipients are not converting to infections.

## 2. Challenge trace: dose credited in full, hazard sum ≈ 0.2

A per-exposure challenge trace finished 47 s before the crash. Whole-run
summary:

```text
"naive_hazard_sum": 0.19714467880398973,
"naive_susceptibility_median": 3.984863006176259e-05,
"protection_values": [0.0],
"new_infections": 0,
"raw_accumulate_calls": 353711,
"raw_fomite_in_sum": 394281.2706410493,
"raw_fomite_in_max": 49572.22592691455,
"raw_fomite_credited_max": 49572.22592691455,
"pathways_seen": ["direct_contact", "fomite", "food", "hvac_airborne"]
```

Representative challenge records:

```text
{"epoch": 26, "agent": 1831, "resident": false, "p_dose": 17210.81535191113, "protection": 0.0, "effective": 17210.81535191113, "susceptibility": 3.557262812657965e-06, "hazard": 0.05938691047764205, "pathways": {"fomite:norwalk_gi": 17210.81535191113}, "infected_after": false}
{"epoch": 20, "agent": 1832, "resident": false, "p_dose": 15012.026968953065, "protection": 0.0, "effective": 15012.026968953065, "susceptibility": 1.0024679020838682e-12, "hazard": 1.5049075060355498e-08, "pathways": {"fomite:norwalk_gi": 15012.026968953065}, "infected_after": false}
```

Hazard is consistent with `1 − exp(−susceptibility × dose)` on the printed
fields (e.g. 1 − exp(−3.557e−6 × 17210.8) = 0.0594).

What this establishes (measured):

- Protection is zero; no immunity term is suppressing infection.
- Fomite dose reaching the accumulator is credited in full
  (`raw_fomite_in_max == raw_fomite_credited_max`).
- All four major pathways reach the challenge step.
- The **summed naive hazard over the whole run is 0.197** — the model expects
  about one fifth of one infection. Zero realised infections is the
  arithmetically expected outcome, not evidence of a structural blocker
  downstream of dose delivery.
- Per-host susceptibility draws span at least six orders of magnitude
  (3.6e−6 to 1.0e−12 in the two records above; median 4.0e−5).

## 3. Hypothesis (not measured)

The remaining gap is one to two orders of magnitude between delivered dose
(1e4 GEC-scale per exposure) and the per-host susceptibility draw (median
4e−5). That is a **dose-scale vs susceptibility-scale mismatch**, the same
seam as `DOSE-FRAIL-01` on the SARS-CoV-2 arm, inverted. This is a hypothesis
from one trace. The discriminating check is arithmetic on shipped
definitions, not a campaign: take the shipped `norwalk_gi` dose-response
parameters and per-host susceptibility draw, compute the expected hazard at
the delivered per-exposure doses above, and compare with the literature
ID50 for Norwalk (grade per `model-parameter-provenance`). Do not change a
constant on the strength of this entry.

## Successor work

Filed for the next bounded session, in order:

1. Susceptibility-vs-dose arithmetic on shipped definitions → ledger
   `NORO-SUSCEPT-01` (measured or closed), no constant change.
2. Only if (1) confirms a scale defect: literature-sourced repair as its own
   PR with provenance.
3. A diagnostic that forces `emesis_event_count > 0` before any claim about
   the emesis pathway is made.
4. Carrier-mediated onward contact (approved direction, unimplemented) as a
   separate session after (1)–(3).
