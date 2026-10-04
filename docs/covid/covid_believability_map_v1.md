# DP-BELIEF-01 — the Diamond Princess believability map: the shipped-default replay is believable on no measured row

> **Status:** Findings (2026-10-04). No cells ran: every figure is scored
> from the synced cell payloads of record — refit lattice
> `campaign/covid_theta_refit_v1/78f52a58/cells/` (180 cells, 9 rows × 20
> seeds), floor `8f49652f` (20), bracket `8f926382` (100), CG-FLOOR corner
> probe `3eae8a2f` (80), CAREGIVER-ATTR-01 `b932d0e9` (40) — all on the
> verbatim `diamond_princess_2020` replay contract (index onset day −1,
> departure day 5, imports 1, seeds 20200205–20200224, SOP-017 days 16–30,
> ascertainment day 14). Takeoff-conditional medians (≥10 recorded onsets)
> unless stated.

This doc is a divergence table, not a mechanism hunt: which checkable
features of the DP record the shipped-default replay satisfies and which
it fails, at every measured Θ. THETA-REFIT-01 already settled that the
clause's two legs are unreachable together (θ_c ∈ (1e6,1.4e6) <
θ_t ∈ (5.62e6,7.9e6)); this map asks the wider question — is *any*
feature set satisfied anywhere — and localises each failure to a
channel. Record values are quoted with their in-tree anchor or their
named publication; "record-informed" marks a quantity the record implies
rather than publishes as a count.

## 1. The measured surface

Takeoff-conditional medians [q05, q95] where spread matters; `lab` =
lab-confirmed total, `date%` = share of confirmed with a dated onset,
`cpos` = campaign positives (of 3,063 replica specimens), `asym` =
asymptomatic share at specimen, `inf` = `infections_total`,
`pre` = share of infections acquired before quarantine day 16,
`pk` = dated-onset peak day index, `qC/qP` = dated onsets days 16–30 by
role, `tk` = takeoff seeds.

| row @SHA | tk | recorded | before_share | lab | date% | cpos | asym | inf | pre | pk | qCrew | qPax |
|----------|---:|----------|--------------|----:|------:|-----:|-----:|----:|----:|---:|------:|-----:|
| record | — | **197** | **0.173** | **634** | **0.28** | **634** | **0.505** | **840** | **~0.6–0.75** | **18** | **48** | **115** |
| Θ1e6 `8f49652f` | 19/20 | 331 [149,760] | 0.051 | 365 | 0.87 | 213 | 0.33 | 771 | 0.08 | 27 | 302 | 6 |
| Θ1.4e6 `8f926382` | 19/20 | 420 [366,840] | 0.064 | 491 | 0.87 | 280 | 0.35 | 825 | 0.12 | 26 | 383 | 19 |
| Θ2e6 `8f926382` | 19/20 | 460 [285,930] | 0.066 | 531 | 0.86 | 316 | 0.36 | 855 | 0.12 | 25 | 427 | 11 |
| Θ3.16e6 `8f926382` | 19/20 | 511 [399,854] | 0.059 | 604 | 0.85 | 357 | 0.37 | 891 | 0.15 | 24 | 463 | 26 |
| Θ5.62e6 `8f926382` | 19/20 | 589 [492,785] | 0.069 | 723 | 0.83 | 388 | 0.42 | 909 | 0.18 | 22 | 520 | 25 |
| Θ7.9e6 `8f926382` | 19/20 | 634 [496,1540] | **0.075 pass** | 789 | 0.83 | 422 | 0.45 | 938 | 0.25 | 23 | 536 | 31 |
| Θ1e7 `78f52a58` | 19/20 | 704 [523,2037] | 0.097 | 845 | 0.83 | 434 | 0.47 | 1,048 | 0.27 | 21 | 566 | 79 |
| Θ1.78e7 `78f52a58` | 19/20 | 793 [631,1619] | 0.135 | 987 | 0.81 | 448 | 0.56 | 1,138 | 0.47 | 20 | 585 | 148 |
| Θ3.16e7 `78f52a58` | 19/20 | 931 [674,2181] | 0.146 | 1,166 | 0.81 | 460 | 0.59 | 1,303 | 0.52 | 20 | 581 | 210 |
| Θ5.62e7 `78f52a58` | 19/20 | 867 [661,2275] | 0.141 | 1,074 | 0.81 | 458 | 0.56 | 1,218 | 0.48 | 20 | 590 | 164 |
| Θ1e8 `78f52a58` | 19/20 | 1,842 [886,2242] | 0.219 | 2,258 | 0.80 | 685 | 0.71 | 2,564 | 0.75 | 18 | 518 | 972 |
| Θ1.78e8 `78f52a58` | 19/20 | 1,495 [830,2241] | 0.255 | 1,880 | 0.80 | 645 | 0.68 | 2,177 | 0.75 | 18 | 537 | 652 |
| Θ3.16e8 `78f52a58` | 19/20 | 1,688 [1121,2424] | 0.287 | 2,080 | 0.79 | 703 | 0.72 | 2,338 | 0.75 | 18 | 480 | 825 |
| Θ5.62e8 `78f52a58` | 19/20 | 2,137 [1638,2410] | 0.279 | 2,660 | 0.79 | 762 | 0.75 | 2,988 | 0.83 | 18 | 449 | 1,122 |
| Θ1e9 `78f52a58` | 19/20 | 2,321 [1518,2445] | 0.452 | 2,858 | 0.79 | 774 | 0.81 | 3,249 | 0.90 | 17 | 300 | 1,044 |
| CG_OFF Θ1e9 `b932d0e9` | 11/20 | 1,559 [10,2428] | 0.200 **clause PASS** | 1,912 | 0.82 | 734 | 0.53 | 2,342 | 0.58 | 20 | 504 | 783 |

