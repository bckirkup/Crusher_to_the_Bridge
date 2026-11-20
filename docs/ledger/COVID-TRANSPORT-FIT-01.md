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

## Provider comparison (corrected 2026-11-20)

The first version of this section said the paired deltas "centre on
zero on every channel", quoted "[0–4]", "[0–11]" and "[−11,+7]" as if
they were ranges, put all DP share deltas within ±0.05, and concluded
the operator choice "does not matter" because dose "is set upstream of
it". A re-read of the same 140 cells does not support that wording.

- The bracketed pairs were the readout's nearest-rank q05–q95. Observed
  Δ (ContamX − native) ranges: DP recorded_onsets −9 to +39, DP
  lab_confirmed −3 to +50, GM campaign_positives −15 to +10.
- DP: 17 of 20 pairs are identical on onsets, confirmations, positives
  and infections; three are not — (onsets, confirmations) (−9, −3),
  (+4, +11), (+39, +50). Mean Δ onsets +1.70 (paired-t 95% −2.54 to
  +5.94), confirmations +2.90 (−2.43 to +8.23). One seed carries
  three-quarters of the absolute difference, and leaving it out turns
  the onset mean negative, so the mean is not a stable summary.
- DP share deltas exceed ±0.05 on dated share (to −0.092) and final
  asymptomatic share (to +0.080), over the 16 pairs where they are
  defined.
- GM: 37 of 50 pairs differ on at least one count, both directions;
  campaign_positives mean Δ −0.48 (−1.83 to +0.87), recorded_onsets
  −0.40 (−1.41 to +0.61).
- Takeoff (≥10 onsets) agreed in all 70 pairs: DP 9 both / 11 neither,
  GM 48 both / 2 neither. Zero observed flips bounds the flip rate only
  loosely (one-sided 95% upper limits 0.139 and 0.058).

What stands: the two providers gave close voyage-wide counts and the
same takeoff classification on these seeds. What does not: any
equivalence claim (no margin was declared), and any statement about
where dose is set — this campaign did not measure dose. The DP pair
also differs in image (canary `sha256:7023d963…` vs `sha256:56f860c8…`).
Tables, method and receipts:
`campaigns/covid/transport_fit_01/READOUT_PAIRED.md`.

## DP vs record (medians equal under both engines)

Median recorded_onsets 8 [q05–q95 0–121; max 454 native, 493 ContamX]
vs 197; lab_confirmed 10.5 [q05–q95 0–145; max 540, 590] vs
712; **takeoff 9/20 seeds**. Pooled lab_confirmed 1,236–1,294 across
20 cells vs CREW-REACH-01's ~1,351–1,453 on the same boxed design
family — pooled volume is roughly preserved, so the ensemble is now a
few record-scale cells carrying a mostly-fizzled set: the airflow
repairs cut outbreak *frequency*, not dose volume. When an outbreak
lands: dated share ~0.8 vs 0.277, asym share ~0.22 vs 0.44, DP-scale
crew share ~0.44 vs 0.29 — the settled ASC/DATING/CREW-REACH
residuals unchanged.

## GM vs record

campaign_positives 110 [q05–q95 18–134; range 1–135] vs 128/217 — magnitude in the record's
neighbourhood, takeoff 48/50. Asymptomatic-at-testing share 0.24
[0.18–0.5] vs 0.8125 — the same symptomatic-overweight composition
residual, now on a held-out hull.

## Verdict

Native and ContamX agree on takeoff in every pair and give equal (DP)
or close (GM: positives 110 vs 110.5, onsets 50.5 vs 49.5) voyage-wide
medians, with seed-level differences up to tens of cases (section
above). "Use whichever is cheaper" is withdrawn: no timing was read when
it was written, and the timing now tabulated in `READOUT_PAIRED.md`
(Batch child medians within 1.1%; a cold ContamX build 55–385 ms slower
in the engineering benchmark) is not a matched cost comparison. The
other finding is negative: after the B1–B3 airflow repairs DP takeoff is
~45% at Θ7.9e6 where the record always took off, so every composition
comparison sits on a mostly-fizzled ensemble. That before/after
contrast is against an earlier campaign, not a paired arm here, so the
attribution to the repairs is a hypothesis. Next measurement target:
which repair (room-air removal ambient exchange, near-field, pool
transport, duty-0 terminal) cut realization frequency — paired-arm cell
runs per repair flag.

Full table: `campaigns/covid/transport_fit_01/LEDGER.md`; readout:
`campaigns/covid/transport_fit_01/readout.py`; paired readout and
verifier: `READOUT_PAIRED.md`, `paired_readout.py` in the same directory.
