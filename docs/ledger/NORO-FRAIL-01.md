# NORO-FRAIL-01
**Date:** 2026-09-28
**Commit:** 27efdbd4
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 27efdbd4

Honest check on the surviving NORO-GROWTH-01 / NORO-GROWTH-01-RERANK
block, **L4 — the winner's frailty draw**. Named example: on s8159 a
dining-hall patch put hand-to-mouth dose 1.28e3 GEC on one host whose
susceptibility frailty drew 1.3e-10 → hazard 5e-8 and no tertiary. The
question: is L4 a true property of the sourced susceptibility
distribution, or a unit/scale artifact — a draw applied in the wrong
decade, or a mean-vs-draw confusion.

Checks: (a) does the per-host draw match the distribution the pathogen
profile declares; (b) is the declared range source-backed at its
recorded evidence grade; (c) does observed conversion equal the
naive-rate expectation under the declared distribution.

## (a) Drawn = declared — measured

The profile declares `dose_response: {model: beta_poisson, alpha:
0.111, beta: 32.81}` with no `susceptibility_scale` (→ 1.0)
(`data/pathogens/active_profiles.json`). The live path is
`_dose_response_susceptibility` (`engines/transmission_core.py`):
one lazy draw per host per pathogen, `rng.beta(alpha, beta) * scale`,
cached on `agent.dose_response_susceptibility`; hazard is
`-expm1(-s · D_eff)` and conversion is one `rng.random()` per challenge.
`test_default_beta_poisson_draws_are_bit_identical` locks the draw to
`np.random.default_rng(seed).beta(0.111, 32.81)`. There is no mean or
expected-value path in the live loop — the closed-form `_dose_response`
helper is exercised by tests only (already an open implementation item,
norovirus open ledger).

Re-ran `tools/noro_diag/growth_chain_census.py` on the seven L4-flagged
`fl_spr_12d` seeds (8114, 8124, 8132, 8148, 8156, 8158, 8159) — verbatim
dose_refit_01 spec plus `rhythm.enabled: false` to reproduce the
pre-rhythm baseline. Per-seed acquisition counts reproduce the baseline
exactly (2+1+1+1+1+3+1 = 9 on 16,714 challenged hosts). Drawn frailties
vs Beta(0.111, 32.81):

| quantile | drawn | declared | ratio |
|---|---|---|---|
| q0.10 | 1.3–1.6e-11 | 1.85e-11 | 0.68–0.86 |
| q0.25 | 6.5–7.6e-8 | 7.13e-8 | 0.91–1.07 |
| q0.50 | 3.3–3.8e-5 | 3.68e-5 | 0.90–1.04 |
| q0.75 | 1.51e-3 | 1.48e-3 | 1.02 |
| q0.99 | 5.1–5.9e-2 | 5.04e-2 | 1.02–1.17 |

KS on the pooled drawn set: stat 0.007, p = 0.74 (runs A) / 0.91
(runs B). No host re-drew; the deep tail populates as declared
(min draw 2.4e-37 ≈ q0.0001). **No defect.**

## (b) Declared range traces to source at recorded grade — verified

Register §3.1 (`docs/parameter_provenance_register.md`, row
`dose_response.alpha / beta`, class **I → M (form and value)**, Lev L0,
"declared and swept"): the shipped pair is the disaggregated GI.1
challenge arm of Teunis 2008, traced via the Edison bundle at origin
**Sec** — Teunis 2008 itself is **?nr** (paywalled; two chunk queries
returned the abstract only), so the pair's provenance grade is the
bundle's, not the paper's. Recorded intervals and their sources:

- **α ∈ [0.072, 0.161]** at fixed β = 32.81 — Rouphael 2022 GII.2
  challenge ID50 5.1e5 → 0.072; Guix 2020 GII outbreak illness ID50
  2,934 → 0.154 (a lower bound on infection α); Ramesh 2020
  gnotobiotic-pig GII.4 → 0.149–0.161, Grade C corroboration
  (tranche 6 §2). 0.111 sits inside, within 3% of the geometric centre.
- **Dose-axis ID50 ∈ [1.32e3, 1.69e4] gEq** — Atmar 2014 logistic O/A
  HID50 1,320 gEq (R + Me + T2) to row-(a)'s closed-form N50 16,871;
  exact confluent-hypergeometric N50 16,644 reproduces in-session.
  Recorded "declared, not applied" — a distance between two studies.
