# Crusher-to-the-Bridge — Game Theory & Fleet Operator's Manual (Presidio)

**Scope:** Stackelberg decisions, information diffusion, reputation, and external utility optimization.

Single-ship Picard operations: [OPERATORS_MANUAL_SHIP.md](OPERATORS_MANUAL_SHIP.md).

---

## Stackelberg move order (each epoch)

1. **Command** — Authorize SOP subsets, corporate communication stance, directives to medical
2. **Medical** — Surveillance cadence, crew instructions, recommendations (stoplight-gated physics)
3. **Population** — Class-aggregated or per-agent actions (default noop)

Standing SOP **physics** remains driven by Crusher Labs stoplights (Law 1). Command can restrict which SOP IDs may auto-activate; medical cannot force activation without stoplight eligibility.

---

## Configuration

| Path | Purpose |
|------|---------|
| `presidio/data/social/information_diffusion_default.json` | Belief propagation parameters |
| `presidio/data/social/class_interactions_default.json` | Crew/passenger contact weights by zone |
| `presidio/data/intelligence/global_health_timeline.json` | Epoch-static global health briefings |
| `picard_framework/data/agent_profiles/default_ship_population.json` | Demographics/medical templates |
| `presidio/data/economics/fleet_economics.json` | Reward weight references (not optimized in-repo) |

Picard run spec `social` block references these paths. See `picard_framework/runs/destroyer_baseline_default.json`.

---

## External optimization workflow

1. Run simulation with `social.export_utility_dir` set
2. External tool reads `utility_observation_bundle` JSON per epoch
3. External tool writes `actions.json` per epoch
4. Re-run or wire `--import-actions-dir` on `presidio_runner.py` (when enabled)

Utility **features** are in-repo; **weights and optimization** are out-of-repo.

---

## Agent hooks

| Hook | Module |
|------|--------|
| Lived experience | `decision_engine/lived_experience.py` |
| Wearable (per-agent) | Epoch `wearable_agent_snapshot` when `social.telemetry.decision_detail: true` |
| Contact graph | `decision_engine/social/contact_graph.py` |
| Information state | `simulation_history[].information_state` |

---

## Validation

```bash
python3 tools/sanity_checker.py --from-config
python3 -m pytest tests/test_stackelberg.py tests/test_picard_framework.py -v
```

Skill: `.agents/skills/stackelberg-utility-export/SKILL.md`
