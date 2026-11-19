# CONTAM-FLEET-WORKUP-PROTOCOL-01
**Date:** 2026-11-19
**Commit:** d5d50d3a7bc30d50231e6f27b5083925f26c9c23
**Pathogens:** all
**Status:** declared

**Design freeze for the fleet native-vs-ContamX workup. No field was solved
and no solver was timed; nothing here may be quoted as a result.** No
pathogen, occupant or stochastic outcome is part of the design. No seeds or
AWS jobs apply.

**Frozen.** The [protocol](../audits/2026-11-19_contam_fleet_workup_protocol/README.md)
and its generated files: input manifest, 82-row roster, 2,156-row run
matrix, protocol document, dry-run counts and checksums. All are derived
from git objects at the commit above by
`tools/contam_fleet_workup_design.py`; `--verify-only` rebuilds them twice
and byte-compares.

**Totals.** 77 hulls in scope, 5 excluded with a roster row each. 13
settings. Planned rows: 1,591 executed, 525 structural non-response (native
lane has no weather input), 40 not applicable. Planned cold cell executions:
9,546, of which 6,810 call ContamX.

**Input finding (static, from the committed files).** The outdoor-air
fraction of positive-duty groups differs between `air_flow_paths.json`
(native) and what the hobbyist export resolves for 339 of 437 groups on 75
of 77 hulls. The comparative ContamX lane is harmonized through existing
input fields; the as-committed export is a separate baseline-only lane.

**Not ready.** No runner, no aggregate reducer, no recorded ContamX
executable digest for this work, no chosen timing host. See the protocol.

**Single next stage.** Smoke and canary on the four rule-selected hulls,
with the field-realization check first; read out and stop before any other
hull runs.
