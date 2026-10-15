# NORO-HULL-SCALE-01 — hull-scaling decomposition + mega arming audit

> **Status:** Measured (analysis leg; census re-parse of landed
> NORO-FOOD-SHAPES-01 zips + static mega audit + 3-voyage local mega
> smoke at engine `49e1993b`, no Batch). Substrate:
> `fl_{exp,cls,spr}_12d_scr_mint` first-500-key re-parse (1,500 cells)
> + `fl_{exp,cls,spr}_12d_scr_ind` first-300-key re-parse (900 cells)
> via `tools/noro_diag/hull_scale_01_scan.py` — ranged summary read +
> rolling-tail census decode; distinct diners from event `taker_ids`.
> Mega smoke: `campaigns/noro/hull_scale_01/mega_smoke_manifest.json`
> (shipped-rung mega tier + `lot_object_probability` forced to 0.95),
> 3 voyages × 120 epochs local.

## 0. The question

SHAPES-01 measured P(post | minted) ≈ 0.93 / 0.58 / 0.36 exp→cls→spr,
and MINT-RATE-01 froze in-band D1 mint-rate windows that shift up
~2×/step: exp [0.004, 0.010], cls [0.007, 0.015], spr [0.011, 0.025].
This leg decomposes the posting chain link by link per hull —

    object minted → pans served / diners covered → cases generated
    → reported → posted (3%-of-complement A9 wire)

— to name which link carries the compression, and audits whether the
common-source lot machinery can arm on `mega_cruise_5000` at all.

The four discriminating hypotheses frozen in the brief:

* **(a) coverage dilution** — a lot serves a similar absolute number
  of pans/diners on every hull, so the attack fraction falls ∝
  complement.
* **(b) near-constant case numerator** — per-object case counts are
  near-constant in absolute terms; dilution only because the
  posting/reporting gate is rate-triggered.
* **(c) report→post differs by hull** — staffing, sick-call
  propensity, venue assignment, trigger semantics.
* **(d) per-object exposure scales with hull** — more pans per lot on
  bigger ships; compression lives elsewhere.

## 1. Measurability map

| Link | Field(s) | In landed zips? |
|---|---|---|
| objects minted | census `common_source.objects[]` (arm, seeded_epoch, lot_servings, lot_titre) | yes |
| pans served | census `common_source.events[]` linked by `object_id` (servings_taken) | yes |
| diners covered | union of event `taker_ids` per object/voyage | yes (distinct, per-object) |
| cases generated | summary `infections_by_dominant_route["common_source_food"]` | yes (dominant-route counts only) |
| ever-ill / symptomatic | summary `cumulative_ever_ill_{passenger,crew}` | yes (all-routes total, not per-route) |
| reported | summary `cumulative_reported_cases_{passenger,crew}` | yes (all-routes total) |
| posted | derived ARs ≥ 3% complement | yes |

**Named missing field (not built):** per-route split of
`ever_ill`/`reported` — the reported counts are all-route totals, so
the marginal cs-driven reported count on a minted voyage is inferred
against the same-arm unminted counterfactual, not read directly. A
`reported_cases_by_dominant_route` summary block would close it.

## 2. The chain, measured per hull (`mint` arm)

Minted-voyage census (scan of first 500 keys/arm; mint rate ~8.4%
reproduces 82–84/1,000 on all three hulls):

| link (median per minted voyage) | exp (n=41) | cls (n=41) | spr (n=41) |
|---|---|---|---|
| lot objects / voyage | 1.10 mean | 1.20 mean | 1.20 mean |
| diners per lot object | 81 | 89 | 89 |
| takers per lot object | 104 | 103 | 103 |
| pans per lot object | 12 | 7 | 8 |
| biggest pan (servings) | 17 | 30 | 20 |
| cs_food cases / voyage | 30 | 32 | 37 |
| ever_ill / voyage | 23 | 56 | 69 |
| reported pax+crew / voyage | 11 | 43 | 56 |
| posted | 90.2% | 63.4% | 36.6% |

Unminted same-arm counterfactual (n=459/hull): reported pax med
2 / 14 / 22, ever_ill med 3 / 26 / 44, ev_takers med 0 / 2,037 /
3,326, cs_food med 0 everywhere — the handler/diner object background
covers hundreds of diners on big hulls but yields ~zero attributed
cases: coverage is not the gate; dose per serving is.

Posted-vs-unposted split inside minted cells shows the gate sits on
the case/diner tail: exp posted n=37 cs_food med 32 / diners 88 /
rep 19 vs unposted n=4 12 / 42 / 7.5; cls posted n=26 82.5 / 242 /
66 vs unposted n=15 17 / 49 / 31; spr posted n=15 60 / 204 / 89 vs
unposted n=26 20.5 / 67 / 53.

### The cross-wire test (decisive instrument)

For each hull's minted voyages, evaluate the 3%-of-complement posting
predicate under *every* hull's complement:

