# Flush aerosolisation, s4 fine arms: six cells, six different crossings

**Measured at:** `7f689b99e50fbc08eec55b5a8037b121935ab32f`
**Declared in:** [`FLUSH-S4`](../ledger/FLUSH-S4.md)
**Readout:** [`flush_sweep_v1_stage4_readout.md`](flush_sweep_v1_stage4_readout.md)
**Campaign:** `flush_sweep_v1_{off,3e-9,1e-8,3e-8,3e-7}_s4`, job definition
`picard-campaign:48`, image digest
`sha256:5c0b6607197b63ba6fdc5d3870dafdb2d94bd1aaaefffb2ac1d1152eb14e2c83`
**Runs:** 6,000 of 6,000 completed, 0 failures of 1,280 array children, seeds
8000–8199 across six hull/length cells. Every archived run carries the engine
SHA above in `parameters.engine_git_sha`; every arm's archived
`flush_aerosol_fraction` was read back from the archive and matches its prefix
(one fraction per arm, no mixed values, no mixed SHAs).

The engine tree is identical to `FLUSH-S3`'s `65d9fb2` — the stamp differs
because the image was built from this branch's tip, which is docs and one
readout script ahead. The reproduction check in §1 is what establishes that,
rather than the commit range.

## 1. `off_s4` reproduces `off_s3` voyage-for-voyage

`off` was re-run rather than re-read so that it could be required to. On all
**600 shared `(cell, seed)` voyages**, `off_s4` and `off_s3` agree exactly on
final ever-infected, the epoch-0 count, posting, and both flush witness fields;
both arms show zero flush events in all voyages, which is the disabled path and
not the sweep evaluated at zero (`scripts/compare_flush_off_arms.py --stage s4
--against s3`). The image, the manifests and the seeding are therefore what this
campaign believes they are, which is the one failure mode that would otherwise
have produced a perfectly plausible-looking contrast.

## 2. The `off` mean at 100 seeds was not a stable baseline

The reproduction is exact and the `off` **means still move sharply** between
`FLUSH-S3` and `FLUSH-S4`, because the second 100 seeds are not like the first:

| cell | `off` mean, seeds 8000–8099 | seeds 8100–8199 | largest voyage, 8000–8099 | largest, 8100–8199 |
|---|---:|---:|---:|---:|
| `fl_exp_7d` | 1.13 | 1.04 | 10 | 4 |
| `fl_exp_12d` | 1.12 | 1.04 | 9 | 4 |
| `fl_cls_7d` | 4.64 | 9.11 | 11 | 475 |
| `fl_cls_12d` | 4.64 | 5.44 | 11 | 109 |
| `fl_spr_7d` | 7.89 | 21.84 | 68 | 372 |
| `fl_spr_12d` | 7.22 | 26.48 | 38 | 621 |

The first 100 seeds contain **no voyage above 68 infections on any cell**; the
second 100 contain voyages of 372, 475 and 621. The baseline outcome
distribution is heavy-tailed, and `FLUSH-S3`'s 100 seeds sampled none of the
tail — so its `off` column understated the mean by up to 3× on the large hulls,
and its intervals were narrower than the process warrants. This is a property of
the voyage distribution, not of the flush route: it is the same engine and the
same arithmetic producing both blocks.

Consequence for reading this campaign: the paired differences below are still
valid (they difference within a seed), but **no cross-stage comparison of a mean
or an interval width is admissible unless it is restricted to shared seeds**, and
the earlier stages' interval widths should be read as optimistic.

## 3. Ever-infected per voyage, paired on the shared seed

Mean over 200 paired seeds; the interval is the 95% normal-approximation
interval on the per-seed paired difference against `off`.

