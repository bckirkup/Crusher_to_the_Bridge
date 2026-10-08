# ONSET-REC-01 design — the onset-recording channel on the boxed crew-mess configuration

Status: declared, pre-run. Criteria in this file are frozen before any
cell runs; nothing below is altered after the surface is seen.

## Question

The CREW-MESS-01 attribution leg resolved the crew-share comparator on
the record's own metric at DP outbreak scale: on `sect_mess_boxed`
(θ7.9e6, 20 seeds) pooled `lab_confirmed` crew share is **0.435**
unconditional and **0.293** conditioned on DP-scale cells
(n_confirmed ≥ 100) vs the record's 0.29
(`reports/funnel_attr/boxed20.json`; `docs/covid/covid_open_ledger.md`).
The residual it left is the dating overshare: dated share of confirmed
**0.839** vs the record's 197/712 = **0.277**, role-flat — the shipped
channel dates every confirmed symptomatic onset.

SERO-CHANNEL-V1 measured the frozen onset-recording channel —
`observation_model.onset_recording` on `sars_cov2_resp`,
`{symptomatic_at_confirmation_required: true, report_probability: 0.56}`,
additive and default-off — on the lambda-cross hull surface and landed
dated share **~0.43–0.53** of lab-confirmed vs the same 0.277 record
(`docs/ledger/SERO-CHANNEL-V1.md`). The channel alone did NOT reach the
record's dating share there.

**What dated share does the same declared channel produce on the boxed
crew-mess configuration — the configuration whose crew composition
already lands — and is it channel-sufficient at DP scale?**

## Arms (2 × 20 seeds = 40 cells)

The boarding-screen arm grammar has no design-level base block and
`_validate_arms` requires the first arm to carry empty overrides, so
the boxed crew-mess configuration — verbatim from the parent's
`sect_mess_boxed` arm overrides — is declared once as the design's
`base_overrides` and composed into every cell's run spec by the
campaign worker (`campaigns/covid/onset_rec_01/cell.py`, via
`apply_arm_overrides` after `prepare_cell_run_spec`). The arm
overrides touch `pathogen_overrides` only — disjoint keys, so the
resolved spec is order-independent.

| arm | overrides | what it is |
|-----|-----------|------------|
| `boxed_declared` | `{}` (empty — required) | boxed crew-mess config on the shipped observation channel; the in-image bit-identity control: resolved spec identical to `sect_mess_boxed`, event counts must reproduce the landed cells at matched seeds |
| `boxed_period` | `pathogen_overrides.sars_cov2_resp.observation_model.onset_recording = {symptomatic_at_confirmation_required: true, report_probability: 0.56}` | boxed config under the record's own onset-recording channel |

The channel's two components are the record's own quantities:
`symptomatic_at_confirmation_required` mirrors the NIID record's
symptomatic-at-specimen field (~51% of DP positives contributed no
onset date); `report_probability 0.56` = (197 dated / 712 confirmed) ÷
~0.49 symptomatic-at-specimen — record-derived arithmetic, **declared
once, never retuned** to the 0.277 anchor or any model output.

## Scoring (frozen)

**Primary — dated share of lab_confirmed**
(`recorded_onsets / lab_confirmed_total`, pooled over the arm's cells
and per-cell median) vs the record's 0.277. Declared expectation band
**[0.43, 0.55]** (SERO-CHANNEL-V1's landing range on a different hull
surface; the funnel attribution on these boxed cells measures gate-only
share ~0.77, so the recall draw is expected to carry the rest). Verdict
grammar:

- **RECORD-MATCHED**: pooled dated share inside [0.227, 0.327]
  (0.277 ± 0.05) — the channel alone reproduces the record's dating
  share on the boxed configuration (report immediately);
- **CHANNEL-INSUFFICIENT**: pooled dated share > 0.327 — the channel
  moves dating but does not reach the record's share; the predicted and
  fully admissible outcome — this design measures the channel, it does
  not certify it;
- **OVER-CLOSED**: pooled dated share < 0.227 (report immediately).

**Secondary — reported beside, never thresholded:** `lab_confirmed_total`
per cell and pooled vs the record's 712 (the ~193/cell under-confirmation
scale is expected to persist — the channel gates dating, not
ascertainment); crew share of lab_confirmed pooled and conditioned on
DP-scale cells (the channel is role-flat so ~unchanged 0.435 / ~0.29-scale
expected — a share move is a signal to investigate, not a defect by
default); symptomatic-at-specimen share (the gate's pass rate,
decomposing dated share into gate × recall); confined-pax during-window
takeoff median vs guard [26, 160]; service deliveries parity ~162k.

**Bit-identity clause:** `boxed_declared` must reproduce the parent's
`sect_mess_boxed` arm bit-identically at matched seeds — resolved spec
equal by construction (`base_overrides` == `sect_mess_boxed.overrides`,
pinned by contract test) and voyage event counts
(`infections_total`, `aboard_total`, `lab_confirmed_total`,
`recorded_onsets`, during-window tallies, `service_deliveries`) equal
to the landed S3 cell payloads, absent engine drift since their image.
A deviation is a defect in the base composition, not a finding —
report immediately.

## Audit invariants (swept on every cell)

- `quarantine_witness.protocol_id == "SOP-017-MESSBOX"`, window_days
  [16,30], activated, 4 exempt crew classes — proves `base_overrides`
  resolved;
- `crew_window.crew_meal_service.mode == "boxed"`, diner_redirects > 0;
- `onset_recording` echo: null on every `boxed_declared` cell; the
  declared block on every `boxed_period` cell;
- `lab_confirmed_total` and `lab_confirmed_by_role` present on every cell;
- `index_onset_day == -1.0`, `index_shedding_at_day0` true, droplet
  split (0.175, 0.0), deliveries > 0.

## Execution

`campaigns/covid/onset_rec_01/` through `scripts/campaign` onto
`picard-analysis-fargate-queue` (the EC2 queue is flooded), jobdef
`picard-covid-onset-rec-01-fargate`, image tag `covid-onset-rec-01`,
S3 prefix `campaign/covid_onset_rec_01/`. All 40 cells are the
canary-scale run — there is no larger array behind it. Read out, then
STOP.

## What this cannot settle

- `report_probability 0.56` is declared, not swept — a different value
  is a different design;
- the channel gates dating, not ascertainment — `lab_confirmed_total`
  staying below 712 is a separate, expected shortfall;
- the dated share on this configuration does not transfer by itself to
  other hulls/configurations — SERO-CHANNEL-V1's landing was a
  different surface and this canary does not reconcile the two.
