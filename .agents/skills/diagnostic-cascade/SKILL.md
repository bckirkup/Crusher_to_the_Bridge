---
name: diagnostic-cascade
description: Configure and test the Tier 0–3 diagnostic cascade, multiplex panels, cascade entry fusion, and SOP gating. Use when editing diagnostic_cascade configs, crusher_labs/diagnostic_cascade.py, cascade smoke specs, or SOP cascade reconfig.
---

# Diagnostic cascade

Clinical escalation ladder that drives surveillance and SOP gating for Picard /
campaign runs. Wearable Tier-0 entry uses confounder-aware `infection_score`
(see `.agents/skills/wearable-anomaly-scoring/SKILL.md`).

## Key files

| Path | Role |
|------|------|
| `data/config/diagnostic_cascade.json` | Standard Tier 0–3 + `cascade_entry` |
| `data/config/diagnostic_cascade_multiplex.json` | Multiplex Tier-1 panel variant |
| `crusher_labs/diagnostic_cascade.py` | Runtime cascade engine |
| `crusher_labs/cascade_entry.py` | Sick-call vs wearable entry fusion |
| `picard_framework/runs/smoke_cascade_6epoch.json` | 6-epoch standard smoke spec |
| `picard_framework/runs/smoke_cascade_multiplex_6epoch.json` | Multiplex smoke spec |
| `docs/SOP_CASCADE_RECONFIG.md` | Design note (partially landed; prefer live JSON) |

## Enable in a Picard run spec

Set without changing default `crusher_labs/config.yaml` (cascade stays off for
golden regression):

```json
"config_overrides": {
  "diagnostic_cascade": { "enabled": true }
}
```

Campaign surveillance presets (`none`, `syndromic`, `cascade`, `cascade_mpx`, …)
live in `picard_framework/runs/mega_cruise_campaign/campaign_manifest.json`.

## Tier sketch

| Tier | Name | Typical tests / action |
|------|------|------------------------|
| 0 | Wearable clinical triage | Implicit / wearable alert → advance |
| 1 | NP / corpsman | `clinical_rdt` (+ impression routing) |
| 2 | Confirmatory | `clinical_qpcr`, `clinical_microbiology` |
| 3 | Full SOP cascade | High-regret SOP unlock |

`cascade_entry` configures `sick_call_tier`, `wearable_alert_tier`, and
`wearable_alert_fusion` / device fusion rules. Per-tier `sop_gate` lists which
SOPs unlock when that tier goes positive.

## Tests

```bash
python3 -m pytest tests/test_diagnostic_cascade.py \
  tests/test_cascade_entry.py \
  tests/test_smoke_diagnostic_cascade.py \
  tests/test_wearable_anomaly_scorer.py -v --tb=short
```

Smoke expected: both 6-epoch specs complete; each epoch records a
`diagnostic_cascade` block in telemetry.

## Operator notes

- Fleet stoplight SOPs (SOP-013/014) still use shipwide wearable `anomaly_rate`;
  cascade Tier-0 uses `infection_score`.
- Treat `docs/SOP_CASCADE_RECONFIG.md` as a design note — prefer
  `data/config/diagnostic_cascade*.json` and `data/config/protocols.json` for
  current behavior.
- Campaign surveillance ladder divergence is covered in
  `tests/test_mega_cruise_campaign.py`.
