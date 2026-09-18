# Flush aerosolisation, s3 re-bracket: the crossing moved up ~2 decades

**Measured at:** `65d9fb2821c4d389eb92d3470d61f0ab06b84b3a`
**Declared in:** [`FLUSH-S3`](../ledger/FLUSH-S3.md)
**Readout:** [`flush_sweep_v1_stage3_readout.md`](flush_sweep_v1_stage3_readout.md)
**Campaign:** `flush_sweep_v1_{off,1e-9,1e-7,1e-5}_s3`, job definition
`picard-campaign:47`, image digest
`sha256:d6490ea6bf4f542729019b8aef137c7e911d5e5ffbef93bd98fe4951a9fbfa6f`
**Runs:** 2,400 of 2,400 completed, 0 non-Spot failures, seeds 8000–8099 across
six hull/length cells. Every archived run carries the engine SHA above in
`parameters.engine_git_sha`, and every arm's archived
`flush_aerosol_fraction` was read back from the archive and matches its
prefix.

## 1. What this supersedes

Stages 1, 2, `s2r` and `s2e` are withdrawn as current-engine measurements
(`FLUSH-S3`). `s2r` placed the crossing at or below `3e-9` in five of six
cells. **On the current engine `1e-9` is a null in all six cells and the
crossing sits strictly inside `(1e-9, 1e-7]` on the four large-hull cells** —
about two decades higher. The HVAC multiplicity fix therefore dominated the
1–1.5 decade emesis increase that pushed the other way, which is the outcome
the re-bracket existed to decide and is not something a correction factor on
the old archive could have produced.

## 2. Ever-infected per voyage, paired on the shared seed

Mean over 100 paired seeds; the interval is the 95% normal-approximation
interval on the per-seed paired difference against `off`.

| cell | `off` | `1e-9` Δ | `1e-7` Δ | `1e-5` Δ |
|---|---:|---:|---:|---:|
| `fl_exp_7d` | 1.13 | +0.00 [−0.03, +0.03] | +0.56 [−0.19, +1.31] | +3.80 [+0.78, +6.82] |
| `fl_exp_12d` | 1.12 | +0.04 [−0.02, +0.10] | +0.81 [−0.18, +1.80] | +9.66 [+4.23, +15.09] |
| `fl_cls_7d` | 4.64 | +0.33 [−0.34, +1.00] | +2.53 [+1.04, +4.02] | +85.95 [+60.84, +111.06] |
| `fl_cls_12d` | 4.64 | +0.00 [−0.06, +0.06] | +19.84 [+7.60, +32.08] | +240.53 [+192.17, +288.89] |
| `fl_spr_7d` | 7.89 | −0.57 [−1.73, +0.59] | +22.56 [+7.19, +37.93] | +189.10 [+146.75, +231.45] |
| `fl_spr_12d` | 7.22 | +2.08 [−1.77, +5.93] | +52.09 [+24.91, +79.27] | +499.24 [+428.69, +569.79] |

- **`1e-9`: null in all six cells.** No interval excludes zero, and the two
  largest point estimates have opposite signs (`fl_spr_12d` +2.08,
  `fl_spr_7d` −0.57), which is what trajectory noise looks like rather than a
  small effect. The pre-declared rule to extend below `1e-9` is therefore
  **not** triggered.
- **`1e-7`: resolves on all four large-hull cells, null on both expedition
  cells.** The crossing is hull-ordered again, but ordered the other way than
  the per-exposure dose is: expedition has the *highest* dose per exposure
  (smallest stateroom volumes) and the *smallest* gain, because it has too
  few chains to compound — the same ordering-by-baseline-yield `s2r` found.
- **`1e-5`: resolves everywhere and is nowhere near saturated.** Ever-infected
  rises ×10–25 from `1e-7` to `1e-5`. This is the third campaign in which
  per-exposure saturation does not imply voyage-level saturation, and it is
  the reason the arm is kept rather than dropped as filler.

## 3. The `off` arm is disabled, not merely small

The sanitary witness reads `flush_dose_delivered / flush_recipients /
flush_events` = `0 / 0 / 0` in every `off` voyage, in all six cells. That
distinguishes "the disabled path emitted nothing" from "the route ran and was
inert" — the distinction the witness was added for (#540) — so the baseline is
a true zero rather than the limit of the sweep.

The witness also shows why the response is not a straight line in `f_aero`
even though emission is: from `1e-9` to `1e-7` the mean delivered dose rises
~136× rather than 100× on `fl_exp_7d`, because recipients and flush events
rise too. Every host the route infects flushes.