| cell | `off` | `3e-9` Δ | `1e-8` Δ | `3e-8` Δ | `3e-7` Δ |
|---|---:|---:|---:|---:|---:|
| `fl_exp_7d` | 1.08 | +0.01 [−0.02, +0.03] | +0.04 [−0.01, +0.08] | +0.38 [−0.27, +1.03] | +0.83 [−0.12, +1.79] |
| `fl_exp_12d` | 1.08 | +0.02 [−0.01, +0.05] | +0.12 [−0.02, +0.25] | +0.14 [+0.02, +0.26] | +1.31 [+0.37, +2.25] |
| `fl_cls_7d` | 6.88 | −0.45 [−4.44, +3.54] | −0.20 [−2.25, +1.84] | +2.26 [−0.42, +4.94] | +7.42 [+2.70, +12.14] |
| `fl_cls_12d` | 5.04 | +1.85 [−0.13, +3.84] | +2.37 [−0.65, +5.38] | +4.41 [+0.60, +8.22] | +30.60 [+18.27, +42.93] |
| `fl_spr_7d` | 14.87 | +4.54 [+0.79, +8.29] | +4.64 [+0.22, +9.07] | +5.50 [+1.04, +9.96] | +32.33 [+21.35, +43.30] |
| `fl_spr_12d` | 16.85 | +3.31 [−2.10, +8.71] | +9.99 [+1.81, +18.17] | +15.62 [+6.25, +24.99] | +86.03 [+63.39, +108.68] |

Reading the first arm whose interval excludes zero, and closing each bracket
with `FLUSH-S3`'s arms on the shared prefix:

| cell | crossing bracket | closed by |
|---|---|---|
| `fl_spr_7d` | `(1e-9, 3e-9]` | `1e-9` null in S3, `3e-9` resolves here |
| `fl_spr_12d` | `(3e-9, 1e-8]` | both arms here |
| `fl_cls_12d` | `(1e-8, 3e-8]` | both arms here |
| `fl_cls_7d` | `(3e-8, 1e-7]` | `3e-8` null here, `1e-7` resolved in S3 |
| `fl_exp_12d` | `(1e-8, 3e-7]` | not resolved further — see below |
| `fl_exp_7d` | `(3e-7, 1e-5]` | `3e-7` null here, `1e-5` resolved in S3 |

