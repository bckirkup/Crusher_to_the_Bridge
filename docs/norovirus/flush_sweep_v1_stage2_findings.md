# Stage 2 of the flush sweep: the crossing is hull-dependent and sits below the stage-1 bracket on the large hulls

Status: measured; **superseded as a measurement of the current engine** —
it ran before the per-pathogen pool transport repair (ledger item 47, under
which the norovirus drift route was dead in every arm) and before the
cabin-venue drain repair (item 48). It stands as the pre-repair reference the
re-run is read against on paired seeds. Companion to the generated tables in
[`flush_sweep_v1_stage2_readout.md`](flush_sweep_v1_stage2_readout.md)
(`telemetry_buffer/observation_model/flush_sweep_v1_s2.json`); design and
declared uncertainty in
[`flush_aerosolisation_v1.md`](flush_aerosolisation_v1.md); stage 1 in
[`flush_sweep_v1_stage1_findings.md`](flush_sweep_v1_stage1_findings.md).
Every dose figure in this repository remains void pending refit
([ledger](norovirus_open_ledger.md)).

Stage 2 ran five arms — `off` (the item-42 `dwell_weighted` configuration,
shared heads executing with the flush route off), `3e-9`, `1e-8`, `3e-8`
and `1e-7` — at 200 paired seeds (8000–8199) on the same six hull/length
cells, 6,000 runs, 0 failed, all under the AERO-CABIN-02 berth-share cabin
dilution (ledger item 45). `off` and `1e-7` are fresh baselines, not the
stage-1 archives, so nothing here is compared across engines. Image
`flush-sweep-v1-s2-6cfe1fd`, job definition `picard-campaign:44`.

## 1. Invariants

- `off` emitted zero flush mass in all 1,200 baseline voyages.
- Imports were identical in 1.000 of pairs in all 24 contrasts.
- Emitted mass per flush event is exactly linear in `f_aero`: on paired
  seeds where neither arm established a secondary and the route emitted,
  659 of 698 `3e-9`→`1e-8` pairs have a mass ratio of 3.333… to floating
  precision, and the median ratio of every adjacent-arm pair is the
  declared step (3.33 / 3.00 / 3.33).
- The pairing is on the boarding cohort, not on the whole trajectory. In
  the remaining 39 no-secondary pairs the mass ratio runs 0.4–31×, and 23
  of the 966 no-secondary pairs differ in the number of flush events. Both arms load the same cohort
  and the route draws no rng of its own, so the divergence is downstream:
  once a flush exposure exists, the dose-response roll on its recipients
  consumes the shared stream and every later draw (stool timing,
  shedding trajectory, contacts) moves. This is the expected behaviour of
  a shared stream, not a leak in the flush code, but it means the paired
  Δ intervals below carry trajectory noise beyond the route's own effect.
  Means are unbiased; pair-level exactness is not available past the
  first exposure.

## 2. Emitted mass rises faster than `f_aero`, and the excess is the feedback

Pooled emitted mass per voyage (classic 7 d): 4.0e5 → 1.0e6 → 9.2e6 →
1.8e7 across `3e-9` → `1e-7`, a ×44 rise over a ×33 span; spirit 7 d
×73; expedition 7 d ×108. The per-event term is exactly linear (§1), so
the surplus is the count and titre of the flushers. A boarded import
under the stationary age draw is mostly convalescent, shedding at the tail
of its curve; a secondary established mid-voyage passes through peak
shedding aboard and, on the pairs where one appears, raises the voyage's
emitted mass by up to 2.3e4–8.8e4× (the maxima of the paired ratios). One
acute case flushes more virus into the ship's heads than the whole
boarding cohort. This is the same mechanism that falsified the stage-1
saturation argument: the route multiplies exposures, and each new
infection is a new source.

## 3. Where the route first becomes resolvable, by cell

Paired Δ secondaries per voyage against `off` (95% CI), the arm at which
it first excludes zero in bold:

| cell | `off` sec/import | 3e-9 | 1e-8 | 3e-8 | 1e-7 |
|---|---|---|---|---|---|
| classic 7 d | 0.010 | **+0.07 [0.03, 0.12]** | +0.25 [0.12, 0.41] | +1.09 [0.35, 1.92] | +2.29 [0.90, 4.24] |
| classic 12 d | 0.009 | **+0.08 [0.04, 0.12]** | +0.40 [0.13, 0.86] | +1.21 [0.47, 2.57] | +3.83 [2.03, 6.09] |
| spirit 7 d | 0.161 | +1.55 [−0.01, 3.64] | **+1.28 [0.29, 2.32]** | +3.26 [1.71, 4.96] | +7.00 [4.72, 9.21] |
| spirit 12 d | 0.209 | +1.68 [−1.14, 4.42] | +3.21 [−0.38, 7.52] | **+5.40 [1.91, 9.72]** | +12.98 [7.41, 19.12] |
| expedition 7 d | 0.093 | +0.03 [−0.01, 0.07] | **+0.23 [0.03, 0.69]** | +0.11 [0.04, 0.20] | +0.32 [0.11, 0.62] |
| expedition 12 d | 0.137 | −0.02 [−0.07, 0.03] | +0.05 [−0.04, 0.14] | **+0.18 [0.03, 0.43]** | +0.55 [0.05, 1.19] |

