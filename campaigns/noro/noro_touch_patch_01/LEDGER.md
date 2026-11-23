# noro_touch_patch_01 — campaign ledger

TOUCH-PATCH canary, declared as `docs/proposals/fomite_touch_patch_spec.md`
(merged via PR #1401). One new arm on the 22 frozen `classic_cruise_1900`
cells (seeds 8000–8019 + 8105/8106, 288 epochs) against the
NORO-POOL-PICKUP-01 measured baseline:

- `classic_cruise_1900_item_instances` — `fomite_representation:
  item_instances`: deposits land on the discrete items each touch
  samples; pickups sample one reachable instance per touch and request
  at that instance's areal density. Same instrumented worker
  (`tools/noro_diag/per_host_dose_challenge.py`), same epoch mass
  ledger plus instance witness columns.

## Gate checklist

- [x] Design declared and merged: `docs/proposals/fomite_touch_patch_spec.md`,
  frozen audit invariants and decision rules in section 6.
- [ ] Local smoke: `--fomite-representation item_instances` resolves
  (`fomite_representation_resolved: "item_instances"` stamped), epoch
  ledger schema intact, instance witness columns present.
- [ ] Jobdef `picard-noro-touch-patch-01` registered against a pinned
  image digest built from `deploy/aws/Dockerfile.campaign`
  (ENTRYPOINT `python3`), digest pinned in campaign.json.
- [ ] Dry-run array count = 22 (describe + submit --dry-run).
- [ ] S3 prefix `campaign/noro_touch_patch_01/` clean.
- [ ] Canary readout: 20-seed canary at one cell, then stop and report.
  Audit invariants per spec section 6: len-288 epoch ledgers per cell,
  four counter reconciliations within 1e-9, instance-mass sum
  reconciles to `surface_pools_by_pathogen` per epoch within 1e-9,
  `fomite_representation_resolved: "item_instances"` stamped on every
  artifact.

## Runs

| date | block | shape | job ids | verdict |
|---|---|---|---|---|
