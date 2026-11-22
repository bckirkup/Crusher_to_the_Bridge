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
- [x] Jobdef `picard-noro-pool-pickup-01:22` registered against image
  digest `sha256:770d24a999374c4f83be3680a7c1c8aa03cb844ac4bffb239e46517430eaecf0`
  (pinned in campaign.json). The first registration was built from the
  root Dockerfile whose `campaign_runner` ENTRYPOINT eats the jobdef
  argv — all 20 first-attempt canary jobs failed on
  `unrecognized arguments` before any sim ran; rebuilt from
  `deploy/aws/Dockerfile.campaign` (ENTRYPOINT `python3`) like every
  prior campaign image.
- [x] Dry-run array count = 22 per block (describe + submit --dry-run).
- [x] S3 prefix `campaign/noro_pool_pickup_01/` clean (no artifacts ever
  landed).
- [ ] Canary readout: 20 jobs `classic_cruise_1900_discrete`
  `-20261122-222149` (index 0, verified RUNNING past entrypoint) +
  `-222726..-222850` (index 1–19), seeds 8000–8019, resubmitted on
  jobdef :23; contract verify per artifact, STOP and report.
- [ ] Arm-B remainder (seeds 8105/8106) + arm-C canary on user approval.
- [ ] Readout committed in `docs/ledger/NORO-POOL-PICKUP-01.md` and the
  decision rule applied; interpretation sent.

## Runs

| date | block | shape | job ids | verdict |
|---|---|---|---|---|
