# COVID-REBASE-01 readout — Θ window re-screen on the post-721 base: the admissible set is EMPTY, and the fleet-shape window is bracketed between 1e11 and 1e12

Measured at `6a7dfe4e` (design + probe code merged at `f280e348`,
stage-2/3 design files at `802cef9a`; engine/data tree identical across
both commits — the stages-2/3 PR carried design JSON only). Base of
comparison: the v11 refine surface measured at `79a3ac3` and the v11
stage-2 replay measured on the pre-721 line; between that SHA and this
one the default engine path moved through AERO-SPLIT-01 (`8551467b`),
CABIN-OCC-01 + ROOM-AIR-01 (`1b9d37ca`), SCHED-WATCH-01 (`e86b73bf`),
DINE-CREW-01, NORO-CABIN-01 (`b49a3ec2`), SERO-CHANNEL-V1
(`03a9db9e`/`7db0e9a6`), LAMBDA-CROSS instrumentation, and the
blackwater/wastewater flips (`fb048b02`/`b120ad3d`).

Three stages, all on AWS Batch EC2 Spot via `picard-covid-boarding-screen`
jobdef revisions 25 (stage A) and 26 (stages 2–3), images digest-pinned:

| stage | design | cells | array | prefix |
|-------|--------|------:|-------|--------|
| A — Θ re-screen (generic voyages) | `covid_rebase_01` | 3,200 | `92d51ecc-47b5-4982-9d3e-6bad5375bee9` | `campaign/covid_rebase_01/f280e348/` |
| 2 — declared replay, clause re-measure | `covid_rebase_01_stage2` | 80 | `41fc6295-0d97-4e89-9584-630890fe5c0e` (+ canary `dd4fdeae`) | `campaign/covid_rebase_01_stage2/6a7dfe4e/` |
| 3 — boarding structure | `covid_rebase_01_boarding` | 200 | `0c3e9e64-d14f-4824-a6cc-bf9272a06609` (+ canary `8d8b1a8f`) | `campaign/covid_rebase_01_boarding/6a7dfe4e/` |

Canaries (all clean): stage-A 20 cells at Θ 4.22e10
(`da148e7d-346c-4c36-b835-14deb604de44`, payload contract intact,
generic-mode index audit clean — no declared onset_day/departure_day in
any seed spec, drawn onset read back per cell); stage-2 Θ 1e9 row
re-measured the QUAR-ATTR-V2 cell of record at seed 20200205:
`infections_total` 3,365 / attack 0.9068 vs 3,458 / 0.9318 on the old
base — a delta of −93 infections reported per the frozen canary clause,
not a defect (the engine legitimately moved); stage-3 B0 row paired
seed-for-seed **bit-identical** with the stage-2 Θ 4.22e10 row
(observables and infections_total equal on all 20 seeds) and carried the
`seed_ring` block with the correct `seed_spec` echo on every cell.

## 1. Stage A — the fleet-shape surface, post-721 base

Selector (frozen, verbatim from v11): across the 200 generic voyages at
each Θ, median recorded attack ∈ [0.0005, 0.008], IQR overlaps
[0.0003, 0.015], mean ≤ 0.06. covid.H3 is the selection anchor
(median 0.002, IQR 0.0003–0.015, mean 0.037; Willebrand 2022);
covid.H1/H2/H5 stay held out. Lattice: union of the v11 decade points,
the v11 refine interior {1.33e10…7.5e10}, and a new 1e12 top bracket;
200 seeds at base 20201001, 168-epoch generic voyages — the seed carries
no declared onset/departure, exactly as v11.

