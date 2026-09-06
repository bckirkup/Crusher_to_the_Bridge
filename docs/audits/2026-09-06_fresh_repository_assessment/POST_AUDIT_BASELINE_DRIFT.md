# Post-audit baseline drift — 2026-09-06 07:00 UTC

The audited baseline remains `07561adf2b93ff6b358859fb382b253c08828156`; do not revise its findings retroactively.

Current GitHub main is `9fafcc9d9ddaf70612b363492c82f8494d68d406`, six commits and 23 changed paths ahead. The changes are scientifically material, not incidental: a new COVID composite-Theta fit, targets/schema/tool/results, held-out hull scoring, norovirus Morris/admissible-region updates, parameter-register changes, and source/test changes.

Implications:

- The r11 assessment remains valid only for its pinned SHA.
- The new fit/result artifacts are unaudited and cannot be used to clear r11 blocks.
- Before adopting current main as a new baseline, perform a focused delta audit: fit target provenance and units; objective/likelihood and uncertainty; held-out-hull separation; identifiability; leakage; runtime/config lineage; and whether new result JSON files are generated, reproducible evidence or merely committed outputs.

Machine record: `scratch/2026-09-06-post-audit-baseline-drift.json`.
