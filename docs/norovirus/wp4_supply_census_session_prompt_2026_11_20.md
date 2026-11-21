# WP4 session prompt — supply census + population/composition contrasts

> **Status:** Session brief written ahead of launch. Gated on the declared
> freeze — its deliverable is campaign-scale runs on the named reference.
> Do not start until the freeze is declared.

Paste into a fresh Devin session on bckirkup/Crusher_to_the_Bridge. One deliverable,
one session (bounded-research-sessions rule).

```
Paper-1, work package WP4 — supply-side census at campaign scale plus the
population/composition contrast legs. Read first:
docs/norovirus/paper1_simulation_plan_assessment_2026_11_20.md (item 3) and
docs/norovirus/paper1_freeze_design_contract_2026_11_20.md. The freeze MUST
be declared before you run any cell — check for the declaration commit that
records the named SHA; if absent, stop and report rather than running on an
unfrozen reference.

Settled inputs (do not re-derive):
- SUPPLY-STRUCTURE-01 Stage A is implemented and its design frozen (PR
  #1319): supply_structure rungs independent / line_shared /
  venue_group_shared / fleet_shared, venue_menu masks, lot_scale. It has
  been smoke-tested, never run at campaign scale — this is the "inexpensive
  first" leg of Edison's item 3.
- Population and composition are config-level contrasts: population draw +
  config_overrides.ship_graph.agent_classes (all seven classes must be
  declared summing to 1.0; agent_class_fractions is the stamped OUTPUT, not
  the input key). Paired-seed designs are the existing pattern.
- Every cell carries the contract §2 frozen block verbatim.
- Spatial/dining organization is NOT a config dial — it needs synthetic
  platform variants and is built only if the cheap legs show a contrast is
  informative. Propose; do not build in this session.

Deliverable (exactly one):
- The Stage A census at campaign scale on the frozen reference plus the
  paired-seed population and composition contrast cells, with the committed
  readout under docs/norovirus/ (campaign dir under campaigns/noro/<name>/,
  LEDGER.md, canary-then-array discipline per campaign-preflight and the
  bounded-research-sessions campaign gate: canary >=20 seeds at one cell,
  read out and reported BEFORE the array is submitted).

Non-goals:
- No synthetic platform variants, no mechanism work, no freeze changes, no
  Edison push beyond the committed readout.

Validation gate before array:
- campaign-preflight in full: local smoke, --dry-run count matching the
  design, pinned image digest, manifest in S3, one canary child inspected,
  then the array with an ETA.

Report immediately if:
- The canary contradicts the Stage A design's expectations (report on
  discovery — do not proceed silently to the array).
- The contrast cells cannot be expressed as config_overrides.

Stop when: the census + contrast readout is committed, the ledger updated,
and this file's Result section records the campaign name, cell counts,
canary verdict and headline findings (commit that update).
```

## Result
