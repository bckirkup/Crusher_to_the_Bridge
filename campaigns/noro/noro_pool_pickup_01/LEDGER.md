# noro_pool_pickup_01 — campaign ledger

D2′ re-spec, declared as `docs/ledger/NORO-POOL-PICKUP-01.md`. Two arms on
the 22 frozen `classic_cruise_1900` cells (seeds 8000–8019 + 8105/8106,
288 epochs) against the NORO-DOSE-LEDGER-01 measured baseline:

- `classic_cruise_1900_discrete` — `contamination_solver: discrete`:
  ordinary zone-pool pickup through per-touch `_deliver_fomite_requests`.
- `classic_cruise_1900_per_surface` — `fomite_representation: per_surface`:
  item-class pools (also routes through the discrete path).

## Gate checklist

- [x] Design declared: `docs/ledger/NORO-POOL-PICKUP-01.md` with frozen
  audit invariants and selection rules.
- [x] Local smoke: `--contamination-solver discrete` resolves
  (`contamination_solver_resolved: "discrete"` stamped), epoch ledger
  schema intact, discrete requested/offered columns present.
- [ ] Jobdef registered with pinned image digest (fill in at submit).
- [ ] Dry-run array count = 22 per block.
- [ ] S3 prefix `campaign/noro_pool_pickup_01/` clean.
- [ ] Canary: 20-seed block `classic_cruise_1900_discrete`
  (seeds 8000–8019), contract verified per artifact, STOP and report.
- [ ] Arm-B remainder (seeds 8105/8106) + arm-C canary on user approval.
- [ ] Readout committed in `docs/ledger/NORO-POOL-PICKUP-01.md` and the
  decision rule applied; interpretation sent.

## Runs

| date | block | shape | job ids | verdict |
|---|---|---|---|---|