(The `3eae8a2f` corner rows reproduce the 1e6/7.9e6 D0 rows bit-identically
and the CG_LOW arm moves no figure here — DELIVERY-STRUCTURAL, ledger
CG-FLOOR-01 — so they are not repeated.)

## 2. The divergence table

Record feature → measured value on the shipped-default tree → record
value → gap → candidate structural cause → the one discriminating
measurement. "needs cells" marks a feature the synced payloads cannot
express; the leg design is in §4.

| # | record feature | record value | shipped-default measured | gap | candidate structural cause | discriminating measurement |
|--:|----------------|--------------|--------------------------|-----|----------------------------|----------------------------|
| F1 | dated-onset count | 197 [197,199] (covid.T1) | band ∋197 only at Θ1e6 ([149,760], med 331); medians rise 420→2,321 across rows ≥1.4e6 with q05 285–1,638 (all above 197) | 1.7–12× median overshoot at 14/15 rows | composite of F3 (dating ~3×) and F9 (mass lands late); the count leg's single pass at 1e6 is band width, not structure | the period-channel arm: `onset_recording` gate (symptomatic-at-specimen + recall draw) — already designed as SERO-CHANNEL-V1, unrun |
| F2 | before-split share | 0.173 ±0.10 (34/197 before day 17 = 6 Feb) | 0.051 @1e6 … 0.075 @7.9e6 (first pass) … 0.452 @1e9 | below-side ≤5.62e6, over-side ≥3.16e8; disjoint from F1 (θ_c < θ_t, certified) | outbreak lands ~1–2 weeks after the record's — see F9 | none new — certified WINDOW-EMPTY-ORDERED (THETA-REFIT-01) |
| F3 | share of confirmed cases with a dated onset | 197/712 = 0.277 (NIID curve / final count) | recorded/lab = 0.87 @1e6, 0.83 @7.9e6–1e7, 0.79–0.80 @≥1e8; CG_OFF 0.82 | **~3× over, flat at every θ and every arm** — θ-independent, mechanism-independent | the onset channel dates every confirmed symptomatic at its true onset day: no symptomatic-at-specimen gate, no recall/reporting loss — this is the ROUTE-ATTR-V1 dating hypothesis, now measured on the whole surface | SERO-CHANNEL-V1's period channel (designed, unrun): rescore whether the gate lands dating near 0.28 — if undershoots, the recall draw alone without the specimen gate is the alternative, declared before the array |
| F4 | confirmed-case total by day 31 | 619–634 (NIID briefing; Mizumoto T3 incl. officers) | lab med 365 @1e6, 491 @1.4e6, 604 @3.16e6, 789 @7.9e6, 845 @1e7, 1,166 @3.16e7, 2,858 @1e9 | 0.6–0.95× under ≤3.16e6; 1.1–4.5× over ≥5.62e6 | at low θ infections clear or land after the campaign ends (peak day 24–27 > day-31 horizon); at high θ truth mass explodes | none — derivative of F5 + ascertainment timing; reads confirmed = f(mass, phase) |
| F5 | ever-infected total (serology-informed) | ≈840, band [712,960] (covid.H5, Hung subgroup extrapolation) | 771 @1e6 **in band**; 938 @7.9e6 **in band**; 1,048 @1e7 (just above); 2,342 CG_OFF; 3,249 @1e9 | **satisfied at both clause-leg crossings** — the replay is NOT over-infected at the θs the clause asks | none needed: this is the map's key negative — believability fails with the right total mass, so "too much virus" is falsified as the sole residual | scored on existing payloads; holds the field open for F9/F3 as the true residuals |
| F6 | campaign positives | 634 of 3,063 (covid.T3; specimen count reproduced by construction on all cells) | med 213 @1e6, 422 @7.9e6, 434 @1e7, 448–460 @~2–6e7, 774 @1e9 | 0.67–0.72× under at 7.9e6–5.62e7; crosses the record between 5.62e7 and 1e8 | same mass/phase composite as F4; its closest region (7.9e6–5.6e7) is again disjoint from both clause legs | rescore after a dating/timing fix — not informative while F9 stands |
| F7 | asymptomatic share at specimen | 320/634 = 0.505 (covid.T4) | 0.33 @1e6, 0.45 @7.9e6, 0.47 @1e7, 0.56–0.59 @1.8–3.2e7, 0.71–0.81 @≥1e8 | under below ~1e7 (late outbreak → positives caught pre-symptom less often), over above | crossing θ ~(1–2)e7 — again neither leg region; driven by where infection sits relative to the test days, not by `symptomatic_fraction` | none new — re-read once F9 resolved; flagged: if a post-fix surface still reads ~0.33 at low θ, symptomatic_fraction 0.31-vs-17.9% (Emery delay-adjusted) is the follow-up sourcing question |
| F8 | infection timing — share acquired before day 16 | most infections pre-quarantine; incidence declining by ~3–4 Feb (Emery 2020 back-calc; Mizumoto & Chowell 2020) — record-informed | `infections_before_quarantine`/total = 0.08 @1e6, 0.12–0.25 @1.4–7.9e6, 0.27 @1e7, 0.47–0.52 @~2–6e7, 0.75 @1e8, 0.90 @1e9 | **inverted at every clause-relevant θ**: 8–25% pre vs record's majority; believable share only at ≥1e8 where totals are ~3× over | two-sided: open-phase (days 0–15) under-delivery (pre-quarantine mass 60–235 vs the ~500–700 the record's ~840 total at majority-share implies) AND quarantine-phase over-delivery (during 678–757 vs a record-informed few hundred) | per-day acquisition histogram vs the published back-calculated infection-date curve — expressible on existing payloads (`acquisition_curve.total_by_day`, event-count caveat §4-A); pair with D4 |
| F9 | dated-onset peak day | ~7 Feb = day 18 (NIID briefing, report-lag adjusted) | med day 27 @1e6, 23 @7.9e6, 21 @1e7, 20 @1.8e7, 18 @≥1e8, 17 @1e9 | 3–9 days late at ≤1e7 | same timing inversion as F8 — onset curve is the acquisition curve shifted by incubation | same as F8 |
| F10 | quarantine-response direction (T2) | passenger onsets decrease after day 16; crew persist (window 7d) | takeoff seeds: passenger mean onsets/day rise days 9–15→16–22 on 18–19/19 seeds at ≤5.62e7 and 13/19 @1e9; crew rise ≤5.62e7 and fall on 13/19 @1e9 | passenger direction wrong at every row; crew direction right only where it shouldn't matter | outbreak still building through the window (F8); crew channel keeps delivering during confinement | already a scored diagnostic; the role-level witness F12 quantifies it |
| F11 | during-quarantine dated role split | 48 crew / 115 passenger = 29% crew (NIID Table 2) | days 16–30 dated: 302/6 @1e6, 536/31 @7.9e6, 566/79 @1e7, 300/1,044 @1e9 — crew share 0.95→0.22 | crew 6–11× over; passengers 4–19× **under** at clause θ — share inverted | during-quarantine passenger dated mass is incubated pre-quarantine infections — absent because F8's early mass is missing; crew mass rides the working-through-quarantine channel (acquisition zone tallies: crew_mess 0.54–0.58 of during-quarantine acquisitions at clause θ) | needs cells: D4 — confinement-strength arm at Θ7.9e6 (crew work suspension / full enforcement), reading whether during-quarantine mass collapses to the ~150–350 band while pre-quarantine mass is unmoved |
| F12 | quarantine tail — dated onsets after quarantine day 7 (~12 Feb, day ≥23) | 3–7 in the 52–92 passenger subset analysed (NIID Table 2); the dated curve effectively ends by ~mid-Feb | dated onsets days ≥24: med 254 @1e6, 285 @7.9e6, 290 @1e7, 130 @1e9 | tens of dated onsets after the record's curve has stopped | the late outbreak (F8) is still presenting after the quarantine calendar has ended; dating channel keeps it all | same as F8 |
| F13 | confined-passenger acquisitions during quarantine | bounded below by ~52–92 dated passenger onsets in cabins without a prior confirmed case (NIID Table 2) — true count higher, record-informed | `confined_passenger_infections_during_quarantine` med 4 @1e6, 19 @7.9e6, 50 @1e7, ~100 @3.2–5.6e7, ~300 @≥1e8 | under at clause θ (4–19 vs ≥52 bound); believable only ~3e7–5e7 | confined-cabin acquisition channel under-delivers at clause θ — cabin-mate chains and the confined co-presence channels | needs cells: D2 — per-cabin case-pair witness (below) |
| F14 | cabin/party clustering | cases increase with cabin occupancy; of 115 during-quarantine passenger onsets, ~20–55% in cabins with a previously confirmed case; cabin-mate attack-rate gradient 18% → 63% (asymptomatic index) → 81% (symptomatic) (CID 72(10):e448; Australian cohort RR 3.78 pre-/6.18 during-quarantine) | only expressible proxy: during-quarantine acquisition zone shares — cabin 0.05–0.08 @≤7.9e6, crew_mess 0.54–0.58, corridor 0.04, other ~0.3; cabin 0.62–0.79 @≥1e8 | literal feature unmeasurable: payloads carry acquisition zone tallies, not per-cabin case pairs or cabinmate-conditioned attack rates | unknown — cannot localise between cabin channel strength and infection phase without the pair-level tally | **needs cells**: D2 — emit `dated_onsets_by_cabin_prior_case` {with_prior, without_prior} + cabinmate-conditioned passenger attack rate; 40 cells {1e6, 7.9e6} × 20 seeds on the current image |
| F15 | aboard-window delivery (index aboard days 0–5) | bound: the record's *entire* dated mass before 6 Feb is 34 onsets | `seed_ring.aboard_window_acquisitions` mean ~10/seed @1e6 → ~64 @1e9; caregiver component med 5→11 per takeoff seed (pooled 105–248) | caregiver-attributed acquisitions alone ≈ 5–13/takeoff seed inside days 0–4 against the 34-onset bound — DELIVERY-STRUCTURAL (CG-FLOOR-01): designation/discovery shape, not dose factors | the designation's existence: `tending_response_probability`, `tending_report_probability`, attendant-discovery stamp | needs cells: D1 — route-tagged dated onsets (emit acquisition route on the onset observation); named witness in CG-FLOOR §5, still unrun |
| F16 | takeoff frequency | silent on probability — one voyage, it took off; cross-ship context: median 3 cases over 104 voyages (covid.H3) | 19/20 at **every** measured row from 1e6 to 1e9; CG_OFF 11/20 | near-certain burn at any θ — the ≥10-onset conditioning binds almost nothing on the shipped tree | the shipped-default stack (caregiver ON + propensity party) ignites every seed; clause conditioning was written against the 50%-fizzle off-tree | none — a model property, not a record match; noted so the takeoff-conditional medians are read as 'what the burn looks like', not 'what the voyage was like' |
| F17 | first dated onset | dated curve begins ~28 Jan–1 Feb (NIID curve; 3 earlier onsets excluded) | `first_onset_day` med 5–8 (25–28 Jan) | consistent | — | — |
| F18 | confirm rate (confirmed / ever-infected) | 712/~840 ≈ 0.75–0.85 | lab/inf med: 0.47 @1e6, 0.62 @2e6, 0.80 @5.62e6, 0.84 @7.9e6, ~0.86–0.89 @≥1e8 | under the record's ~0.75–0.85 below ~5e6 — early infections clear or land after the specimen days | phase problem (F8), not assay — PCR catches fewer when infection postdates specimens | none — derivative |

