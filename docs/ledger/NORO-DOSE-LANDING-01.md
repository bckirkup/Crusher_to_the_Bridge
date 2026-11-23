# NORO-DOSE-LANDING-01
**Date:** 2026-11-23
**Commit:** d752427e
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** f357dd16

Post-hoc decomposition of `noro_external_sequester_01` artifacts (the
20 arm-S+R cells measured in `NORO-EXTERNAL-SEQUESTER-01`, image
`sha256:d92f1d4c` at code `f357dd16`, `classic_cruise_1900`, seeds 8000–8019) to locate the
bound the sequester verdict left open: mouth-dose → infection.

## Measurement (seed 8016, arm S+R — worked example)

`per_host_dose_challenge_sequester_sr_seed8016.json.gz` joined to the
cell's `hand_partition`:

- `sink_mouth_pickup` 29,596 + `sink_mouth_residual` 42,060 ≈ **71.7k
  GEC mouthed**; `credited_raw` on susceptibles ≈ 21.0k → **~70% of
  mouthed mass is swallowed by already-infected carriers** whose mouths
  never become challenges (superinfection closed without a registry).
  Biologically real — dead mass, not a defect.
- Credited → scaled ≈ 6.0k GEC after `susceptibility_multiplier` and the
  class gate; **72% of scaled mass sits on host 1449** (raw 13,435 →
  4,299, secretor-negative 260/260 crediting epochs,
  `dose_response_susceptibility` s = 6.9e-9, hazard 3e-5); top-2 hosts
  ≈ 90%. `naive_hazard` 0.568 → 1 secondary at hazard 0.00023.
- Draws verified honest: 1521 challenged hosts, mean s = 0.00338 ≈
  E[Beta(0.111, 32.81)] = 0.00337, matching quantiles — the
  DOSE-FRAIL-01 class of wiring bug is ruled out for this path.
  Dose-weighted s = 1.0e-4 (≈33× below the unconditional mean).

## Hot contrast (same decomposition)

- Seed 8000 (hot): 4.26M raw credited across ≥36 hosts (90% mass over 36
  hosts, max share ~6%) → naive 33.7 → 36 secondaries.
- Seeds 8018/8009 (cold): naive 2.09 / 0.46; 8009 has 76% of mass on one
  host.

## Read

Mouth dose reaches hands and the challenge resolves booked hazard
faithfully (182 secondaries vs 184 summed naive hazard,
NORO-DOSE-LEDGER-01). The binding structure is **where the dose lands**:
(a) a ~70% dead-mouth share on uninfectable carriers; (b) a
concentration lottery — cold-cell take-off is decided by one or two
Beta(0.111, 32.81) draws; (c) survivorship enrichment — the dominant
carriers are exactly the hosts the challenge cannot convert (~20% of
crediting epochs on 8016 were secretor-negative). The remaining
structural lever is carrier redistribution: under `shedders_only` a
loaded non-shedder is a dead end on surface redeposit, food deposit and
hand→hand donation alike. This motivates the CARRIER-DISTRIBUTE (D3″)
proposal, `docs/proposals/hand_carrier_distribute_spec.md`
(`hand_redeposit_mode: "carriers"` + new `hand_donor_mode`), and is its
§0 settled input.
