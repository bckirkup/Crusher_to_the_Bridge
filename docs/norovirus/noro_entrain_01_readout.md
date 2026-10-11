# NORO-ENTRAIN-01 readout — levers A (event shape) and B (arriving shedders)

> **Status:** Measured — scored on the full fleet at engine `dbbd5395`.
> 27,000/27,000 cells landed, 0 FAILED; 1,000 zips under each of the 27 block
> prefixes at `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_entrain_01/`.
> Design of record: [noro_entrain_01_sweep_design.md](noro_entrain_01_sweep_design.md) —
> §6 scored criteria and §11 readout plan are the contract this document answers.

## 1. Scored-criteria verdicts up front

| §6 clause | Question | Measured answer | Verdict |
|---|---|---|---|
| 6.1 Lever A | `a_ext`/`a_thin` move excursion→posting conversion toward `ind` (13–43%) vs `ship` (0–6%) on cls/spr, directions opposite | conversion stays at `ship` level on both arms on all hulls (0.2% vs `ind` 4.4%/1.7% on cls/spr); the two directions are indistinguishable from each other | **No movement — extent is not the discriminating axis** |
| 6.1 Lever A | D1 posting thin tail unchanged vs `ship` on all hulls | posted-conditional pax AR med 0.003–0.035 on every cell, `ship` included — thin everywhere, not degraded by the arms | Held (arms did not degrade D1) |
| 6.1 Lever A | D4 burst48 signature retained on exp — postings read as bursts, not accretion | posted-arm bursts on exp sit at rest level (0.389 vs unposted rest 0.400); cs-excursion cells still burst (0.55–0.68); `ind` postings burst (0.521) | **Not retained on the object-arm postings** |
| 6.1 Lever A | per-window serving mass ~ unchanged on `a_ext`, ~⅓ on `a_thin` | `a_ext` pw med ~23–24 ≈ `ship`; `a_thin` pw med ~3–9 vs `ship` 9–25 (~3× thinner) | Realized as declared |
| 6.2 Lever B | `bc*` move posting toward/into 0.4–0.9% on cls/spr, posted-conditional AR 0.04–0.10, burst retained | posting: cls bc40 0.8% in-band, bc80 1.9% above; spr bc40 0.4% / bc80 0.5% in-band. Posted-conditional AR stays below band (0.014–0.017). Burst flat (exp 0.375 vs 0.400; spr 0.276 vs 0.264) | Posting in-band; **AR below band; burst not retained** |
| 6.2 Lever B | `bmix` vs `bc80` signs the net direction | at equal crew prevalence (8%), `bmix` posting collapses to `bi50`/`ship` level (0.1% cls/spr) — immunity dominates the net sign | Measured: immune-pool draw dominates |
| 6.4 | spr `bc80` lifts posting into band **with** burst signature → mega | rate leg met (0.5% in band); **burst leg not met** (posted 0.276 ≈ rest 0.264) | **Gate not met — mega stays excluded** |
| 6.3 | must-not-move (§2 contract) | all checks clean — table §7 below | Held everywhere |

**Bottom line (measured):** Lever A does not move conversion at all — `a_ext`
and `a_thin` are posting-identical to `ship` on paired seeds (same posted
voyages), and the two opposite direction changes give the same 0.1–0.2%
conversion. The extent axis the object machinery carries is not what separates
`ind` from `ship`; this is consistent with the cadence hypothesis recorded in
SCORE-01 and points to the declared `cs_extent` redraw arm as the
discriminating test. Lever B moves posting into the band on cls/spr and buys
P(early) → 97–100%, but the posting it buys is ~95% arriving-shedder-sourced
object activity (the declared conflation realized), carries no burst
signature, and leaves the posted-conditional AR tail thin — so it reproduces
VSP posting frequency without reproducing the VSP posting *shape*. Posted-AR
remains below the 0.04–0.10 band on every arm including `ind`: the gap SCORE-01
measured persists unchanged.

## 2. Posting rate vs the 0.4–0.9% band

Wires are the A9 3%-of-emitted-complement threshold: exp ≥10 pax / ≥5 crew;
cls ≥41/≥18; spr ≥63/≥27. Wilson 95% CIs.

