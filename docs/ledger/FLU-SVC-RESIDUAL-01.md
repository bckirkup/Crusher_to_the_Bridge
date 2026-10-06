# FLU-SVC-RESIDUAL-01
**Date:** 2026-10-06
**Commit:** 02ab79b8
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** 02ab79b8

Attribution of the residual second channel flagged open by
`docs/ledger/CAREGIVER-SVC-01.md`: the passenger/droplet surplus at
`contact_factor: 0` on seeds 8112/8184/8120 (exp `r200_dec`), with confined
cabin-mate pooling named as the candidate.

## Method

Paired arms on the VIS-01 conditioned cell (`expedition_cruise_450`, 288
epochs, organic confinement), steward factor held at 0 so only the
report/response scale varies: `r200_f0` (report_scale 2.0) vs `r100_f0`
(1.0). Same seeds — deterministic; an arm re-run is bit-identical
(infection sets and epochs match across runs). Probe:
`tools/flu_svc_residual_probe.py` (paired arm, per-agent infection rows,
compliance-log replay for confinement intervals, class-level
`execute_transmission` capture for event zone/pathway/dose, protocol
activation log). Payload: `reports/flu_svc_residual_01.json`.

## Measured

Onboard-acquired infections: `r200_f0` 51/49/11, `r100_f0` 24/1/1 on
8112/8184/8120 → surplus 31/48/10 (89 pooled). Confined cohort end-state:
58/70/6 vs 35/3/3. Every surplus event is droplet-dominant bar one
hvac_airborne.

Target-side channel decomposition (pooled 89):

| channel | n | share |
|---------|---|-------|
| `free_no_mate` — free target, no earlier-infected clique mate | 65 | 73% |
| `co_confined_pooling` — both confined, earlier-infected mate | 13 | 15% |
| `free_pair` — earlier-infected mate, neither confined | 5 | 6% |
| `crew` | 5 | 6% |
| `cross_boundary_mate` | 1 | 1% |

Two distinct signatures inside the surplus:

- **The pooling tail is real but minor and late.** All 13
  `co_confined_pooling` cases land at epoch ≥194 (the wave runs 102-182),
  droplet-only, in `PC_*` cabin zones, carrying small doses (~56-74 vs
  ~700-1300 on the non-surplus cabin events) — the signature of the
  5%-scaled confinement emission + mate addback/pair terms. This is the
  named candidate, confirmed — and it is downstream of the wave, not its
  seed.
- **The dominant term is a free-pool droplet wave in shared venues.**
  60/89 surplus infections establish in `CasualDining`/`MainDining`
  (epochs ~102-182) at full-strength doses (~480-820, same magnitude as
  the non-surplus dining events), plus Theater/PoolDeck/Casino/Reception.
  Only ~17% of the surplus establishes in cabin zones at all — the
  corridor-pooled-emitter variant of the candidate is bounded small
  (≤15 cases).

## The ignition pivot — the admission lottery

Replaying the compliance log against the seeded founders
(`first_infection_epoch == 0`, identical sets in both arms):

- **8184** founders {85, 266}: arm B orders both at ep 53 → **admitted**
  ep 54 → outbreak collapses (1 onboard). Arm A admits 266 at ep 36 but
  **85 refuses at ep 52** → a permanently free symptomatic founder →
  dining wave ignites ~ep 102 → 49 onboard.
- **8120** founders incl. {94, 121}: arm B orders 121 at ep 126 and
  catches 94 via cascade → **both admitted** ep 127-128 → collapse (1).
  Arm A: **both refuse at ep 73** → sustained wave ep ~250 → 11 onboard.
- **8112**: arm B never orders 7/8 founders (253 admitted ep 211) → the
  founders roam free anyway → wave in both arms (51 vs 24) → surplus is
  the pooling tail plus trajectory churn, not a qualitative difference.

Refusal is absorbing — no refused host is ever re-ordered on any seed.
Infected refusers per arm: A = 8/8/4, B = 2/0/1 (refusal events overall
23/26/6 vs 8/0/1) — realized refusal scales with order volume
(escort_orders 46/53/5 vs 29/3/2), which the escalation cascade drives
(SOP-008/010/011 active at r200; no mass `general_confinement` actions
fired on either arm).

## Verdict

The residual is **not principally the named candidate**:

1. ~85% of the surplus is a free-pool droplet wave sustained by the
   **admission lottery**: every confinement order on an infectious host
   is a Bernoulli admit/refuse draw, and a refused host is a permanently
   free full-strength symptomatic shedder. Order volume scales with
   report scale, so refusal realizations scale with it. On 8184/8120 the
   lottery landed refuse on the *seeded founders* — the highest-leverage
   hosts — converting arm-B-style collapse into a sustained dining-venue
   wave; on 8112 both arms kept free founders and the wave ran in both.
2. ~15% is the confirmed **confinement-compartment pooling tail**:
   co-confined cabin-mate pairs at full mate strength plus the 5%-scaled
   corridor emissions — real, droplet-only, post-confinement, downstream
   of the wave it is fed by.

Accounting caveat: per infectious host, `r200` strictly removes *more*
free shedding than it creates — a refused host is functionally identical
to a never-detected host, and refusal is only reached through an order.
There is no systematic dose path at f=0 beyond the pooling tail; the
surplus is lottery **variance** concentrated on the seeded founders plus
that systematic ~15%. Direction is consistent on 3/3 seeds, n=1
replicate per seed — the mechanism is measured, the magnitude is a
seed-lottery bound, not a constant.

## Bounds and gaps

- Per-source attribution unavailable: with strain surveillance off the
  contributor ledger is empty, so the refusal→wave link is order-and-
  timing evidence (refusal epochs precede ignition on all three seeds),
  not event-level source proof.
- Arm-B protocol activation timeline not captured (baseline cells
  predate the `protocol_log` field); arm-B activations are inferred from
  its order volume (3-29 vs 46-53), not read directly.
- If a re-score wants the systematic component alone: the pooling tail
  is sweepable via the confinement-compartment terms (isolation factor,
  mate pair factor, addback); the variance component thins with founder
  count — an n≥20-seed window would show whether the lottery mean is
  net-zero.
