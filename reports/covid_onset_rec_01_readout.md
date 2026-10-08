# ONSET-REC-01 readout

- source: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_onset_rec_01/`
- design: `picard_framework/runs/covid_onset_rec_01_design.json`
- coverage: 40/40 cells (partial: False)
- audit invariants: 0 violation(s)

| arm | n | takeoff | lab_conf med | pooled conf | pooled rec | dated share (pooled / med) | lab_conf crew share (pooled / DP-scale pooled) | symp@specimen med | confined-pax med | deliveries med | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| boxed_declared | 20 | 9 | 8.500 | 819 | 687 | 0.839 / 0.833 | 0.435 / 0.293 (n=2) | 0.688 | 28.000 | 162184.500 | BASELINE (bit-identity control) |
| boxed_period | 20 | 7 | 8.500 | 819 | 341 | 0.416 / 0.323 | 0.435 / 0.293 (n=2) | 0.688 | 29.000 | 162184.500 | CHANNEL-INSUFFICIENT (dated share 0.416 > 0.327; expected band (0.43, 0.55)) |

Record dated share 0.277 (197/712); record band (0.227, 0.327); declared expectation band (0.43, 0.55); confined-pax guard (26.0, 160.0); deliveries parity 138080-186814; DP-scale conditioning n_confirmed >= 100.

## Audit-invariant violations

- none

## Bit-identity witness (boxed_declared vs landed sect_mess_boxed)

- seed 20200205: IDENTICAL
- seed 20200206: IDENTICAL
- seed 20200207: IDENTICAL
- seed 20200208: IDENTICAL
- seed 20200209: IDENTICAL
- seed 20200210: IDENTICAL
- seed 20200211: IDENTICAL
- seed 20200212: IDENTICAL
- seed 20200213: IDENTICAL
- seed 20200214: IDENTICAL
- seed 20200215: IDENTICAL
- seed 20200216: IDENTICAL
- seed 20200217: IDENTICAL
- seed 20200218: IDENTICAL
- seed 20200219: IDENTICAL
- seed 20200220: IDENTICAL
- seed 20200221: IDENTICAL
- seed 20200222: IDENTICAL
- seed 20200223: IDENTICAL
- seed 20200224: IDENTICAL
