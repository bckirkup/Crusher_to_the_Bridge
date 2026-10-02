# VSP-EITHER-CHANNEL-01
**Date:** 2026-10-02
**Commit:** def39066
**Pathogens:** all
**Status:** closed

## Defect

The published VSP posting rule — cumulative reported cases at 3% of
passengers *or* 3% of crew — was implemented only on the passenger channel.
The shipped `ship_graph.infection_counters` gave
`passenger_reported_case_rate` a `threshold: 0.03` with
`on_exceed: confine_symptomatic`, while `crew_reported_case_rate` was
computed but log-only, and `compute_derived_metrics`' `vsp_trigger_epoch`
read the passenger counter alone. A voyage posting on crew reports alone
therefore ran the whole episode with no in-sim VSP response — the
definitional gap recorded as outstanding in
`docs/norovirus/norovirus_open_ledger.md` (the quiet-region item measured
51.5% of its postings crew-only; the observed series carries 0.5–9.3%).

## Change

- `crusher_labs/config.yaml`: `crew_reported_case_rate` carries
  `threshold: 0.03` + `on_exceed: confine_symptomatic`, mirroring the
  passenger counter. The response either channel triggers is the same
  ship-wide symptomatic confinement, as the rule posts the vessel rather
  than a channel.
- `picard_framework/runs/mega_cruise_campaign/campaign_execution.py`:
  emits `crew_reported_case_rate_newly_confined` and
  `crew_reported_case_rate_exceeded` beside the passenger fields, and
  `vsp_trigger_epoch` now stamps the first epoch *either* channel's
  counter is exceeded.
- `telemetry_buffer/observation_model/score_anchors.py`:
  `A9_flag_disagreements` compares the either-channel posting against the
  flag instead of the passenger channel alone — on payloads produced
  before this change it counts exactly the crew-only postings the gap
  created.
- `docs/reports/05_vsp.tex`: equation `vsp-trigger` restated in or-form
  ($G_P/N_P \ge \theta$ or $G_C/N_C \ge \theta$).

## Declared caveat

The repair makes the trigger faithful *and* amplifies the known crew-side
over-firing: the conversion channel under-fires illness while crew reports
overshoot (the quiet region's 51.5% crew-only postings against an observed
0.5–9.3%), so more crew-only postings will now engage the response than
the observed fleet shows. That is the conversion-defect family measured at
NORO-CHANNEL-03 surfaced through a now-correct trigger — declared, not
hidden: a cell that over-posts on the crew channel will show both the
posting and the flag where before it showed only the posting.

## Determinism note

The change alters no seed, draw, or transmission quantity; it alters when
the confinement response fires, so trajectories re-roll wherever the crew
channel crosses before the passenger channel — or alone. Pairings declared
against the pre-change image pin to that image, not to this commit.