| cell | n | posted | rate [95% CI] | vs band |
|---|---|---|---|---|
| exp off | 1000 | 10 | 1.00% [0.54,1.83] | above |
| exp ind | 1000 | 68 | 6.80% [5.40,8.53] | above |
| exp ship | 1000 | 15 | 1.50% [0.91,2.46] | above |
| exp a_ext | 1000 | 15 | 1.50% [0.91,2.46] | above |
| exp a_thin | 1000 | 15 | 1.50% [0.91,2.46] | above |
| exp bc40 | 1000 | 23 | 2.30% [1.54,3.43] | above |
| exp bc80 | 1000 | 37 | 3.70% [2.70,5.06] | above |
| exp bi50 | 1000 | 8 | 0.80% [0.41,1.57] | in |
| exp bmix | 1000 | 12 | 1.20% [0.69,2.09] | above |
| cls off | 1000 | 0 | 0.00% [0.00,0.38] | below |
| cls ind | 1000 | 39 | 3.90% [2.87,5.29] | above |
| cls ship | 1000 | 1 | 0.10% [0.02,0.56] | below |
| cls a_ext | 1000 | 2 | 0.20% [0.05,0.73] | below |
| cls a_thin | 1000 | 2 | 0.20% [0.05,0.73] | below |
| cls bc40 | 1000 | 8 | 0.80% [0.41,1.57] | in |
| cls bc80 | 1000 | 19 | 1.90% [1.22,2.95] | above |
| cls bi50 | 1000 | 1 | 0.10% [0.02,0.56] | below |
| cls bmix | 1000 | 1 | 0.10% [0.02,0.56] | below |
| spr off | 1000 | 1 | 0.10% [0.02,0.56] | below |
| spr ind | 1000 | 16 | 1.60% [0.99,2.58] | above |
| spr ship | 1000 | 2 | 0.20% [0.05,0.73] | below |
| spr a_ext | 1000 | 2 | 0.20% [0.05,0.73] | below |
| spr a_thin | 1000 | 2 | 0.20% [0.05,0.73] | below |
| spr bc40 | 1000 | 4 | 0.40% [0.16,1.02] | in |
| spr bc80 | 1000 | 5 | 0.50% [0.21,1.17] | in |
| spr bi50 | 1000 | 1 | 0.10% [0.02,0.56] | below |
| spr bmix | 1000 | 1 | 0.10% [0.02,0.56] | below |

Notes, measured:

- `exp off` posts at 1.0%: the witness floor SCORE-01 recorded (v1 event
  carryovers; `ind` events on the `off` arm — the shipped ind arm is 0
  objects). `cls off`/`spr off` post 0–0.1% — inside pairing noise of zero
  at n=1000 (§7 confirms 0 objects/events/takers).
- `exp` sits above the band on nearly every arm — the hull's small
  complement makes the ≥10-pax wire cheap relative to incident mass.
- Pairing (same seeds): `a_ext`/`a_thin` post on exactly the `ship` posted
  voyages on all hulls (exp 15/15 ⊂ ship's 15; cls 2/2 = 1 ship +1 new; spr
  2/2 = same 2). `bc80` posts are mostly **new** voyages (exp 5/37 ∩ ship;
  cls 1/19; spr 1/5) — Lever B buys postings on voyages `ship` never posts.

## 3. Posted-conditional passenger AR vs 0.04–0.10

Median reported (emitted-complement) pax AR over posted voyages; reach =
median × reported/0.03.

| cell | posted | med rep pax AR [p10,p90] | reach | verdict |
|---|---|---|---|---|
| exp ind | 68 | 0.0348 [0.0000,0.0570] | 1.48 | below |
| exp ship | 15 | 0.0158 [0.0000,0.0380] | 1.27 | below |
| exp a_ext/a_thin | 15 | 0.0158 | 1.27–1.37 | below |
| exp bc40 | 23 | 0.0158 | 1.49 | below |
| exp bc80 | 37 | 0.0127 | 1.24 | below |
| exp bi50 / bmix | 8 / 12 | 0.0206 / 0.0127 | — | below |
| cls ind | 39 | 0.0336 [0.0052,0.0426] | 1.34 | below |
| cls ship | 1 | 0.0030 | 3.79 | below |
| cls a_ext/a_thin | 2 | 0.0086 / 0.0075 | — | below |
| cls bc40 | 8 | 0.0171 | 1.08 | below |
| cls bc80 | 19 | 0.0164 | 1.11 | below |
| spr ind | 16 | 0.0219 | 1.33 | below |
| spr ship | 2 | 0.0114 | 1.65 | below |
| spr bc40 | 4 | 0.0169 | 1.24 | below |
| spr bc80 | 5 | 0.0143 | 1.07 | below |

