# QUAR-ATTR-V2
**Date:** 2026-09-20
**Commit:** d62f10d
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** d62f10d

## Hypothesis

Same as QUAR-ATTR-V1, re-measured on the repaired engine: which transmission
channel carries infections into the confined population during the enforced
quarantine (day 16 on). The design, arms, seeds and frozen criterion are
unchanged (`picard_framework/runs/covid_quarantine_attribution_v1_design.json`,
six arms × Θ {1e5, 1e9} × 20 seeds); only the engine moved, `861a0b9` →
`d62f10d` (REINFECT-01, `docs/ledger/REINFECT-01.md`).

## Evidence for

- Under the now-valid frozen criterion at Θ 1e9, two channels are
  **load-bearing**: confining the crew (A1) cuts the conditional
  during-quarantine median 829.5 → 212.5 (−74%, n = 12 overlapping takeoff
  seeds) and removing cross-zone pool transport (A2) cuts 348.5 → 119
  (−66%, n = 8). Both together (A4) cut 119 → 59 (−50%, n = 7) on a
  survivor-biased set — A4 also suppresses takeoff itself 12/20 → 8/20.
- Post-fix the measure *is* the first-infection count:
  `infections_during_quarantine == ledger_events_during` in all 240/240
  cells (measured), confirming both the fix and v1 §5's post-hoc ledger
  reading, whose shifts it reproduces (v1 ledger −76%/−65%/−85% vs v2
  −74%/−66%/−50%).
- Canary parity: A0 seed `20200205` at `d62f10d` is byte-identical to the
  `7f105a7` readings (Θ 1e5: 950/0.2560/745-198-7; Θ 1e9:
  3458/0.9318/3414-43-1).

## Evidence against / limits

- Near-field air (A3) is non-load-bearing at Θ 1e9 (+19%, n = 8).
- At Θ 1e5 only 3/20 seeds take off per arm; nothing is decidable at that Θ.
- A5 (all shared air off) collapses takeoff (1/20 at 1e9, 0/20 at 1e5);
  uninterpretable for the window.
- Removing reinfection barely moved A0's Θ 1e9 attack rate (0.314 → 0.310)
  while cutting the saturated seed's during-window count 973 → 43 — the
  reinfection inflation lived in the window counts, not in distinct-host
  totals.
- The cell payload carries no `episode`/`first_infection_epoch` field;
  first-infection counting is asserted by the ledger identity and the
  probe, not readable off the payload (see readout §6).

## Supersedes

- QUAR-ATTR-V1's frozen-criterion verdict ("no single channel is
  load-bearing at either Θ", measured at `861a0b9`) is **void** — the
  measure counted second episodes (REINFECT-01). The readout is
  `docs/covid/covid_quarantine_attribution_v2_readout.md`; surface CSV at
  `docs/covid/covid_quarantine_attribution_v2_surface.csv`.
- QUAR-ATTR-V1's §5 ledger-based first-infection shifts are confirmed, not
  voided.

## AWS jobs

- Canaries `31cc4ab3-4b20-41bb-8f94-f8d027b20767` (Θ 1e5) and
  `d42369cb-5ca2-4878-853a-750e59dd3e68` (Θ 1e9), SUCCEEDED.
- Array `acae64f8-14df-45ad-8ba4-8e7d370aa552`
  (`picard-attribution-v2-d62f10d`), 240/240 SUCCEEDED, 0 failed, ~30 min,
  job-def `picard-covid-boarding-screen:10`, image
  `picard-campaign@sha256:2ce4b13c5a32f0ee21f2cb4f094cde54547850d4482099592f448aa976b2fc5b`.

## S3 prefix

`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_quarantine_attribution_v2/d62f10d/cells/`
(240 objects). Nothing is running.