Three readings, none of them a value:

- **The crossing is not one number.** On classic it is already resolved
  at `3e-9`, so it lies in (1e-9, 3e-9] — the bottom of Johnson's own
  measured droplet-nuclei range — and stage 1's "(1e-9, 1e-7)" bracket
  was wide because 100 seeds could not see a +0.07. On spirit it is
  (3e-9, 1e-8] at 7 d and (1e-8, 3e-8] at 12 d; on expedition (3e-9,
  1e-8] and (1e-8, 3e-8]. Every cell resolves by `3e-8`.
- **The multiplier is hull-ordered by the baseline, not by the dose.**
  At `1e-7` secondaries per import rise ×52–97 on classic, ×7.6–10.4 on
  spirit, ×4.4–4.9 on expedition. Expedition has the highest dose per
  exposure at every fraction (3.4e3–5.5e3 particles at `1e-7` against
  3.8e2 on classic — fewer, smaller heads) and the smallest multiplier,
  because with ~1 import per voyage and 6–12 exposure events there are
  few chains to multiply. Classic has the lowest baseline yield in the
  fleet (0.010) and the largest relative gain. The route amplifies what
  reaches it; it does not set the level alone.
- **Length matters where there is something to compound.** Δ secondaries
  is larger at 12 d than at 7 d on classic and spirit at every fraction
  (×1.1–1.9), and flat or noisy on expedition, where the chains are too
  short to compound.

## 4. What it does to the outcome the sweep exists for

Zero-secondary voyages fall from 97% (`off`) to 72% (`1e-7`) on classic
and from 90% to 41% on spirit; flush becomes the dominant attributed
route in 43–70% of establishments where it is on, taking share from
fomite. Posting remains a tail: 0/1,000 in 7-day cells at every arm
(upper CI 12.5), 5/1,000 at `1e-7` on classic 12 d and 10 on expedition
12 d, and on spirit 12 d 5 → 15 → 20 per 1,000 across `off`/`1e-8` →
`3e-8` → `1e-7`. No McNemar discordance is significant (best 4/1,
p = 0.375). Median reported passenger attack rate over postings is
0.017–0.058 on 1–4 postings per cell — too few to read a distribution.

Reported beside the measurement, used to select nothing: A9's 6–7 day
band is 0.33 per 1,000 and its 11–14 day band 18.3; A4's median
passenger AR over postings is 0.052–0.055 on these hulls. Stage 2's
7-day posting is consistent with the first at every arm; its 12-day
spirit posting at `3e-8`–`1e-7` sits in the neighbourhood of the second.
That is a statement about where the observed series falls inside the
frozen span, not about which fraction is true: the sourced interval
[1e-9, 1e-3] is not narrowed by this measurement, because the reason it is
wide — no virus measurement exists for a vacuum marine blackwater system,
and Johnson and Boles measure different aerosol fractions — is untouched
by anything a cruise outcome can say.

## 5. What is not measured here

- **The cabin-venue drift path.** Flush and emesis mass emitted in a
  stateroom is keyed by compartment, and the epoch-boundary drain
  (`orchestrator_epoch`) only credits keys present in the zone-mass map,
  so cabin-venue event mass never enters the HVAC reservoir; only
  sanitary-venue mass does, and sanitary HVAC is exhaust-only. The
  in-room dose measured here is unaffected. Ledger item 46.
- **`cabin_air_mode`.** All arms ran the default `zone_pool`. The switch
  gates the continuous short-range inhalation route, which is a null on
  this arm by construction (zero continuous emission share, item 44b);
  `_dose_flush_cabin` partitions into staterooms and dilutes into the
  berth share regardless of the switch. Setting `cabin_compartment` would
  not move a stage-2 dose.
- **Emesis** still dilutes into the 100 m³ fallback (item 45), on and
  identical in every arm, so it cancels in the paired contrast.

## 6. Stage 3 is not declared

Stage 2 answers the staged question — at which half-decade, in which
cells, the paired contrast first excludes zero — and the answer is a
band, (1e-9, 3e-8], ordered by hull and length. A further half-decade
below `3e-9` on classic would locate its crossing more finely and say
nothing new about the ships; a stage that picked an arm on posting would
be a fit. The next measurement that would move the model is not another
arm of this sweep but the mechanisms this one exposes as missing:
cabin-venue drift (item 46), the emesis dilution (item 45), and the
food-contamination zero.