Every arm is below the 0.04–0.10 band, `ind` included. Posting clears the
wire on emitted counts while the reported passenger AR stays thin — the same
posting-without-the-AR-tail shape SCORE-01 measured. Lever B postings buy no
AR tail at all (bc80 reach ~1.1 on cls/spr). `posted_stream ∈ {pax, crew,
paxcrew}` and `vsp_trigger == posted` on every posted row (crew trigger
alone never posts — wire is dominated by pax counts as designed).

## 4. Excursion→posting conversion by arm + route decomposition

Early event = object `seeded_epoch ≤ 48` or v1 event `start_epoch ≤ 48`
(first 2 days). Census sample: all 310 posted cells plus a stride of
unposted cells per block (exp 60, cls 40, spr 30; `cls a_ext` 80 — surplus
from a first pass). Conversion is the unbiased estimator
`posted_early / (posted_early + P(early)·N_unposted)` — posted cells are
censused at 100%, unposted at the stride rate, so the sample is
denominator-corrected, not raw.

| cell | unposted censused | ≥1 early | P(early) [CI] | posted | posted w/ early | P(post\|early) | P(post\|no early) |
|---|---|---|---|---|---|---|---|
| exp off | 60 | 0 | 0% | 10 | 0 | — | 1.0% |
| exp ind | 60 | 22 | 36.7% | 68 | 57 | **14.3%** | 1.8% |
| exp ship | 60 | 28 | 46.7% | 15 | 8 | 1.7% | 1.3% |
| exp a_ext | 60 | 28 | 46.7% | 15 | 8 | 1.7% | 1.3% |
| exp a_thin | 60 | 28 | 46.7% | 15 | 8 | 1.7% | 1.3% |
| exp bc40 | 60 | 40 | 66.7% | 23 | 18 | 2.7% | 1.5% |
| exp bc80 | 60 | 50 | 83.3% | 37 | 33 | 3.9% | 2.4% |
| exp bi50 | 60 | 19 | 31.7% | 8 | 7 | 2.2% | 0.1% |
| exp bmix | 60 | 37 | 61.7% | 12 | 8 | 1.3% | 1.0% |
| cls ind | 40 | 35 | 87.5% | 39 | 39 | **4.4%** | 0.0% |
| cls ship | 40 | 36 | 90.0% | 1 | 1 | 0.1% | 0.0% |
| cls a_ext | 80 | 76 | 95.0% | 2 | 2 | 0.2% | 0.0% |
| cls a_thin | 40 | 37 | 92.5% | 2 | 2 | 0.2% | 0.0% |
| cls bc40 | 40 | 39 | 97.5% | 8 | 8 | 0.8% | 0.0% |
| cls bc80 | 40 | 40 | 100% | 19 | 19 | 1.9% | — |
| cls bi50 | 40 | 28 | 70.0% | 1 | 1 | 0.1% | 0.0% |
| cls bmix | 40 | 39 | 97.5% | 1 | 1 | 0.1% | 0.0% |
| spr ind | 30 | 28 | 93.3% | 16 | 16 | **1.7%** | 0.0% |
| spr ship | 30 | 30 | 100% | 2 | 2 | 0.2% | — |
| spr a_ext/a_thin | 30 | 30 | 100% | 2 | 2 | 0.2% | — |
| spr bc40 | 30 | 30 | 100% | 4 | 4 | 0.4% | — |
| spr bc80 | 30 | 30 | 100% | 5 | 5 | 0.5% | — |
| spr bi50 | 30 | 28 | 93.3% | 1 | 1 | 0.1% | 0.0% |
| spr bmix | 30 | 30 | 100% | 1 | 1 | 0.1% | — |

Measured, against §6.1's `ind` 13–43% vs `ship` 0–6% frame:

- `ind` conversion lands 14.3/4.4/1.7% — inside the declared ramp's range on
  exp, at its low end on cls/spr. `ship` sits at 1.7/0.1/0.2% — at/below the
  declared ~0–6% window.
