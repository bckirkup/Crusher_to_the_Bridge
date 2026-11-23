# noro_external_sequester_01 — campaign ledger

EXTERNAL-SEQUESTER (D2'') canary, declared as
`docs/norovirus/hand_external_sequester_spec.md` (merged via PR #1404;
moved to the norovirus subject directory on implementation per the docs
filing rule).
Two arms on the 20-cell cold cohort of the TOUCH-PATCH canary
(seeds 8000–8019, `classic_cruise_1900`, 288 epochs, `norwalk_gi`),
stacked on `fomite_representation: item_instances` — **40 cells**:

- `classic_cruise_1900_sequester_s` — **arm S (attribution control):**
  `hand_residual_mouthing: per_epoch` + `hand_sequester_fill: stool_only`.
  What residual mouth sampling alone buys.
- `classic_cruise_1900_sequester_sr` — **arm S+R (full mechanism):**
  `hand_residual_mouthing: per_epoch` + `hand_sequester_fill: any_load`.
  Externally acquired hand mass may migrate into the wash-proof
  protected compartment, bounded by a per-host capacity draw from the
  shipped `logU(50, 3200)` band.

Same instrumented worker (`tools/noro_diag/per_host_dose_challenge.py`),
same epoch mass ledger plus the hand-loss partition columns
(`hand_partition_delta_gec`, `hand_pending_end_gec`,
`hand_protected_end_gec`) and the summary `hand_partition` audit block.
Zero new constants; held seeds 8105/8106 stay held.

## Frozen decision criteria (recorded 2026-11-23 before any cell ran)

Take-off gate inherited verbatim from noro_touch_patch_01: cold-cell
floor Sigma-hazard >= 1.1; Ignites := >=9 of 18 previously-cold cells
(8000 and 8006 are the known-hot seeds); per arm.

Decision rules frozen in spec section 6 (S x S+R outcome matrix):

- **Arm S ignites, S+R does or does not:** residual sampling frequency
  was the binding stage; retention is not the missing structure —
  report, do not promote the fill.
- **Arm S+R ignites, arm S does not:** hand-reservoir retention was the
  needed addition; promotion to default-on is a separate change and
  decision.
- **Neither ignites; mouth fraction rises on S but S+R adds nothing
  over S:** the protected compartment is measured not-binding; report
  the partition, change nothing else.
- **Neither ignites, but mouth fraction rises materially on S+R vs S:**
  dwell restored but the ~1%/h capture still strands the dose — the
  bound moves to mouth-touch structure or the challenge.
- **Mouth fraction does not rise on either arm:** the capacity band or
  settle rate itself bounds retention — a bound on both components.

Audit invariants (a violation is an instrument defect, not a null
result):

- `len(epoch_mass_ledger) == 288` per cell; the four counter
  reconciliations within 1e-9 relative.
- Hand-loss partition closes: `sources = sinks + residual` within 1e-9
  relative; internal flows (sequester_migrated, settle, protected leak)
  witnessed but not balance terms.
- `hand_sequester_fill_resolved` / `hand_residual_mouthing_resolved`
  stamped per cell.
- Bit-identity gate: both knobs at defaults reproduce the pre-change
  tree on one seed.
- On-arm provenance witness: no host holds protected/pending mass with
  neither `fill_stool` nor `fill_external` provenance.

Preflight order enforced: local smoke (arm resolution + partition
closure) -> dry-run count -> pinned jobdef revision + image digest ->
S3 prefix clean -> single-child canary inspect -> both 20-seed arrays
with an announced ETA -> stop and report.

## Gate checklist

- [x] Design declared and merged: `docs/norovirus/hand_external_sequester_spec.md`
  (PR #1404); frozen audit invariants and decision rules in section 6.
- [x] Engine + worker implementation (this branch): two selectors with
  bit-identical defaults, hand-loss partition witness across every
  `hand_load + pending` mutation, carrier-provenance witness, reset
  sinks witnessed from the worker, resolved-arm stamps.
- [x] Engine tests: `tests/test_hand_external_sequester.py` (10 cases:
  arm resolution, capacity band + memoization, migration bound,
  residual sweep, partition bookkeeping, inert/draw-free off-arm).
- [x] Local smoke (out/sequester_smoke/, seed 8000, 12 epochs,
  arm S+R): resolved stamps `any_load`/`per_epoch`/`item_instances`/
  `discrete`; partition closes at 3.5e-18 rel; migration exercised
  (0.021 GEC migrated, 25 protected carriers, 0 provenance violations);
  12-row ledger carries the partition columns.
- [x] Baseline-identity gate: seed 8000 / 12 epochs / `item_instances` +
  `discrete`, both knobs at defaults — the branch artifact is bit-identical
  to a `main` worktree (`c3030809`) artifact on every shared key, 12/12
  ledger rows included. Excluded from the comparison, by construction:
  `wall_clock_seconds_*`, `arm_tag`, and the keys that only exist on the
  new tree (`hand_partition`, `hand_sequester_fill` /
  `hand_residual_mouthing` resolved stamps, the per-epoch
  `hand_partition_delta_gec` / `hand_pending_end_gec` /
  `hand_protected_end_gec` columns) — all additive witness, none
  behavioural.
- [x] Jobdef registered against pinned image digest; digest pinned in
  campaign.json. **Image defect found and fixed at canary: the first
  image was built from the root `Dockerfile` (ENTRYPOINT
  `campaign_runner`), which mangles `command: [entrypoint.py, ...]`
  into extra campaign_runner argv — every child exits 2 in ~2.5 s.
  Campaign images must be the two-layer build: root `Dockerfile` as
  `BASE_IMAGE`, then `-f deploy/aws/Dockerfile.campaign` (ENTRYPOINT
  `python3`).** Rebuilt as
  `sha256:d92f1d4c1a440ff0e46a045621d0db8bd5cccfccb157093834c43d8324c78abb`
  (code == f357dd16; verified `deploy/aws/`, `tools/`, `campaigns/`
  present in-container), jobdef `picard-noro-external-sequester-01:3`.
- [x] Dry-run array count = 40 (2 blocks x 20 seeds).
- [x] S3 prefix `campaign/noro_external_sequester_01/` clean.
- [ ] Single-child canary inspected against the audit invariants
  (job `ceb69538-a9cf-4c41-aa3f-79980fc2a6ae`, seed 8000, arm S+R,
  RUNNING).
- [ ] Both 20-seed arrays submitted; ETA announced; stop and report.