| minted data \ wire | exp wire | cls wire | spr wire |
|---|---|---|---|
| exp (n=41) | 0.90 | 0.17 | 0.02 |
| cls (n=41) | 1.00 | 0.63 | 0.39 |
| spr (n=41) | 1.00 | 0.71 | 0.37 |

cls voyages under the spr wire post at 0.39 vs measured spr
0.37 — the wire alone reproduces essentially all of the cls→spr
step; spr's own voyages are mildly stronger (37 vs 32 median cases)
but the gate is what flips the answer. The residual exp→cls gap
(exp data under cls wire 0.17 vs cls actual 0.63) is the
second-order hull-scaling term: mild per-object yield growth
(30→32→37) plus the bigger-hull background epidemic contributing
more non-cs reported cases toward the wire (unminted rep_pax
2→14→22; minted-voyage rep_pax 6→32→40).

### The `ind` (v1) chain, same decomposition

| posted-voyage median | exp | cls | spr |
|---|---|---|---|
| v1 events | 7 | 26 | 100 |
| v1 takers | 80 | 837 | 2,474 |
| v1 diners | 74 | 628 | 1,477 |
| cs_food cases | 16 | 51 | 57 |

Same physics on the v1 arm: the coverage required to post grows fast
with hull while the case yield needed grows slower than complement
(background reported fills part of the wire).

## 3. Which link carries the compression — verdict

**Primary carrier: the reported→posted link — the absolute-count A9
wire (≥3% of complement in reported cases) applied to a hull-flat
per-minted-voyage cs yield.** Hypothesis (b) holds: a minted voyage's
case output is titre-limited, not complement-scaled — med ~30 cs_food
cases on exp and cls alike, ~80–110 diners per object, ~104 servings
per object — while the wire grows 10→41→63 pax cases / 5→18→27 crew.
P(post|minted) = P(yield + background ≥ wire) falls 0.93→0.58→0.36.

Consequently the admissible mint-rate window scales mechanically as
p* ∝ target/P(post|minted): predicted step factors ×1.0 / ×1.6 /
×2.6 vs measured window midpoints rising ≈ ×1.6 / ×1.6 — the P(post)
compression *is* the window shift.

**Runner-ups, quantified:**

* (d) coverage scaling is real but small: diners/object 81→89→89,
  takers ~103 flat, pans 12→7→8 — ~1.1×/step against the 4.2×/1.6×
  complement factors. Per-object case yield rises mildly
  (30→32→37), opposite in sign to the compression.
* (a) "dilution" is correct but locates at the rate-normalized gate,
  not coverage — diners per object do *not* dilute; the lot is
  served to ~100 takers on every hull.
* (c) report chain is hull-invariant (same 3% predicate, same
  sick-call machinery); the wire's complement scaling *is* the hull
  difference, not semantics.
* Offset: the non-cs background epidemic's reported counts grow with
  hull (unminted rep_pax med 2→14→22), so the marginal cs yield
  needed to post grows *sublinearly* with the wire — the reason the
  compression is ~2×/step rather than the full 4.2×/1.6× complement
  factor.

### Countervailing per-object-efficacy mechanisms (user hypotheses e–g)

Three upstream-efficacy candidates were measured explicitly; each
would raise cases-per-minted-object and push the required mint rate
DOWN — opposite in sign to the measured upward-shifting window — so
if confirmed they would be the countervailing force keeping the
compression below the full complement factor:

| mechanism | exp | cls | spr | verdict |
|---|---|---|---|---|
| (e) larger lots upstream: objects/voyage | 1.10 | 1.20 | 1.20 | no consolidation — flat |
| (e) pans per object | 12 | 7 | 8 | falls, not rises |
| (e) lot_servings (lot size) | 104 | 104 | 104 | hull-flat by draw |
| (f) RTE fraction in minted mix | uniform 7-label mix | uniform | uniform | hull-invariant by construction (uniform draw, :12601) — realized mix confirms |
| (g) pan consumption: servings_served / lot_servings | ~100% | ~100% | ~100% | flat — the lot is fully consumed on every hull |
| (g) take-fraction per pan (servings_taken/cohort_size, med) | 0.33 | 0.32 | 0.31 | flat (minted-key supplement, n=45/49/49 objects) |
| (g) per-serving dose on linked pans (med) | 1.7e5 | 2.2e5 | 1.9e5 | flat — titre-driven, not hull-driven |

**All three are measured flat-to-absent in the lot chain.** Cases
per minted voyage (30→32→37, alongside posted-fraction 90→63→37)
rise only ~10% per step — far too weak to counter the complement
scaling. The real countervailing term is the background epidemic's
reported-case growth, quantified above: it fills an increasing share
of the wire, so the marginal cs yield needed falls relative to a
pure wire/yield law.

## 4. The physical explanation

