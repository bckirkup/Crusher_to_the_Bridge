# ONSET-REC-01 ledger

**Status:** measured — verdict CHANNEL-INSUFFICIENT (dated share pooled
0.416 vs record band top 0.327); see `docs/ledger/ONSET-REC-01.md` and
`reports/covid_onset_rec_01_readout.md`.

**Design:** `picard_framework/runs/covid_onset_rec_01_design.json` —
the frozen onset-recording channel armed on the boxed crew-mess
configuration (the parent's `sect_mess_boxed` arm, carried as
`base_overrides` composed by the cell worker so the empty-override
baseline arm reproduces it bit-identically). 2 arms x 20 seeds = 40
cells, theta 7.9e6, seeds 20200205-20200224. The whole design is the
canary — there is no larger array.

**Frozen scoring:** primary = dated share of lab_confirmed
(recorded_onsets / lab_confirmed_total, pooled + per-cell median) vs
the record's 0.277, declared expectation band [0.43, 0.55], verdict
grammar RECORD-MATCHED / CHANNEL-INSUFFICIENT / OVER-CLOSED.
Secondaries reported beside never thresholded: lab_confirmed_total vs
712, lab_confirmed crew share (channel is role-flat; expect unchanged),
confined-pax [26,160], deliveries parity ~162k.

## Runs

| leg | array / image / jobdef | cells | status |
|-----|----------------------|-------|--------|
| canary (all 40) | image `picard-campaign:covid-onset-rec-01` @ `sha256:812b02bb` (built at `bccc9daa` — Docker Hub 429'd the root `python:3.11-slim`, overlay on in-ECR base `covid-gm-rescore-02` + all source trees); jobdef `picard-covid-onset-rec-01-fargate:2` on `picard-analysis-fargate-queue` | 2 x 20 | SUCCEEDED 40/40 ~16:0xZ: boxed_declared `0b49e3f6-4f4e-461e-9edd-f5af5d1d8083`, boxed_period `3391150c-b556-4168-9e8e-8afab55e8566` |

## Readout (40/40, zero audit violations)

| arm | dated share (pooled / med) | pooled conf | pooled rec | lab_conf crew share (pooled / DP) | verdict |
|-----|---------------------------|-------------|------------|-----------------------------------|---------|
| boxed_declared | 0.839 / 0.833 | 819 | 687 | 0.435 / 0.293 (n=2) | BASELINE — bit-identical to landed `sect_mess_boxed` on all 20 seeds |
| boxed_period | 0.416 / 0.323 | 819 | 341 | 0.435 / 0.293 (n=2) | CHANNEL-INSUFFICIENT |

Secondaries: confined-pax takeoff med 28/29 in [26,160]; deliveries med
162,184 vs ~162k; symp@specimen med 0.688 both arms. The channel removes
~half the dated mass (687→341) and still leaves dated share ~0.14 above
the record's 0.277 — the residual is observational, not transmission.
