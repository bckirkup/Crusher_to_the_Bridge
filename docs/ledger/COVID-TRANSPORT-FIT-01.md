# COVID-TRANSPORT-FIT-01
**Date:** 2026-11-19
**Commit:** 106a3583
**Pathogens:** sars_cov2_resp
**Status:** measured

Re-scored the Diamond Princess (training hull) and Greg Mortimer
(held-out hull) outbreak replays after the ROOM-AIR-PAIRED-VALIDATION-01
airflow repairs (B1–B3, PRs #1330–1332) under both transport solvers:
the native ContamTransportEngine and the NIST ContamX binary. 140 cells,
zero failures, audit clean — DP `boxed_s1s2` @ Θ7.9e6 ×20 seeds ×2
engines; GM `hygiene_cycle` @ Θ2.37e11 ×50 seeds ×2 engines
(campaign `campaigns/covid/transport_fit_01`, arm key
`transport_engine: native|contamx`).

## Solver indistinguishability

Seed-paired contamx−native deltas centre on zero on every channel: DP
recorded_onsets Δ0 [0–4], lab_confirmed Δ0 [0–11], all share channels Δ0
within ±0.05; GM campaign_positives Δ−0.48 mean [−11,+7]. At the
voyage-outcome grain the HVAC transport operator choice does not matter —
the repaired model's dose is set upstream of it.

## DP vs record (both engines identical)

Median recorded_onsets 8 [0–121] vs 197; lab_confirmed 10.5 [0–145] vs
712; takeoff 9/20 seeds. When an outbreak lands: dated share ~0.8 vs
0.277, asym share ~0.22 vs 0.44, DP-scale crew share ~0.44 vs 0.29.
**The repaired airflow model under-carries DP ~30× relative to
CREW-REACH-01's pre-repair boxed baseline** (pooled ~1,351–1,453
lab_confirmed over 20 cells on the same design family). The takeoff
failure is new and is attributable to the airflow repairs' delivered
dose collapse, not solver or ascertainment. Composition residuals
(too-symptomatic, crew-loaded, dated-heavy) are the settled
ASC/DATING/CREW-REACH residuals unchanged.

## GM vs record

campaign_positives 110 [18–134] vs 128/217 — magnitude in the record's
neighbourhood, takeoff 48/50. Asymptomatic-at-testing share 0.24
[0.18–0.5] vs 0.8125 — the same symptomatic-overweight composition
residual, now on a held-out hull.

## Verdict

Native ≈ ContamX on both hulls (paired deltas ≈ 0): the transport-solver
question is closed at this grain — use whichever is cheaper. The real
finding is negative: after the B1–B3 airflow repairs the DP replay no
longer produces a record-scale outbreak at Θ7.9e6, so every
composition comparison sits on a mostly-fizzled ensemble. Next
measurement target: which repair (room-air removal ambient exchange,
near-field, pool transport, duty-0 terminal) removed the delivered dose
— paired-arm cell runs per repair flag.

Full table: `campaigns/covid/transport_fit_01/LEDGER.md`; readout:
`campaigns/covid/transport_fit_01/readout.py`.
