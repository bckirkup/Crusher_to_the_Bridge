# COVID-COOP-03
**Date:** 2026-09-29
**Commit:** a2586422
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** a2586422

The COVID-COOP-V1 conditioned array: the cooperative-packet dose law
(PR #778, read in COVID-COOP-02) scored on the declared arm grid
against the Diamond Princess record — ~197 recorded onsets,
before_share 0.173 — over the takeoff-conditioned lattice
θ ∈ {1e11, 2.37e11, 1e12} × seeds 20200205–14, 16 arms per point
(beta-Poisson baseline + n* ∈ {2,3,5} × carrier_loading corners
{lo-lo, lo-hi, hi-lo, hi-hi} + interior {dry 0.05, wet 20}),
480 cells under `picard_framework/runs/covid_coop_v1_design.json`,
plus the report-only 2400-cell fleet-shape companion
`covid_coop_v1_fleet_design.json`. No constants were fitted; every
declared point is a COVID-COOP-01 envelope corner or the declared
interior.

## Canary (θ 2.37e11 × 16 arms × 10 seeds; AWS Batch
`picard-covid-coop-v1-canary-a2586422`, 160/160 succeeded)

Each cell's resolved `dose_response` (model, n_star, carrier_loading,
alpha/beta, susceptibility_scale) is echoed in the payload — the
echo field shipped in this design (PR #781) and was inspected on a
downloaded cloud cell (n2_hihi: `cooperative_packet`, n* = 2,
{dry 0.1, wet 500}, α 0.18, β 58, scale 7.66e13). The audit
invariant (index_onset_day == -1.0, index_shedding_at_day0) held in
100% of cells. The baseline arm reproduces the v13 stage-2 anchor
seed-for-seed (extinct seeds byte-identical).

Baseline arm at the anchor θ: 7 takeoff seeds, recorded_onsets
q05–q95 [2082, 3542], median 3008, before_share median 0.606 —
the ~9–10× overshoot reproduced as the paired reference.

### Per-seed recorded_onsets, θ 2.37e11

| seed | beta_poisson | n2_lolo | n2_lohi | n2_hilo | n2_hihi | n2_int | n3_lolo | n3_lohi | n3_hilo | n3_hihi | n3_int | n5_lolo | n5_lohi | n5_hilo | n5_hihi | n5_int |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20200205 | 1981 | 2328 | 2294 | 1948 | 1993 | 1948 | 2836 | 2904 | 2354 | 2274 | 2372 | 136 | 2907 | 254 | 2904 | 2789 |
| 20200206 | 3539 | 0 | 3 | 0 | 3 | 3428 | 0 | 3 | 0 | 3 | 3384 | 0 | 3 | 0 | 3 | 3379 |
| 20200207 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 20200208 | 2316 | 2865 | 2846 | 2489 | 2670 | 2506 | 2929 | 2892 | 2817 | 2705 | 2783 | 194 | 2978 | 218 | 2912 | 2836 |
| 20200209 | 2757 | 0 | 759 | 0 | 1840 | 0 | 0 | 691 | 0 | 492 | 0 | 2 | 702 | 2 | 739 | 0 |
| 20200210 | 0 | 3167 | 314 | 3295 | 485 | 3442 | 0 | 311 | 0 | 296 | 3414 | 0 | 302 | 0 | 307 | 3386 |
| 20200211 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 20200212 | 3008 | 1408 | 804 | 1733 | 919 | 1844 | 0 | 1139 | 0 | 647 | 1384 | 0 | 1560 | 0 | 1151 | 1316 |
| 20200213 | 3544 | 2795 | 0 | 3040 | 0 | 2932 | 0 | 0 | 0 | 0 | 2486 | 0 | 0 | 0 | 0 | 2342 |
| 20200214 | 3237 | 122 | 4 | 609 | 4 | 257 | 0 | 4 | 0 | 4 | 243 | 0 | 4 | 0 | 4 | 236 |

### Record-band cells (150 ≤ recorded_onsets ≤ 270) at the anchor θ

| arm | seed | onsets | before | before_share | infections | first_onset_day |
|---|---|---|---|---|---|---|
| n5_hilo | 20200205 | 254 | 151 | 0.594 | 301 | 3 |
| n5_lolo | 20200205 | 136 | 93 | 0.684 | 174 | 4 |
| n5_hilo | 20200208 | 218 | 17 | 0.078 | 513 | 8 |
| n5_lolo | 20200208 | 194 | 14 | 0.072 | 454 | 8 |
| n2_int | 20200214 | 257 | 6 | 0.023 | 978 | 9 |
| n3_int | 20200214 | 243 | 6 | 0.025 | 969 | 9 |
| n5_int | 20200214 | 236 | 6 | 0.025 | 962 | 9 |

## Full-array readout

480/480 cells, zero failed children, sanitary witness consistent in
480/480, audit invariant in 100% of cells. `merge_screen` surface over
the takeoff-conditioned lattice; the declared clause: among takeoff
seeds (recorded_onsets ≥ 10), q05–q95 of recorded_onsets contains 197
AND median before_share within 0.10 of 0.173, scored only when ≥ 5
takeoff seeds.

### Clause map (θ × arm)

takeoff n / [q05, q95] recorded_onsets / median before_share / clause:

| arm | θ 1e11 | θ 2.37e11 | θ 1e12 |
|---|---|---|---|
| beta_poisson | 8 [1764,3521] .778 fail | 7 [2082,3542] .606 fail | 9 [1739,3595] .764 fail |
| n2_lolo | 5 [497,3017] .353 fail | 6 [444,3092] .245 fail | 7 [2088,3462] .716 fail |
| n2_lohi | 7 [505,3043] .298 fail | 5 [403,2736] .667 fail | 6 [2139,3351] .796 fail |
| n2_hilo | 5 [446,3138] .353 fail | 6 [890,3231] .241 fail | 7 [1721,3460] .741 fail |
| n2_hihi | 7 [733,3103] .354 fail | 5 [572,2535] .667 fail | 6 [1861,3388] .821 fail |
| n2_int | 6 [797,3372] .647 fail | 7 [733,3438] .640 fail | 8 [1179,3512] .828 fail |
| n3_lolo | 4 [1584,2848] .552 n/a | 2 [2841,2924] .849 n/a | 7 [280,3078] .400 fail |
| n3_lohi | 7 [500,2975] .232 fail | 5 [387,2902] .667 fail | 6 [2712,3282] .635 fail |
| n3_hilo | 4 [2058,2912] .797 n/a | 2 [2377,2794] .946 n/a | 7 [300,3236] .482 fail |
| n3_hihi | 7 [600,3068] .378 fail | 5 [335,2619] .667 fail | 6 [2194,3338] .757 fail |
| n3_int | 6 [844,3340] .561 fail | 7 [585,3405] .545 fail | 8 [1284,3522] .800 fail |
| n5_lolo | 2 [18,89] .570 n/a | 2 [139,191] .072 n/a | 2 [270,783] .344 n/a |
| n5_lohi | 7 [500,3032] .257 fail | 5 [382,2964] .667 fail | 6 [2783,3310] .658 fail |
| n5_hilo | 2 [18,95] .515 n/a | 2 [220,252] .078 n/a | 2 [403,952] .250 n/a |
| n5_hihi | 7 [506,3061] .281 fail | 5 [393,2910] .667 fail | 6 [2761,3290] .623 fail |
| n5_int | 6 [864,3364] .559 fail | 7 [560,3384] .535 fail | 8 [1339,3519] .800 fail |

No row passes. Two distinct failure classes:

- **Scored rows (takeoff n ≥ 5):** all 33 scored rows fail the count
  leg — q95 never reaches 197; the floor is ~2–15× the record
  (lowest scored median: n3_hihi θ2.37e11 = 647). Seven of them pass
  the before_share leg alone (n2_lolo/hilo .24, n3_lohi .23, n5_lohi
  .26, n5_hilo .25 at various θ) but never jointly with the count.
- **Under-scored rows (n < 5):** the n5_{dry:lo} corners (lolo, hilo)
  at every θ — suppression strong enough to land the band kills 8 of
  10 seeds, so the row is inadmissible by the declared scoring rule
  itself. n3_{lolo,hilo} at θ ≤ 2.37e11 same class.

### Record-band cells (150 ≤ onsets ≤ 270), all θ

θ2.37e11: n5_lolo s20200208 = 194 (bsh .072); n5_hilo s20200205 =
254 (.594), s20200208 = 218 (.078); n2_int s20200214 = 257 (.023);
n3_int = 243 (.025); n5_int = 236 (.025). θ1e12: n5_lolo s20200208 =
241 (.344). θ1e11: none (n5 rows collapse to [18,95] —
oversuppressed).

### n*- and loading-graded suppression (paired Δmedian vs baseline,
takeoff seeds)