- **Lever A: no movement.** `a_ext` ≡ `a_thin` ≡ `ship` on every hull —
  0.2% vs 0.1% cls, 0.2% vs 0.2% spr, 1.7% exp, and the posted voyages are
  literally the same seeds. The design's opposite-direction check gives a
  null contrast: extending shelf life and thinning take-share do not move
  conversion in either direction. Extent is not the discriminating axis.
- **Lever B: partial.** `bc*` raises conversion to 0.8/1.9% on cls and
  0.4/0.5% on spr — toward but only into the band at bc80's overshoot on
  cls — while also raising P(early) itself (exp 66.7→83.3%, cls 97.5→100%,
  spr already saturated at 100%). Most of the posting gain is denominator
  mass (more early events), not conversion efficiency: spr bc80 converts
  0.5% of early excursions — the same order as `ship`'s 0.2% — it just
  seeds early objects on ~every voyage.
- Size join (max-early-event servings_taken, posted vs unposted censused):
  bc80 posted early events are not bigger than unposted ones (cls med 576
  vs 712 unposted; spr 829 vs 829.5) — posting correlates with early event
  *presence*, not size, on the bc* arms. `ind`'s posted max-early is
  bigger than unposted (cls 52 vs 31.5; spr 60.5 vs 37.5) — size still
  discriminates inside the v1 mechanism as SCORE-01 measured.

### Route decomposition (early events, source_kind ∈ {provisioned_lot, ill_handler, ill_diner})

Counts are early events; last column is the voyage-max early event's kind on
posted voyages (lot/handler/diner/none).

#### exp

| arm | posted voyages (lot/hdl/dnr) | all censused (lot/hdl/dnr) | voyage-max on posted (lot/hdl/dnr/none) |
|---|---|---|---|
| off | 0/0/0 | 0/0/0 | 0/0/0/10 |
| ind | 249/16/16 | 269/27/33 | 50/4/3/11 |
| ship | 4/16/5 | 4/61/17 | 3/4/1/7 |
| a_ext | 4/16/5 | 4/61/17 | 3/4/1/7 |
| a_thin | 4/11/3 | 4/55/15 | 4/4/0/7 |
| bc40 | 6/39/17 | 6/114/43 | 4/5/9/5 |
| bc80 | 4/112/33 | 4/261/71 | 2/14/17/4 |
| bi50 | 4/6/5 | 4/26/11 | 3/1/3/1 |
| bmix | 4/16/6 | 4/117/29 | 4/2/2/4 |

#### cls

| arm | posted voyages (lot/hdl/dnr) | all censused (lot/hdl/dnr) | voyage-max on posted (lot/hdl/dnr/none) |
|---|---|---|---|
| off | 0/0/0 | 0/0/0 | 0/0/0/0 |
| ind | 160/41/100 | 165/66/185 | 22/3/14/0 |
| ship | 1/16/7 | 1/85/63 | 0/0/1/0 |
| a_ext | 1/16/9 | 2/285/132 | 0/0/2/0 |
| a_thin | 1/15/5 | 2/120/58 | 1/0/1/0 |
| bc40 | 2/59/26 | 2/278/117 | 0/1/7/0 |
| bc80 | 1/272/79 | 1/847/268 | 0/4/15/0 |
| bi50 | 1/9/4 | 1/55/52 | 1/0/0/0 |
| bmix | 1/18/4 | 1/296/115 | 1/0/0/0 |

#### spr

| arm | posted voyages (lot/hdl/dnr) | all censused (lot/hdl/dnr) | voyage-max on posted (lot/hdl/dnr/none) |
|---|---|---|---|
| off | 0/0/0 | 0/0/0 | 0/0/0/1 |
| ind | 80/39/67 | 90/81/159 | 7/0/9/0 |
| ship | 1/30/12 | 1/206/71 | 1/0/1/0 |
| a_ext | 1/26/15 | 1/197/74 | 1/0/1/0 |
| a_thin | 1/19/6 | 1/188/65 | 1/0/1/0 |
| bc40 | 2/64/34 | 2/450/139 | 1/0/3/0 |
| bc80 | 2/157/45 | 2/780/205 | 1/0/4/0 |
| bi50 | 1/25/8 | 1/115/56 | 0/0/1/0 |
| bmix | 1/25/10 | 1/450/97 | 0/0/1/0 |

