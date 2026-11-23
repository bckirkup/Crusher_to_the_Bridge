# noro_touch_patch_01 — campaign ledger

TOUCH-PATCH canary, declared as `docs/norovirus/fomite_touch_patch_spec.md`
(merged via PR #1401). One new arm on the 22 frozen `classic_cruise_1900`
cells (seeds 8000–8019 + 8105/8106, 288 epochs) against the
NORO-POOL-PICKUP-01 measured baseline:

- `classic_cruise_1900_item_instances` — `fomite_representation:
  item_instances`: deposits land on the discrete items each touch
  samples; pickups sample one reachable instance per touch and request
  at that instance's areal density. Same instrumented worker
  (`tools/noro_diag/per_host_dose_challenge.py`), same epoch mass
  ledger plus instance witness columns.

## Frozen decision criteria (recorded 2026-11-23 before any cell ran)

Spec section 6 leaves the take-off gate to be frozen here. Frozen
values, both sourced from D0' (docs/ledger/NORO-DOSE-LEDGER-01.md,
measured `1f8a027c`):

- **Hot-cell floor:** the lowest Sigma-hazard among D0' take-off
  cells is 1.1 (seed 8105; hot cells were 8000: 31.0, 8006: 146.0,
  8105: 1.1, each >=98% patch-delivered).
- **Previously-cold canary cells:** 18 of 20 (8000 and 8006 took off
  under the baseline; 8105 is held for the full-campaign decision).
- **Ignites :=** at least 9 of the 18 previously-cold canary cells
  reach Sigma-hazard >= 1.1 under `item_instances`. Below that the
  arm did not ignite; the "requests rise / stay ~0" rules in spec
  section 6 then classify the bound.

Preflight order enforced: a single-child job (`--canary --index 0`,
seed 8000) runs first and its artifact is inspected against the
section-6 audit invariants; only then does the 20-child canary array
(seeds 8000-8019) go out. The two held seeds 8105/8106 and any
promotion decision remain gated on the full canary readout.

## Gate checklist

- [x] Design declared and merged: `docs/norovirus/fomite_touch_patch_spec.md`,
  frozen audit invariants and decision rules in section 6.
- [x] Local smoke (out/touch_patch_smoke/, seed 8105, 24 epochs):
  `fomite_representation_resolved: "item_instances"` stamped, epoch
  ledger schema intact, instance witness columns present,
  instance-pool drift 0.0, `contamination_solver_resolved: "discrete"`
  stamped while configured continuous (per-surface rep forces discrete).
- [x] Jobdef `picard-noro-touch-patch-01:1` registered against pinned
  image digest `sha256:946ef435cb8e70516d53ed00c3612af51df4f58c98b1d2efc65b434bc4cd8217`
  built from `deploy/aws/Dockerfile.campaign` over
  `picard-campaign:touch-patch-base` (ENTRYPOINT `python3`), digest
  pinned in campaign.json. Baseline-identity gate: pooled artifact
  bit-identical branch-vs-stash except volatile wall-clock (additive
  witness keys now emitted only when the arm ran / solver diverges).
- [x] Dry-run array count = 22 (describe + submit --dry-run).
- [x] S3 prefix `campaign/noro_touch_patch_01/` clean.
- [x] Canary readout: 20-seed canary at one cell, then stop and report.
  Single-child preflight inspection PASSED (row above).
  Audit invariants per spec section 6: len-288 epoch ledgers per cell,
  four counter reconciliations within 1e-9, instance-mass sum
  reconciles to `surface_pools_by_pathogen` per epoch within 1e-9,
  `fomite_representation_resolved: "item_instances"` stamped on every
  artifact, and child-0 artifact inspected before any further
  submission.

## Runs

| date | block | shape | job ids | verdict |
|---|---|---|---|---|
| 2026-11-23 | classic_cruise_1900_item_instances | 20-child array, seeds 8000-8019 (indices 0-19; 8105/8106 held for the full-campaign decision) | 110a1dae-ff16-4cc3-a616-be36e8eccdd7 | FAILED fast, all 20: manual submit passed `python3` as argv[0]; container ran `python3 python3`, exit 2 |
| 2026-11-23 | classic_cruise_1900_item_instances | 20-child array, seeds 8000-8019 | cc56f036-cab8-49fd-9c98-ca85fa9531e6 | TERMINATED: bare --s3-prefix fails _s3_uri (requires s3:// scheme) |
| 2026-11-23 | classic_cruise_1900_item_instances | single-child preflight canary, index 0 (seed 8000), jobdef :2 | b5f62f1b-d1b0-4adc-9b0e-57d040267ff1 | SUCCEEDED; artifact inspected: len-288 ledger, resolved arm stamped, solver resolved discrete (configured continuous), instance<->pool drift 0.0 (max over 288 epochs, per-epoch ~1e-22), credited==read-at-challenge 3,889,087 GEC, witness 6.56M touches / 1.26M contaminated / 44.6k coincident / 1064 instances, hazard 26.9, 28 acquisitions |
| 2026-11-23 | classic_cruise_1900_item_instances | 20-child array via --size 20 (seeds 8000-8019; 8105/8106 held), jobdef :3 | ff4673b5-20f0-4196-b177-945580d8cf4a | 20/20 SUCCEEDED, audit clean. VERDICT: requests rose, take-off no (2/18 cold >=1.1 vs >=9 gate) -> bound moved downstream to hand-reservoir -> mouth conversion. Full entry: docs/ledger/NORO-TOUCH-PATCH-01.md |
