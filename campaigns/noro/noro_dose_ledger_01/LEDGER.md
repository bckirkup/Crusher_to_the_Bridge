# noro_dose_ledger_01 — campaign ledger

**Design of record:** `docs/ledger/NORO-DOSE-LEDGER-01.md` (declared,
criteria frozen before any cell ran).

## What this is

D0′ of the 2026-11-22 hand/fomite mechanism review: the joined per-epoch
mass ledger across every cell of the NORO-DOSE-BLOCK-01 design, answering
"where does deposited hand/fomite mass stop between emission and
infection?" — emission → deposit → pickup offer → delivered → hand carriage
→ hand-to-hand → swallowed → credited → hazard, plus the standing
reservoirs (hands, surface pool, emesis patches) at each epoch end.

## Cells

| Block | Platform | Seeds | Epochs | Worker |
|-------|----------|-------|--------|--------|
| classic_cruise_1900 | classic_cruise_1900 | 8000–8019, 8105, 8106 (22) | 288 | tools/noro_diag/per_host_dose_challenge.py |

## Status

- [x] Instrument built and locally smoke-verified (seed 8105, 24 epochs:
  ledger sums reconcile to voyage counters exactly; epoch-20 emesis event
  captured end-to-end)
- [ ] `scripts/campaign describe` dry-run count check
- [ ] image `noro-dose-ledger01` built from a commit containing the
  instrument; digest pinned in campaign.json
- [ ] jobdef registered; revision recorded below
- [ ] canary: 20 seeds, block `classic_cruise_1900`
- [ ] canary readout + report to user
- [ ] full array (remaining cells; already-uploaded cells skip)
- [ ] readout + decision (gates D2′; scopes D1′)

## Pinned refs (fill at submit time)

- job definition: `picard-noro-dose-ledger-01:<rev>`
- image digest: `sha256:…`
- S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_dose_ledger_01/`
- canary job id: …
- array job id: …

## Canary readout (fill when measured)

…

## Array readout (fill when measured)

…
