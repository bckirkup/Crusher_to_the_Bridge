# COVID-TRANSPORT-FIT-01
**Date:** 2026-11-19
**Commit:** 106a3583
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 106a3583

Re-scored the Diamond Princess (training hull) and Greg Mortimer
(held-out hull) outbreak replays after the ROOM-AIR-PAIRED-VALIDATION-01
airflow repairs (B1–B3, PRs #1330–1332) under both transport solvers (the 20-cell dp_contamx_canary ran at
8de77294 — identical voyage code, predating only the fail-closed cell
check and GM funnel_echo):
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
712; **takeoff 9/20 seeds**. Pooled lab_confirmed 1,236–1,294 across
20 cells vs CREW-REACH-01's ~1,351–1,453 on the same boxed design
family — pooled volume is roughly preserved, so the ensemble is now a
few record-scale cells carrying a mostly-fizzled set: the airflow
repairs cut outbreak *frequency*, not dose volume. When an outbreak
lands: dated share ~0.8 vs 0.277, asym share ~0.22 vs 0.44, DP-scale
crew share ~0.44 vs 0.29 — the settled ASC/DATING/CREW-REACH
residuals unchanged.

## GM vs record

campaign_positives 110 [18–134] vs 128/217 — magnitude in the record's
neighbourhood, takeoff 48/50. Asymptomatic-at-testing share 0.24
[0.18–0.5] vs 0.8125 — the same symptomatic-overweight composition
residual, now on a held-out hull.

## Verdict

Native ≈ ContamX on both hulls (paired deltas ≈ 0): the transport-solver
question is closed at this grain — use whichever is cheaper. The real
finding is negative: after the B1–B3 airflow repairs DP takeoff is
~45% at Θ7.9e6 where the record always took off, so every composition
comparison sits on a mostly-fizzled ensemble. Next measurement target:
which repair (room-air removal ambient exchange, near-field, pool
transport, duty-0 terminal) cut realization frequency — paired-arm cell
runs per repair flag.

Full table: `campaigns/covid/transport_fit_01/LEDGER.md`; readout:
`campaigns/covid/transport_fit_01/readout.py`.
