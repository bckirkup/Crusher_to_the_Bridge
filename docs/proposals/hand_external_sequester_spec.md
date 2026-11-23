> **Status:** Proposed (design PR). No field exists, no value is adopted, and
> a run without the new block must stay bit-identical to the pre-change
> engine. No epidemiological constant is added, moved, re-sourced, or tuned:
> every number quoted is either a repository constant read at its definition
> site or a measurement quoted from its ledger entry with that entry's
> `Measured at` SHA — and every dose figure in the repository remains void
> pending the norovirus refit (`docs/norovirus/norovirus_open_ledger.md` §1).

# EXTERNAL-SEQUESTER — hand-reservoir retention for acquired (non-stool) mass

The stage the 2026-11-23 TOUCH-PATCH readout converged on (D2′′ of the
hand/fomite programme). D0′ (`NORO-DOSE-LEDGER-01`) measured that ~4% of
delivered mass reaches a mouth; D2′ (`NORO-POOL-PICKUP-01`) measured that
ordinary encounters request ~0; TOUCH-PATCH (`NORO-TOUCH-PATCH-01`) fixed the
request structure and measured that requests rose — and take-off still did not
cross the gate. The binding stage moved downstream of delivery entirely, into
the hand reservoir between "mass on a susceptible's hand" and "dose at the
mouth".

## 0. Settled inputs (quoted, not re-derived)

- **`NORO-TOUCH-PATCH-01`** (`docs/ledger/NORO-TOUCH-PATCH-01.md`, measured at
  `8a698da7`, seeds 8000–8019 `classic_cruise_1900`, 288 epochs,
  `item_instances`): mechanism fired (up to 6.6M touches, 58k coincident
  deliveries, 6–2850 contaminated instances per cell); ordinary-instance
  requests rose to 0–14.6k GEC (vs ~0 baseline); non-patch delivered reached
  hands on 16/18 cold cells (up to 12.4k, seed 8014); 2/18 cold cells crossed
  the frozen Σhazard ≥ 1.1 gate (8008: 2.27, 8018: 1.39, both
  patch-dominated) — **no ignition**. Mouth dose stayed ~1–4% of delivered on
  every cell (8018: 2.25M → 26.3k; 8014: 23.8k → 301).
- **`NORO-DOSE-LEDGER-01`** (`docs/ledger/NORO-DOSE-LEDGER-01.md`, measured at
  `1f8a027c`, same 22 cells): secondaries ≈ Σhazard (182/184) — once mass
  reaches a mouth, the challenge converts at ~99%. The challenge itself is
  measured not-binding at these mouth magnitudes.
- **`NORO-HAND-CARRIAGE-01`** (`docs/ledger/NORO-HAND-CARRIAGE-01.md`, merged
  `#811`, measured `1c94de2d` + re-census `a3c76061`): the hand reservoir is
  two compartments — *accessible* (pad-surface smear: inactivation
  `U(0.61, 1.7)`/h, stripped by every wash act) and *protected* (subungual /
  crease sites a wash cannot reach: sheltered inactivation
  `U(0.01, 0.06)`/h, fills from a `logU(50, 3200)` GEC draw queued per
  propensity-fired contaminating visit and settling over `U(24, 72)` h).
  Occupancy partial vs Liu 2013 (R = 0.746).
- **Shipped mouth step** (`engines/transmission_core.py`): each pickup event
  books `contacts × f × e × hand_load`, with `contacts ~ N(2.9, 2.5)`/h
  non-eating (`N(7.7, 4.1)`/h eating), `f ~ U(0.008, 0.012)`,
  `e ~ N(0.339, 0.132)` — a ~1%/h capture of the *instantaneous* load.
- **RNG caveat (from NORO-POOL-PICKUP-01):** any arm that adds draws perturbs
  the shared stream; per-seed arm contrasts are not paired realizations —
  pooled readouts are the unit of evidence.

## 1. What is wrong with the present structure

The protected compartment's fill is gated on the dose's *origin*, not on the
compartment's function. `_replenish_hand_hygiene_cycle` queues a sequester
draw only inside a stool event, and only when `target > 0.0` — i.e., only for
a host whose own defecation carries the pathogen. A susceptible who picks mass
up from a surface, a hand, or a sanitary venue acquires **accessible-only**
load: it can never queue into the pending→protected path at all.

What that does to picked-up mass, epoch by epoch:

1. At the pickup instant the mouth takes `contacts × f × e` ≈ **~1%** of the
   instantaneous load.
2. The remainder sits accessible and dies at the pad inactivation rate
   `U(0.61, 1.7)`/h (≈ 46–82% per epoch), plus routine washes
   (`Poisson(2–8/day)` acts at ~1.5–2 log10 each) and the compliance-gated
   post-visit wash.
