# History

> **Status:** Historical. Kept for provenance; not current documentation.

Resolved audits, superseded versions, one-off implementation briefs for work that
has landed, and plans that are complete. Nothing here is deleted, and nothing
here should be read as a description of current behaviour.

Agents doing implementation work do not need this directory. Read it when you
need to know *why* something is the way it is.

| Doc | Status |
|-----|--------|
| [epoch_time_unit_audit.md](epoch_time_unit_audit.md) | Resolved by #327 and #328 — the `hour = 12` hard-code and the day/hour epoch conflict. Live successor: [`../clock_unit_safety_spec.md`](../clock_unit_safety_spec.md) |
| [incubation_reconciliation_plan.md](incubation_reconciliation_plan.md) | Complete — R1 (one source of truth for pathogen delay parameters) marked DONE; `sentinel/profile_delays.py` and `incubation_distributions.json` exist |
| [ctb_incubation_devin_brief.md](ctb_incubation_devin_brief.md) | Complete — implementation brief for [`../ctb_incubation_spec.md`](../ctb_incubation_spec.md), which is implemented |
| [todo_resolutions.md](todo_resolutions.md) | Complete — resolutions for the five TODOs in formal spec v1 Appendix C. Several resolutions are "deferred", which is itself the record |
| [migration_feasibility.md](migration_feasibility.md) | Complete — found that establishment is not a drop-in replacement as written. Assessed against snapshot `d557f39` |
| [instrument_parameterization.md](instrument_parameterization.md) | Superseded by [`../instrument_parameterization_v2.md`](../instrument_parameterization_v2.md) |
| [clinical_dx_review.md](clinical_dx_review.md) | Historical review behind `data/config/clinical_instrument_params.json` |
| [issue_111_enhanced_wearables_plan.md](issue_111_enhanced_wearables_plan.md) | Plan, partially superseded — confounder-aware scoring landed via [`../WEARABLE_ANOMALY_REDESIGN.md`](../WEARABLE_ANOMALY_REDESIGN.md) |
| [SOP_CASCADE_RECONFIG.md](SOP_CASCADE_RECONFIG.md) | Design note, "may be partially landed". Prefer `data/config/diagnostic_cascade*.json` and `protocols.json` as the source of truth |
| [CTB HVAC Star Topology Fix.md](CTB%20HVAC%20Star%20Topology%20Fix.md) | Implemented (merged) — native + ContamX AHS use AHU star topology. Living guidance: [`../CONTAM_INTEROP.md`](../CONTAM_INTEROP.md) |
| [CTB PRJ Config Fixes v2 (PRJ-primary).md](<CTB PRJ Config Fixes v2 (PRJ-primary).md>) | Implemented (merged) — PRJ-primary Contam config fixes |