| Θ | median rec. attack | IQR | mean | P(takeoff) | P(a≥.015) | P(a≥.10) | P(a≤.01) | attack q10/q50/q90 | fleet_shape |
|---|------|---------------|------:|-----:|-----:|-----:|-----:|------------------|:-----------:|
| 1e4   | 0 | [0, 0] | 0.0001 | 0.00 | 0.01 | 0.00 | 0.99 | 0 / 0 / 0.0003 | fail (floor) |
| 1e5   | 0 | [0, 0] | 0.0001 | 0.00 | 0.01 | 0.00 | 0.98 | 0 / 0 / 0.0014 | fail (floor) |
| 1e6   | 0 | [0, 0] | 0.0002 | 0.01 | 0.04 | 0.00 | 0.94 | 0 / 0.0003 / 0.0065 | fail (floor) |
| 1e7   | 0 | [0, 0.00007] | 0.0005 | 0.04 | 0.14 | 0.01 | 0.85 | 0 / 0.0003 / 0.0214 | fail (floor) |
| 1e8   | 0 | [0, 0.00027] | 0.0014 | 0.07 | 0.21 | 0.04 | 0.77 | 0 / 0.0003 / 0.0546 | fail (floor) |
| 1e9   | 0 | [0, 0.00027] | 0.0037 | 0.14 | 0.33 | 0.16 | 0.67 | 0 / 0.0008 / 0.1671 | fail (floor) |
| 1e10  | 0 | [0, 0.00061] | 0.0085 | 0.23 | 0.46 | 0.34 | 0.53 | 0.0003 / 0.0061 / 0.4843 | fail (floor) |
| 1.33e10 | 0 | [0, 0.00229] | 0.0100 | 0.25 | 0.51 | 0.36 | 0.49 | 0.0003 / 0.0187 / 0.5390 | fail (floor) |
| 1.78e10 | 0.00027 | [0, 0.00404] | 0.0111 | 0.28 | 0.55 | 0.41 | 0.42 | 0.0003 / 0.0329 / 0.5955 | fail (floor) |
| 2.37e10 | 0.00027 | [0, 0.00613] | 0.0124 | 0.31 | 0.57 | 0.44 | 0.40 | 0.0003 / 0.0319 / 0.6136 | fail (floor) |
| 3.16e10 | 0.00027 | [0, 0.00552] | 0.0141 | 0.30 | 0.59 | 0.46 | 0.36 | 0.0003 / 0.0534 / 0.6739 | fail (floor) |
| 4.22e10 | 0.00027 | [0, 0.00970] | 0.0161 | 0.35 | 0.66 | 0.51 | 0.32 | 0.0003 / 0.1064 / 0.6838 | fail (floor) |
| 5.62e10 | 0.00027 | [0, 0.01132] | 0.0189 | 0.36 | 0.67 | 0.51 | 0.30 | 0.0003 / 0.1361 / 0.7326 | fail (floor) |
| 7.5e10  | 0.00027 | [0, 0.01502] | 0.0213 | 0.37 | 0.70 | 0.56 | 0.28 | 0.0005 / 0.1804 / 0.7641 | fail (floor) |
| 1e11    | 0.00027 | [0, 0.01677] | 0.0247 | 0.41 | 0.74 | 0.61 | 0.23 | 0.0005 / 0.2736 / 0.7913 | fail (floor) |
| 1e12    | 0.01536 | [0, 0.09741] | 0.0733 | 0.61 | 0.92 | 0.86 | 0.07 | 0.0372 / 0.7627 / 0.9117 | fail (ceiling + mean) |

**Admissible set: EMPTY.** Two failures bracket the window from inside:

- *Below — the median floor never lifts.* From 1.78e10 through 1e11 the
  median voyage records exactly one onset (0.00027 of 3,711); below that
  the median is zero. On the v11 refine surface the same interior rows
  carried medians 0.00067–0.00168 (in-window) — so the post-721 base
  collapsed the median voyage back below the floor across the whole
  band. The per-seed pairing shows it is suppression, not shift: at the
  seven shared Θ, recorded onsets fell on 100–128 of 200 seeds and rose
  on only 10–17, while P(takeoff) dropped ~15–20 pp (e.g. 0.47 → 0.30 at
  3.16e10). More voyages fizzle entirely; the ones that take off still
  burn (q75 stays in the 0.005–0.017 band and rises).
- *Above — 1e12 overshoots.* Median 0.0154 > 0.008 and mean 0.0733 >
  0.06 together. The admissible interior, if any exists on this base,
  lies inside (1e11, 1e12): 1e11 fails the floor by ~2× and 1e12 fails
  the ceiling by ~2×. A bisection there is a **new stage decision**, not
  part of this design.

The shape change is the finding: covid.H3's fleet is a median voyage at
~0.2% with rare DP-class excursions. v11 satisfied that by placing
P(takeoff) ≈ 0.5 so the median sat on the boundary of the takeoff
class. On the post-721 base the takeoff transition has moved up half a
decade (P(takeoff) 0.3–0.4 through the old band, 0.61 only at 1e12) —
the median voyage fizzles everywhere the takeoff tail is DP-sized, and
by the time the median lifts (1e12) the tail has already overshot the
fleet mean. **The geometry of the selector no longer has a fixed point
on this lattice.**

## 2. Stage 2 — the conditional clause re-measured at the v11 band

Clause (frozen, verbatim): among takeoff seeds (recorded_onsets ≥ 10) of
the declared replay — onset_day −1.0, departure_day 5.0, 20 matched seeds
at base 20200205, 768 epochs — the q05–q95 interval of recorded_onsets
contains 197 AND the median `before_share` (onsets before day 17) is
within 0.10 of 0.173. Audit invariant held on all 80 cells
(index_onset_day == −1.0, index_shedding_at_day0 true, departure at
epoch 120).

