# PROVISIONED-SOURCE-01 — provisioned-source mechanism design (frozen contract)

**Status: frozen design — declared before implementation.** The contract
below is what the implementation leg builds against; any post-landing
change goes in a ledger entry that names what changed and why. This is
a mechanism contract, not an evaluation design — the noro-driven eval
is `docs/norovirus/noro_provisioned_source_01_sweep_design.md`;
ledger entry `docs/ledger/PROVISIONED-SOURCE-01.md`.

**Branch:** off `origin/main` at `f7bbec40` (merge of #1001,
NORO-HULL-SCALE-01). Engine references below are line numbers at that
SHA on `engines/transmission_core.py`.

## 0. The mechanism

The shipped `lot_mode: "object"` voyage gate is **fiat**: one Bernoulli
on a per-voyage drawn `lot_object_probability` decides whether the
voyage carries a contaminated lot at all, then a geometric
`extra_lot_probability` tail decides how many (`_cs_plan_objects`
≈:12538). Nothing upstream of the hull produces that number — the rate
is a dial, not a supply chain. The physically honest statement (his
words): *a contaminated lot coming on board from a warehouse at some
defined rate*. Provisioning is platform-neutral — a cruise embarkation
port, an airport caterer, an institution's commissary are all
`provisioning source` configs; cruises are the first consumer.

PROVISIONED-SOURCE-01 replaces the fiat gate with a **derived draw**:
every voyage provisions `N_lots` lots — one per (served food-service
venue, item line) station the platform's dining footprint defines —
and each lot is independently contaminated with upstream prevalence
`q_source`. Contaminated lots mint `provisioned_lot` objects; clean
lots are uninteresting food and mint nothing. Supply-side quantities
(`N_lots`, `q_source`) are the mechanism's interface; everything
downstream of the contaminated lot — realization, service, dose — is
the shipped object machinery unchanged.

Worker-seeded objects (`ill_handler`/`ill_diner`) are untouched: they
are already mechanistic — live-shedding crew arriving under the
boarding-prevalence channel seed handler/diner spans through the
shipped eligibility read (ENTRAIN-01: ~95% of early objects
import-sourced). The two sources mint through one object grammar and
one census; this contract changes only the provisioned_lot mint.

## 1. Config schema

### 1.1 Engine block (per-arm override surface)

```json
"transmission": {
  "common_source": {
    "lot_mint_model": "provisioned_source" | "fiat",
    "provisioned_source": {
      "source_id": "<provisioning-source registry key>",
      "q_source": <scalar | [lo, hi]>
    }
  }
}
```

- `lot_mint_model` — `"provisioned_source"` is the shipped **default
  once the mechanism lands** (standing rule: the better mechanism
  ships default-ON); `"fiat"` is the labelled baseline mode and draws
  the shipped `lot_object_probability` + `extra_lot_probability`
  sequence verbatim — bit-identical to pre-mechanism main and to every
  landed object-arm cell (`ship`/`mint`/rung arms of SHAPES-01 and
  MINT-RATE-01). Only meaningful under `lot_mode: "object"`; the
  `"independent"` and `"off"` modes ignore it.
- `q_source` — upstream contamination prevalence at the provisioning
  source, drawn once per voyage on the common-source stream at the
  lot-rate draw position (scalar or `[lo, hi]` spec, same grammar as
  every `_COMMON_SOURCE_SPECS` constant). **Hull-invariant by
  construction** — the supply chain does not know which ship it feeds.
  Declared rung intervals are arm configuration (the MINT-RATE-01
  scalar-rung precedent), not provenance-registered constants; the
  *shipped default* interval is a real constant and registers in
  `parameter_provenance_register.md` at Grade C when the
  implementation leg lands it.
- `source_id` — scenario covariate naming the provisioning source
  (§1.3). Resolved to a declared `q_source` interval through the
  registry; an explicit `q_source` in the block wins over the registry
  value (that is how rung arms express).

Under `"fiat"`, `lot_object_probability` / `extra_lot_probability`
keep their shipped semantics and the `provisioned_source` block is
inert. Under `"provisioned_source"` those two keys are unread —
the census gate (§4) makes a missed mode switch loud.

`lot_posture_coupling` stays `false` under both models: upstream
contamination is upstream of galley practice; the source-side
covariate is `source_id`, not `food_safety_posture`. Declared —
the mechanism does not re-arm posture on the lot arm.

### 1.2 N_lots — the station census (derived, not configured)

