# ONSET-REC-01 ledger

**Status:** designed + canary submitted; readout pending.

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
| canary (all 40) | _pending_ | 2 x 20 | _pending_ |
