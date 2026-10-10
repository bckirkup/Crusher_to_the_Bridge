# NORO-ENTRAIN-01
**Date:** 2026-10-10
**Commit:** 13cf35a5
**Pathogens:** norwalk_gi
**Status:** declared

Two approved levers aimed at raising VSP posting rates appropriately
per hull, on the SCORE-01 measurement frame, plus a design-note-only
third. **Lever A (event shape)**: whether dose spread across more
service windows recovers `ind`-like conversion on honest
contamination objects — config arms `a_ext` (lot_shelf_life_days
(4,7)) and `a_thin` (item_take_share (0.04,0.20)), plus the spec'd
`cs_extent` mechanism contract (forced-extent draw + per-window
state re-mint) for the iso-dose and cadence isolations config cannot
express. **Lever B (arriving-shedder proxy)**: one-voyage
approximation of entrainment — crew boarding prevalence raised to
declared 0.040/0.080 points (`bc40`/`bc80`), crew-only embarkation
immunity 0.5 (`bi50`), the net-sign cell `bmix`; the clean
class-weighted shedder-conditioned channel is spec'd as the
`arriving_shedder` contract. **Design note only**: full chained-cruise
entrainment (terminal→initial carryover, turnover, run clustering) —
not built.

Grid: 3 hulls (exp/cls/spr; mega excluded — objects never armed
there, v1 saturates short of its wire) × 9 arms (`off`, `ind`,
`ship` baselines + the six lever arms) × 1,000 seeds = 27,000
voyages on the `gen` age mix, fixed coordinates identical to
SCORE-01 (rung `shipped`, bp32.5, nsf29, 288 epochs, dose_adjustment
7.57, `syndromic_comp65`), SCORE-01 seed lists verbatim (exp
8000–8999, cls/spr 8105–9104).

Frozen admissibility, must-not-move invariants, thin-cell
declaration, canary (24 `bc80` + 12 `a_ext` + 8 `ship` + 4 `off` on
exp, then STOP), wave order and report-immediately triggers:
`docs/norovirus/noro_entrain_01_sweep_design.md`. Campaign package
`campaigns/noro/noro_entrain_01/`; manifest
`noro_entrain_01_manifest.json` (27 tiers, 27,000 cells). No engine
changes; nothing submitted under this design until the user gates
image build, canary and each wave.
