# NORO-CS-EXTENT-01
**Date:** 2026-10-12
**Commit:** f00bf90f
**Pathogens:** norwalk_gi
**Status:** open

Mechanism landing of the `cs_extent` contract declared in the
NORO-ENTRAIN-01 design
([`docs/norovirus/noro_entrain_01_sweep_design.md`](../norovirus/noro_entrain_01_sweep_design.md)
§4.3) — the two lot-arm knobs the iso-dose and draw-cadence
isolations need and config alone could not express. The entry
reports no numbers; nothing in it may be quoted as a result until
the arm cells read out.

**`transmission.common_source.lot_extent_mode`** — `"emergent"`
(shipped default) | `"declared"`. Under `"declared"`, the mint draws
`extent_windows` from a declared interval (`lot_extent_windows`,
shipped interval (3,12) — documentary bracket of the shelf-life span
in services, Grade C declared) and the minted `lot_servings` are
distributed uniformly over that window count: a per-window serving
cap, the integer-division leftover folded into the last declared
window. Titre mints once, exactly as emergent, so expected
titre x servings dose is unchanged. Close reason `extent_met`
records the span spent with servings left; `exhausted`, `perished`,
`voyage_end` are unchanged. Expresses the design's `fx_wide`
(12,24) and `fx_narrow` (2,4) arms as config.

**`transmission.common_source.lot_state_redraw`** — `"per_object"`
(shipped default) | `"per_window"`. Under `"per_window"`,
`lot_titre_gec_per_g` and `item_take_share` re-mint at each served
window — in the mint's draw order — off a per-object stream
partition spawned from the common-source seed sequence, so the
shared stream consumes no draw and the shipped `"per_object"` pair
stays bit-identical at shared seeds. Extent is untouched: the
seeded-draw-shape discriminator (`ind`'s lottery cadence on the
object's autocorrelated extent).

**Ship convention.** Both knobs are arm config, not defaults — the
contract waives the default-ON rule. Witness fields `extent_mode`,
`redraw`, `extent_windows` echo on `common_source_objects` rows
(null on handler/diner objects); `windows_covered`,
`servings_served`, `end_reason` and the pan bookkeeping gate
integrity unchanged.

**Gates pinned** (`tests/test_common_source_cs_extent.py`, 11):
uniform-spread bookkeeping with the leftover window, `extent_met`
close with servings left, emergent's uncapped bookkeeping, both arm
intervals expressible, profile-block override, per-window re-mints
across windows, partition draws leaving the shared stream
untouched, seeded determinism, default-vs-explicit-baseline
bit-identity.

**Collision note.** Lands alongside in-flight PR #990's
`lot_titre_gec_per_g` two-mode conditioning (orthogonal): the
per-window titre re-mint draws the same spec name the mint site
draws, so #990's conditioned bands apply to re-mints unchanged when
it merges.