`N_lots` is **not** a config constant. It is derived at the same
scheduling point as `_cs_plan_objects` (the first armed epoch, when
every served window is enumerable):

```
stations       = { (zone, item) : zone ∈ served dining venues,
                                  item ∈ COMMON_SOURCE_LOT_ITEM_LINES }
N_lots         = |stations| = (# dining venues with ≥1 served meal
                               window in the embarkation span) × 7
```

The shipped grammar already asserts this census: `max_objects =
len(served_zones) × len(COMMON_SOURCE_LOT_ITEM_LINES)` (≈:12569) is
the degenerate-config bound "a voyage cannot carry more distinct
provisioned lots than (zone, item-line) stations exist to bind them."
PROVISIONED-SOURCE-01 makes the bound the *model*: each station is one
lot provisioned at embarkation (consistent with
`embarkation_lot_window_days` — the lot boards inside the embarkation
window; mid-voyage restock is outside the shipped binding semantics
either way). Galley-only zones self-filter as today — a lot is only a
station if its venue can serve it.

Resolved per platform from `data/platforms/<p>/spatial_layout.json`
(the venue data the configs already carry — no provisioning block
exists in any platform config and none is needed):

| platform | served Dining zones (galley zones excluded) | N_lots |
|---|---|---|
| `expedition_cruise_450` | 3 (MainDining, CasualDining, CrewMess) | 21 |
| `classic_cruise_1900` | 5 (2×MDR, LidoBuffet, Specialty, CrewMess) | 35 |
| `spirit_cruise_3000` | 9 (2×MDR, 2×buffet, 3×specialty, 2×crew_mess) | 63 |
| `mega_cruise_5000` | 10 (3×buffet, 2×MDR, 3×specialty, 2×crew_mess — the 3 `galley`-service zones never serve) | 70 |

**Rejected alternative, recorded:** a consumption-throughput census
(`N_lots = complement × meals/day × days / E[lot_servings]` ≈
130/551/865/2019) was the other candidate. Rejected because (a) no
platform config carries a restock cadence or per-voyage provisioning
count — that N would be invented, not derived; (b) it requires
multi-object-per-station semantics the shipped grammar's own bound
caps out — a bigger mechanism change than the gate replacement; (c) it
*moves* the hull-free prediction: required objects are not ∝
complement (exp needs ~2.7× cls/spr per capita), so throughput-N
splits the admissible region on exp while station-N does not (§5). If
the eval's hull-free claim fails, throughput-N is the fallback
derivation to revisit.

### 1.3 Provisioning-source registry (the port covariate)

New data file the implementation leg adds:
`data/config/provisioning_sources.json`

```json
{
  "sources": {
    "<source_id>": {
      "q_source": [lo, hi],
      "platform_types": ["cruise", ...],
      "evidence": "declared Grade C — pending sourcing leg",
      "notes": "<what this source id stands for>"
    }
  }
}
```

- `source_id` is a **scenario covariate** — the embarkation port (or
  airport caterer, institutional commissary) the voyage provisions
  from. A scenario that names no `source_id` resolves the shipped
  default source.
- Port → q mapping is declared-interval, Grade C, until the sourcing
  leg lands. Source types the leg consults (named, no citations
  invented): FDA/state food-facility inspection records, MMWR
  foodborne-outbreak surveillance summaries, VSP supplier/provisioning
  posture data, EU RASFF notifications — per platform type.
- The registry is the extension seam for non-cruise platforms: an
  airport scenario declares a caterer `source_id`; the engine's N_lots
  census reads that platform's food-service venue tree the same way.

## 2. RNG / stream contract

All draws stay on the dedicated common-source stream
(`_COMMON_SOURCE_STREAM_KEY`, ≈:1627). The contract pins the layout
because the eval's nested-draw integrity gates read it verbatim.

Under `lot_mint_model: "provisioned_source"`, per pathogen per voyage:

1. **Rate draw** — `_cs_draw_voyage_rates` composes the lot arm's rate
   names as `("q_source",)` in place of fiat's
   `("lot_object_probability", "extra_lot_probability")`: q sits at the
   draw position `lot_object_probability` occupied, before the
   handler/diner draws. Declared consequence: handler/diner rate draws
   shift one stream position earlier vs fiat at shared seeds (one
   fewer lot-rate draw). Scalar `q_source` specs consume zero uniforms
   (the `lo == hi` early return) — all scalar-rung arms share one
   rate-stream layout, exactly the MINT-RATE-01 scalar-rung precedent.
