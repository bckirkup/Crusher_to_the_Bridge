# Crusher-to-the-Bridge — Documentation Index

**Python 3.11+.** Prefer `python3` on Linux/cloud VMs. Agent-oriented runbook:
[AGENTS.md](AGENTS.md).

## How this directory is organised

Two independent axes. **Directory = subject. Header = status.** Do not infer one
from the other: several implemented systems are documented in files nothing else
links to, and several heavily-linked files describe work that is finished.

| Location | Contains | Read it when |
|---|---|---|
| `docs/` root | Operator manuals, the governing specs, and mechanism docs for behaviour that is live in-tree | Working on the simulation |
| [`norovirus/`](norovirus/) | The norovirus calibration thread: ledger, defect history, provenance audit, observation priors | Touching any epidemiological constant or anchor |
| [`covid/`](covid/) | The SARS-CoV-2 thread: arm execution status, parameter provenance audit | Touching any `sars_cov2_resp` constant or the COVID fit |
| [`sentinel/`](sentinel/) | Sentinel surveillance, port health, wastewater ops, shore-side, economics | Working on `picard_framework/analysis/sentinel/`, `shore/`, `economics/` |
| [`paper3/`](paper3/) | Variant surveillance and phylodynamics | Working on strain state, mutation, lineage observables |
| [`proposals/`](proposals/) | Documents whose primary artifact **does not exist yet** | Deciding what to build; never as a description of current behaviour |
| [`history/`](history/) | Resolved audits, superseded versions, one-off task briefs, completed plans | Auditing why something is the way it is |
| [`literature/`](literature/) | Raw literature-search output (PDFs, review notes) | Sourcing or checking a constant's provenance |
| [`reports/`](reports/) | Manuscripts, monographs, submission artifacts | Writing or revising a paper |

**Filing rule.** A document lives in `proposals/` until the artifact it
specifies exists in-tree; then it moves to its subject directory or to the root.
When a document is fully superseded or its question is settled, it moves to
`history/`. Nothing is deleted.

**Status header convention.** Every document under `docs/` should open with one
line, before the first section:

```markdown
> **Status:** Living | Implemented | Partially implemented | Proposed | Resolved | Superseded | Historical reference
```

Add the qualifier that matters (`Implemented in <path>`, `Resolved by #327/#328`,
`Superseded by <file>`). About a third of these files carry it today; add it when
you touch one. **A document's own status line can be stale — prefer in-tree
evidence.** Two known cases are called out below.

**Agents:** you do not need `literature/`, `history/`, or `reports/` for
implementation work. Read the root plus the one subject directory you are
working in.

## First successful run

```bash
pip install -r requirements.txt
python3 tools/sanity_checker.py --from-config
python3 orchestrator.py                          # 24 epochs
python3 -m streamlit run dashboard.py --server.headless true
python3 -m pytest tests/ -m 'not slow' -v --tb=short
```

Optional Presidio smoke:

```bash
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1
```

## Run the simulation

| Doc | Status | Role |
|-----|--------|------|
| [OPERATORS_MANUAL_SHIP.md](OPERATORS_MANUAL_SHIP.md) | Living | Ship manual: run specs, API, outputs |
| [OPERATORS_MANUAL_GAME_THEORY.md](OPERATORS_MANUAL_GAME_THEORY.md) | Living | Fleet, Stackelberg, OIS, utility export/import |
| [simulation_step_order.md](simulation_step_order.md) | Living | Epoch phase order |
| [OPERATORS_MANUAL.md](OPERATORS_MANUAL.md) | Historical reference — **but load-bearing** | The pre-split monolith. §§5–11 are the *only* documentation in the repo for SOP authoring, the GIS spatial bridge CLI, sanity-checker categories, lab-notebook fidelity tiers, the LCARS dashboard stations, console output format, and upstream-project provenance. Do not treat as a duplicate. Appendix A's test count (~875) is stale; the suite is 3229. |
| [../picard_framework/runs/mega_cruise_campaign/README.md](../picard_framework/runs/mega_cruise_campaign/README.md) | Living | ~17,780-run mega cruise campaign |

## Governing specs

| Doc | Status |
|-----|--------|
| [sourcing_protocol.md](sourcing_protocol.md) | Living — process of record; no sourcing pass has run under it yet |
| [formal_spec_v2.md](formal_spec_v2.md) | Final, implementer-ready. §8 tissue tropism is an optional extension, default-off, not implemented |
| [clock_unit_safety_spec.md](clock_unit_safety_spec.md) | Implemented (`engines/sim_clock.py`, `tests/test_clock_units.py`) |
| [ai_handshake.md](ai_handshake.md) | Living — architecture manifest for external LLMs |
| [AGENTS.md](AGENTS.md) | Living — agent instructions, commands, CI, caveats |

## Mechanisms live in-tree