3. `protected` stays exactly zero for the whole carriage episode — the only
   compartment with a 24–72 h dwell is unreachable.

Net: every GEC picked up lives ~1–3 epochs and is mouthed once at ~1%. The
measured ~1–4% delivered→mouth is this arithmetic, not a magnitude shortfall —
and the mass that real carriage studies describe working into subungual sites
(Lin 2003, McNeil 2001, McGinley 1988 — the same sources the compartment is
built on) is never offered that migration because it arrived by the wrong
route.

## 2. Design principle — retention, not magnitude

Keep every rate, fraction and kernel at its shipped value and provenance. The
only change is *which mass may enter an already-measured compartment*: the
fill rule admits externally acquired load instead of gating on stool-linked
self-contamination. The compartment's content bound (`logU(50, 3200)` GEC),
settle rate (`U(24, 72)` h) and sheltered inactivation (`U(0.01, 0.06)`/h) are
all already shipped constants; the arm re-reads the sequester draw as the
compartment's **per-host capacity** (a standing site-limited reservoir —
McGinley 1988's ~10⁵ CFU subungual standing pool is a capacity, not a
per-event quantity) instead of a per-event increment. No new physical
constant is introduced; the capacity re-reading is declared, Grade C.

## 3. Mechanism

Selectors: two independent knobs, each defaulting to shipped behaviour so a
run without them is bit-identical:

- `transmission.hand_sequester_fill: "stool_only" | "any_load"` — the fill
  rule of §3.1. Applies only under `hand_reservoir_mode: "hygiene_cycle"`
  (the protected compartment exists nowhere else); under `wash_reuptake` /
  `spike_decay` it resolves but has no state to fill and must warn.
- `transmission.hand_residual_mouthing: "pickup_only" | "per_epoch"` — the
  residual mouth draw of §3.3. `"pickup_only"` is the shipped `discrete`
  behaviour; under `continuous` the integrator already mouths residual load
  so the knob is a no-op there (declared, warned).

They are separate because the canary must attribute its outcome: residual
sampling alone is measurable (~few %, §4) but must not be credited to
retention — `noro_external_sequester_01` therefore runs **two arms** per
cell (§6).

### 3.1 The fill rule

In each `hygiene_cycle` branch of `_replenish_hand`, after
`_hand_protected_decay` has split `(protected, accessible)` and decay has
applied — before routine washes and self-contact ticks — when the host's
accessible load is positive:

```text
capacity   = lazy per-(host, pathogen) draw ~ logU(50, 3200)      # drawn once
migrate    = min(max(0.0, capacity − protected − pending), accessible)
pending   += migrate
accessible −= migrate
```

`pending` then settles into `protected` at the host's already-drawn
`protected_sequester_per_hour`, exactly as shipped. Washes keep acting on the
accessible part only; `hand_load = accessible + protected` keeps the shipped
convention that queued mass is not rinse-visible until settled.

- The capacity draw is **once per host per pathogen** (lazy, like
  `hand_inactivation_rate_by_pathogen`) — a host that acquires, clears and
  re-acquires refills toward the same capacity while load lasts; protected
  drains at its sheltered rate and is topped back up only to the draw.
- `migrate` is clamped at zero: a host whose queued stool draw already
  exceeds its capacity draw migrates nothing that epoch — the capacity
  re-read bounds the *external* fill only and never pulls mass back out of
  the queue (the stool fill keeps its shipped unbounded semantics).
- The queue admits only the draw's free capacity, so mass is *relocated*,
  never created — unlike the stool path, where the draw is new source mass
  from defecation. Migration is an internal flow, not a sink (§6 audit).
- **Queue enrollment:** `_replenish_hand` early-returns when
  `target ≤ 0 and current ≤ 0`; a host whose entire load just migrated
  into `pending` would strand the queue forever — no settle, no decay,
  invisible to the mouth. Under the arm the enrollment condition gains
  `pending > 0`: a host holding queued mass keeps running
  `_hand_protected_decay` each epoch until the queue is empty, exactly as a
  shedder with a stool-queued pending does today.
- The stool-gated shedder fill is unchanged: propensity-fired visits queue
  their per-event draw exactly as shipped. A host can hold both fill
  contributions; `pending` is a queue, not a flag.

### 3.2 Where it engages

A susceptible's picked-up mass (surface pickups, emesis patch, sanitary
venue, hand-to-hand under `carriers`) lands in `hand_load` and so in
`accessible` — the arm needs no touch-point list; any path that puts mass on
the hand feeds the same fill rule. Deposits and mouth draws read
`hand_load` as shipped.

### 3.3 Residual mouth exposure under `discrete`