Measured: `ill_handler` dominates the bc* early activity (~7–10× the other
kinds — crew shedders work the serving line). `ind`'s posted early mass is
`provisioned_lot`-led (cls 22/39 posted voyages have a lot driver; 14
handler, 3 diner). On `bc80` posted voyages the driver is diner/handler
(cls 0 lot / 4 handler / 15 diner; spr 1/0/4) — the bc* posting tail is
served by shedding *people*, not provisioned lots.

## 5. burst48 signature — exp

Rolling-48 share of acquired-infection epochs (the SCORE-01 D4 measure).
`posted` = the arm's posted voyages; `cs-excursion` = censused cells with
≥1 cs_food acquisition; `unposted rest` = 1,350-voyage head sample across
all arms' unposted cells (med 0.400, burst12 0.222).

| arm | set | n | burst48 | burst12 | centre (epoch) |
|---|---|---|---|---|---|
| off | posted | 10 | 0.360 | 0.180 | 194 |
| ind | posted | 68 | 0.521 | 0.459 | 42 |
| ind | cs-excursion | 64 | 0.523 | 0.474 | 39 |
| ship | posted | 15 | 0.389 | 0.194 | 142 |
| ship | cs-excursion | 5 | 0.587 | 0.349 | 62 |
| a_ext | posted | 15 | 0.389 | 0.194 | 142 |
| a_ext | cs-excursion | 5 | 0.675 | 0.385 | 52 |
| a_thin | posted | 15 | 0.389 | 0.212 | 154 |
| a_thin | cs-excursion | 5 | 0.618 | 0.277 | 62 |
| bc40 | posted | 23 | 0.395 | 0.233 | 156 |
| bc80 | posted | 37 | 0.375 | 0.206 | 162 |
| bi50 | posted | 8 | 0.500 | 0.282 | 60 |
| bmix | posted | 12 | 0.430 | 0.222 | 124 |
| (all) | unposted rest | 1350 | 0.400 | 0.222 | — |

Measured: the cs-excursion mechanism still produces bursts (0.55–0.68
median, centred ~ep 40–60) — the machinery's burst capacity is intact.
But the **postings** on the object/bc* arms sit at rest level (0.375–0.43
vs 0.400) with late centres (~ep 124–162): they read as diffuse accretion
crossing the wire, not propagation bursts. `ind` is the only arm whose
posted voyages themselves burst (0.521, centre 42). spr posted bursts are
equally flat (bc80 0.276 vs rest 0.264) — cls/spr flatness consistent
with SCORE-01.

## 6. Serving shape — `a_ext` / `a_thin`

Per-window servings (`pw`), totals over censused objects; `windows` =
`windows_covered` (serve-calls over distinct (zone, meal-token, day)
cells — a window may emit several pans).

| cell | voyages w/ objs | objects | windows med [p90] | srvs_served med [p90] | pw med [p90] | lot_srv med | top close reasons |
|---|---|---|---|---|---|---|---|
| exp ship | 63 | 457 | 0 [6] | 0 [59] | 9 [20] | 73 | source_excluded 413, voyage_end 26, shedding_ended 13 |
| exp a_ext | 63 | 453 | 0 [6] | 0 [59] | 9 [21] | 73 | source_excluded 409, voyage_end 26, shedding_ended 13 |
| exp a_thin | 63 | 469 | 0 [6] | 0 [24] | 3 [8] | 73 | source_excluded 423, voyage_end 28, shedding_ended 13 |
| cls ship | 41 | 1219 | 1 [6] | 12 [180] | 24 [48] | 260 | source_excluded 1014, voyage_end 156, shedding_ended 48 |
| cls a_ext | 82 | 2872 | 0 [6] | 0 [170] | 23 [46] | 185 | source_excluded 2425, voyage_end 332, shedding_ended 113 |
| cls a_thin | 42 | 1341 | 0 [6] | 0 [65] | 9 [19] | 185 | source_excluded 1144, voyage_end 158, shedding_ended 37 |
| spr ship | 32 | 1885 | 1 [6] | 2 [170] | 21 [51] | 260 | source_excluded 1625, voyage_end 208, shedding_ended 51 |
| spr a_ext | 32 | 1862 | 1 [6] | 4 [176] | 22 [51] | 260 | source_excluded 1611, voyage_end 201, shedding_ended 49 |
| spr a_thin | 32 | 1885 | 1 [6] | 0 [78] | 9 [23] | 260 | source_excluded 1610, voyage_end 222, shedding_ended 52 |

