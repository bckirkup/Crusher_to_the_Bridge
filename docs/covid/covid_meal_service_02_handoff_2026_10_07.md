# Meal-service-02 handoff — 2026-10-07

Status: handoff record. Reports no new campaign numbers — no cell has
run; every quoted figure is a prior measurement with its `Measured at`
SHA. Retires the MEAL-SVC-02 implementation/design session at the
frozen-design boundary: the owner directed the Batch legs to run in a
fresh session with credentials provisioned (this VM carried no AWS
secrets — not a compromise, a missing environment).

## 1. The question

On the verbatim `diamond_princess_2020` replay at θ7.9e6: **where on
the door-drop attenuation axis does `service_to_host` land the
passenger mass — and does the same point keep the crew share near the
record?** MEAL-SVC-01 measured the steward→host direction real and
~15× hot at the shared door-drop factor (confined-pax median 804 vs
bound ≥52, crew share 0.379 vs 0.29, `32b11ccf`); this leg sweeps an
independent per-direction `contact_factor_to_host` to find where the
declared factor lands.

## 2. Current hypothesis

An interior host-factor arm lands the confined-pax median in the bound
region (~52–160) — the MEAL-SVC-01 overcorrection (~15× at shared
~0.175 mean) scales roughly with the factor, putting (0.005, 0.02)
through 0.01 in the landing neighbourhood. Hypothesis, not measurement:
the factor need not act linearly through takeoff/age-structure.

## 3. What landed this session

- **Grammar + seam** (`engines/transmission_core.py`):
  `contact_factor_to_host` on `transmission.caregiver.roles.service` —
  absent → host direction uses the delivery's shared realized draw
  (status quo); scalar/`[lo,hi]` → own corner/interval drawn per
  delivery on its own spawn (`_SERVICE_HOST_CONTACT_STREAM_KEY =
  0x5EC7CF`). Seam at `_credit_service_to_host` (shared factor passed
  in, host factor resolved inside); steward side untouched — the
  `*_svc_base`/`responder` cells are unaffected by construction.
- **Witnesses**: resolved block echoes `contact_factor_to_host` +
  `contact_factor_to_host_mode` (`shared`/`declared`); `crew_window`
  mirrors both plus `service_contact_factor{,_to_host}` and
  `service_host_factor_draws` {n, mean, median, q05, q95, min, max}
  (n == deliveries on DIR cells, 0 on responder cells).
- **Tests**: `TestMealSvc02` — 7 tests covering scalar scaling,
  OFF zero-credit, absent shared-draw, dedicated-stream isolation
  (voyage + shared contact streams untouched), no-spawn on
  fixed/shared, malformed spec-lands failure, responder arms drawing
  nothing. 46/46 in `test_caregiver_mechanism.py` pass.
- **Frozen design**: `docs/covid/covid_meal_service_02_design.md` +
  `picard_framework/runs/covid_meal_service_02_design.json` — 10 arms
  × 20 seeds = 200 cells @θ7.9e6, verbatim CW-02 contract; verdict
  grammar MAGNITUDE-LANDED / OVER-ATTENUATED / STILL-HIGH /
  NONLINEAR-BREAK; audit invariants including the host-factor echo and
  the realized-draw lottery check.
- **Campaign registration**: `campaigns/covid/meal_service_02/`
  (campaign.json 10 blocks × 20 seeds, cell.py, entry.py, readout.py
  with the factor echo/lottery/parity audits + ladder monotonicity
  check + CW-02 and MEAL-SVC-01 drift witnesses, LEDGER.md with the
  preflight checklist).

## 4. What is verified vs not

- Verified locally: unit tests (46/46), design JSON loads and
  enumerates exactly 200 cells, payload contract for the new fields
  asserted in tests.
- **Not verified**: capped-voyage smoke through `run_cell` (the
  payload-shape check on a real voyage), `--dry-run` count, image
  build, jobdef, manifest, canary, array — all Batch-side steps are
  the next session's.

## 5. PRs landed this session

- `devin/1791336679-meal-svc-02` → PR #___ (grammar + seam + witnesses +
  frozen design + campaign registration + readout + ledgers + this
  handoff).

## 6. Running jobs / artifacts

None — no Batch job submitted. S3 `campaign/covid_meal_service_02/` is
empty; jobdef `picard-covid-meal-svc-02` and image `covid-meal-svc-02`
do not yet exist.

## 7. Execution instructions for the successor session

Needs AWS creds (`provisioning-devin-aws-access` skill — the
`picard-devin` bootstrap → `picard-devin-role` path, or the
`PICARD_AWS_*` secrets). Then, per `campaign-preflight`:

1. Merge the PR; record the merge SHA.
2. `scripts/campaign submit covid/meal_service_02 --dry-run` — count
   must be 200.
3. Local smoke: `campaigns/covid/meal_service_02/cell.py --design
   picard_framework/runs/covid_meal_service_02_design.json --theta
   7900000 --arm zone_narrow_svc_dir_cf_lo --seed 20200205 --num-epochs
   <cap>` — check `service_host_factor_draws.n == service_deliveries`,
   echo mode `declared`, host dose scaled, deliveries parity.
4. Build `covid-meal-svc-02` at the merged SHA via
   `Dockerfile.campaign`, push, record the digest; render the jobdef
   via `submit --dry-run` (or `--register-only`), edit
   `containerProperties.image` to `<repo>@sha256:<digest>`, register
   `picard-covid-meal-svc-02` via `--cli-input-json`.
5. Manifest to `s3://crusherbucket-994254241749-us-east-1-an/
   campaign/covid_meal_service_02/`.
6. Canary: `scripts/campaign submit covid/meal_service_02 --block
   zone_narrow_svc_dir_cf_lo --bucket <bucket> --queue
   picard-analysis-queue` — read out with
   `campaigns/covid/meal_service_02/readout.py --prefix s3://…/
   zone_narrow_svc_dir_cf_lo/`, report, **STOP** before the array.
7. If the gate passes: submit the remaining 9 blocks, read out the
   full grid, commit the readout + fill `LEDGER.md`, update
   `docs/ledger/MEAL-SVC-02.md` to `measured` with the merge SHA and
   `Measured at`, and rewrite the §2 measurement of record in
   `docs/covid/covid_open_ledger.md`.

## 8. The single open decision

Where the host-factor ladder lands — and if a MAGNITUDE-LANDED arm
emerges, whether its factor is a sourceable physical magnitude
(contact-pattern literature on door-drop handover asymmetry) or a
signature that the channel's dose law still over-serves confined
hosts.

## 9. Do not reopen

- The 15× overcorrection is a measurement, not a defect — do not
  re-litigate the full pair dose.
- The shared-draw default for the steward side — pinned by owner
  decision; `*_svc_base` rows exist to parity-check it, not to change
  it.
- Delivery cadence, episode share, host-direction efficiency
  constants — parked axes; deliveries parity is an audit invariant,
  not a tuning surface.