2. **Station census draw** — at the `_cs_plan_objects` scheduling
   point, one uniform `u_s` per station in canonical station order
   (served-zone order as `_cs_dining_zones` resolves it, ×
   `COMMON_SOURCE_LOT_ITEM_LINES` order). Station `s` is contaminated
   iff `u_s < q_source` (the voyage-drawn value).
   `E[objects] = N_lots · q` exactly; the count is Binomial(N, q).
3. **Object realization** — each contaminated station, in station
   order, mints one `provisioned_lot` object through the shipped
   realization path (`_cs_realize_lot_object` ≈:12585) **minus** the
   zone/item draws: the station binds `(zone, item)` directly. The
   remaining minted state — embarkation day window, `lot_servings`,
   titre (the `_cs_titre_spec("provisioned_lot")` band under
   `two_mode`), `item_take_share`, `lot_shelf_life_days`, strain mix —
   draws exactly as today, on the shared stream, in draw order.
   Realization draws are conditional on contamination — downstream
   non-lot draws shift between rungs wherever the contaminated sets
   differ (declared; voyage-level pairing holds, interior pairing does
   not — the §3.4 convention MINT-RATE-01 declared for scalar rungs).

**Nested draws across q rungs.** Because every scalar rung compares
the *same* per-station uniforms against a larger threshold, the
contaminated-station sets nest exactly: station sets at
q_a ⊆ q_b whenever q_a ≤ q_b, per seed, per hull, per pathogen.
That is the eval campaign's stream-layout integrity gate — the direct
analog of MINT-RATE-01's nested-mint-sets gate on the fiat gate.

**Rejected draw scheme, recorded:** `rng.binomial(N, q)` — numpy's
sampler switches algorithms (inversion vs BTPE) and consumes a
*variable* number of uniforms per call, so the stream layout becomes
q-dependent and no nested-set gate exists. Per-station Bernoulli is
the integrity-gate-preserving choice and is the honest physical read
(lots are independent deliveries).

**`"fiat"` baseline:** the shipped sequence verbatim — voyage Bernoulli
on `lot_object_probability`, geometric `extra_lot_probability` tail,
uniform zone + item draws per realized object — bit-identical to
pre-mechanism main at shared seeds. This is what makes `ship`/`mint`
arm bridges to SHAPES-01 cells valid.

## 3. Witness fields

Existing object rows already carry the census split the eval needs:
`source_kind ∈ {"provisioned_lot", "ill_handler", "ill_diner"}` on
every closed object row (`_cs_close_object` ≈:13060) — the
worker-vs-provisioned decomposition needs no new per-kind field. The
mechanism adds:

- **Voyage block** `common_source.provisioned_source` (census +
  summary): `{source_id, q_source_drawn, n_stations, n_contaminated}` —
  the q echo, the resolved N_lots, and the realized contamination
  count, per armed pathogen.
- **Object row** `provisioned_source_id` on `provisioned_lot` rows
  (null on agent objects): which provisioning source minted the lot —
  the per-object source tag the port-covariate analysis reads. The
  object's `(zone, item_label)` already identifies its station.
- **Summary block** `reported_cases_by_dominant_route` — the named gap
  from NORO-HULL-SCALE-01 §1/§7, required for the eval's
  posted-vs-acquired decomposition. **Exact semantics:** for each
  agent counted in `cumulative_reported_cases` (the
  `ever_reported_ids` rule — first symptomatic true-positive report,
  `update_ever_reported_ids` ≈orchestrator_init:1038), increment the
  bucket of the dominant route attributed to that agent's established
  infection episode — the same dominant-route rule
  `infections_by_dominant_route` applies (`update_route_attribution`
  ≈orchestrator_init:1018: argmax over `acquired_particles_by_route`
  at establishment, `event.pathway` fallback when no acquired ledger).
  Reported agents whose infection is a boarding import (no
  establishing event) bucket under `"imported"`. Shape mirrors the
  cumulative fields:
  `{"passenger": {<route>: n, ..., "imported": n},
    "crew": {<route>: n, ..., "imported": n}}`, with
  `sum(values) == cumulative_reported_cases_{passenger,crew}` per
  role. One count per reported case, never double-counted.

## 4. Integrity gates (contract-level, eval gates extend them)

1. **Baseline bit-identity** — `"fiat"` cells are bit-identical to
   pre-mechanism main at shared seeds on every field (the mode draws
   the identical stream sequence and mints through the identical
   realization path).
2. **Nesting** — contaminated-station sets nest in q order across
   scalar rungs at shared seeds (§2). A voyage/station contaminated at
   a lower rung but absent at a higher one is a stream-layout defect.
