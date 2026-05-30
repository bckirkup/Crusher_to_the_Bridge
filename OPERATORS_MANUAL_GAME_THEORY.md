# Crusher-to-the-Bridge — Game Theory & Fleet Operator's Manual (Presidio)

**Scope:** Stackelberg decisions, information diffusion, reputation, and external utility optimization.

Single-ship Picard operations: [OPERATORS_MANUAL_SHIP.md](OPERATORS_MANUAL_SHIP.md).

---

## Stackelberg move order (each epoch)

After instruments compute stoplights, before SOP evaluation:

1. **Command** — Authorize SOP subsets, surveillance budget emphasis (reporting), corporate communication stance, directives to medical
2. **Medical** — Surveillance cadence, isolation posture nudges, crew instructions, SOP recommendations (stoplight-gated)
3. **Population** — Class-aggregated or per-agent actions (default noop in-repo)

Standing SOP **physics** remains driven by Crusher Labs stoplights (**Law 1**). Command can restrict which SOP IDs may auto-activate; medical cannot force activation without stoplight eligibility.

---

## Presidio fleet runner

```bash
# Smoke (1 cruise × 2 epochs)
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1

# Default fleet (see presidio/data/config/default_fleet.json)
python3 presidio_runner.py

# Utility export / action import (external optimizer)
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1 \
  --export-utility-dir presidio/data/experiences/utility_bundles \
  --import-actions-dir presidio/data/experiences/imported_actions
```

Fleet config references a Picard run spec (`picard_run_spec_path`). Per-cruise `social_config` merges fleet overrides and sets `cruise_id` for file naming.

---

## Configuration

| Path | Purpose |
|------|---------|
| `presidio/data/social/information_diffusion_default.json` | Belief propagation (`alpha`, `homophily_strength`, `message_decay`) |
| `presidio/data/social/class_interactions_default.json` | Crew/passenger contact weights by zone |
| `presidio/data/intelligence/global_health_timeline.json` | Epoch-static global health briefings |
| `picard_framework/data/agent_profiles/default_ship_population.json` | Demographics/medical templates |
| `presidio/data/economics/fleet_economics.json` | Reward weight references (not optimized in-repo) |
| `presidio/data/config/default_fleet.json` | Fleet run spec |
| `presidio/data/experiences/` | Experience store and cruise output roots |

Picard run spec `social` block references these paths. Example: `picard_framework/runs/destroyer_baseline_default.json`.

---

## External optimization workflow

1. Enable `social.export_utility_dir` on the Picard run spec (or `--export-utility-dir` on `presidio_runner.py`).
2. Run simulation; each epoch writes `cruise_{id}_epoch_{NNNN}_utility.json` (`schemas/utility_observation_bundle.schema.json`).
3. External tool computes utility \(U = w \cdot f\) and writes `cruise_{id}_epoch_{NNNN}_actions.json` (`schemas/decision_action.schema.json`).
4. Re-run with `--import-actions-dir` or set `social.import_actions_dir` so `StackelbergRound` applies imported envelopes.

Utility **features** and action **validation** are in-repo; **weights and optimization** are out-of-repo.

---

## Agent hooks & telemetry

| Hook | Module / field |
|------|----------------|
| Lived experience | `decision_engine/lived_experience.py` |
| Contact graph | `decision_engine/social/contact_graph.py` |
| Information state | `simulation_history[].information_state` |
| SOP events | `simulation_history[].reactive_protocols.sop_events` |
| Wearable (per-agent) | `wearable_agent_snapshot` when `social.telemetry.decision_detail: true` |
| Agent profile ID | `agents[].profile_id` |

---

## JSON schemas (Stackelberg)

| Schema | Data file |
|--------|-----------|
| `information_diffusion.schema.json` | `presidio/data/social/information_diffusion_default.json` |
| `class_interactions.schema.json` | `presidio/data/social/class_interactions_default.json` |
| `global_health_briefing.schema.json` | `presidio/data/intelligence/global_health_timeline.json` |
| `agent_profile.schema.json` | `picard_framework/data/agent_profiles/*.json` |
| `utility_observation_bundle.schema.json` | Exported utility JSON |
| `decision_action.schema.json` | Imported action envelopes |

---

## Validation

```bash
python3 tools/sanity_checker.py --from-config
python3 -m pytest tests/test_stackelberg.py tests/test_picard_framework.py \
  tests/test_decision_engine.py tests/test_presidio_runner.py -v
```

Skills:

- `.agents/skills/stackelberg-utility-export/SKILL.md`
- `.agents/skills/configuring-stackelberg-social/SKILL.md`
- `.agents/skills/presidio-fleet-run/SKILL.md`
- `.agents/skills/testing-picard-presidio/SKILL.md`

CI: `.github/workflows/picard-presidio.yml` and `.github/workflows/ci.yml` (Presidio smoke on `main`).
