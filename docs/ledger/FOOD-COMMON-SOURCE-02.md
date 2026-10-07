# FOOD-COMMON-SOURCE-02
**Date:** 2026-10-07
**Commit:** a3acb043
**Pathogens:** norwalk_gi
**Status:** open

Frozen design of the coupled contamination-object redesign of the
common-source food mechanism —
[`docs/food_common_source_02_design.md`](../food_common_source_02_design.md).
The design was `declared` at 4d41be11; **leg 1 is implemented** at
a3acb043 (status `open` — the entry reports no numbers and nothing in
it may be quoted as a result until the scoring canary reads out).

**What it replaces.** FOOD-COMMON-SOURCE-01's per-window iid event draws
— one Bernoulli per voyage producing at most one contaminated pan, and
Bernoulli per (shedding agent, meal window) for the handler/diner arms —
are replaced by **contamination objects** persistent in (station/zone,
interval): a provisioned lot contaminates the pan stream it feeds until
exhausted or perished (pan count emerges from lot extent, demand and
window cadence, never a drawn count); a handler/diner object is seeded
once per shedding-while-on-duty span / infectious course and emits a pan
per covered window. One object = one realized contamination state (one
titre, one strain mix, one take-share) shared across every pan and
serving it emits — the draw discipline's "one physical event, one
realized draw" made structural.

**Why.** Fleet measurements this design must explain (NORO-FOOD-01,
NORO-FOOD-02, AGE-FOOD-01 per-tier readouts): the lot interval sits
~10–20× above the posting anchor; posted-conditional reported pax AR is
thin (0.019–0.032 vs class IQRs ~0.04–0.10) — one-pan clusters are too
small to read as foodborne outbreaks; the posting ceiling compresses to
~1.7–1.9% on the 3,000-agent hull; and iid per-window contamination is
mechanistically wrong — pans contaminated by the same lot, the same
working handler, or the same dining shedder are autocorrelated in space
and time.

**Modes.** `transmission.common_source.{lot,handler,diner}_mode:
"object"` ships default-ON per arm (better physics ships on);
`"independent"` is the labelled v1 baseline per arm;
`transmission.common_source.mode` (`on`/`off`) is unchanged. Draws
re-roll vs v1 inside the re-roll band — attribution is
distribution-level contrast, not per-seed pairing.

**Legs.** Leg 1: the provisioned-lot object (implementation-ready in the
spec). Leg 2: handler/diner conditioning on the realized infectious
course. Scoring campaign is a later stage with its own frozen
admissibility.

**Leg 1 landed (a3acb043).** `lot_mode: "object"` is the shipped
default: the voyage plan is a count draw (`lot_object_probability` +
geometric `extra_lot_probability` tail), each provisioned lot is one
realized contamination state (titre, strain mix, take-share) shared by
every pan it emits, and pan count emerges from lot extent, cohort
demand and window cadence. Objects bind one (zone, item-line) station,
serve each covered window once, and close exhausted, perished, or at
voyage end — witnessed on `matrix.common_source_objects` with
`object_id`/`pan_serial` threaded through the pan and exposure rows.
`"independent"` is the labelled v1 baseline, verified bit-identical to
the pre-change tree on forced lot + handler/diner rates (same events,
exposures, doses, stream positions); `mode: off` still draws nothing.
Handler/diner arms still run v1 semantics under their own mode keys.
The v1-era readings above remain the measurements the object physics
must explain — the scoring readout is a later stage.
