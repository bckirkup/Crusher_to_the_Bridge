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
- [x] Jobdef `picard-noro-pool-pickup-01:1` registered against image
  digest `sha256:2b498f102f32ea6d4637e4d75739a2d5668c392a8faf4a1a5c726b695db7ab15`
  (pinned in campaign.json).
- [x] Dry-run array count = 22 per block (describe + submit --dry-run).
- [x] S3 prefix `campaign/noro_pool_pickup_01/` clean (new prefix).
- [ ] Canary readout: 20 jobs `classic_cruise_1900_discrete`
  `-20261122-215919..-220039` (seeds 8000–8019) submitted 2026-11-22 ~22:00Z;
  contract verify per artifact, STOP and report.
- [ ] Arm-B remainder (seeds 8105/8106) + arm-C canary on user approval.
- [ ] Readout committed in `docs/ledger/NORO-POOL-PICKUP-01.md` and the
  decision rule applied; interpretation sent.

## Runs

| date | block | shape | job ids | verdict |
|---|---|---|---|---|