| Θ | role | takeoff | ro q05–q95 (takeoff seeds) | contains 197 | before_share med | clause | mass∈[98.5,394] |
|---|------|--------:|----------------------------|:------------:|-----------------:|:------:|:---:|
| 1e9   | canary anchor | 11/20 | 85 – 3,164 | **yes** | 0.087 | *pass-form* | 0.09 |
| 3.16e10 | v11 set | 19/20 | 1,485 – 3,462 | no | 0.480 | FAIL | 0.00 |
| 4.22e10 | v11 set | 19/20 | 1,674 – 3,476 | no | 0.451 | FAIL | 0.00 |
| 5.62e10 | v11 set | 19/20 | 2,210 – 3,493 | no | 0.660 | FAIL | 0.00 |

Against the v11 stage-2 record (same seeds, pre-721 base):

- **Mass failure unchanged in class.** Takeoff-class recorded onsets
  still land ~15–17× over 197 (v11: q05–q95 ~2,100–3,560; now
  ~1,485–3,493 — the band moved down and slightly narrowed, but there is
  still no seed anywhere near the record: mass∈[98.5,394] = 0.00
  everywhere in the band, as before).
- **before_share moved materially toward target.** v11 read 0.77–0.92;
  the post-721 base reads 0.45–0.66 — roughly half the onset mass now
  arrives after the day-17 quarantine split (SOP-017 days 16–30 bites on
  the post-721 compartments that the pre-721 run burned through earlier).
  It still fails the ±0.10-of-0.173 tolerance by 2.8–4.9× — same failure,
  smaller margin.
- **The Θ 1e9 anchor passes the clause in form** (q05–q95 [85, 3,164]
  contains 197; before_share 0.087 within 0.10) — but this is the
  declared structure of the clause, not a fit: takeoff mass 11/20,
  mass-near-197 only 0.09, and Θ 1e9 is far outside the stage-A window
  (its generic median is 0). The pass is interval-spanning plus a shifted
  before_share, i.e. exactly the "pass by width, not mass" structure the
  clause's flank reporting was designed to expose. Reported as the
  boundary readout; never selected on.
- Unconditional read: declared-geometry takeoff fraction is 0.95 in the
  band (vs 0.30–0.36 on the generic fleet at the same Θ) and 0.55 at
  1e9 — the symptomatic-at-boarding index remains the takeoff machine;
  what the post-721 base changed is how often the drawn-introduction
  fleet takes off, not what a taken-off voyage looks like.

## 3. Stage 3 — boarding structure (INDEX-GEOM-01 / SEED-ONSET-01 measured)

Ten arms at Θ 4.22e10 (declared fallback, the v11 band centre — a fixed
measurement point, not a fit), 20 matched seeds at base 20200205, full
768-epoch declared replay. Every cell carries the `seed_ring` block; the
`seed_spec` echo audit passed on 200/200 cells (each arm's declared
patch fields, and only those, present on `explicit_seeds[0]`).
`aboard_window` = every non-seeded first acquisition while a seeded host
is aboard (epochs < 120, i.e. days 0–5); `clean_bound` = acquisitions
before the first non-seeded host's earliest possible shed epoch — the
index-only floor. `yield_per_seeded_host` on takeoff seeds (rec ≥ 10).

| arm | shed@d0 | takeoff | aboard-acq med | IQR | clean med | yield/seed (takeoff) | window share of infections (takeoff med) | recorded med | infections med |
|-----|:---:|:---:|---:|---|---:|---:|:---:|:---:|---:|
| B0 declared (−1, ×1) | 1.00 | 19/20 | 18 | 6 – 444 | 3 | 18.0 | 0.005 | 3,333 | 3,438 |
| B_onset_p3 (+3) | 0.00 | 19/20 | 24 | 2 – 165 | 7.5 | 31.0 | 0.009 | 3,400 | 3,425 |
| B_onset_p1 (+1) | 1.00 | 19/20 | 121 | 21 – 506 | 12 | 129.0 | 0.037 | 3,441 | 3,502 |
| B_onset_0 (0) | 1.00 | 20/20 | 20 | 5 – 74 | 2 | 19.5 | 0.006 | 3,235 | 3,406 |
| B_onset_m3 (−3) | 1.00 | 20/20 | 207 | 69 – 1,344 | 3 | 207.0 | 0.059 | 3,428 | 3,513 |
| B_onset_m5 (−5) | 1.00 | 20/20 | 162 | 54 – 1,140 | 3 | 161.5 | 0.046 | 3,445 | 3,506 |
| B_count_2 | 1.00 | 20/20 | 264 | 104 – 535 | 6 | 132.0 | 0.075 | 3,445 | 3,506 |
| B_count_4 | 1.00 | 20/20 | 722 | 271 – 1,422 | 16.5 | 180.6 | 0.206 | 3,362 | 3,518 |
| B_count_8 | 1.00 | 20/20 | 1,472 | 1,198 – 1,768 | 8 | 183.9 | 0.417 | 3,130 | 3,516 |
| B_count_32 | 1.00 | 20/20 | 2,330 | 2,206 – 2,483 | 0 | 72.8 | 0.667 | 2,528 | 3,498 |