| Doc | Status |
|-----|--------|
| [SHEDDING_AND_CABINMATES.md](SHEDDING_AND_CABINMATES.md) | Implemented — per-agent shedding variance, cabin-mate pairing |
| [density_contact_spec.md](density_contact_spec.md) | Implemented — `per_partner_contact` is the default; the zone-average mode it replaced was superseded by #329 |
| [multi_pathogen_model_changes_spec.md](multi_pathogen_model_changes_spec.md) | Implemented (Phase A route weights / dose / FUT2; Phase B dining, food, source zones) |
| [tiered_escalation_spec.md](tiered_escalation_spec.md) | Implemented — SOP policy, decision latency, bimodal compliance |
| [ship_operations_spec.md](ship_operations_spec.md) | Implemented — data model and config hooks; `effects_enabled` flag-gated |
| [medical_response_spec.md](medical_response_spec.md) | Implemented — per-platform medical response via `voyage_config.json` |
| [ctb_incubation_spec.md](ctb_incubation_spec.md) | Implemented — stochastic incubation, dose-dependent onset, host frailty |
| [incubation_sensitivity_protocol.md](incubation_sensitivity_protocol.md) | Implemented (`picard_framework/analysis/incubation_arms.py`) |
| [WEARABLE_ANOMALY_REDESIGN.md](WEARABLE_ANOMALY_REDESIGN.md) | Implemented — confounder-aware `infection_score` |
| [preboarding_wearable_decision_model_spec.md](preboarding_wearable_decision_model_spec.md) | Phase 1 implemented (`picard_framework/analysis/boundary/`); ship-sim handoff deferred |
| [PLATFORM_CABIN_REVISION.md](PLATFORM_CABIN_REVISION.md) | Implemented — cabin-level spatial resolution |
| [ENTERPRISE_CABIN_REVISION.md](ENTERPRISE_CABIN_REVISION.md) | Implemented — Constitution + Galaxy rebuilt to cruise-class |
| [MATHEMATICAL_FIDELITY_AUDIT.md](MATHEMATICAL_FIDELITY_AUDIT.md) | Living audit — records what is *not* implemented (stratified SEIQR, crew schedule) |

## Contam / HVAC

| Doc | Status |
|-----|--------|
| [CONTAM_INTEROP.md](CONTAM_INTEROP.md) | Living — Path A ContamX interop, SIM reader, compare tools |
| [CONTAM_PRJ_AUDIT.md](CONTAM_PRJ_AUDIT.md) | Living audit — fiction PRJ realism |
| [SHIP_BLUEPRINT_IMPORT.md](SHIP_BLUEPRINT_IMPORT.md) | Implemented (`tools/ship_blueprint_import/`) |

## Campaign analysis & calibration tooling

| Doc | Status |
|-----|--------|
| [stan_analysis_tool_spec.md](stan_analysis_tool_spec.md) | Implemented — analysis bundle + two-stage Stan hurdle |
| [stan_hurdle_lessons.md](stan_hurdle_lessons.md) | Field notes (C12c + C14/C14b Step-2) |
| [boundary_aws_pipeline_lessons.md](boundary_aws_pipeline_lessons.md) | Field notes — boundary surface AWS pipeline |
| [synthetic_recovery_and_vsp_degradation.md](synthetic_recovery_and_vsp_degradation.md) | Findings — synthetic recovery + VSP degradation campaigns |

## Parameter sources

Constants carry their source and evidence grade at the point of definition; see
`.agents/skills/model-parameter-provenance/SKILL.md`. These files hold the
longer justifications.

| Doc | Status |
|-----|--------|
| [parameter_provenance_register.md](parameter_provenance_register.md) | Register, authoritative — every quantity in all three arms with its provenance class and adoption state. Read it before changing any epidemiological constant, and update it in the same change |
| [pathogen_notes.md](pathogen_notes.md) | Living — per-pathogen literature justifications |
| [covid/](covid/) | The SARS-CoV-2 thread — arm status and the parameter provenance audit. Read the audit before quoting any `sars_cov2_resp` constant |
| [instrument_parameterization_v2.md](instrument_parameterization_v2.md) | Living — feeds `data/config/clinical_instrument_params.json`. v1 is in `history/` |
| [pricing_notes.md](pricing_notes.md) | Living — assay/labour cost assumptions for `resource_costs.json` |
| [norovirus/](norovirus/) | The norovirus thread — start at the ledger |
| [literature/](literature/) | Raw search output behind the above |

## Where to edit docs

| Change | Update |
|--------|--------|
| How to run ship/fleet | Ship or game-theory operator manual, + this index if entry points change |
| Agent/CI commands | `AGENTS.md` + matching `.agents/skills/` |
| JSON contracts | `schemas/README.md` + schema files |
| ContamX / HVAC physics | `CONTAM_INTEROP.md` and [`exterior_zone_ahu_audit.md`](exterior_zone_ahu_audit.md) |
| An epidemiological constant | The constant's provenance comment, `norovirus/norovirus_open_ledger.md` if it invalidates a recorded measurement, and `norovirus/norovirus_model_history.md` if it is a defect |
| A document's implementation state | Its status header — and move the file if the filing rule above now puts it elsewhere |