At fixed θ, suppression is n*-graded exactly as COVID-PACKET-01
predicted — n2 trims ~100–500 onsets, n3 ~300–1500, n5 ~700–3500 —
and dry-loading-direction dominates wet: at n5 the dry-lo pair
(lolo, hilo) suppresses ~10–50× more than the dry-hi pair
(lohi, hihi). At fixed dry:lo, wet-μ 0.04 out-suppresses 500
(near-empty carriers vs fused ~0.002 weight), while interior wet-20
is the least suppressive declared point everywhere — the
nonmonotone packet_share peak, measured now as designed.

### The opposing legs

The count-band and timing-band are structurally opposed under this
law: settings strong enough to pull a burner to ~200 push first
onset to day 8–9 and leave before_share ≈ 0.02–0.08 (record wants
0.173), while settings weak enough to keep early timing read
before_share .24–.35 but leave the count at 3–15× the record. The
single cell that matches 0.173 within ~2× (n5_lolo s20200208 θ1e12,
bsh .344, onsets 241) overshoots the count leg instead. No declared
point produces the record's joint signature.

`seed_ring` per-seed ring blocks are not emitted by this design's
payloads — absent from the map (instrument not instrumented for arm
designs).

## Fleet-shape companion

2400/2400 cells (`voyage_mode: "generic"`, 50 seeds per row, report-only
`fleet_shape_selector`; the conditioned-design index-geometry invariant
does not apply — generic voyages seed the index mid-progression,
`index_onset_day` ≈ −1.37). The fleet arm echo fires identically
(n2_lolo cloud cell: `cooperative_packet`, n* = 2, {dry 0.004,
wet 0.04}).

