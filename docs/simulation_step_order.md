# Simulation Epoch Step Order (Picard ShipSimulation)

Each epoch executes in this order (matches legacy orchestrator):

1. Apply `ActionEnvelope` (Picard strategic overrides)
2. FRED compliance (`step_fred_compliance`)
3. Mid-cruise pathogen introductions
4. Sync isolation/quarantine IDs to Korkin engine
5. `engine.step()` — agent schedules and legacy internal transmission skip
6. Multi-pathogen infection progression
7. `TransmissionCore.execute_transmission`
8. CONTAM `transport_step` (if enabled)
9. Zone microflora shifts (dual-signal)
10. Ground-truth schema export and optional `ground_truth.json` write
11. Wearable monitoring query
12. Syndromic / RDT / PCR / sequencing modality queries
13. Six-instrument observation sampling
14. Escalation matrix update
15. Stoplight computation and protocol engine evaluation
16. Apply merged SOP modifiers (HVAC, transmission, zone closure, surfaces)
17. Cost accounting
18. Quarantine confinement
19. Infection counter thresholds
20. `record_epoch` → append to `simulation_history`

Finalization writes `simulation_history.json` and `artificial_lab_notebook.json`.
