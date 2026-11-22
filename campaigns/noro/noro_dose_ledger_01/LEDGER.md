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
- [x] `scripts/campaign describe` dry-run count check (array=22)
- [x] image `noro-dose-ledger01` built from `1f8a027c` (contains the
  instrument + review fixes); digest pinned in campaign.json
- [x] jobdef registered; revision recorded below
- [x] canary: 20 seeds, block `classic_cruise_1900` — all SUCCEEDED
- [x] canary readout + report to user
- [ ] full array (remaining cells; already-uploaded cells skip)
- [ ] readout + decision (gates D2′; scopes D1′)

## Pinned refs (fill at submit time)

- job definition: `picard-noro-dose-ledger-01:1`
- image digest: `sha256:958502fdb33283d41db65dbbd937791e687945311e4a7fbf842d14fe67ec652f`
- S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_dose_ledger_01/`
- canary job ids: `picard-noro-dose-ledger-01-classic_cruise_1900-20261122-195110` …`-195151` (20 jobs, seeds 8000–8019)
- array job id: …

## Canary readout (measured 2026-11-22, 20 cells × 288 epochs)

Contract: all frozen invariants pass on every cell — `len(epoch_mass_ledger)==288`,
ledger sums reconcile to voyage counters within 1e-9, `Σ secondaries == acquired_ids`,
`Σ emesis_events` matches the emesis witness.

Pooled: net_gain 213,796 GEC; delivered-to-hands 23.54M GEC of which
patch-delivered 23.47M (99.7%); mouth dose 956,720 GEC (discrete 504k +
solver-integrated 452k); hand-to-hand moved 3,994 GEC; Σhazard 183.0 →
181 secondaries.

Structure, per cell:

- Hot cells are patch cells. Every high-hazard cell (8000: 31.0, 8006:
  146.0, 8009: 0.28) is ≥98% patch-delivered. Secondaries ≈ Σhazard
  (144/146) — in hot cells the challenge converts at ~99%.
- The zone pool is a write-only reservoir: cold cells deposit
  65–14,129 GEC of net pool gain yet deliver ~0–4k total. Pool mass
  sits; it is almost never delivered.
- Delivered→mouth conversion is ~4% pooled (956k/23.5M) — the hand
  reservoir sheds ~96% of delivered mass to wash/decay before a
  swallowing event.
- Hand→hand moved mass is negligible everywhere (max 2,015 GEC on the
  hottest cell) — the multi-hop leg contributes nothing measurable.

Array note: with the canary cells uploaded, the full array runs only
the two remaining paired seeds (8105, 8106).

## Array readout (fill when measured)

…