- Dose unit closed as **administered genome copies** (tranche 23);
  the ≈925 copies-per-aggregate bridge is withdrawn and the pooled
  µ_c = 517 aggregation fit retracted, each with arithmetic shown.

Honest caveat carried forward from the register, not a new finding: the
shipped pair is a **GI.1** arm while the profile's genotypes are
GII.4/GII.17/GII.2 — the α interval exists precisely as the GII
bracketing evidence, and no retarget is adopted on genogroup grounds.
If a GII-fitted pair (α nearer 0.15) were ever licensed, the left tail
thins and L4 softens — that is a provenance choice, not an artifact.

## (c) Conversion = naive rate under the declared law — measured

Per-host over the same 7-seed re-run (dose summed through first
acquisition epoch, truncated thereafter):

| seed | challenged | observed acq | E[drawn s] | E[declared marginal] |
|---|---|---|---|---|
| 8114 | 2393 | 2 | 2.01 | 2.53 |
| 8124 | 2374 | 1 | 0.49 | 0.44 |
| 8132 | 2390 | 1 | 1.00 | 0.50 |
| 8148 | 2386 | 1 | 1.00 | 0.42 |
| 8156 | 2391 | 1 | 1.02 | 0.87 |
| 8158 | 2391 | 3 | 3.03 | 1.95 |
| 8159 | 2389 | 1 | 1.10 | 1.52 |
| **all** | **16714** | **9** | **9.65** | **8.23** |

`E[drawn s]` = Σ over hosts of `1 - exp(-s_i · ΣD_i)`; `E[declared
marginal]` = Σ `1 - ₁F₁(0.111; 32.921; -ΣD_i)`. Observed (9) sits
between the two — consistent with NORO-GROWTH-01's pooled 17.7 vs 18
and the RERANK's 4.22 vs 3 on the rhythm cell. Selection works as
declared, not uniformly: acquired hosts' frailties sit at median
quantile 0.74–0.84 of the law (s8159's converter: s = 4.5e-3, q0.84,
converted at D_eff 222 with hazard 0.64) — high-frailty hosts take the
doses that arrive.

The named example reproduced draw-for-draw in the re-run: s8159 epoch
187, agent 1965, s = 1.319e-10 → hazard 5.07e-8. Two notes on it: the
draw is the **12.4th percentile** of the declared law — ordinary, not a
tail accident (P(s ≤ 1.3e-10) = 0.124); and the 5e-8 hazard implies an
effective dose of ~384 GEC against the 1.28e3 hand-to-mouth figure — a
route-efficiency factor on the dose axis, outside this check's scope
and outside the frailty question.

Under the declared law ~26% of hosts draw s < 1e-7 (hazard < 1e-4 even
at D = 1e3), and ~12–16% are effectively unchallengeable at any
achievable dose (hazard < 1e-4 at D = 1e5–1e6); the marginal
P(infection|D) is nearly dose-flat — 0.34 at D = 1,280, 0.50 at the
N50 16,644, 0.59 at 1e5 — which is why L4 reads as a lottery rather
than a threshold.

## Verdict

**L4 is a real property of the declared — and sourced — Beta(0.111,
32.81) frailty draw.** The drawn distribution matches the declared one
(KS p ≥ 0.74, n = 16,714); the declared range traces to human-challenge
sources at the recorded grades (pair Sec via the Edison bundle, Teunis
?nr; α interval on Rouphael/Guix/Ramesh; dose span on Atmar vs row-(a)
N50); and conversion runs at the naive rate the law predicts (9.65
expected vs 9 observed on the re-run cells, 17.7 vs 18 on the baseline
census). The mechanism kills most big-dose challenges because α = 0.111
puts a quarter of hosts below 1e-7 susceptibility — that tail mass is
what Teunis's disaggregated GI.1 fit ships, not a misplaced decade or a
mean substituted for a draw. No constants moved; nothing here licenses
a retune — the GI.1-pair-on-GII-profile question is the register's
recorded caveat, open as a provenance item, not an L4 defect.

## Instruments

`tools/noro_diag/growth_chain_census.py` on the dose_refit_01 manifest,
tier `fl_spr_12d`, `rhythm.enabled: false` overlay; fold script +
manifest under `telemetry_buffer/noro_frailty_check/` (scratch; this
table is the durable record). Declared-law arithmetic recomputed
in-session with scipy `beta`/`hyp1f1` (N50 = 16,643.78, matching the
register's 16,644).