## 3. What the map says — three orthogonal divergences, none θ-shaped

1. **Mass is reachable — falsifying "too much virus" as the residual.**
   `infections_total` lands inside the serology band [712,960] at both
   clause-leg crossings (771 @1e6; 938 @7.9e6). At the θ where the timing
   leg passes, truth mass is right *and* confirmed mass is within ~20%
   (789 vs 619–634): everything wrong there is between infection and the
   dated count.

2. **Timing is inverted — "too cold early, too hot during-quarantine."**
   At every mass-righteous θ the model puts 75–92% of its infections
   *during* quarantine where the record's back-calculated outbreak was
   mostly over by 5 Feb. The signatures stack: onset peak day 21–27 vs
   ~18; during-quarantine dated mass ~95% crew vs the record's 29%;
   confined-passenger acquisitions 4–19 vs the ≥52 bound; a tail of
   130–292 dated onsets past the day the record's curve ended. θ trades
   one side against the other — pre-share reaches the record's ~0.75
   only at ~1e8 where totals are 3× over — which is the quantitative
   shape of "the too hot for DP scenario" predating CAREGIVER-V1: the
   replay cannot put enough mass in the free-mixing phase without
   over-running the voyage. QUAR-ATTR-V2 already measured the
   during-quarantine half of this at Θ1e9 (crew confinement −74% and
   pool-transport −66% each load-bearing); this map shows the same
   channel dominates the whole clause-relevant surface.

