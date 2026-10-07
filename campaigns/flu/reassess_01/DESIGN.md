# FLU-REASSESS-01 — open-voyage re-census on the post-enhancement engine

Status: **spec**. Frozen before any cell runs. The criteria below are the
measurement contract — none may be altered after the surface is seen.

## Why this campaign exists

Every scored flu surface predates the realism enhancement generation that
merged 2026-10-06/07:

| change | PR | shipped default | probe-scale measurement |
|---|---|---|---|
| `transmission.caregiver.service.contact_factor` U[0.05,0.3] — door-drop dose discount on every R3 service delivery | #936 CAREGIVER-SVC-01 | ON | exp onboard 36→~7 median on the 8-seed grid (`docs/ledger/CAREGIVER-SVC-01.md`) |
| `fred_behavior.defiant_escalation_hours: 24` — defiant refusers compelled into `enforced_confinement` at +24 h instead of absorbing forever | #945 DEFIANT-ESC-01 | ON | residual surplus +89 → −25 pooled on seeds 8112/8184/8120 (`docs/ledger/DEFIANT-ESC-01.md`) |
| MEAL-SVC-01 arms (`service.direction:"both"`, `service_responder_mode:"section"`) | #937 | **OFF** (`responder`/`uniform`) | armed but unmeasured on flu |

The baselines of record — FLU-OPEN-01 `7f4702ef` (400 cells), FLU-VIS-01
`ca775a0b` (2400 cells) — were measured pre-enhancement. This campaign
re-measures the open-voyage surface at the merge SHA of record so the flu
line's verdicts rest on the shipped engine.

## Cells

Same spec as FLU-VIS-01 (`tools/diag/conditioned_cell.conditioned_spec`,
`confinement="organic"`, explicit 2-passenger epoch-0 index pair, shipped
boarding-prevalence draw, isolated `influenza_a` on `active_profiles`,
288 epochs) under two observation corners:

- `r100_dec` — shipped vectors verbatim (report_scale 1.0, declared
  eligibility). This IS the new-engine census: re-scores every OPEN-01
  frame.
- `r200_dec` — both reporting vectors ×2 (clip 1.0), declared eligibility.
  The arm that carried the serviced-quarantine sign-reversal at VIS-01;
  the paired r200−r100 contrast re-scores it under both fixes at fleet
  scale.

Blocks: `{exp,spr,cls,mega} × {r100_dec,r200_dec}` = 8 blocks × seeds
8105–8204 = **800 cells**. Queue `picard-analysis-queue` (On-Demand —
the Spot drought precedent; Spot remains the fallback per the playbook).
Resources 1 vCPU / 4096 MB / shm 512 (mega verified under the cap in
OPEN-01). Image tag `flu-reassess01`, digest-pinned at the merge SHA.

## Cell worker and payload

`cell.py` is the VIS-01 contract plus the enhancement witnesses the
engines now produce:

- `mechanism_echo` — resolved `defiant_escalation_epochs`,
  `escort_delay_epochs`, `service_contact_factor` (parsed spec),
  `service_direction`, `service_responder_mode`, `service_enabled`.
- `compliance_actions` — per-action tallies of `state.compliance_log`.
- `enforced_events` — the `enforced_confinement` entries verbatim.
- `refusal_events` — the `refused_*` entries verbatim.
- `caregiver_telemetry` — carries `service_dose_to_host_*` counters
  (must read zero under `direction:"responder"`).

## Audit invariants (a violation is a defect, not a failed criterion)

1. `schema == "flu_reassess_01.v1"` on every cell.
2. `mechanism_echo.service_contact_factor == ["uniform", 0.05, 0.3]`,
   `defiant_escalation_epochs == 24`, `service_direction == "responder"`,
   `service_responder_mode == "uniform"` on every cell.
3. `caregiver_telemetry.service_dose_to_host_credited == 0.0` on every
   cell — the host direction is not armed.
4. `enforced_events` count ≤ `refusal_events` count per cell; enforced
   exists only where a refusal exists.
5. `index_cases >= 2` on every cell (carried invariant).

## Frozen predictions (measured/inferred basis stated)

- **P1 (measured at probe scale):** the r200 sign-reversal is dead on the
  scored grid. On exp, paired r200−r100 mean Δonboard lands ≤ +0.3/seed
  (VIS-01 measured +1.62; DEFIANT-ESC-01 collapsed the named channels on
  the residual seeds and contact_factor discounts the service bridge).
  Reads as sign-reversal-dead verdict when the exp share-positive is also
  ≤0.15 (VIS-01 tail-driven, all medians 0).
- **P2 (inference):** census incidence drops vs OPEN-01 — onboard-acquired
  pooled counts fall on exp (was 282) and plausibly on every class via the
  discounted crew bridge; caregiver share of onboard-acquired drops below
  the 49–55 % measured band.
- **P3 (inference):** presenting attack falls toward Ward on exp (0.89 %
  was sustained by the ~2× voyage attack), and the big-hull residual
  widens — spr/cls/mega sit at 0.13–0.25 % vs Ward 0.7 % and cannot gain.
- **P4 (structural):** pooled rep/inf stays far above the F5 frame
  [0.03, 0.15] on every class — the reporting layer is untouched and the
  floor was structural (~0.19 minimum at r025_str).
- **P5 (mechanism):** `enforced_confinement` fires on a nonempty share of
  cells at both arms (refusers exist on every outbreak voyage); enforced
  epochs cluster ≈24 h after the refusal events.
- **P6 (invariant-ish):** outbreak formation ≥ ~0.6 on exp and ≥ ~0.8
  elsewhere; organic confinement forms on ≥95 % of cells; final ≥ALERT
  within a few points of OPEN-01's 67/96/97/99.

## Reported but never selected on

`mild_onsets`, `escort_delay_epochs`, per-band presentation tallies,
`service_section_steward_draws`, alert-epoch distributions, refusal event
timing, isolated/quarantined splits.

## Reading rules

- Paired deltas are arm-internal to this campaign (same seeds, same
  engine). Deltas vs the `_BASE` constants are cross-engine contrasts —
  flagged as such, never treated as paired.
- No baseline-reuse claim: the engine changed, so nothing here must
  bit-match OPEN-01/VIS-01 payloads. The canary check is payload-schema +
  mechanism-echo conformance, not payload equality.
- A P1–P6 miss is reported as measured; the conclusion then follows the
  surface, not the prediction.

## Non-goals

- `service.direction:"both"`/`section` arming — covid's MEAL-SVC-02
  attenuation decision owns that axis; flu takes the shipped default.
- Conditioned confined-SAR re-census — mechanically invariant (declared
  confinement precedes any order lottery; the factor discounts steward-
  side dose, not host-side). Settled at `8c03e9d7`, not reopened.
- Other reporting corners (r025/r050/strict) — the saturation conclusion
  is structural; only the reversal arm is re-measured.