What the two axes say:

- **SEED-ONSET-01 (position in the shedding course at boarding):** the
  takeoff class is insensitive to it — 19–20/20 takeoff everywhere,
  including a boarder who does not emit at all on day 0 (B_onset_p3,
  shed opens day 1). The onset axis moves the *window composition* (late
  boarders burn a median 162–207 aboard-window acquisitions vs 18–121
  for early/onset-adjacent boarders) but not the voyage outcome —
  because takeoff on this arm is already saturated (0.95–1.00), not
  because boarding geometry is inert.
- **INDEX-GEOM-01 (co-primaries):** aboard-window acquisitions scale
  super-linearly into the takeoff-class burn — 1 index: median 18 window
  acquisitions (0.5% of infections); 8 co-primaries: median 1,472
  (42%); 32 co-primaries: median 2,330 (67%, and 19/20 takeoff seeds
  with the window holding ≥50% of infections). Yield per seeded host
  rises then saturates (18 → 184 → 73 by count 32) — the day-0 ring
  saturates because the host pool it can reach is finite, and by count
  32 the recorded-onset median has already *dropped* to 2,528: the
  window burn consumes susceptibles the later voyage would have
  recorded.
- **Route split:** the aboard-window acquisitions are ~87–90% `droplet`
  and ~10–12% `hvac_airborne` in every arm (pooled), `direct_contact`
  ~0 — consistent with COVID-SEED-GEOM-01's far-field-pool-dominated
  read on the old base; the post-721 far-field share (0.175 under
  AERO-SPLIT-01) is still the load-bearing window route.
- **The clean index-only bound stays small** (median 0–16.5
  everywhere) — most window acquisitions are generation-2+ chains that
  begin inside the window, not direct index dose. The bound collapses
  to 0 at count 32 because secondaries shed so early that almost every
  acquisition already has an earlier potential emitter.

**The prompt's majority test, answered at the record's geometry:**
boarding structure alone does NOT account for the majority of
takeoff-class burn — at the declared index (count 1, onset −1, departs
day 5) the entire day-0→5 window is a median 0.5% of infections and the
index-only bound is a median of 3. The co-primaries mechanism *can*
reach the majority but only at ≥~8–32 simultaneous seeds — an order of
magnitude beyond anything in the record. Boarding geometry is a
multiplier on an already-saturated takeoff, not the burn itself.

## 4. What this changes

- **Every prior fitted Θ stays void, and there is no admissible Θ to
  replace it with.** The fleet-shape window is bracketed between 1e11
  and 1e12; the v11 band {3.16e10, 4.22e10, 5.62e10} is dead on this
  base (median-floor failures, paired-seed suppression confirmed).
- **The conditional clause still fails everywhere measured** — same
  ~17× mass class — but the failure composition changed: before_share
  halved (0.77–0.92 → 0.45–0.66) while mass stayed put, so the takeoff
  burn now arrives later, inside the quarantine window, rather than
  earlier.
- **INDEX-GEOM-01's boarding-debt hypothesis is measured and is not the
  burn.** The declared index's whole-aboard contribution is a median
  ~0.5% of takeoff-class infections; effective co-primaries reach
  majority scale only at count ≥ ~8, and saturate by 32. Whatever makes
  takeoff-class voyages record ~3,300 onsets is downstream of the index
  window — post-departure chains in the post-721 compartment structure —
  not the day-0 ring.
- **SEED-ONSET-01's onset_day is a real but bounded lever:** it moves
  the window's acquisition mass ~10× across its span yet cannot move
  takeoff on the declared geometry (already 0.95–1.00) — so on this arm
  it cannot explain the conditional-clause mass failure either.

## Reproduction

```bash
# surfaces
python3 tools/fit_covid_theta.py screen --cells <cells dir> \
    --design picard_framework/runs/covid_rebase_01_design.json
python3 tools/fit_covid_theta.py screen --cells <s2 cells dir> \
    --design picard_framework/runs/covid_rebase_01_stage2_design.json
# CSVs of record
python3 tools/covid_theta_screen_csv.py <surface.json> --out <out.csv>
```

S3 prefixes per stage in the table above; cell objects are
`cells/cells/screen_diamond_princess_2020_*.json` under each. Design
files: `picard_framework/runs/covid_rebase_01{,_stage2,_boarding}_design.json`,
mirrored beside each prefix.
