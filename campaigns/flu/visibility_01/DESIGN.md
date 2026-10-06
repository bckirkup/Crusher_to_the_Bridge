# FLU-VIS-01 — influenza visibility sweep on the open voyage

> **Status:** Specced — criteria frozen, no cells run. Design of record for
> `campaigns/flu/visibility_01`. Sits on the FLU-OPEN-01 census
> (`7f4702ef`, 400/400 cells).

## 1. Question

The `influenza_a` `observation_model` reporting vectors are declared
scenario axes (evidence grade P) whose own notes say they start "~2× too
visible" and that "closing that is the sweep's job." On the open voyage
the arm now reads **hot on the per-infection ratio** (reported/infected
0.20–0.53 pooled per class vs the Ward-derived frame [0.03, 0.15]) and
**cold on Ward's own metric** — presenting attack ≈0.7 % of complement
was measured exp 0.89 %, cls 0.25 %, spr 0.21 %, mega 0.15 %. A single
scalar cannot reconcile both surfaces if the gap is compositional; this
sweep measures which **declared corner** of the reporting/eligibility
space lands near Ward on each surface, per class — or records the
residual gap as the measurement that the reporting layer's floor is
miscalibrated.

## 2. Measurement gap this closes

- FLU-OPEN-01 measured one grid point (the shipped corner) on both
  comparators; nothing else in the reporting/eligibility space is
  measured. The profile declares the axes precisely so they can be
  swept — this is the sweep.
- The reporting layer feeds back into transmission: reported cases drive
  escalation, recognition flips pre→post reporting vectors, and organic
  confinement removes transmitters. Whether a visibility arm moves
  onboard acquisition (not just counts of reports) is unmeasured.