The frozen cells run `contamination_solver: "discrete"`, and under it the
shipped mouth step fires **only at pickup events**
(`_hand_to_mouth_dose` inside `_deliver_one_pickup`): retained load is
never re-sampled. A retention arm without residual sampling would hold the
dose for days and still mouth ~0 — the retention bound in §5 is realizable
only if the retained reservoir is re-exposed. The
`hand_residual_mouthing: "per_epoch"` arm therefore adds a residual mouth
draw under `discrete`, built entirely from shipped constants and scoped to
the same population the `continuous` solver mouths: **each susceptible
host** with positive `hand_load` books
`contacts × f × e × hand_load` through the same `_hand_to_mouth_dose`
accounting — `contacts` drawn from the shipped non-eating
`N(2.9, 2.5)`/h (eating `N(7.7, 4.1)`/h when the epoch's schedule state is
an eating venue), `f ~ U(0.008, 0.012)`, `e ~ N(0.339, 0.132)`, all
`× hours_per_epoch`. Susceptible-only matches the population
`_flow_mouth_rates` integrates on `continuous` (a shedder mouthing its own
hand adds no new infection), so the arm is solver-symmetric; it adds no
constant and changes no shipped value.

## 4. Why this and not the alternatives

- **vs mouth-touch frequency / swallow efficiency / contact fraction:** the
  per-contact product `f × e × contacts` is a sourced constants triple
  (~1%/h); moving it is constant tuning against the outcome — forbidden. The
  lever that does not touch a constant is *how long the mass stays
  mouth-reachable*.
- **vs residual-load mouthing alone (§3.3 without §3.1):** sampling the
  residual every epoch without the protected compartment mouths the same
  dying accessible load each epoch — the capture is ~1%/epoch and the load
  still clears in ~1–3 epochs, so residual sampling alone adds only a few
  percent. Retention (§3.1) is what gives the residual draw something to
  sample.
- **vs the challenge floor:** measured not-binding — D0′: once a dense
  encounter exists the challenge converts at ~99% (secondaries ≈ Σhazard,
  182/184); β-Poisson susceptibility (α = 0.111, β = 32.81) is linear at
  these doses.
- **vs D1′ (carrier redeposition):** orthogonal and parked — D1′ moves mass
  *between hands/surfaces*; this arm keeps mass on one hand *longer*. Under
  `shedders_only` a carrier does not re-deposit, so the retained mass can
  only leave via mouth / inactivation / wash — the clean isolation this arm
  wants.
- **vs doing nothing:** a ~1% capture with a ~1-day lifetime is the measured
  status quo; the question the campaign answers is whether the protected
  compartment was the missing retention structure.

## 5. Retention bound — what the arm can change (bound, not result)

Per GEC of picked-up mass, shipped constants — with two shipped semantics
the table names precisely: the protected compartment's 0.01–0.06/h is a
**leak back into accessible**, not a kill (the shipped split writes
`accessible = current − protected_post_decay`, returning decayed sheltered
mass to the rinse), and the ~0.010/h mouth capture exists on `discrete`
only through §3.3's residual draw (`continuous` has it natively):

| compartment | loss /h | mouth capture /h | expected dwell | eventual mouth share |
|---|---|---|---|---|
| accessible | 0.61–1.7 kill + washes | ~0.010 (non-eating, via §3.3) | ~0.6–1.6 h | ~1–2% |
| protected | 0.01–0.06 leak→accessible | ~0.010 (non-eating, via §3.3) | ~17–100 h | ~15–60% |

So each GEC migrated to protected converts ~15–60% to mouth over its dwell
(the leak returns the rest to accessible, where the same exposure and kill
rates apply) — an order ~10–40× the accessible conversion, bounded above by
the per-host capacity draw (geometric mean ~400 GEC, arith ~800).

Cell arithmetic, illustrative on the measured canary cells: 8014 delivered
23.8k to hands and mouthed 301. If that mass spread over ~10²–10³ carriers,
capacity-bounded protected ≈ `min(capacity, load)` per host gives a protected
pool of order 10⁴ GEC → mouth of order 10³–10⁴ GEC — Σhazard
~1–30, bracketing the frozen 1.1 floor rather than landing far below it.
Whether carrier counts and capacity draws actually put ≥9 of 18 cold cells
over the floor is exactly what the canary measures; this spec claims only
that the arm creates the retention the shipped fill rule provably lacks,
using no new physical input.

## 6. Frozen criteria (for `noro_external_sequester_01`, written before any cell runs)

A two-arm factorial on the same 20-cell cold cohort (seeds 8000–8019,
`classic_cruise_1900`, 288 epochs, `norwalk_gi`, `item_instances` — the arm
stacks on the TOUCH-PATCH representation that produced the measured
requests), same instrumented worker and epoch mass ledger — **40 cells**:

- **Arm S (sampling-only):** `hand_residual_mouthing: "per_epoch"`,
  `hand_sequester_fill: "stool_only"` — the attribution control: what
  residual sampling alone buys.