## 4. HVAC drift is no longer the dominant route at baseline

Dominant-route shares from the readout, `off` arm: **fomite 88.9–100% in every
cell, `hvac_airborne` 0.0% in every cell.** `s2r` found `hvac_airborne`
dominant in 26–68% of establishments. The multiplicity fix and the ×0.05
confinement between them did not trim the drift route, they removed it as a
baseline contributor entirely — and that, not the emesis increase, is what
moved the crossing up two decades.

Drift returns only when the flush route loads the air for it: `hvac_airborne`
rises to 38–52% at `1e-5` on the large hulls. So on the current engine drift
is a *downstream consequence* of an aerosol source rather than a source in its
own right, which is the behaviour the confinement factor was supposed to
produce.

One reading trap the same columns set: at `fl_exp_7d`/`1e-9` the flush route
takes 18.2% of dominant-route attributions while the paired Δ in ever-infected
is +0.00 [−0.03, +0.03]. The route is firing and winning attributions, and the
outcome is unchanged — it is substituting for fomite establishments that would
have happened anyway. **Attribution share is not effect size**, and a
non-zero flush share is not evidence that the arm resolves.

## 5. Posting, reported for contrast only

Voyages per 1,000 exceeding the VSP 3% reportable-case threshold.

| cell | `off` | `1e-9` | `1e-7` | `1e-5` |
|---|---:|---:|---:|---:|
| `fl_exp_7d` | 0 | 0 | 0 | 10 |
| `fl_exp_12d` | 0 | 0 | 0 | 50 |
| `fl_cls_7d` | 0 | 0 | 0 | 130 |
| `fl_cls_12d` | 0 | 0 | 60 | 420 |
| `fl_spr_7d` | 0 | 0 | 30 | 200 |
| `fl_spr_12d` | 0 | 10 | 80 | 520 |

Two observations, neither of which selects anything:

1. **Posting is now ordered by hull size, and expedition is the quietest cell
   at every arm.** At `off` and `1e-9` no expedition voyage in 200 posts at
   all. Whatever produced the earlier surplus of VSP-scale expedition
   outbreaks is not present on this engine at these arms; the surplus, if it
   returns, now returns on the large hulls first.
2. **`1e-7` already overshoots A9's 0.33 per 1,000 by two orders of
   magnitude** on the large 12-day cells, and `off` undershoots it with a hard
   zero in 600 voyages. The comparator sits *inside* the swept span. This is
   recorded as the contrast it is; no arm is selected for resembling it, the
   frozen `[1e-9, 1e-3]` band is not narrowed, and `flush_aerosol_fraction`
   remains a declared uncertainty rather than a value.

## 6. Caveats

- **Pairing holds on the boarding cohort, not on the whole trajectory.** The
  first timeseries row is written *after* epoch 0 executes, so it already
  contains same-epoch flush transmission: it is equal to `off` in 600/600
  voyages at `1e-9`, and differs in 8/600 and 14/600 at `1e-7` and `1e-5`,
  **strictly upward in every differing voyage**. That is the route acting in
  epoch 0, not a pairing failure — but it is why the metric of record here is
  the paired difference in final ever-infected, which needs no import
  subtraction, rather than a secondaries count that depends on where the
  boarding cohort stops being countable.
- The dose-response roll on flush recipients consumes the shared rng, so the
  paired intervals carry trajectory noise beyond the route itself. This is the
  same caveat as `s2r` and is the reason a single-cell point estimate is not
  read off this table.
- 100 seeds per cell resolves a Δ of roughly ±0.05 ever-infected on the quiet
  cells and ±30 on `fl_spr_12d`. It is a bracket, not a measurement of the
  crossing's location inside `(1e-9, 1e-7]`.

## 7. What the pre-declared rule selects next

From `FLUSH-S3` §"predeclared follow-up", read against the table above:
`1e-9` is null, so no arms below it; `1e-7` resolves, so the fine arms go
inside `(1e-9, 1e-7)`; and the response still rises materially from `1e-7` to
`1e-5`, which the rule also answers by placing the fine arms below `1e-7`.
Both conditions point the same way:

| Arm | Role |
|---|---|
| `3e-9` | lower half-decade, expected null on expedition |
| `1e-8` | mid-interval |
| `3e-8` | upper half-decade, expected to resolve on the large hulls |

at the full 200 paired seeds on the two arms that end up straddling the
crossing, with `off` re-run rather than re-read (the same-engine `off_s3`
archive is re-readable only for as long as the engine does not move again).
The arms are placed by the shape of the contrast in §2; none is placed by
distance to A9, VSP, MIDRS or Park.