P(takeoff) / takeoff-conditional median recorded_onsets /
record-band (150–270) count of takeoffs:

| arm | θ 1e11 | θ 2.37e11 | θ 1e12 |
|---|---|---|---|
| beta_poisson | .64 / 79 / 2 | .66 / 144 / 11 | .76 / 298 / 10 |
| n2_lolo | .32 / 31 / 0 | .38 / 42 / 1 | .58 / 101 / 6 |
| n2_lohi | .16 / 24 / 0 | .26 / 22 / 0 | .38 / 50 / 0 |
| n2_hilo | .34 / 33 / 0 | .40 / 46 / 0 | .56 / 128 / 7 |
| n2_hihi | .16 / 24 / 0 | .34 / 24 / 0 | .38 / 70 / 2 |
| n2_int | .38 / 36 / 0 | .50 / 50 / 4 | .66 / 136 / 7 |
| n3_lolo | .10 / 13 / 0 | .14 / 15 / 0 | .24 / 20 / 0 |
| n3_lohi | .14 / 20 / 0 | .28 / 20 / 0 | .38 / 38 / 0 |
| n3_hilo | .06 / 18 / 0 | .18 / 16 / 0 | .26 / 20 / 0 |
| n3_hihi | .14 / 22 / 0 | .32 / 22 / 0 | .38 / 51 / 0 |
| n3_int | .38 / 43 / 1 | .48 / 55 / 1 | .66 / 114 / 3 |
| n5_lolo | .00 / — / 0 | .00 / — / 0 | .00 / — / 0 |
| n5_lohi | .14 / 20 / 0 | .26 / 22 / 0 | .38 / 35 / 0 |
| n5_hilo | .00 / — / 0 | .00 / — / 0 | .00 / — / 0 |
| n5_hihi | .14 / 20 / 0 | .26 / 20 / 0 | .38 / 35 / 0 |
| n5_int | .38 / 43 / 0 | .48 / 51 / 1 | .66 / 116 / 7 |

The fleet readout is the conditioned readout's falsification leg made
explicit: the baseline law already lands generic DP-shaped voyages in
the record band on a substantial share of takeoffs (26–33% of takeoffs
at θ 2.37e11–1e12 read 150–270 onsets — the fleet shape centered on
the record scale), while the corners that come nearest the band on the
conditioned lattice — n5_{dry:lo} — collapse **every** fleet takeoff
at every θ (0/50). A world whose far-field aerosol carried that law
would show essentially no cruise-scale outbreaks: the same corner that
brackets the record on the conditioned seeds removes the phenomenon
generically. Interior arms stay the least suppressive at every θ —
the packet_share peak again.

## Verdict

**No declared point lands the record.** Scored rows (≥5 takeoff seeds)
never contain 197 in q05–q95 — the suppression floor on a scored row
is ~3× the record (n3_hihi θ2.37e11 median 647). The under-scored
n5_{dry:lo} rows bracket the count at the anchor (medians 165 / 236,
seed 20200208 landing 194/218 under the two corners) but score n = 2
out of 10 — and the cells that do land the band carry before_share
0.02–0.08 against the record's 0.173, because the law's suppression
works by delaying the outbreak past the split day. The count leg and
the timing leg are structurally opposed: every configuration strong
enough to trim the count ~10× erases the early-onset share the record
requires. The fleet companion closes the loop — the same corners
collapse takeoff to 0/50 on generic voyages.

The mechanism is measured working as designed — n*-graded suppression,
nonmonotone wet-loading peak, bolus family untouched — but the
cooperative-packet carrier law cannot produce the record's joint
signature at any declared envelope point: to fix the count it must be
strong enough to destroy the early-onset share (and generic-voyage
takeoff entirely). Per the declared verdict grammar the arm is
**retired as an explanation of the 197/0.173 record** — the
~9–10× gap is not a non-independent-action dose law at the
carrier-packet level. The remaining named options are the
complete-virion bound (now moot: the binding failure is the timing
leg, not loading sourcing) and stage-2 refinement (ruled out by the
opposed legs — refinement can approach the count at n5_{lolo,hilo}
θ2.37e11 but cannot move before_share up at the same point).

**Next decision: mechanism retired.** The standing suspects per
ROUTE-ATTR-V1/LAMBDA-CROSS-V1 remain fixed ring structure, index
day-0 exposure geometry, and the observational channel — the gap
survives a dose-law change of a different kind than sampled rings or
carrier packets.
