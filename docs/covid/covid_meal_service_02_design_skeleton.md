# MEAL-SVC-02 design skeleton — attenuating `service_to_host` on the door-drop factor

Status: **draft skeleton for owner review — not a design, not frozen, no
cells may run against this file.** It exists to put the follow-on arm
ladder on paper so the owner can steer the grid before a design is
written and frozen. `covid_meal_service_01_design_skeleton.md` is the
format this file imitates; a real MEAL-SVC-02 design lands only after
the open decisions below are answered.

## Question

MEAL-SVC-01 answered the existence question (canary CHANNEL-FOUND at
`32b11ccf`, #937/#943, `covid_meal_service_01_readout.md`): adding the
steward→host direction (`direction: "both"`) converts deliveries into
confined-passenger acquisitions — takeoff-conditional median **804** vs
the ≥52 bound, during-total 1,267, crew share 0.379 (record 0.29). At
the declared full pair-dose magnitude the channel overcorrects ~15× —
signature recovered, interval sits high. The shipped responder-only
crediting was the conversion defect CW-02 measured (~4–19 pax).

Question for this leg: **where on the door-drop attenuation axis does
`service_to_host` land the passenger mass — and does the same point keep
the crew share near the record?** The owner has chosen the axis: the
per-delivery `contact_factor` (#936's mechanism), applied asymmetrically.

## What the engine actually offers (verified against the tree, 2026-10-06)

- `CAREGIVER_SERVICE_CONTACT_FACTOR = (0.05, 0.3)` — declared Grade C
  tuple (#936, `engines/transmission_core.py` ~562): the door-drop
  realization, bounded strictly below R1's steward interval (0.3,0.7)
  and above 0 (DP crews did seroconvert on door-drop service).
- Grammar already shipped: `contact_factor` absent → declared tuple;
  scalar → fixed corner; `[lo,hi]` → per-delivery uniform draw on the
  dedicated `_SERVICE_CONTACT_STREAM_KEY` spawn (~994). `1.0` is the
  labelled un-discounted baseline (spawns nothing, bit-identical).
- Applied per-branch at the shared `_caregiver_service_dose` funnel;
  #937's merge hoisted the per-delivery draw into
  `_caregiver_service_epoch` — **one door-drop, one realized factor,
  both directions** (~10246 comment).
- `direction: {"responder", "both"}` resolved at ~2848;
  `_credit_service_to_host` (~10282) credits the host under route
  `service_to_host` beside the steward-side `caregiver` tally.
- Structure witness shipped: distinct stewards per confined host
  (median 44 on the uniform draw; section-binding collapse expectation
  ~1–2 untested — the SECT arm never ran under the stop rule).
- Nonlinearity is expected in both directions: the channel feeds back
  (infected passengers shed → stewards pick up → more passenger
  emitters), so the elasticity of confined-pax acquisitions in the
  factor is *not* linear — the ladder exists to measure it.

## The arm axis (owner-chosen): asymmetric door-drop factor

Ship the host direction its own declared factor so the shared
realization stays the door-drop's physical draw while the two
directions can carry different attenuation:

- Grammar sketch: `contact_factor_to_host` on
  `transmission.caregiver.roles.service` — absent → falls back to the
  shared draw (status quo); scalar/`[lo,hi]` → an independent declared
  corner/interval for the steward→host direction on the same dedicated
  spawn stream family. Steward side keeps the shipped (0.05,0.3)
  regardless.
- Physical claim being swept: the door-drop's effective contact for a
  *passenger opening the door* is shorter/more distant than for the
  steward working the corridor — the same delivery, different exposure.

The ladder (declared intervals/scalars for `contact_factor_to_host`,
steward side pinned at shipped):

| arm | host factor | expected pax if ~linear (×804) |
|---|---|---:|
| `CF_HOST_SHIPPED` | (0.05,0.3) shared | ~804 (re-measure — control row) |
| `CF_HOST_MID` | (0.02,0.08) | ~230 |
| `CF_HOST_LO` | (0.005,0.02) | ~60 — the bound neighbourhood |
| `CF_HOST_FLOOR` | scalar 0.01 | ~45 — under the bound |
| `CF_HOST_OFF` | scalar 0.0 | ~4–19 ≈ responder-only corner |

Expected-pax column is the linear-elasticity sketch only — the readout
replaces it with measured medians; a nonlinear response is a finding,
not a failure.

## Cells, seeds, pairing (sketch)

θ7.9e6 only (settled). Replay arm `ZONE_NARROW` (the landed arm — the
record-faithful base) × the five factor arms × 20 seeds = **100 cells**
plus ride-alongs:

- `D0 × {CF_HOST_SHIPPED, CF_HOST_OFF}` — the all-crew-working corner
  pair (40 cells): reads whether the attenuation holds when the steward
  pool is everyone.
- `ZONE_NARROW × CF_HOST_LO × SECT` — the section-binding arm at the
  bound-corner factor (20 cells): sections concentrate the sick-steward
  round — does structure recover mass at low factor?
- `*_svc_base` rows — the CW-02 drift-witness pairing carried open from
  MEAL-SVC-01 (40 cells).

~200 cells total. Canary: `ZONE_NARROW × CF_HOST_LO` @7.9e6, 20 seeds —
the arm most likely to sit near the bound.

## Scoring surface and verdict grammar (sketch — freeze before cells run)

Same surface as MEAL-SVC-01, now with the magnitude frame:

- Confined-pax during-window acquisitions vs the bound region (~52;
  record-implied passenger mass roughly 45–160 against the crew share
  and band together — stated as context, not a threshold).
- Crew share vs 0.29 — direction, not threshold.
- During-total **reported beside** [150,350] — not gating (settled).

Grammar sketch: MAGNITUDE-LANDED (an arm's pax median sits in the bound
region with share moving record-ward), OVER-ATTENUATED (pax collapses
toward the responder-only floor), STILL-HIGH (median above ~200),
NONLINEAR-BREAK (the median response departs monotone in the factor —
flag for attribution, not a failure).

## Audit invariants (sketch)

- Factor echo: every cell's resolved block echoes the effective host
  factor (tuple or scalar) — a missing/mismatched echo halts the readout.
- Realized factor distribution: the median of host-direction realized
  factors ≈ the declared arm's mean (the lottery check, CW-02 pattern).
- Deliveries parity vs the MEAL-SVC-01/CW-02 rows; direction echo
  `both` on DIR cells; distinct-steward count (≈44 uniform, ~1–2 on the
  SECT sub-arm); CW-02 window/index/propensity/reach set carried.

## Report immediately if

Any arm's pax median lands the bound region with share ≤~0.5 moving the
right way (near-landing — stop, report before the array); a scalar corner
lands exactly on the bound (the factor's floor is the answer — a source
tranche, not more cells); the response departs monotone (NONLINEAR-BREAK);
deliveries parity fails; >5% child failures.

## Non-goals

- No fitting: factor intervals are declared arms; whichever lands is a
  magnitude to source afterward, not a constant to adopt — the ladder
  brackets the bound, it doesn't tune onto it.
- Episode share, delivery cadence, host-direction efficiency constants —
  rejected axes, parked (the design names them; this leg doesn't run them).
- SECT is subordinate — one sub-arm at the bound-corner factor, not a
  grid of its own.
- Crew-side mass is reported (the channel amplifies both directions) but
  the crew attenuation answer stands on CW-02 — no re-run of that ladder.
- No new Devin child sessions; Batch cells only.

## Required deltas before cells run (sketch)

1. `transmission.caregiver.roles.service` grammar: `contact_factor_to_host`
   (per-direction factor; absent → shared draw, status quo), resolved-block
   echo for the effective host factor.
2. `engines/transmission_core.py`: split the host-side credit's factor
   application at `_credit_service_to_host` — shared draw × host factor
   (or independent interval draw on the dedicated stream family).
3. Payload witnesses: realized host-factor stats per cell (median/quantiles
   of the draws), `service_to_host` tallies carried, distinct-steward count.
4. Campaign registration under `campaigns/covid/meal_service_02/`, design
   JSON with the frozen admissibility + ladder verbatim, readout pairing
   against the MEAL-SVC-01 canary row and the CW-02 base rows.

## Open decisions for the owner

1. Grammar shape: independent per-direction interval
   (`contact_factor_to_host`, recommended — cleanest attribution) vs a
   multiplier on the shared draw (keeps "one door-drop, one realization"
   literal but couples the two sides' noise).
2. The ladder: the five arms above vs a three-arm {SHIPPED, LO, OFF}
   minimum (60 cells on ZONE_NARROW alone).
3. Whether D0 rides (recommended — the corner pair measures the
   attenuation against a full steward pool, 40 cells).
4. Whether the SECT sub-arm rides at CF_HOST_LO (recommended — structure
   × magnitude interaction in one shot) or stays parked.
5. Crew-side co-surface: report the steward share of during-window crew
   acquisitions per arm (the channel's other direction quantified) —
   recommended, it's already in the tallies.
