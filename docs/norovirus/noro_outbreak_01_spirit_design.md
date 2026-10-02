# NORO-OUTBREAK-01b design — spirit hull addendum

Status: declared, pre-run. Criteria in this file are frozen before any
spirit cell runs; nothing below is altered after the surface is seen.
Extension of `noro_outbreak_01_design.md` — every clause there (axes,
pins, instruments, triggers, gates) applies verbatim; this file adds
only the spirit cell set and its pairing.

## Scope change

`noro_outbreak_01_design.md` §Non-goals deferred spirit/mega to a later
stage. This addendum runs the spirit class now (the user's call that
spirit sits with the smaller classes for this assessment); mega remains
deferred.

## Cells added

Two tiers on `spirit_cruise_3000` (num_agents 3000, 288 epochs / 12 d),
identical in shape to the classic tiers:

| tier | cells | contents |
|---|---|---|
| `fl_spr_12d_scr` | 3 | rung `shipped` (screening comparator) x Axis A diagonal (0.025,0.007) / (0.0325,0.0185) / (0.040,0.030), nsf 0.29 |
| `fl_spr_12d_ren` | 1 | rung `reportable` (shipped default renewal + stream + crew clause), nsf 0.29 |

`dose_adjustment` 7.57, surveillance `syndromic_comp65`, the IMPORT-01
`config_overrides` block — all verbatim from the parent design.

## Seeds and pairing

- spirit: 1000 seeds per cell, `8105-9104` — same convention the
  classic tiers used.
- the leading 200 (`8105-8304`) pair voyage-for-voyage with
  NORO-IMPORT-01's `fl_spr_12d_scr` / `fl_spr_12d_ren` nsf-0.29 cells
  (the import map ran 200 seeds on spirit; pairing covers those 200).

4 cells x 1000 = 4,000 voyages (manifest total 16,000 with the parent's
12,000).

At spirit's larger complement a posted voyage has a wider numerator
window than expedition/classic; the 1000-seed sizing is kept for the
same A9-resolution argument as the parent design.

## Instruments

Unchanged from the parent design — the same `outbreak_anchor_readout.py`
per-cell frequency/progression/anchor/paired-delta table, now covering
the spirit cells, plus the spirit A4 class IQR from
`vsp_outbreak_series.csv` era `pre` (the scoring table already carries
`spirit_cruise_3000`).

## Report-immediately triggers

Parent triggers, plus:

- Spirit takeoff frequency clearly below the classic cells at matched
  prevalence — hull-size dilution would contradict the expedition->classic
  gradient and needs stating before mega runs.

## Gates

Same as the parent design: this file + manifest tier committed before
any spirit cell runs; canary >= 20 seeds on one spirit cell, read out,
then STOP and report; image rebuilt at the merge SHA and the jobdef
revision recorded in the ledger before the array.

## Non-goals

- mega_cruise_5000 (still deferred).
- Any axis the parent design froze off (nsf sweep, renewal_stationary).