3. **Dating is overshared — a flat ~3× observation-channel factor.**
   `recorded/lab` = 0.79–0.87 on every measured row, invariant to θ, to
   seeds, and to the caregiver mechanism (0.82 on CG_OFF). The record's
   convention admitted ~28% of confirmed cases to the dated curve; the
   model's channel admits ~4 in 5. This factor — not transmission — is
   what makes the dated count read 3× over at Θ7.9e6 where infections
   and confirmeds are already near-record. It is the SERO-CHANNEL-V1
   period-channel hypothesis, now shown to bind on the whole surface.

Secondary: the clause-passing surface is itself unbelievable — CG_OFF at
1e9 passes both legs (band ∋197, share 0.200) while carrying 2,342
infections (2.8× the band) and a 0.82 dating share. Clause satisfaction
and believability are different objects; the map is the right object to
score.

## 4. Needs cells — the designed legs (declared, not run)

Payloads of record carry route tallies on *acquisitions* only; no
route-tagged dated onsets, no per-cabin case pairs, no case age. Three
minimal additions — each an emit extension on the existing
boarding-screen readout, no constants, no mechanism change:

- **D1 — route-tagged dated onsets.** Emit the acquisition route on each
  onset-observation entry (the witness CG-FLOOR-01's design already
  named). Cells: {Θ1e6, Θ7.9e6} × 20 seeds = 40 cells on the current
  image. Resolves F3/F15: which mechanism's product is being dated —
  whether the pre-quarantine dated mass is caregiver-carried or
  general-delivery-carried.