The mint rate stands in for **contaminated lots arriving per voyage**.
A mint is per-voyage Bernoulli; a lot is provisioned to ONE zone, one
item line, `lot_servings` logU(30,600) and a `two_mode` titre draw —
all hull-independent quantities. The scored quantity, posting, is a
*rate* of the whole complement. So a hull-parametrized p*(hull) IS
the right compact statement for exp/cls/spr — the gate is p ∝
complement × (target posting fraction) / (hull-flat yield). But the
right frame for mechanism work is not "redial p per hull": if lot
arrivals physically scale with provisioning throughput (galleys,
venue count), the honest knob is E[lots per voyage] provisioned
per-venue — which on big hulls raises BOTH the mint frequency and the
diner coverage per voyage in the same mechanism.

## 5. Mega arming audit

**Verdict: the machinery ARMS on mega — engine-default reachable, and
confirmed firing in local smoke.** The blockers the design docs
implied do not exist:

* `common_source_mode` defaults `"on"` when the tier carries no
  `transmission.common_source` block (`transmission_core.py` ~:3335)
  — mega tiers as-written arm the mechanism; the SHAPES-01 design's
  "objects are never armed there" line was wrong at engine level
  (omission ≠ off; it only means the shipped default gate
  U(0.001,0.02) and default modes apply).
* `norwalk_gi` ships `common_source_events.enabled: true`.
* `_cs_dining_zones` resolves from `zone_types` — mega's
  `spatial_layout.json` has 13 `type: "Dining"` zones, all carrying
  `dining_service_type` (crew_mess/mdr/buffet/specialty/galley);
  galley zones get no served cells and self-filter; the diner
  self-serve gate resolves per venue.
* Dining assignment is populated: `_crew_dining_catalog` /
  `_passenger_dining_catalog` built from those zones, meal tokens via
  `dining_meal_weights` in `voyage_config.json`.
* Provisioning path works: a `transmission.common_source` override in
  the tier `config_overrides` reaches the engine (proven by the
  forced-mint smoke below).
* Landed complement: NORO-MEGA-IMPACT-01 (`7e1b54bc`, 926 zips,
  `docs/norovirus/noro_mega_impact_01_readout.md`) already ran mega
  with common-source armed — 0/20 canary provisioned lots under the
  U(0.02,0.15) draw, 0/926 VSP posts on every arm, food lifting only
  the reach tail (max 0.746→0.810 of the crew wire). That is the
  landed mega witness; the smoke below is the machinery check at a
  forced mint. The SHAPES-01 *manifest* itself carries no mega tier,
  and the older `noro_mega_01` zips (2026-10-04) predate the
  machinery entirely.

**Local smoke (≤5 seeds, local only):** mega_cruise_5000 voyages
(n=7,000, 120 epochs, `lot_object_probability` forced 0.95), shipped
prevalence tier, seed 8000 at all three rung prevalence points:

| voyage | prevalence | provisioned_lot | cs objects | cs events | cs takers |
|---|---|---|---|---|---|---|
| 8000a | nsf29_bp25c7 | 1 — bakery, SpecRest_B, 80 srv, titre 1467, exhausted | 19 | 33 | 1,030 |
| 8000b | nsf29_bp32p5c18p5 | 1 — same realized draw | 50 | 92 | 2,198 |
| 8000c | nsf29_bp40c30 | 1 — same realized draw | 82 | 116 | 3,395 |

The 8000a voyage carried 23 cs_food cases from its 80-serving lot —
the same hull-flat ~25–30 per-lot yield band as exp/cls/spr — and did
NOT post (rep AR 0.49% pax / 0.14% crew vs wires ≥147 pax / ≥63
crew). Event/taker counts rise with prevalence because
handler/diner objects scale with the ill population; the
provisioned_lot mint is the machinery check (fires, serves,
exhausts).

## 6. Mega window extrapolation

With hull-flat per-lot yield ~25–30 cases and mega wires ≥147/≥63
reported cases (background-reported partial offset ~30–40), a single
typical lot cannot post on mega: needs ~5–6 simultaneous lots or an
extreme titre/coverage draw. Estimating P(post|minted)_mega ≈
0.05–0.15 and applying the measured scaling law
p* ∝ target/P(post|minted) off the spr edge:

    p*_mega ≈ 0.025 × (0.36 / ~0.10) ≈ 0.09–0.25

— i.e., at or above the powered `U(0.02,0.15)` arm's top. **Mega
cannot join the current mint-rate grid**: its admissible window sits
outside it (wide uncertainty; extrapolation off a 3-point law + a
3-seed smoke). The physically honest route is the mechanism leg the
scaling analysis already points at — venue-provisioned lot arrivals
(several lots per voyage on a 13-zone dining footprint) rather than a
voyage-level Bernoulli redial — which raises mint frequency and
per-voyage coverage together and plausibly lands mega inside an
admissible region.

## 7. Named gaps (instruments needed, not built)

* `reported_cases_by_dominant_route` (or an ever-ill equivalent) in
  summary.json — would make the cases→reported link direct instead of
  counterfactual-inferred.
* Per-pan `cohort_size` distribution already exists; a per-object
  `distinct_diners` counter would avoid the taker_ids union, but the
  union already works — listed only for scan cost.
