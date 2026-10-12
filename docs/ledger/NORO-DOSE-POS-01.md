# NORO-DOSE-POS-01
**Date:** 2026-10-11
**Commit:** 21a66021
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** dbbd5395

ENTRAIN-01 dose-position audit + unposted mint census over the landed
`campaign/noro_entrain_01/` zips (27,000 design cells summary pass; 2,740-cell
census pass — all 310 posted + seeded-stratified unposted sample, 219,468
acquisition rows). Full tables: `docs/norovirus/noro_dose_position_audit.md`.

**Measured.** E[Hill(delivered dose)] over acquired infections ≈ realized
presentation within ~4 points on every hull × posted/unposted cell set
(unposted: E[p] 0.23–0.24 vs realized 0.19–0.22; posted: 0.31–0.35 vs
0.31–0.40), and realized tracks the declared Hill monotonically across dose
bands. The presentation hop is doing what the profile declares; the realized
~0.13–0.17 ill/infected funnel is a delivered-dose-magnitude measurement —
median cumulative dose 27–36 units unposted (position p≈0.2–0.25 on the
declared η=0.508, γ=0.095 curve), ~5 orders of magnitude below the dose the
curve needs to return the profile's challenge-cohort reference share
(p=0.71 at ~9×10⁵ units). The severity prior cannot absorb symptomatic
share (renormalized inside presentation), so no candidate sink remains at
the hop. Everything is position-on-curve: the dose scale itself is
withdrawn (open-ledger §4 item 00).

**Measured.** On unposted cells the lot channel is absent rather than
unconverted: provisioned_lot objects mint at ~0% (2/1,620 cells) and
provisioned_lot events at ≤1.7% on every object arm, while handler/diner
objects and events fire at ~0.87–1.00 on cls/spr. On `ind`, provisioned_lot
events mint at 4–12% of unposted voyages and appear on 87–100% of posted
ones — P(posted | ≥1 lot event) ≈ 0.70–0.91 — mint-rate × conversion
reproduces the observed `ind` posting rates. Posted `ind` infections sit
far higher on the Hill than unposted `ind` (median cumulative dose
2–10×; >0.5 tail 5–10×): posting correlates with the dose tail, not
infection count.