- **D2 — cabin-cluster witnesses.** Emit per-cell: dated onsets in a
  cabin with vs without a previously confirmed case (the NIID Table 2
  cut), cabinmate-conditioned passenger attack rate (the CID 18/63/81
  gradient), and cabin-ring size of each dated case. Same 40-cell grid.
  Resolves F13/F14: whether the confined-passenger deficit is channel
  strength or phase.
- **D3 — readout-only (no cells). MEASURED, see §4-D3 addendum below.**
  Score the existing `infections_before/during/after_quarantine` and
  `acquisition_curve.total_by_day` against Emery 2020's back-calculated
  infection-date distribution — the sharpest available timing test.
  Caveat declared: `acquisition_curve` counts ledger events (includes
  repeat episodes), the certified distinct-host windows are the
  `infections_*` fields; use the curve for shape and the fields for
  mass. (Emery 2020 is barred as a parameter source — tranche 3 — and
  is used here only in its sanctioned role as comparator for what our
  own fit recovers.)
- **D4 — quarantine-phase suppression arm at clause θ** (needs cells).
  {Θ1e6, Θ7.9e6} × {D0_declared, QUAR-ATTR-V2's crew-confinement arm
  grammar} × 20 seeds = 40 cells. Discriminates F8's two readings: if
  during-quarantine mass collapses toward the ~150–350 record-informed
  band while pre-quarantine mass is unmoved, the inversion is
  confinement-channel over-delivery; if unmoved, it is open-phase
  under-delivery — different mechanisms, different fixes.

