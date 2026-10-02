# NORO-OUTBREAK-01
**Date:** 2026-10-02
**Commit:** 232292f2649431a1e05c2385244a176033489d57
**Pathogens:** norwalk_gi
**Status:** declared

Anchor assessment of simulated norovirus outbreaks on the smaller VSP hull
classes after the hand-reservoir rebuild (`a3c76061`: hygiene_cycle +
protected sequestration + own-pool, shipped default) and the
presentation-share repair (`890bfce3`: `presentation_draw_mode:
once_per_course`, shipped default, `daily_hazard` labelled baseline).
Question: outbreak *frequency* (posting probability / A9, takeoff,
establishment), *progression* (within-voyage epidemic curve: onset,
detection, VSP-flag and peak epochs, span, peak prevalence), and *ultimate
attack rate* (reported pax AR vs hull-class IQR / A4, A1 ever-ill,
infection AR, A2, A5, A8), on expedition_cruise_450 {7d, 12d} and
classic_cruise_1900 {12d}.

Design, cell layout, seeds/pairing, report-immediately triggers and the
canary gate are frozen in
`docs/norovirus/noro_outbreak_01_design.md` — nothing there may be quoted
as a result until the canary readout moves this entry to `measured`.

Settled inputs (not re-derived): NORO-IMPORT-01's import-region map
(`402a4df6`, one posting in the licensed map; prevalence the load-bearing
axis; establishment gradient ~10% exp / ~40% cls / ~55% spr / ~90% mega at
hi prevalence with ~0 postings); the hand census measurements
(`docs/norovirus/noro_hand_carriage_handoff_2026_10_01.md`); the anchor
machinery (`telemetry_buffer/observation_model/score_anchors.py`,
`vsp_class_era_scoring.py`, `midrs_incidence_targets.py`); every dose
figure void pending refit (dose_adjustment fixed 7.57, quoted nowhere).

Manifest: `picard_framework/runs/mega_cruise_campaign/noro_outbreak_01_manifest.json`
(12 cells x 1000 seeds = 12,000 voyages). Readout:
`tools/noro_diag/outbreak_anchor_readout.py`. Harness reuses the
NORO-IMPORT-01 entrypoint/submit path verbatim; overlay image
`deploy/aws/Dockerfile.noro_outbreak_01` + jobdef
`deploy/aws/batch_job_definition_noro_outbreak_01.json`. S3 prefix
`campaign/noro_outbreak_01/`.
