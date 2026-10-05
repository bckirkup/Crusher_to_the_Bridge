# DP-BELIEF-01-D4 quarantine-phase suppression arm — CONFINEMENT-CHANNEL over-delivery (tail *is* the crew exemption)

> **Status:** Findings (2026-10-04). Campaign measured at `6ea3093d`
> (image `picard-campaign@sha256:2c279aa2…` / tag
> `campaign-f31de83a-quarsuppress`, jobdef
> `picard-covid-boarding-screen-fargate:2`, queue
> `picard-analysis-fargate-queue`, prefix
> `campaign/covid_quar_suppression_v1/6ea3093d/cells/`).

DP-BELIEF-01's believability map scored three orthogonal divergences;
its §4 named D4 as half of the discriminating pair: does a
quarantine-phase suppression arm collapse the during-quarantine mass
toward the record-informed band (~150–350 infections on days 16–30)
while leaving pre-quarantine mass unmoved? If yes, the fat day-16+ tail
is a confinement-channel over-delivery; if unmoved, the divergence
localizes to open-phase under-delivery.

Design `picard_framework/runs/covid_quar_suppression_v1_design.json`:
{Θ1e6, Θ7.9e6} × {`D0_declared`, `SOP017_ALLHANDS`} × 20 seeds = 80
cells on the verbatim `diamond_princess_2020` replay contract
(theta-major then arm then seed: 0–19 = 1e6/D0, 20–39 = 1e6/ALLHANDS,
40–59 = 7.9e6/D0, 60–79 = 7.9e6/ALLHANDS — the map's "40 cells" line
was arithmetically inconsistent with its own canary coordinates and is
author-resolved to 80 in the design's `cells_note`). `SOP017_ALLHANDS`
is the design-arm override `{"scheduled_protocol_id": "SOP-017-ALLHANDS"}`
which swaps the scenario's single scheduled-protocol slot to the
all-hands diagnostic counterfactual declared in
`data/config/protocols.json` (historically FALSE — crew kept working;
never scored against any anchor). The verdict grammar
(CONFINEMENT-CHANNEL / OPEN-PHASE / PARTIAL-SUPPRESSION /
SUB-IGNITION) is frozen in `admissibility` before any cell ran.

80/80 cells SUCCEEDED, zero audit failures — `quarantine_witness`
echoes `SOP-017-ALLHANDS` + `exempt_classes []` + `window_days [16,30]`
+ `activated true` on every ALLHANDS cell and the shipped `SOP-017`
four-crew-class exemption on every D0 cell; the propensity/caregiver/
delivery/index-geometry echoes all pass.

## Replication check (the in-design drift witness)

The two `D0_declared` rows re-run cells already of record — the floor
probe's Θ1e6 row and the bracket's Θ7.9e6 row. **20/20 per row
bit-identical modulo bookkeeping** (`design_id`, `cell.index`) **plus
one additive zero-count route key**: the f31de83a-generation image
emits `common_source_food: 0` in the `during_*_by_route` tallies
(FOOD-COMMON-SOURCE-01 landed after the refit-generation cells; covid
food is disabled, so the key is a constant zero). `max|delta| 0` on
every numeric leaf — the engine tree moved textually but not
behaviorally for this contract.

## Clause scorecard (per row, takeoff-conditional; arm rows non-scoring context)

| Θ | arm | takeoff | rec q05/med/q95 | before_share med | count | timing | clause |
|--:|-----|--------:|------------------|-----------------:|:-----:|:------:|:------:|
| 1e6 | D0_declared | 19/20 | 149 / 331 / 760 | 0.051 | **PASS** | FAIL | FAIL |
| 1e6 | SOP017_ALLHANDS | 19/20 | 15 / 60 / 352 | 0.269 | (context) | (context) | (non-scoring) |
| 7.9e6 | D0_declared | 19/20 | 496 / 634 / 1,540 | 0.075 | **PASS** | **PASS** | **PASS** |
| 7.9e6 | SOP017_ALLHANDS | 19/20 | 71 / 231 / 1,410 | 0.250 | (context) | (context) | (non-scoring) |

The in-design D0 rows reproduce the cells of record's clause map
exactly — the drift witness carries the clause, not just the cells.

## The verdict: CONFINEMENT-CHANNEL — and it is the whole tail, not just the excess

During-quarantine mass (`infections_during_quarantine`, certified
distinct-host days-16–30 count), takeoff-conditional:

| Θ | D0_declared med [q05, q95] | SOP017_ALLHANDS med [q05, q95] | record-informed band |
|--:|------------------------------|-------------------------------|----------------------:|
| 1e6 | **678** [480, 821] | **27** [5, 154] | 150–350 |
| 7.9e6 | **730** [398, 813] | **105** [36, 225] | 150–350 |

Seed-paired deltas (ALLHANDS − D0, n = 19 per row):

| Θ | Δduring med [q05, q95] | Δbefore med | Δduring-crew med | Δtotal med | Δrecorded med |
|--:|------------------------|------------:|-----------------:|-----------:|--------------:|
| 1e6 | **−602** [−712, −291] | **0** | −604 | −646 | −285 |
| 7.9e6 | **−624** [−760, −166] | **0** | −623 | −642 | −417 |

`infections_before_quarantine` is **bit-identical seed-for-seed** on
both rows — Δ 0 [0, 0] — and the pooled acquisition curve is identical
day-for-day through day 15 (events: 347/2,611 and 833/7,367 pooled on
days 0–8 / 9–15, both arms). The swap touches only the days-16–30
protocol; the entire open phase is provably unmoved — the grammar's
(a) precondition holds in its strongest form.

The during-window collapse is driven almost entirely by the crew
channel: Δduring-crew ≈ Δduring (residual ~0–19). Pooled role tallies:

| Θ | arm | during crew | during pax | crew share | record dated-crew share |
|--:|-----|------------:|-----------:|-----------:|--------------------------:|
| 1e6 | D0 | 12,053 | 524 | **95.8%** | 29% (NIID T2) |
| 1e6 | AH | 563 | 511 | 52.4% | |
| 7.9e6 | D0 | 12,285 | 970 | **92.7%** | |
| 7.9e6 | AH | 1,510 | 973 | 60.8% | |

**Grammar mapping:** (a) CONFINEMENT-CHANNEL over-delivery — the arm
collapses the during-window mass toward the record-informed band while
the open phase is unmoved. With the honest sharpening the grammar did
not pre-write: the collapse **overshoots the band's low edge** (med 27
and 105 vs 150–350). At clause thetas the fat day-16+ tail is not
merely over-delivered by the crew exemption — it is ~92–96% *carried*
by it. Even the residual is not the record's shape: under all-hands
confinement the during-window tally stays crew-majority (52–61% vs the
record's 29% dated-crew share) because crew share cabins with crew —
the residual is a confined-cabin channel, not a corridor/venue channel.

The zone tallies show it directly:

| Θ | arm | cabin | corridor | crew_mess | galley | other |
|--:|-----|------:|---------:|----------:|-------:|------:|
| 1e6 | D0 | 1,056 | 590 | **6,694** | 493 | 3,744 |
| 1e6 | AH | **1,072** | 0 | 1 | 0 | 1 |
| 7.9e6 | D0 | 1,610 | 577 | **6,696** | 442 | 3,930 |
| 7.9e6 | AH | **2,466** | 0 | 1 | 0 | 16 |

Under the arm, the crew_mess/corridor/galley channels vanish (all-hands
confinement enforced) and the residual lands almost entirely in cabins.
`confined_passenger_infections_during_window` — the confined-pax bound
— is itself unmoved (med 4→2 at 1e6; 19→18 at 7.9e6): the arm does
nothing for the passenger cabin channel, which the record needs more
of, not less.

## The day-curve witness (D3's flagged artifact answered)

Pooled acquisition-event days (takeoff cells):

| window | 1e6 D0 | 1e6 AH | 7.9e6 D0 | 7.9e6 AH |
|--------|-------:|-------:|---------:|---------:|
| days 0–8 | 347 | **347** | 833 | **833** |
| days 4–6 (dip) | 60 | **60** | 105 | **105** |
| days 9–15 | 2,611 | **2,611** | 7,367 | **7,367** |
| days 16–30 | 12,577 | 1,074 | 13,255 | 2,483 |
| days 31+ | 421 | 4 | 77 | 13 |

The **day-5–6 dip is arm-independent** — identical pooled counts under
both arms at both thetas. D3 flagged it as a possible
scheduled-structure artifact; it survives the protocol swap untouched,
so it is an open-phase mechanism artifact (contact-calendar structure
before the confinement order), not a quarantine interaction.

Under the arm the acquisition curve cliff at day 16 is sharp: at 7.9e6
pooled events drop 1,741 → 195 (day 15 → 16) and the residual tail
decays to ~13–30/day by day 30 — a cabin-exhaustion profile, not an
ongoing-channel profile.

## What this closes and what it opens

D4 answers the map's discriminating question: **the during-quarantine
mass is confinement-channel mass.** Suppressing the channel removes
~92–96% of the day-16+ tail while leaving every pre-window byte
identical — so the believability fix on the tail side is not "harder
suppression" of an open-phase surplus (there is none); it is *where the
channel delivers*. The declared SOP-017 exempts four crew classes who
keep working through crew_mess/galley/corridor venues; the record's
during-window mass is dominated by passenger cabin transmission instead.

Two stated-limitation caveats:

- The band [150, 350] is a record-informed estimate (NIID 163 dated
  onsets scaled to infections); the arm's medians landing *below* it
  could partly reflect a generous band rather than a below-record
  residual channel. Either way the ordering verdict is unchanged.
- The arm rows' clause scores (recorded med 60/231) are reported as
  context only — SOP-017-ALLHANDS is a diagnostic counterfactual,
  never an anchor score.

Chain of record (DP-BELIEF-01): θ-shaped? no → anchor-shaped? no →
factor-shaped? no → structure-shaped (CG-FLOOR-01) → phase-inverted +
flat overshare → **D4: the tail half is the crew-exemption confinement
channel** — measured, seed-paired, drift-witnessed.

## Run note

Canary = the 1e6/SOP017_ALLHANDS row (cells 20–39), reported and
approved before the remaining 60 cells ran. The first canary submit
parked >1 h on `picard-analysis-queue` — an account-wide EC2 On-Demand
capacity drought (a sibling noro canary parked identically); at the
1-hour mark the campaign moved to the pre-declared Fargate fallback:
new jobdef `picard-covid-boarding-screen-fargate` rev 2
(`platformCapabilities: FARGATE`, 1 vCPU/4 GiB, `assignPublicIp
ENABLED`, same digest-pinned image) submitted on
`picard-analysis-fargate-queue`, and the parked EC2 array was
terminated before any child started. All 80 cells produced on Fargate
in three arrays (`ce62462e` canary 20, `3868638a` D0-1e6 20, `c425833e`
7.9e6-both-arms 40); ~75 min total wall on Fargate for the 60-cell
follow-on, zero child failures, zero audit failures. The EC2 jobdef
rev 56 remains registered and unused by cells.