### 4-D3. D3 measured addendum (2026-10-04)

Scored on the 300 shipped-D0 cells of `78f52a58`/`8f49652f`/`8f926382`
plus the arm rows of `3eae8a2f` (CG_LOW) and `b932d0e9` (CG_OFF) —
34 of 40 CG_OFF cells and 76 of 80 cg_floor cells carry the fields
(the rest are no-takeoff short cells). Comparator: Emery 2020's
back-calculated DP infection-date distribution — barred as a parameter
source (tranche 3), used here only in its sanctioned comparator role.

Pooled event-curve shape (takeoff seeds, `acquisition_curve` =
event counts, shape only):

| θ / arm | inf med | <d16 share (certified) | event peak day | event median day | shape |
|---|---|---|---|---|---|
| record | ~840 | majority (~0.6–0.75, record-informed) | ~day 14–15 | — | declining into quarantine |
| 1e6 D0 | 771 | 0.079 | 21 | 23 | **inverted** — still rising through day 16, no boundary signature |
| 1e6 CG_LOW | 770 | 0.093 | 23 | 23 | unmoved vs D0 (DELIVERY-STRUCTURAL confirmed at shape level) |
| 7.9e6 D0 | 938 | 0.251 | 15 | 18 | right *shape* — peaks at the boundary and declines — wrong *split* (~25/75) |
| 7.9e6 CG_LOW | 946 | 0.236 | 18 | 18 | unmoved |
| 1e9 D0 | 3,249 | 0.902 | 13 | 12 | clean pre-quarantine spike, cliff at day 16, ~3× over mass |
| 1e9 CG_OFF | 2,342 | 0.579 | 15 | 15 | **caregiver-off drops the early hump** — mass slides into the quarantine window |

- **The phase fix is not a global shift.** At the timing-leg θ
  (7.9e6) the curve already has the record's *shape* (peak ~day 15,
  declining during quarantine) but puts ~25% of mass before the
  boundary instead of ~65/35. The empty region is days 0–8:
  event share <day 9 is 0.011–0.019 at θ≤7.9e6 (the index's ring
  produces almost nothing while the voyage is still open), vs
  0.10+ at ≥1e8. Conforming therefore needs BOTH (a) front-loading
  of days ~5–12 — open-phase under-delivery — and (b) a harder
  quarantine suppression to cut the day-16+ tail — confinement
  over-delivery. D4 reads (b); (a) has no designed leg yet.
- **θ moves the split monotonically** (certified <d16 share
  0.08 → 0.90 across the lattice) but only by stretching the same
  wrong-phase curve earlier — no θ produces the record's
  front-loaded shape; at every θ the early window stays empty.
  The residual is shape-structured, not amplitude-structured.
- Artifact flagged for D4 design: a day-5–6 event dip at low θ
  (pooled 50 → 1–8 events at 1e6) that is absent at 1e9 — looks
  scheduled/structural (a transition the exposure kernel rides
  over), not record physics; verify it survives the
  quarantine-phase arm before scoring off it.

**D3 discriminates the fix family:** the missing mass is specifically
days 5–12 aboard-window delivery — the exact window the caregiver
designation and early co-presence channels own (F15: aboard-window
acquisitions run mean ~10–64/seed across θ, caregiver-attributed
5–11/takeoff seed) — plus the quarantine-phase tail suppression D4
will measure. A mechanism that front-loads days 5–12 without touching
the during-quarantine channel leaves the tail wrong; D4 establishes
whether suppressing the confinement channel alone recovers the split.