- The strict-eligibility corner ("mild ILI self-treats rather than
  presenting to the infirmary") is the mechanism most often cited for
  cruise ILI under-ascertainment; its effect on dated onsets and reports
  is declared but unmeasured.

## 3. Cell definition (settled inputs — do not re-derive)

Identical to FLU-OPEN-01 — `conditioned_spec(..., confinement="organic")`,
isolated `influenza_a`, explicit 2-passenger epoch-0 seed, shipped
boarding-prevalence draw, `k = 6e-4`, 288 epochs, seeds 8105–8204,
four classes — **plus a per-arm `pathogen_overrides.influenza_a.
observation_model` patch**:

**Axis A — report scale** (multiplies every entry of
`reporting_probability_by_severity_{pre,post}_recognition`, clipped at
1.0; the hazard composition `eligibility × reporting` and the 3-day
`episode_reporting_window_days` are untouched):

| arm | pre-recognition vector | post-recognition vector |
|-----|------------------------|--------------------------|
| r025 | [0, 0, 0.025, 0.1375, 0.25] | [0, 0, 0.045, 0.175, 0.25] |
| r050 | [0, 0, 0.05, 0.275, 0.5] | [0, 0, 0.09, 0.35, 0.5] |
| r200 | [0, 0, 0.2, 1.0, 1.0] | [0, 0, 0.36, 1.0, 1.0] |

(moderate/severe saturate at the 1.0 ceiling under r200 — the ceiling is
part of the declared space, not a defect.)

**Axis B — eligibility corner** (`syndrome_case_eligibility_by_severity`,
states `[asymptomatic, subclinical, mild, moderate, severe_critical]`):

| corner | vector | reading |
|--------|--------|---------|
| dec | [0, 0, 0.85, 1.0, 1.0] | shipped — mild presents at 0.85 |
| str | [0, 0, 0, 1.0, 1.0] | mild never presents — the
"self-treat, avoid confinement" corner; also makes mild onsets
undatable via `_onset_eligible` |

Grid: 3 × 2 = **6 arms** × 4 blocks (`expedition_cruise_450`,
`spirit_cruise_3000`, `classic_cruise_1900`, `mega_cruise_5000`) × 100
seeds = **2400 cells**.

**Baseline reuse (declared):** the seventh grid point —
r100 × dec, the shipped corner — is FLU-OPEN-01's cells at the
identical seed block and an engine-identical SHA (the spec PR touches
only `campaigns/` + `docs/`). It is **not re-run**; instead a baseline
canary (`flu_exp_12d_r100_dec` index 0 = seed 8105) must reproduce
OPEN-01's `flu_exp_12d/cell_8105.json` counts exactly. If it does not,
the four `*_r100_dec` blocks are submitted as real arms and the reuse
claim is void — the contingency is declared here, before any cell runs.

## 4. Frozen verdict frames (declared before any cell runs)

A sweep, not a screen: **no cell or arm is selected on** — arms are
declared coordinates and the comparators are reading frames.

| # | Surface | Frame |
|---|---------|-------|
| 1 | **Presenting attack** — `ever_reported / complement` per cell, arm × class | read against Ward's ~0.7 % presenting share and the OPEN-01 baseline (exp 0.89 %, cls 0.25 %, spr 0.21 %, mega 0.15 %). An arm×class landing inside ~[0.4 %, 1.0 %] reads "brackets Ward"; a whole class whose every arm misses one direction names the composition gap. |
| 2 | **Reported/infected, pooled** — arm × class | against the F5 frame [0.03, 0.15]; arms below/at it record which declared corner reaches the Ward ratio. |
| 3 | **Reported/infected, acquired cohort** (`infection_epoch > 0`) | same frame; the decomposition the OPEN-01 census proved necessary (imports pool the ratio down). |
| 4 | **Reporting feedback** — `ever_infected`, `onboard_acquired`, `quarantined+isolated`, per-seed paired vs baseline | hypothesis (declared, not a criterion): r025/r050 → fewer reports → less organic confinement → weakly **more** onboard acquisition; r200 → the reverse. A strong monotone response means the visibility level is a transmission-relevant parameter, not just an observation one. |
| 5 | **Recognition timing** — first epoch reaching each escalation status from `escalation_log` | hypothesis: scale-down delays or prevents recognition (pre-recognition reports drive the trigger); strict-mild delays it further. Measured, no threshold. |
| 6 | **Eligibility mechanism witness** — `onset_severity_counts["mild"]` | str arms: ≈0 dated mild onsets confirms the corner fired. A nonzero mild onset count under str = defect (override did not resolve). |
| 7 | **Route mix** — dominant-route histogram + caregiver share, arm × class | reported for the OPEN-01 comparison; reporting level should not move acquisition routes materially (they precede the observation funnel). |

## 5. Audit invariants (deviation = defect, not a failed criterion)

- **Index present**: ≥2 `infection_epoch == 0` infections per cell.
- **Arm echo**: each payload stamps the **resolved** severity model the
  engine used (`_severity_model` post-run: eligibility, reporting_pre,
  reporting_post, window_days) — the smoke and the readout check the
  resolved vectors equal the arm's declared vectors, not just the argv.
- **Baseline canary**: `flu_exp_12d_r100_dec` seed 8105 payload must
  equal OPEN-01 `flu_exp_12d/cell_8105.json` on every count field
  (arm-stamp fields excluded); failure → the four `r100_dec` blocks run
  for real and reuse is void (§3).
- **Artifact contract**: `cell_<seed>.json` per child under its block
  prefix; readout consumes emitted payloads only.
- **Determinism**: same seed + arm + SHA → identical counts.
- **No constant refits**; arms move only declared observation vectors.

## 6. Execution plan (approval-gated)

- Grammar: `campaigns/flu/visibility_01/` —
  `campaign.json` + `cell.py` + `readout.py` + `LEDGER.md`; submit via
  `scripts/campaign`.
- Image: build at the merge SHA of this spec's PR, tag `flu-vis01`;
  `ENGINE_GIT_SHA` echoed per cell.
- Queue `picard-analysis-queue` (On-Demand — Spot droughted on
  FLU-OPEN-01's submit day and On-Demand was approved there; revisit
  Spot if capacity returns).
- Preflight order: `campaign describe` → 2800 cells / 28 blocks ���
  literal `Dockerfile.campaign` build + in-container layout check →
  digest pinned → `--canary` on `flu_exp_12d_r100_dec` (doubles as the
  §5 baseline-identity check) → inspect → submit the 24 non-baseline
  blocks with an announced ETA (or all 28 if the canary voids reuse).
- Expected wall: ~5–15 min/cell by class (OPEN-01 measured 400 cells in
  ~75 min on On-Demand); ~6–8 h for 2400 cells at observed concurrency.
- Definition of done: `docs/flu/flu_visibility_01_readout.md` +
  `docs/ledger/FLU-VIS-01.md` (Measured-at SHA), `flu_open_ledger.md`
  §2 row, and the verdict + next decision delivered.

## 7. Non-goals

- No fitting: comparators are read against declared corners; no corner
  is invented to land on Ward, and a residual gap is reported, not
  tuned.
- No `active_screening` arm — case-finding changes the observation
  *channel* (reaches never-presented hosts), not the reporting level;
  the profile's own notes reserve it for Ward-denominator scenarios.
- No engine or natural-history changes; severity fractions and the
  boarding `state_split` stay shipped.
- No other pathogens; covid/noro arms untouched.
- No confined-SAR re-measurement — the conditioned census owns that
  surface.
