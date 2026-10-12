# NORO-CS-EXTENT-02
**Date:** 2026-10-12
**Commit:** 36ce23c8
**Pathogens:** norwalk_gi
**Status:** open

Integration pin for the NORO-CS-EXTENT-01 × NORO-TWO-MODE-TITRE union
— no mechanism change, no numbers.

The `lot_state_redraw: "per_window"` re-mint landed (in #991) already
routed through `_cs_titre_spec`, the same site rule the object mint
uses: a `provisioned_lot` re-mint resolves
`lot_titre_implicated_gec_per_g` under the shipped
`titre_draw_mode: "two_mode"` and the single-mode
`lot_titre_gec_per_g` spec under the `"background"` baseline. The
object's own stream partition consumes the uniform either way, so the
re-mint cadence is unchanged and the shipped `"per_object"` pair keeps
zero new draws at shared seeds.

**Gates pinned** (`tests/test_common_source_cs_extent.py`, +2): a
spec-name pin lands every re-minted window titre on the pinned value
under each mode (a re-mint that bypassed the resolver would leave the
pin unconsumed), and same-seed two_mode/background runs pair every
re-minted titre at equal log-uniform quantiles across the implicated
(1.5e2, 5e3) and single-mode (1e1, 1e4) bands.
