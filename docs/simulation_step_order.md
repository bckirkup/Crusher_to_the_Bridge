# Simulation Epoch Step Order

## Picard `ShipSimulation` (with `DecisionRuntime`)

When the Picard run spec includes a `social` block, each epoch follows this order:

1. Clear per-epoch behavioral overrides; reset `EpochDecisionContext` ephemeral fields
2. Apply external `ActionEnvelope` (e.g. Presidio `DecisionRound` or imported actions)
3. FRED compliance (`step_fred_compliance`)
4. Mid-cruise pathogen introductions
5. Sync isolation/quarantine IDs to Korkin engine
6. `engine.step()` — agent schedules
7. Multi-pathogen infection progression
8. `TransmissionCore.execute_transmission`
9. CONTAM `transport_step` (if enabled)
10. Zone microflora shifts (dual-signal)
11. Ground-truth schema export
12. Wearable monitoring query (multi-device epoch generation, confounder sampling, detection profile gating, visibility filtering)
13. **Information diffusion** (belief update from contact graph)
14. **Stackelberg population** (`solve_population`) → apply population actions (`hide_symptoms`, `report_sick_call`, `refuse_quarantine`)
15. **Syndromic / RDT** (behavioral overrides + belief-scaled sick-call probability)
16. PCR / sequencing (verification-test queue zones merged into surface wipes)
17. Six-instrument observation sampling
18. Escalation matrix update
19. Stoplight computation
20. **Stackelberg command / medical** (`solve_command_medical`) → apply command/medical actions
21. Protocol engine evaluation (`forced_protocol_ids` + stoplight triggers; authorized debits)
22. Apply merged SOP modifiers (HVAC, transmission, zone closure, surfaces)
23. Cost accounting (financial / labor / materials)
24. Quarantine confinement
25. Infection counter thresholds
26. **Operational impact score (OIS)** accounting
27. `record_epoch` → append to `simulation_history`

Finalization writes `simulation_history.json` and `artificial_lab_notebook.json`.

## Legacy `orchestrator.py` loop

Same Crusher Labs physics and instruments as Picard, but **no** Stackelberg population/command passes. OIS is accumulated after confinement. Epoch order matches the pre–game-theory orchestrator (stoplight-only SOPs, flat syndromic `sick_call_probability` unless extended later).

1. FRED compliance through ground-truth export
2. Wearable (multi-device, confounders, detection profiles) → syndromic → RDT → PCR → sequencing → instruments
3. Escalation → stoplights → protocol evaluation → modifiers
4. Cost accounting → quarantine → infection counters → **OIS** → `record_epoch`
