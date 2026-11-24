# noro_carrier_distribute_01 — campaign ledger

CARRIER-DISTRIBUTE (D3'') canary, declared as
`docs/norovirus/hand_carrier_distribute_spec.md` (merged via PR #1409;
moved to the norovirus subject directory on implementation per the docs
filing rule).
Two arms on the 20-cell cold cohort of the TOUCH-PATCH canary
(seeds 8000–8019, `classic_cruise_1900`, 288 epochs, `norwalk_gi`),
stacked on the measured S+R sequester stack
(`fomite_representation: item_instances`,
`hand_sequester_fill: any_load`, `hand_residual_mouthing: per_epoch`,
`contamination_solver: discrete`) — **40 cells**:

- `classic_cruise_1900_carrier_r` — **arm R (redeposit):**
  `hand_redeposit_mode: carriers` + `hand_donor_mode: shedders_only`.
  Isolates surface+food redistribution the shipped selector already
  provides.
- `classic_cruise_1900_carrier_rd` — **arm R+D (redeposit + donation):**
  `hand_redeposit_mode: carriers` + `hand_donor_mode: carriers`.
  Adds carrier→hand donation through the direct-contact donor pool.

Same instrumented worker (`tools/noro_diag/per_host_dose_challenge.py`),
same epoch mass ledger and hand-loss partition audit, plus the
carrier-activity witness (`hand_partition.carrier_activity` and
`carrier_provenance_violations` in each summary). Zero new constants;
held seeds 8105/8106 stay held.

## Frozen decision criteria (from spec section 6, recorded before any cell ran)

Take-off gate inherited verbatim from noro_touch_patch_01: cold-cell
floor Sigma-hazard >= 1.1; Ignites := >=9 of 18 previously-cold cells
(8000 and 8006 are the known-hot seeds); per arm.

- **Arm R+D ignites, arm R does not:** hand->hand donation was the
  missing hop — promotion to default-on is a separate change and
  decision.
- **Arm R ignites:** deposit-route redistribution was sufficient —
  promotion is a separate change and decision.
- **Breadth rises materially (hosts_for_90pct >= ~8 median) but neither
  ignites:** dose landing is fixed and aggregate delivered volume is
  still short — the bound becomes the measured multiplier to hot-cell
  credited mass (~200x); report, change nothing else.
- **Breadth flat on both arms:** carriers never deposited/donated — the
  provenance witness decides whether the mechanism even fired; the
  carriers mechanism is measured bounded; report, change nothing else.

Audit invariants (a violation is an instrument defect, not a null
result):

- `len(epoch_mass_ledger) == 288` per cell; the four counter
  reconciliations within 1e-9 relative.
- Hand-loss partition closes: `sources = sinks + residual` within 1e-9
  relative; `internal_host_transfer*` and `sink_redeposited` witness the
  redistributed mass.
- `hand_redeposit_mode_resolved` / `hand_donor_mode_resolved` stamped
  per cell.
- Bit-identity gate: both selectors at defaults reproduce the
  pre-change tree on one seed.
- Carrier provenance: every non-shedder that deposits or donates
  (`deposited_carrier` / `donated_carrier`) has a witnessed earlier
  positive acquisition (`acquired` or `fill_stool`/`fill_external`) —
  `carrier_provenance_violations` must be empty.

Preflight order enforced: local smoke (arm resolution + partition
closure) -> dry-run count -> pinned jobdef revision + image digest ->
S3 prefix clean -> single-child canary inspect -> both 20-seed arrays
with an announced ETA -> stop and report.

## Gate checklist

- [x] Design declared and merged: `docs/proposals/hand_carrier_distribute_spec.md`
  (PR #1409); frozen audit invariants and decision rules in section 6.
- [x] Engine + worker implementation (this branch): `hand_donor_mode`
  selector widening `_direct_contact_unit`'s donor sampling pool to
  shedders + gate-passing carriers; target excluded from its own pool;
  `donated_carrier`/`deposited_carrier`/`acquired` provenance flags and
  `hand_carrier_activity` counters across surface, food, sanitary and
  hand->hand sites; resolved stamps `hand_redeposit_mode_seen` /
  `hand_donor_mode_seen` in the worker.
- [x] Engine tests: `tests/test_hand_carrier_distribute.py` (12 cases:
  arm resolution, pool membership and gate, selector independence,
  carrier-only unit staying alive, donation/deposit witnesses,
  default-path inertness, spec/CLI/manifest plumbing).
- [ ] Local smoke (arm R+D): resolved stamps; partition closes;
  carrier activity and provenance exercised.
- [ ] Baseline-identity gate: both selectors at defaults reproduce the
  pre-change tree on one seed on every shared key.
- [ ] Jobdef registered against pinned image digest (two-layer build:
  root Dockerfile as BASE_IMAGE + `deploy/aws/Dockerfile.campaign`);
  digest pinned in campaign.json.
- [ ] Dry-run array count = 40 (2 blocks x 20 seeds).
- [ ] S3 prefix `campaign/noro_carrier_distribute_01/` clean.
- [ ] Single-child canary inspected against the audit invariants.
- [ ] Both 20-seed arrays submitted — STOP and report before this step
  per the bounded-research rule.
- [ ] Readout: verdict and waterfall in `docs/ledger/NORO-CARRIER-DISTRIBUTE-01.md`.