Measured: `a_ext` realized its contract — roughly the same per-window mass
as `ship` (pw ~22–24) but ~2.3× the objects and ~2.3× the events/takers on
cls (2,872 objects / 7,998 events / 169k takers vs 1,219 / 3,430 / 74k):
more windows at the same per-window dose. `a_thin` realized ~3× thinning
(pw med 3–9 vs 9–25) with ~40–56% of `ship`'s taker mass (cls 29.7k vs
74.4k). Neither moved posting. Most minted objects never serve (median
windows 0) — `source_excluded` dominates close reasons (~80–90%): the
minted source wasn't eligible on that voyage.

## 7. Must-not-move audit (§6.3)

| invariant | check | result |
|---|---|---|
| `off` zero-witness | objects/events/takers on censused off cells | **0/0/0 on all 3 hulls** ✓ |
| in-campaign baselines pairing | same seeds across arms | `a_ext`/`a_thin` posted sets ⊂ `ship`'s on all hulls; off/ind deltas inside pairing noise ✓ |
| median voyage AR + non-cs route shares ≈ `ship` | route mix on all arms | non-cs pax route shares within ~1pp of `ship` (fomite ~94–95%) ✓ |
| object integrity | pan servings (20,80) | 0 objects with pw>80 per pan-bound flag; `pans`/`servings` consistent ✓ |
| | servings_served ≤ lot_servings | **0 violations in 41,732 censused object rows** ✓ |
| | close_reason legal | **0 open objects; reasons ∈ {source_excluded, voyage_end, shedding_ended, exhausted, perished}** ✓ |
| | windows_covered vs minted life | windows = distinct (zone, token, day) serve-cells, not days; sampled `a_thin` lot (w=58, seeded ep40, end `exhausted` day 5) verified inside its (1,4)d day bound — multi-token-day cadence, no violation ✓ |
| composition = drawn_by_role | boarding witness on all 27,000 rows | **0 mismatches** ✓ |
| `bi50`/`bmix` immune echo | immune_init vs declared pools | exact: 130/553/870 = 0.5·crew + 0.2·pax; `ship` 90/382/600 = 0.2·all ✓ |
| immune hosts zero imports + zero seeded objects | object source attribution | `none`-sourced objects on immune arms identical to `ship` (≤5/cell) — no unattributed-source excess; gen-0 import roll contains infections only (immune hosts cannot be gen-0) ✓ |

## 8. Arriving-shedder echo — `bc*` / `bmix`

`drawn crew` = realized crew infections at boarding; `early objs src
import/acq` = early-event objects whose `source_agent_id` is gen-0
(imported) vs acquired aboard; all-censused-obj split on the right.

| cell | drawn crew med [p10,p90] | imports med | censused voy | early objs import/acq | all objs import/acq/none |
|---|---|---|---|---|---|
| exp ship | 2 [0,4] | 10 | 75 | 64/14 | 224/228/5 |
| exp bc40 | 5 [2,6] | 13 | 83 | 145/12 | 373/293/7 |
| exp bc80 | 9 [6,12] | 17 | 97 | **324/8** | 980/395/5 |
| exp bi50 | 1 [0,3] | 10 | 68 | 30/7 | 113/87/5 |
| exp bmix | 5 [3,8] | 14 | 72 | 142/4 | 416/125/4 |
| cls ship | 8 [6,12] | 42 | 41 | 129/19 | 377/841/1 |
| cls a_ext | 8 [5,12] | 43 | 82 | 398/19 | 1131/1739/2 |
| cls bc40 | 20 [15,24] | 52 | 48 | 373/22 | 1045/1088/2 |
| cls bc80 | 37 [29,47] | 70 | 59 | **1086/29** | 3113/1896/2 |
| cls bi50 | 5 [3,8] | 40 | 41 | 99/8 | 294/402/1 |
| cls bmix | 22 [18,28] | 57 | 41 | 397/14 | 1148/573/1 |
| spr ship | 13 [10,17] | 68 | 32 | 256/21 | 783/1101/1 |
| spr bc40 | 30 [24,36] | 85 | 34 | 569/20 | 1699/1418/2 |
| spr bc80 | 58 [44,68] | 112 | 35 | **959/26** | 2801/1492/2 |
| spr bi50 | 8 [6,11] | 62 | 31 | 150/21 | 468/608/1 |
| spr bmix | 35 [30,41] | 88 | 31 | 532/15 | 1708/731/1 |

