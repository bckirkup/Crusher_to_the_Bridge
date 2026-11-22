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
- [x] Canary readout: 20 jobs `classic_cruise_1900_discrete`
  `-20261122-222149` (index 0, verified RUNNING past entrypoint) +
  `-222726..-222850` (index 1–19), seeds 8000–8019, resubmitted on
  jobdef :23; all SUCCEEDED, all 20 artifacts clean (solver resolved
  `discrete`, len-288 ledgers, reconciliations pass).
  **Readout:** pooled requested 79.8M GEC, offered 2.14B, delivered
  79.6M — per-touch pickup works (~100% of requested filled) but
  ~99.9% of delivered mass is still emesis-patch; cold cells request
  ~0–10k and deliver ~0–5k, same order as the continuous baseline.
  Σhazard 220.2 vs baseline 184.1 (same cells hot: 8006 177 vs 146,
  8000 39 vs 31; mouth dose 2.3M vs 1.0M pooled). Cold cells do not
  ignite → per frozen rule, deficit is upstream of pickup: the pool
  holds mass and pickup works, but encounters on ordinary high-touch
  surfaces request almost nothing.
- [ ] Arm-B remainder (seeds 8105/8106) + arm-C canary on user approval.
- [ ] Readout committed in `docs/ledger/NORO-POOL-PICKUP-01.md` and the
  decision rule applied; interpretation sent.

## Runs

| date | block | shape | job ids | verdict |
|---|---|---|---|---|
| 2026-11-22 | classic_cruise_1900_discrete | 20-seed canary | `-222149`, `-222726..-222850` | delivered≈patch only; deficit upstream of pickup |
