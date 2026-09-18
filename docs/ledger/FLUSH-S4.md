# FLUSH-S4
**Date:** 2026-09-17
**Commit:** 588582c
**Pathogens:** norwalk_gi
**Status:** open

The fine arms the `FLUSH-S3` re-bracket's predeclared rule selects, at the full
200 paired seeds. `FLUSH-S3` measured `1e-9` as a null in all six hull/length
cells, `1e-7` resolving on the four large-hull cells and null on both
expedition cells, and `1e-5` resolving everywhere without saturating. That
places two distinct crossings, not one, and this campaign brackets both.

## Arms

| Arm | Role |
|---|---|
| `off_s4` | disabled path, re-run rather than re-read (below) |
| `3e-9_s4` | lower half-decade of `(1e-9, 1e-7)` |
| `1e-8_s4` | mid-interval |
| `3e-8_s4` | upper half-decade |
| `3e-7_s4` | brackets the **expedition** crossing from below |

`3e-7` is above the interval the rule names because the rule was written for a
single crossing. `FLUSH-S3` found the expedition cells null at `1e-7` and
resolved at `1e-5`, so their crossing lies in `(1e-7, 1e-5)` and no arm below
`1e-7` can locate it; `3e-7` is the lowest half-decade step that brackets it
from below. It is declared here, before the archives land, for exactly the
reason the rest of the design is: an arm chosen after seeing a readout is
chosen for what it produced.

Five arms × 1,200 runs = 6,000. Seeds 8000–8199, the full matched block, a
prefix of the same block every earlier stage used, so every cell pairs
run-for-run with every other arm and with `FLUSH-S3`'s 100-seed prefix.

Manifests `flush_sweep_v1_{off,3e-9,1e-8,3e-8,3e-7}_s4_manifest.json`, built by
`scripts/build_flush_sweep_v1_manifest.py --stage-tag s4`, verified
field-identical to each other apart from the campaign name and the swept
`flush_aerosol_fraction`. Every arm pins the same four transmission settings
and `hvac.pathogen_pool_transport: airflow`, so the measurement records the
engine state it was taken under rather than inheriting whatever the defaults do
next.

## Why `off` is re-run and not re-read

Main has not moved the engine since `FLUSH-S3` (`65d9fb2…` → `588582c` is docs
and one readout script), so `off_s3` is in principle re-readable on the
overlapping 100 seeds. It is re-run anyway, for two reasons. The fine arms need
`off` on all 200 seeds and the manifest builder takes a seed *prefix* by
construction — never an offset block — so a 100-seed re-read would leave the
second half of every fine arm unpaired. And re-running it buys a check worth
more than the 1,200 runs it costs: **`off_s4` must reproduce `off_s3`
voyage-for-voyage on the 100 shared seeds.** If it does not, the image, the
engine or the seeding is not what this campaign believes it is, and that is
detected here rather than inferred later from a contrast that looks plausible.

## What this campaign may and may not conclude

It may report where the paired difference in ever-infected against `off` first
excludes zero, per hull and length, and the shape of the response between the
brackets. It may not adopt a value: the frozen `[1e-9, 1e-3]` refusal band is
unchanged, `flush_aerosol_fraction` remains a declared uncertainty spanning
Johnson 2013 and Boles 2021, and no arm is selected for its distance to A9,
VSP, MIDRS, Park, or any passenger/crew ratio. Posting is reported as contrast
only.

## Predeclared readout

Primary outcome: paired difference in **final** cumulative ever-infected per
voyage against `off` on the shared seed, per cell, with the 95% interval on the
per-seed difference. Not a secondaries count — `FLUSH-S3` established that the
first timeseries row is written after epoch 0 executes and so already contains
same-epoch flush transmission.

Reported alongside, none of them selecting anything: the flush execution
witness (`flush_events`, `flush_aerosol_emitted`, `flush_recipients`,
`flush_dose_delivered`), which must be `0/0/0` in every `off` voyage;
dominant-route shares, read as attribution and not as effect size (at
`FLUSH-S3`'s `fl_exp_7d`/`1e-9` the flush route took 18.2% of attributions at a
paired Δ of +0.00); posting per 1,000 with its Wilson interval; and the
`off_s4` vs `off_s3` reproduction check above.