3. **Declared expectation** — realized contaminated-station counts
   track Binomial(N_lots, q_drawn) within binomial tolerance, and
   realized `provisioned_lot` object counts track N·q per hull
   (E[objects] table §5). A rung minting at fiat-gate rates says the
   mode switch didn't reach the engine.
4. **Station witness** — every `provisioned_lot` object's
   `(zone, item_label)` is a member of the voyage's station census and
   was drawn contaminated; `n_stations` echoes the platform's resolved
   N_lots (exp 21, cls 35, spr 63, mega 70 on the cruise hulls).
5. **Worker/diner arms untouched** — handler/diner span mechanics,
   eligibility reads and object rows unchanged modulo the declared
   §2-1 stream-position shift; their census counts move only through
   that shift, never semantically.

## 5. Declared expectations and the hull-free-q claim

Measured inputs (MINT-RATE-01 design §1/§3.3, SHAPES-01 readout §7 —
do not re-derive): required posting marginal 0.4–0.9 pp per hull;
measured per-hull `P(post | ≥1 lot object)` ≈ 0.93 / 0.58 / 0.36
exp→cls→spr, hull-flat per-object yield ~30–37 cs cases, ~104 takers
per object; MINT-RATE-01 in-band gate windows exp [0.004, 0.010],
cls [0.007, 0.015], spr [0.011, 0.025] → required E[objects]
(presence × 1.163) ≈ [0.0047, 0.0116] / [0.0081, 0.0174] /
[0.0128, 0.029]; mega extrapolation p* ≈ 0.09–0.25 → E[objects]
≈ 0.105–0.29.

Under the mechanism, `E[objects] = N·q` and the thin-rate posting
marginal ≈ `100 · N·q · P(post | ≥1)`:

| platform | N | required q for the D1 band | rung landing in-band |
|---|---|---|---|
| exp | 21 | ≈ [2.0e-4, 4.6e-4] | `q03` centre |
| cls | 35 | ≈ [2.0e-4, 4.4e-4] | `q03` centre |
| spr | 63 | ≈ [1.8e-4, 4.0e-4] | `q03` centre |
| mega | 70 | ≈ [1.5e-3, 4.1e-3] (P1 0.05–0.15) | `q15`–`q30` region |

**THE TESTABLE CLAIM (the campaign's headline):** the venue-station
census scales almost exactly like the measured required-object scale —
21 : 35 : 63 vs 0.008 : 0.012 : 0.019 (ratios ≈ 1 : 1.6 : 2.4) — so a
single `q_source` puts every cruise hull in-band simultaneously. The
admissible region becomes **hull-free in q**: one upstream prevalence
describes the whole fleet, and the fiat model's hull-parametrized
p*(hull) ladder is revealed as `p*(hull) ≈ N(hull)·q` — hull scaling
was the supply chain's venue footprint, not a property of the
mechanism. Frozen prediction: `q_source ≈ 3e-4` lands exp ≈ +0.59 pp,
cls ≈ +0.61 pp, spr ≈ +0.68 pp — all inside the 0.4–0.9 band. The
campaign measures the realized marginals; the claim survives if ≥1
rung is simultaneously in-band on all three small hulls, and is
*quantified* by how wide the common-q window is.

**Mega expectation.** `N_mega = 70` lands E[objects] ≈ 0.02 at the
common q — a typical voyage carries no contaminated lot, and the
~10 served venues do not rescue mega the way a ∝complement census
would. Its in-band q extrapolates to ≈ [1.5e-3, 4.1e-3] — ~10× the
small-hull band — *unless* multi-lot voyages lift P(post|voyage)
above the single-lot line faster than the extrapolation assumes
(Binomial(70, q) puts ≥2-lot voyages within reach from `q08` up).
Whether mega's measured window lands at the extrapolation, below it
(multi-lot lift), or stays unreachable (per-object yield still can't
fill a 7,000-agent wire) is the campaign's second headline read —
mega joins the hull set explicitly because the mechanism now derives
its rate rather than extrapolating a fiat gate it could never reach.

## 6. Non-goals

No engine code in this PR; no `q_source` sourcing leg (source types
named, Grade C stands); no restock/mid-voyage provisioning cadence;
no multi-object-per-station semantics; no port-itinerary coupling
(`source_id` is a scenario label, not a routed itinerary leg); no
absolute dose figures anywhere (dose ledger withdrawn —
positions-on-curve only); no changes to handler/diner span mechanics
beyond the declared stream-position consequence.