**The crossings span about three decades and are ordered by baseline chain
yield, not by dose per exposure.** Spirit crosses lowest and expedition
highest, although expedition has the *highest* per-exposure dose (smallest
stateroom volumes, §5's `dose/exp` column). That is the third campaign in a row
to order this way: what matters is how many onward chains a hull can support,
not how hard one exposure is.

**`fl_exp_12d`'s nominal first exclusion at `3e-8` is not credible as a
crossing and is not read as one.** Its point estimate there (+0.14) is
indistinguishable from `1e-8`'s (+0.12), which does not exclude zero, and
`FLUSH-S3` measured a *larger* point estimate (+0.81) at the 3× higher `1e-7`
without excluding zero. With 24 interval statements in this table, one marginal
exclusion at the resolution of the quiet cells is what multiplicity produces.
The honest statement for that cell is the bracket above, not a location in it.

## 4. No single `f_aero` in the swept span is consistent across hulls

Within `[3e-9, 3e-7]` there is **no arm that is null on every cell and no arm
that resolves on every cell**: `3e-9` already resolves on spirit 7 d while
`3e-7` is still null on expedition 7 d. So this campaign cannot narrow
`flush_aerosol_fraction` to a window by asking which arm "looks right"
everywhere — the sweep parameter and the hull interact, and the response is
hull-conditional over the whole span. The frozen `[1e-9, 1e-3]` refusal band is
unchanged and no arm is adopted.

## 5. The witness: emission is linear, the response is not

From the readout, `off` reads `flush_dose_delivered / flush_recipients /
flush_events` = `0 / 0 / 0` in all 1,200 `off` voyages. On the active arms,
emitted mass tracks `f_aero` almost exactly — `fl_spr_12d` emits 7.46e8 /
2.80e9 / 1.10e10 / 2.39e11 across `3e-9` → `3e-7`, i.e. ×3.8 / ×3.9 / ×21.7
against nominal ×3.3 / ×3 / ×10 — while **recipients rise with it** (82,750 →
193,950 on the same cell, ×2.3). The emission term is linear in `f_aero`; the
exposure count is not, because every host the route infects flushes. The
exposure counts also show the route firing identically in every arm's *voyage*
count (83–197 emitting voyages of 200 per cell, unchanged across arms), so the
arms differ in dose and not in whether the route executes.

Dominant-route shares repeat `FLUSH-S3`'s finding rather than qualifying it:
`hvac_airborne` is **0.0–0.1% at `off` in every cell** and rises to 13.7–30.9%
at `3e-7`. Drift remains a downstream consequence of an aerosol source, not a
baseline route. And the trap `FLUSH-S3` flagged recurs: at `fl_exp_7d`/`3e-9`
the flush route takes 26.7% of dominant attributions at a paired Δ of +0.01
[−0.02, +0.03]. Attribution share is not effect size.

## 6. Posting and conditional attack rate, reported for contrast only

Voyages per 1,000 exceeding the VSP 3% reportable-case threshold, and the median
reported passenger attack rate among posted voyages:

| cell | `off` | `3e-9` | `1e-8` | `3e-8` | `3e-7` |
|---|---:|---:|---:|---:|---:|
| `fl_exp_7d` | 0 | 0 | 0 | 0 | 5 |
| `fl_exp_12d` | 0 | 0 | 0 | 0 | 5 |
| `fl_cls_7d` | 5 | 5 | 5 | 10 | 15 |
| `fl_cls_12d` | 5 | 15 | 5 | 10 | 65 |
| `fl_spr_7d` | 20 | 20 | 25 | 25 | 50 |
| `fl_spr_12d` | 20 | 25 | 40 | 40 | 140 |

Three observations, none of which selects anything:

1. **The baseline already overshoots A9's 0.33 per 1,000, with the flush route
   disabled.** Classic posts 5 per 1,000 and spirit 20 per 1,000 at `off`. On
   `FLUSH-S3`'s 100 seeds every `off` cell posted zero — §2 says why: the posting
   voyages live in the tail that those seeds missed. So the posting surplus is
   not something the flush sweep introduces, and no `f_aero` can be chosen to fix
   it; it is a property of the baseline engine and belongs to a separate
   measurement.
2. **Expedition is the quietest cell at every arm**, posting 0 per 1,000 until
   `3e-7`. The historical surplus of VSP-scale *expedition* outbreaks is not
   present on this engine at these arms; if the model overshoots posting now, it
   overshoots on the large hulls.
3. **The attack rate conditional on posting barely moves with `f_aero`** —
   median reported passenger AR is 0.036–0.116 across every cell and arm, with no
   trend in the sweep parameter, while posting frequency moves ×2–7. The route
   changes how often a voyage becomes reportable, not how severe a reportable
   voyage is. That separation is worth more than either column alone, and it is
   recorded as a contrast: nothing here is fitted to A1, A4, VSP or MIDRS.

## 7. Caveats

- **Pairing holds on the boarding cohort, not on the whole trajectory.** The
  first timeseries row is written after epoch 0 executes, so it already contains
  same-epoch flush transmission: epoch-0 counts are equal to `off` in
  1,198/1,200 voyages at `3e-9` and 1,184/1,200 at `3e-7`, **strictly upward in
  every differing voyage**, monotone in `f_aero`. That is the route acting in
  epoch 0. It is also why the metric of record is the paired difference in final
  ever-infected, which needs no import subtraction.
- The dose-response roll on flush recipients consumes the shared rng, so the
  paired intervals carry trajectory noise beyond the route itself.
- §2 is the load-bearing caveat for everything measured before this campaign: at
  200 seeds `fl_cls_7d`'s paired Δ still has a ±4 interval at `3e-9`, dominated
  by a handful of tail voyages. Locating a crossing *inside* one of §3's
  brackets would need seeds by the thousand, not another half-decade arm.