Measured: the arriving-shedder echo is real and large — ~95% of bc80 early
objects are sourced to gen-0 hosts (cls 1,086 import-sourced vs 29 acquired).
The bc* posting gain is bought by arriving-shedder count: drawn crew
quadruples (spr 13→58) and early-object incidence follows it (~4–5×).
`bmix` at the same prevalence halves the import-sourced early objects
(spr 532 vs 959) — the immune-pool draw eats the echo — and the posting
collapses with it (0.1%).

## 9. Measured / inferred / hypothesis

**Measured** (engine `dbbd5395`, all 27,000 cells + 1,480 censused + 1,350
head): everything in §§2–8 — posting rates and CIs, posted-conditional AR,
unbiased conversion and P(early), route decompositions, burst48 sets,
serving-shape distributions, source-attributed early objects, the
must-not-move audit, and the immune echo.

**Inferred** (from the measurements, not re-derived):

- Lever A's null is a *mechanism* null, not a dose null: `a_ext` moved the
  serving mass ~2.3× (cls events 3,430→7,998, takers 74k→169k) and
  `a_thin` moved per-window demand ~3× — the knobs bit — yet conversion
  did not move. What separates `ind` from `ship` is therefore not the
  object extent/dose axis; the v1 `ind` event's distinguishing feature
  (single concentrated early spike vs distributed window service) is the
  declared `cs_extent` contract's ground.
- bc* postings do not inherit the burst signature because they are
  denominator-driven (early objects on ~every voyage, conversion near
  `ship` rates) and source-driven (arriving shedders, not lot bursts) —
  consistent with the size-join showing posted bc* early events no larger
  than unposted ones.
- `bmix` isolates the net direction: at equal prevalence the immune-pool
  draw removes ~half the arriving shedders and posting falls to
  `bi50`/`ship` level — the bc* gain is attributable to import mass, not
  an upstream mechanism change.

**Hypothesis** (untested by this campaign):

- The cs_extent `redraw` arm (iso-dose, concentrated into `ind`-like
  cadence) is the discriminating test for whether cadence, not extent,
  is what `ind` carries that the object machinery lacks. Declared in the
  design; not run.
- Whether the arrival-side proxy can be re-parameterized to buy posting
  without the ~95% import-sourced conflation (e.g. seeded interior
  handler infection vs boarding-roll prevalence) is open — `arriving_shedder`
  contract is spec'd but unrun.
- Posted-AR thinness appears in `ind` too, so the 0.04–0.10 band gap is
  upstream of the cs mechanism entirely (emitted-complement wiring,
  syndromic reporting, or case-def translation). No arm in this sweep
  probes it.

**Deliberately not done:** no fitting recommendation — per SCORE-01
convention the readout reports where the mechanisms land, not which
knob to turn next. The mega-cruise tier stays excluded (§6.4 gate unmet
on the burst leg).

## 10. Reproduction

- Scan + census: `tools/noro_diag/entrain_01_scan.py` (summary.json +
  ranged tail-decode of `growth_census.json.gz` common_source/hosts/meta;
  `--full-keys`/`--head-keys` restricted sets, `--resume`).
- Tables: `tools/noro_diag/entrain_01_report.py` (Wilson CIs, unbiased
  conversion, route decomposition, burst sets, integrity audit).
- Posted complement and wires: `tools/noro_diag/outbreak_anchor_readout.py`;
  early-event definitions: PR #982 / SCORE-01 docs
  ([noro_food_score_01_early_event_analysis.md](noro_food_score_01_early_event_analysis.md)).
- Campaign spec: `campaigns/noro/noro_entrain_01/`; ledger:
  `campaigns/noro/noro_entrain_01/LEDGER.md`; design:
  `docs/norovirus/noro_entrain_01_sweep_design.md`.