## 5. Verdict

**BELIEVABILITY-DIVERGENT — three orthogonal divergences, none
θ-shaped.** The shipped-default replay is unbelievable on every measured
row on [1e6, 1e9]: the mass is right where either clause leg passes
(F5 in-band at 1e6 and 7.9e6), but the outbreak's phase is inverted
(F8/F9/F11/F12 — infection mass lands during quarantine instead of
before it) and the observation channel dates ~3× too much of what it
confirms (F3). The residual stack at the timing-leg θ (7.9e6) is:
infections ≈ record, confirmed ≈ record ×1.2, dated ≈ record ×3.2 —
dating, not delivery, is the largest single factor on that row. The two
record features with no reachable surface at all are the confined-
passenger cabin signature (F13/F14 — needs cells D2) and the
route-tagged dated onset (D1). The single measurement that most
resolves the map is D1+D4 together: route-tag the dated curve and
suppress the quarantine channel at 7.9e6 — after which the residual
should read as pure timing/open-phase.

Chain of record: θ-shaped? no → anchor-shaped? no → factor-shaped? no →
structure-shaped (CG-FLOOR-01) → **decomposed here: phase-inverted
delivery + observation-channel overshare; the caregiver designation is a
contributor to the pre-quarantine term, not the whole of it.**

## Sources

- Cell payloads of record (SHA / prefix / count): `78f52a58`
  `campaign/covid_theta_refit_v1/78f52a58/cells/` (180);
  `8f49652f` `..._floor_v1/` (20); `8f926382` `..._bracket_v1/` (100);
  `3eae8a2f` `campaign/covid_cg_floor_v1/3eae8a2f/cells/` (80, synced
  from the `cells/cells/` landing); `b932d0e9`
  `campaign/covid_caregiver_off_v1/b932d0e9/cells/` (40).
- Record anchors: `data/observation/covid_fit_targets.json` (covid.T1–T4,
  H5); `data/scenarios/covid_hull_scenarios.json` provenance (day_zero,
  SOP-017 window, ascertainment day 14, 3,711 = 2,666 + 1,045);
  `data/observation/covid_testing_campaigns.json` (3,063 schedule).
- NIID Field Briefing 19–23 Feb 2020: 619 confirmed as of 20 Feb (82
  crew / 537 passengers); 3,011 specimens / 621 positive; 197 dated
  onsets 34:163 at 6 Feb; 163 during-quarantine onsets (48 crew / 115
  passengers), 52–92 in cabins without a prior confirmed case, 3–7
  after quarantine day 7; 318/51% asymptomatic at specimen; onset peak
  ~7 Feb after report-lag adjustment; cabin-occupancy gradient.
- Mizumoto 2020 (Eurosurveillance 25(10):2000180) Table 1 — test
  volumes; Mizumoto & Chowell 2020 (J Clin Med 9(3):657) — incidence
  declining by ~3–4 Feb; Emery et al. 2020 — most infections
  pre-quarantine, delay-adjusted asymptomatic 17.9% (CrI 15.5–20.2);
  Hung et al. 2020 — serology-informed ≈840 [712,960]; Willebrand 2022 —
  712 final; CID 72(10):e448 — cabinmate-conditioned attack rates
  18%/63%/81%; Australian cohort (PLoS One 2021) — cabinmate RR 3.78
  pre- / 6.18 during-quarantine.
- Prior measurements: `docs/ledger/THETA-REFIT-01.md` (leg map),
  `docs/ledger/ANCHOR-DERIVE-01.md` (mechanism-independence),
  `docs/ledger/CG-FLOOR-01.md` (DELIVERY-STRUCTURAL),
  `docs/covid/covid_caregiver_off_v1_readout.md` (off-tree reference),
  `docs/covid/covid_channel_anchor_handoff_2026_09_25.md` (dating
  hypothesis; SERO-CHANNEL-V1 design), `docs/ledger/QUAR-ATTR-V2.md`
  (confinement-channel load-bearing at 1e9).
