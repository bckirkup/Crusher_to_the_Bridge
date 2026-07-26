# Crusher-to-the-Bridge — Documentation Index

**Python 3.11+.** Prefer `python3` on Linux/cloud VMs. Agent-oriented runbook: [AGENTS.md](AGENTS.md).

## First successful run

```bash
pip install -r requirements.txt
python3 tools/sanity_checker.py --from-config
python3 orchestrator.py                          # 24 epochs
python3 -m streamlit run dashboard.py --server.headless true
python3 -m pytest tests/ -v --tb=short           # full suite
```

Optional Presidio smoke:

```bash
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1
```

## Run the simulation

| Doc | Audience | Role |
|-----|----------|------|
| [OPERATORS_MANUAL_SHIP.md](OPERATORS_MANUAL_SHIP.md) | Operators / Picard | Living ship manual: run specs, API, outputs |
| [OPERATORS_MANUAL_GAME_THEORY.md](OPERATORS_MANUAL_GAME_THEORY.md) | Operators / Presidio | Fleet, Stackelberg, OIS, utility export/import |
| [simulation_step_order.md](simulation_step_order.md) | Developers | Epoch phase order (population → instruments → command/medical) |
| [../picard_framework/runs/mega_cruise_campaign/README.md](../picard_framework/runs/mega_cruise_campaign/README.md) | Operators | ~17,780-run mega cruise campaign (`run_campaign.bat` / `.sh`) |
| [OPERATORS_MANUAL.md](OPERATORS_MANUAL.md) | Reference | **Historical** full monolith; prefer the ship/fleet manuals above |

## Configure & extend

| Doc | Role |
|-----|------|
| [SHEDDING_AND_CABINMATES.md](SHEDDING_AND_CABINMATES.md) | Host shedding variance + cabin-mate pairing |
| [pathogen_notes.md](pathogen_notes.md) | Pathogen profile notes |
| [pricing_notes.md](pricing_notes.md) | Assay / labor cost assumptions |
| [SOP_CASCADE_RECONFIG.md](SOP_CASCADE_RECONFIG.md) | Design note (partially landed) — prefer `data/config/diagnostic_cascade*.json` |
| `../schemas/README.md` | JSON Schema ↔ config/output contracts |
| `../.agents/skills/` | Task skills (platform, pathogen, ContamX, wearables, …) |

## Contam / HVAC

| Doc | Status | Role |
|-----|--------|------|
| [CONTAM_INTEROP.md](CONTAM_INTEROP.md) | Living | Path A ContamX interop, SIM reader, compare tools |
| [CONTAM_PRJ_AUDIT.md](CONTAM_PRJ_AUDIT.md) | Living audit | Fiction PRJ realism notes |
| [CTB HVAC Star Topology Fix.md](CTB%20HVAC%20Star%20Topology%20Fix.md) | Implemented | Native AHU star vs N×N over-mixing |
| [CTB PRJ Config Fixes v2 (PRJ-primary).md](CTB%20PRJ%20Config%20Fixes%20v2%20(PRJ-primary).md) | Implemented | PRJ-primary Contam config fixes |

## Agents & AI context

| Doc | Role |
|-----|------|
| [AGENTS.md](AGENTS.md) | Cursor/cloud agent instructions (commands, CI, caveats) |
| [ai_handshake.md](ai_handshake.md) | Architecture manifest for external LLMs |

## Audits, plans & historical design notes

These are **not** day-to-day operator manuals. Prefer living manuals above unless you are auditing or continuing a design thread.

| Doc | Status |
|-----|--------|
| [MATHEMATICAL_FIDELITY_AUDIT.md](MATHEMATICAL_FIDELITY_AUDIT.md) | Living audit |
| [PLATFORM_CABIN_REVISION.md](PLATFORM_CABIN_REVISION.md) | Implemented (mega-cruise cabin corridors) |
| [WEARABLE_ANOMALY_REDESIGN.md](WEARABLE_ANOMALY_REDESIGN.md) | Implemented (confounder-aware infection_score) |
| [issue_111_enhanced_wearables_plan.md](issue_111_enhanced_wearables_plan.md) | Historical plan / partially superseded — see WEARABLE_ANOMALY_REDESIGN |
| [SOP_CASCADE_RECONFIG.md](SOP_CASCADE_RECONFIG.md) | Historical design note (also listed under Configure) |
| [OPERATORS_MANUAL.md](OPERATORS_MANUAL.md) | Historical reference (dashboard LCARS docs still deferred here) |

## Where to edit docs

| Change | Update |
|--------|--------|
| How to run ship/fleet | Ship or game-theory operator manual + this index if entry points change |
| Agent/CI commands | `AGENTS.md` + matching `.agents/skills/` |
| JSON contracts | `schemas/README.md` + schema files |
| ContamX / HVAC physics | `CONTAM_INTEROP.md` (+ audit notes if fidelity claims change) |
