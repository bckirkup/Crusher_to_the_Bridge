# FOOD-COMMON-SOURCE-02
**Date:** 2026-10-07
**Commit:** 4d41be11
**Pathogens:** norwalk_gi
**Status:** declared

Frozen design of the coupled contamination-object redesign of the
common-source food mechanism —
[`docs/food_common_source_02_design.md`](../food_common_source_02_design.md).
Per the ledger README a `declared` entry is the campaign-design
declaration: it carries no numbers and nothing in it may be quoted as a
result.

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
