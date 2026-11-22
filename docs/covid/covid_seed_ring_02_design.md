# COVID-SEED-RING-02 — voyage-stage contact declaration (design, frozen)

**Status:** Declared. Design frozen on the COVID-EARLY-GROWTH-01
measurement and the voyage-stage evidence memo
(`docs/covid/covid_voyage_stage_contacts_evidence.md`). No campaign runs
until the engine change lands and a canary is read out. θ, dose constants
and imports>1 are not axes. GM stays gated; H5 stays held out.

## The question

Does a two-stage contact declaration — a dense embarkation-window field
that relaxes to an independently justified routine field — land the
founder/ignition legs *and* keep early growth at the record's slope, with
θ=3.162e8 unchanged?

This is the follow-up the NULL-PLACEMENT verdict named, sharpened by
EARLY-GROWTH-01: founders alone cannot land the clause (record-timed cells
already overshoot mass), so the window declaration must be tested jointly
with the routine stage, not as a surge add-on.

## Mechanism — the voyage itinerary layer already exists

No engine change. `engines/voyage_itinerary.py` already resolves a
per-day `contact_rate_multiplier` into `tx_core.voyage_contact_multiplier`
(`ship_simulation.py:1141`) when `voyage.effects_enabled` is true. The DP
platform `voyage_config.json` ships `effects_enabled: false` with an
empty itinerary — the replay runs the flat POLYMOD draw because the stage
declaration was never turned on, not because the mechanism is missing.

The declaration is a scenario `config_overrides.voyage` block:
`effects_enabled: true`, itinerary declaring days 1..W as
`type: "embarkation"` (voyage_day is 1-indexed; voyage_day 1 = day 0,
the Yokohama turnaround), `defaults.embarkation.contact_rate_multiplier:
α`, all remaining days `sea_day` (identity defaults — onboard fraction,
dining demand and contact all 1.0, so the routine stage is untouched).
Declared caveats, frozen here so the readout attributes correctly:

- The contact uplift applies to the **whole embarkation voyage day**.
  Hour-windowing exists only for `buffet_surge_fraction`
  (`embarkation_window_hours_of_day`); the contact multiplier has no
  hour window. The declared unit is the voyage day, matching W in days.
- An embarkation day also sets `embarkation_buffet_surge` — surge dining
  assignment on day 0, which is part of the embarkation declaration, not
  a confound: it is the same boarding-day crowd declared through the
  dining channel. `buffet_surge_fraction` stays at its default 0.80.
- `voyage.shore_exposure.enabled` stays false — no ashore/port exposure
  enters the arm.

Open call (owner): W = 1 (voyage_day 1 only — the turnaround day) vs
W = 5 (voyage_days 1–5 — the index's aboard window, departing day 5).
Fastest cells' founder bursts concentrate day 0–1; lean W=1, declare
the alternative as a second arm rather than choose.

α is a **declared assumption band**, not a sourced constant — no cruise
embarkation sensor record exists (memo §3). Bound: mass-gathering
measurements put transient proximities well above routine rates; declare
α ∈ {2, 4, 8} as a swept band, prediction frozen per level.

## Arms (verbatim boxed_s1s2 replay, θ=3.162e8, 20 seeds each)

| arm | window | routine |
|---|---|---|
| `D0_declared` | `effects_enabled: false` (flat) | POLYMOD flat — pairing base + drift witness |
| `WINDOW_W1_A*` | voyage_days 1..W embarkation, `contact_rate_multiplier` α ∈ {2,4,8} | POLYMOD flat |

The routine stage is held flat deliberately: the memo's open Polymod-vs-Pung
definition gap means the routine count is not yet independently justified;
what is frozen is that the routine draw does not change, so any founder/
growth move attributes to the window stage only. A second declaration
(routine β) follows once the Pung episode-threshold mapping in memo §2
is resolved.

## Frozen predictions (declared before any cell runs)

Leg 1 — **early establishment** (Edison P1): on `WINDOW_W1_A8`,
founder-yield median ≥10 aboard-window acquisitions AND takeoff-seed
ignition median ≤9. At α=2 the prediction is intermediate lift
(median 4–10); α=4 predicts median ≥10 on ≥half of seeds.

Leg 2 — **routine does not over-produce** (Edison P2): on record-timed
cells of every window arm, pre-quarantine (d15) cumulative infections
median ≤960 (the band top) — i.e., landing founders does not push mass
further over, because the routine field is unchanged. EARLY-GROWTH-01
reading: this leg **fails** — d15 median is already 1,292 at α=1 and the
window only adds mass — UNLESS the window pulls founders earlier so the
growth spend lands inside the window while the routine field stays flat.
If leg 2 fails on all α, the residual is in the routine field itself
(dose-structure, not stage timing) and the declaration pointer moves to
`activity_contacts` + partner structure, per memo §5.

## Verdict grammar

- **WINDOW-LANDED:** leg 1 AND leg 2 both land at some declared α — the
  voyage-stage declaration is the missing structure.
- **FOUNDERS-ONLY:** leg 1 lands, leg 2 fails at every α — the window is
  real but the routine field is independently over-dense; next seam is the
  routine stage itself (Pung mapping + `activity_contacts`), not θ.
- **SPLIT-STAGE:** the legs land at different α and no arm lands both
  (e.g. leg 1 only at α=8 while leg 2 only holds at α=2) — read as
  FOUNDERS-ONLY: the uplift that buys founders is itself what breaks the
  mass leg, so the residual is again the routine field, not stage timing.
- **NULL-WINDOW:** leg 1 fails at α=8 — even maximal crowd exposure
  doesn't reach the founder lottery; the founder channel is something
  narrower than voyage-stage mixing (itinerary-level realized schedule,
  Arm-B continuation).

An arm that flips `effects_enabled` without declaring an itinerary is
rejected at design check — an identity-effects run would confound the
pairing (the layer being on is itself a delta).

## Audit invariants (carried from SEED-RING-01)

Departure epoch 120; quarantine window days 16–30; propensity/delivery
echoes unchanged; droplet split vs shipped constants; no cell may alter θ
or dose constants. Every cell echoes its window schedule in the seed
record.

## Deliverables when run

Per-cell evidence table (founders, ign, d15 cum, before-17 onsets,
d34 cum) under `campaigns/covid/seed_ring_02/`; measured ledger entry
`docs/ledger/COVID-SEED-RING-02.md`; handoff §8 updated in the same
change.
