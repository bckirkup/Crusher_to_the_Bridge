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
uv sync --locked --all-extras --no-install-project --no-build
source .venv/bin/activate   # or prefix commands with `uv run`
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
| [near_field_air_spec.md](near_field_air_spec.md) | Implemented, off by default — `AERO-NEAR-01`, the near/far-field air compartment over the cabin and the dining table (`transmission.near_field_air`, `retained_fraction` 0 is the well-mixed route) |
| [cabin_air_compartment_spec.md](cabin_air_compartment_spec.md) | Implemented, off by default — `AERO-CABIN-01`, the stateroom as the inhalation unit inside a `Cabin_Corridor` (`transmission.cabin_air_mode`, `zone_pool` default is the pre-change whole-corridor pool); block volume partitioned by berths, no constant added |
| [density_contact_spec.md](density_contact_spec.md) | Implemented — `per_partner_contact` is the default; the zone-average mode it replaced was superseded by #329 |
| [contact_architecture_spec.md](contact_architecture_spec.md) | Implemented, off by default — `transmission.activity_contacts` derives the contact draw from schedule, zone type, mixing unit and duty state; no rate adopted, no campaign run |
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
| [shared_sanitary_zones.md](shared_sanitary_zones.md) | Implemented — `Sanitary` head zones on all 12 platforms with exhaust-only one-way air wiring; `transmission.sanitary_visit_mode` (`none` default / `dwell_weighted`); flush emission is a separate change |
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
| [covid/covid_open_ledger.md](covid/covid_open_ledger.md) | Living — current withdrawals and measurement status for the COVID arm |
| [instrument_parameterization_v2.md](instrument_parameterization_v2.md) | Living — feeds `data/config/clinical_instrument_params.json`. v1 is in `history/` |
| [pricing_notes.md](pricing_notes.md) | Living — assay/labour cost assumptions for `resource_costs.json` |
| [norovirus/](norovirus/) | The norovirus thread — start at the ledger |
| [norovirus/vsp_ship_class_denominators.md](norovirus/vsp_ship_class_denominators.md) | Implemented — current record of class denominators, the Jenkins/project “Mega” label collision, and the unmapped-band decision |
| [norovirus/introduction_mechanism_ab.md](norovirus/introduction_mechanism_ab.md) | Implemented — the boarding-prevalence vs fiat-index-case A/B: posting frequency, reported incidence against A8, per-import secondary yield, and the prevalence-denominator unit question |
| [norovirus/symptomatic_boarding_stream.md](norovirus/symptomatic_boarding_stream.md) | Implemented, default-on under renewal — derivation of record for the `symptomatic_stream` arm: the renewal import rate partitioned into ill-at-embarkation and not-ill shares, with the backward-recurrence draw and the ashore-emesis drop |
| [norovirus/preboarding_assessment.md](norovirus/preboarding_assessment.md) | Implemented, reference crew clause default-on under renewal — derivation of record for the `preboarding_assessment` arm: the VSP §4.1.1.2 three-day declaration screen, with reportability and denial of boarding as separately switchable consequences |
| [norovirus/full_complement_vs_industry_occupancy.md](norovirus/full_complement_vs_industry_occupancy.md) | Sourced measurement, nothing applied — what each hull's declared complement is a capacity *of* (lower berths, not maximum), against audited operator occupancy, and what that makes of the occupancy probe |
| [norovirus/route_attribution_headcount_scaling.md](norovirus/route_attribution_headcount_scaling.md) | Measurement of record, taken under the pre-deletion engine — `hull_compounding_route_v1` attributes all 1,800 Arm B re-run voyages to routes: droplet carried 85–99% of establishments and the whole N^1.7–2.0 per-import headcount scaling; direct contact is inert. That droplet share was `DROPLET_AEROSOL_FRACTION`, since deleted on the emesis-conditioned arm |
| [norovirus/droplet_deletion_route_v1.md](norovirus/droplet_deletion_route_v1.md) | Measurement of record for the default engine — the matched `profile_conditioned` vs `shipped_uniform` arms of `droplet_deletion_route_v1` (3,600 runs): deleting the continuous droplet share cuts secondaries per import 31–49×, zeroes droplet attribution, leaves fomite carrying the same N^1.7 headcount exponent off a 30–50× lower base, and drops posting to 0/300 in five of six cells — an interval that does not resolve either side of A9. Supersedes `route_attribution_headcount_scaling.md` as current behaviour |
| [norovirus/flush_aerosolisation_v1.md](norovirus/flush_aerosolisation_v1.md) | Implemented, default-off — design and declared uncertainty of `FLUSH-AERO-01`: bowl-load aerosolisation at defecation events, the [1e-9, 1e-3] refusal band spanning Johnson 2013 and Boles 2021, and the staged sweep that measures where the route first resolves |
| [norovirus/flush_sweep_v1_stage1_readout.md](norovirus/flush_sweep_v1_stage1_readout.md) | Generated measurement of record — `flush_sweep_v1` stage 1 (off / 1e-9 / 1e-7 / 1e-5, 600 paired runs per arm): per-arm witness, paired contrasts against `off`, posting margins |
| [norovirus/flush_sweep_v1_stage1_findings.md](norovirus/flush_sweep_v1_stage1_findings.md) | Interpretation of the stage-1 measurement — emission linear in `f_aero` as predicted, the outcome-level saturation prediction falsified (3–11× more secondaries 1e-7 → 1e-5), resolvability crossing strictly inside (1e-9, 1e-7); ledger item 43. Pre-AERO-CABIN-02 engine; supersession noted in the document and stage 2 carried its own baselines |
| [norovirus/flush_sweep_v1_stage2_readout.md](norovirus/flush_sweep_v1_stage2_readout.md) | Generated measurement of record — `flush_sweep_v1` stage 2 (off / 3e-9 / 1e-8 / 3e-8 / 1e-7, 1,200 paired runs per arm under the AERO-CABIN-02 berth-share partition): per-arm witness, paired contrasts against `off`, posting margins |
| [norovirus/flush_sweep_v1_stage2_findings.md](norovirus/flush_sweep_v1_stage2_findings.md) | Interpretation of the stage-2 measurement — the resolvability crossing is hull/length-dependent (classic (1e-9, 3e-9], spirit and expedition cells resolving at 1e-8–3e-8, all cells by 3e-8), multipliers ×52–97 classic / ×7.6–10.4 spirit / ×4.4–4.9 expedition at 1e-7; cabin-venue drift defect opened; ledger item 46. **Pre-repair engine — superseded as a measurement of current behaviour by the `s2r` re-run** |
| [norovirus/flush_sweep_v1_stage2r_readout.md](norovirus/flush_sweep_v1_stage2r_readout.md) | Generated measurement of record — `flush_sweep_v1` stage-2 re-run (`s2r`: off / 3e-9 / 1e-8 / 3e-8 / 1e-7, 1,200 paired runs per arm) on the repaired per-pathogen transport and cabin-drain engine, both air-model settings pinned in the manifests: per-arm witness, paired contrasts against `off`, posting margins |
| [norovirus/flush_sweep_v1_stage2r_findings.md](norovirus/flush_sweep_v1_stage2r_findings.md) | Interpretation of the `s2r` measurement and current behaviour of record — five of six cells resolve at the bracket floor `3e-9`, so the crossing is bounded above by `3e-9` and no longer bracketed below; `hvac_airborne` dominant in 26–68% of establishments where it was inert; posting at `1e-7` reaches 85–110 per 1,000 on the 12-day large hulls against A9's 0.33, so the comparator now lies inside the span — nothing selected, span not narrowed; ledger items 47–48. **Pre-multiplicity-fix engine — superseded as a measurement of current behaviour by the `FLUSH-S3` re-bracket** |
| [norovirus/flush_sweep_v1_stage2e_readout.md](norovirus/flush_sweep_v1_stage2e_readout.md) | Generated measurement of record — `flush_sweep_v1` stage-2 re-run (`s2e`: the same five arms and 200 paired seeds) on the emesis-berth-share engine (item 50): per-arm witness, paired contrasts against `off`, posting margins |
| [norovirus/flush_sweep_v1_stage2e_findings.md](norovirus/flush_sweep_v1_stage2e_findings.md) | Interpretation of the `s2e` measurement — the emesis berth-share repair is a measured null at 200 paired seeds (imports 1.000, Δ spi within noise, emesis dominant share ≈0 in both stages); the `s2r` interpretation stands as the measurement of record; ledger item 54 |
| [norovirus/flush_sweep_v1_stage3_readout.md](norovirus/flush_sweep_v1_stage3_readout.md) | Generated measurement of record — the `FLUSH-S3` re-bracket (`off` / 1e-9 / 1e-7 / 1e-5, 600 paired runs per arm) on the current engine (`65d9fb2`, stamped in every archived run) after the HVAC multiplicity, confinement, per-stateroom pool and emesis source-term changes: per-arm witness, dominant-route shares, posting margins |
| [norovirus/flush_sweep_v1_stage3_findings.md](norovirus/flush_sweep_v1_stage3_findings.md) | Interpretation of the `FLUSH-S3` measurement and current behaviour of record — `1e-9` is a null in all six cells and the crossing moved up ~2 decades into `(1e-9, 1e-7]` on the large hulls; `1e-5` resolves everywhere and is still unsaturated; `hvac_airborne` is 0.0% of dominant attributions at baseline where `s2r` had it dominant in 26–68%; posting reported as contrast only, nothing selected, `[1e-9, 1e-3]` unchanged; supersedes the stage 1/2/`s2r`/`s2e` readings |
| [norovirus/flush_sweep_v1_stage4_readout.md](norovirus/flush_sweep_v1_stage4_readout.md) | Generated measurement of record — the `FLUSH-S4` fine arms (`off` / 3e-9 / 1e-8 / 3e-8 / 3e-7, 1,200 paired runs per arm, `7f689b9` stamped in every archived run): per-arm witness, dominant-route shares, posting margins, median reported AR among posted voyages. **Pre-emesis-footprint engine — the `off`-arm posting readings and fomite attributions were measured on zone-wide bolus delivery and are invalidated by `EMESIS-FOOTPRINT-01`** |
| [norovirus/flush_sweep_v1_stage4_findings.md](norovirus/flush_sweep_v1_stage4_findings.md) | Interpretation of the `FLUSH-S4` measurement and current behaviour of record — six cells give six crossing brackets spanning ~3 decades ordered by baseline chain yield, and no arm in `[3e-9, 3e-7]` is null or resolving on every cell; `off_s4` reproduces `off_s3` on all 600 shared voyages while the `off` *mean* moves up to 3× because the voyage distribution is heavy-tailed and 100 seeds missed the tail; posting at `off` already exceeds A9 with the route disabled, and the AR conditional on posting is flat in `f_aero`; contrast only, `[1e-9, 1e-3]` unchanged. **Pre-emesis-footprint engine — the `off`-arm posting readings were measured on zone-wide bolus delivery and are invalidated by `EMESIS-FOOTPRINT-01`** |
| [norovirus/environmental_observation_v1.md](norovirus/environmental_observation_v1.md) | Implemented — the environmental-observability derivation: surface density + Park 2015 per-swab LOD (shipped behind `observation.surface_swab_source`, default `airborne_fraction`), blackwater holding tank + copies/L assay (shipped behind `transmission.blackwater_plumbing` and `observation.wastewater_assay_mode`, both default-off), emesis source-term replacement (shipped; see [norovirus/emesis_source_term_v1.md](norovirus/emesis_source_term_v1.md)); ledger items 56–57 and 13 |
| [literature/consensus_tranche_42_boarding_prevalence_renewal_check.md](literature/consensus_tranche_42_boarding_prevalence_renewal_check.md) | Evidence assembled — boarding-prevalence renewal-identity check; both repairs are now the default mechanism for `norwalk_gi` (historical arm selectable as the `shipped` rung) |
| [literature/consensus_tranche_43_illness_duration_harris_2019.md](literature/consensus_tranche_43_illness_duration_harris_2019.md) | Implemented, default-on where a survival table exists — Harris 2019 Fig 4C illness-duration survival table; the `illness_duration` dispersed arm on `norwalk_gi` |
| [literature/](literature/) | Raw search output behind the above |

## Where to edit docs

| Change | Update |
|--------|--------|
| How to run ship/fleet | Ship or game-theory operator manual, + this index if entry points change |
| Agent/CI commands | `AGENTS.md` + matching `.agents/skills/` |
| JSON contracts | `schemas/README.md` + schema files |
| ContamX / HVAC physics | `CONTAM_INTEROP.md` and [`exterior_zone_ahu_audit.md`](exterior_zone_ahu_audit.md) |
| An epidemiological constant | The constant's provenance comment, the relevant open ledger (`norovirus/norovirus_open_ledger.md` or `covid/covid_open_ledger.md`) if it invalidates a recorded measurement, and `norovirus/norovirus_model_history.md` if it is a defect. New ledger entries are one file each under `docs/ledger/<ID>.md` (see its README) with Pathogens and Commit SHA; do not append numbered items. |
| A document's implementation state | Its status header — and move the file if the filing rule above now puts it elsewhere |