- **Arm S+R (retention + sampling):** `hand_residual_mouthing: "per_epoch"`,
  `hand_sequester_fill: "any_load"` — the full mechanism.

Arm S exists so the verdict separates the two components: residual sampling
is bounded at a few percent (§4) but must not be credited to retention.
8105/8106 stay held for the full-campaign decision.

Audit invariants — a violation is an instrument defect, not a null result:

- `len(epoch_mass_ledger) == 288` on every cell; the four counter
  reconciliations within 1e-9 relative as in the frozen D0′/D2′/
  TOUCH-PATCH audits.
- **Hand-loss partition closes:** per cell, cumulative hand-pathogen mass
  reconciles within 1e-9 relative as
  `sources = sinks + residual`, where **sources** = delivered to hands
  (all touch points) + mass created on the hand (stool-linked sequester
  draws + the stool visit's `accessible = max(accessible, target)` top-up +
  self-contact reloads + `hygiene_cycle` first-event priming),
  **sinks** = mouth (pickup-instant + §3.3 residual draws) + accessible
  inactivation + routine-wash strips + post-visit wash strips +
  redeposited + infection/recovery resets (hand load cleared at recovery,
  pending dropped at infection), and **residual** = end-state
  `accessible + pending + protected`. The internal flows — `sequester_migrated`, pending→protected
  settle, and the protected→accessible leak — are witnessed but are **not**
  balance terms (migration relocates mass; sheltered decay returns mass to
  accessible rather than killing it).
- **Off arm = shipped baseline, enforced by the bit-identity gate** — the
  off arm keeps the shipped stool-gated fill untouched (shedders
  legitimately hold pending/protected), so there is no separate
  all-hosts-zero check. **On arm provenance witness:** every host that
  holds `protected` or `pending` mass without a propensity-fired stool
  event must have a witnessed earlier positive accessible acquisition —
  the carrier-provenance check that distinguishes the new fill from the
  shipped stool path.
- The worker stamps `hand_sequester_fill_resolved` and
  `hand_residual_mouthing_resolved` per cell (the "resolved" convention), so
  a dropped override is a witnessed fact.
- Baseline-identity gate: with both knobs at their defaults the engine is
  bit-identical to the pre-change tree on one seed.

Reported, never selected on, per cell:

- the hand-loss partition (sources / sinks / residual / the internal
  flows) — the decomposition the verdict needs;
- delivered→mouth fraction per cell, split non-patch vs patch delivered;
- protected occupancy among carriers (share of hosts with acquired load that
  ever hold protected mass) and the capacity-draw distribution realized;
- Σhazard, secondaries, take-off per cell; wall-clock multiplier vs the
  `item_instances` arm.

Selection / decision rules (the frozen Σhazard ≥ 1.1 gate applies to arm
cells, 18 cold cells per arm):

- **Arm S ignites** (≥9/18 at ≥1.1): residual sampling frequency was the
  binding stage all along; retention is not the missing structure — report,
  do not promote the fill.
- **Arm S+R ignites, arm S does not:** retention was the needed addition —
  the missing structure was hand-reservoir retention; promotion to
  default-on with the shipped behaviours as labelled baselines is a
  *separate* change and decision.
- **Neither ignites; mouth fraction rises on arm S but S+R adds nothing
  over S:** sampling exposure moves mouth dose but retention does not —
  the protected compartment is measured not-binding, and the stranded term
  is the ~1%/h capture product or the challenge; report the partition,
  change nothing else.
- **Neither ignites, but mouth fraction rises materially on S+R vs S:**
  dwell is restored but the ~1%/h capture still strands the dose — the
  bound moves to mouth-touch structure or the challenge; report the
  partition, change nothing else.
- **Mouth fraction does not rise on either arm:** the capacity band or
  settle rate itself bounds retention, and the residual-draw magnitude is
  measured — a bound on both components, reported with the partition.

## 7. Out of scope / follow-ups this spec does not authorize

- Any change to a shipped constant, draw family, band or rate — including
  the sequester draw, settle rate, sheltered/pad inactivation, mouth-contact
  frequency, contact fraction and transfer efficiency.
- Residual-load mouthing promoted as the mechanism on its own — arm S runs
  it only as the attribution control inside this campaign, never as a
  candidate answer (§4 bounds it at a few percent).
- Carrier redeposition eligibility (D1′), `sanitary_visit_mode`, schedule /
  rhythm (D3′), food pathway, challenge-floor questions — all parked or
  measured-not-binding.
- `wash_reuptake` / `spike_decay` arms (no protected compartment to fill).
- Campaign submission — gated on user approval of this design, then the
  usual preflight (smoke → dry-run count → pinned digest → canary ≥20 seeds
  at one cell → stop and report).
