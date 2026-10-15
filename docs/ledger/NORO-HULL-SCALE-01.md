# NORO-HULL-SCALE-01
**Date:** 2026-10-15
**Commit:** 49e1993b
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 49e1993b

Analysis-only leg over landed NORO-FOOD-SHAPES-01 zips (first-500-key
re-parse of `fl_{exp,cls,spr}_12d_scr_{mint,ind}` ≈ 2,400 cells via
`tools/noro_diag/hull_scale_01_scan.py`) plus a 3-voyage local mega
forced-mint smoke. Full write-up:
`docs/norovirus/noro_hull_scaling_decomposition.md`.

Measured findings:

- The P(post|minted) compression (0.90 / 0.63 / 0.37 exp→cls→spr on
  n=41 minted voyages per hull) is carried by the reported→posted
  link: the absolute-count A9 wire (≥3% of complement reported)
  applied to a hull-flat per-minted-voyage yield (~30–37 cs_food
  cases, ~103 takers, ~85–90 diners per object). Cross-wire test:
  cls minted voyages evaluated under the spr wire post at 0.39 vs
  measured 0.37.
- Residual exp→cls offset is second-order: mild yield growth +
  background-epidemic reported growth (unminted rep_pax med
  2→14→22) fills an increasing share of the wire, which is why the
  admissible-window step is ~1.6× rather than the full 4.2×/1.6×
  complement factor.
- Countervailing per-object-efficacy hypotheses measured flat:
  objects/voyage ~1.1–1.2, pans/object 12→7→8, lot_servings 104 on
  every hull, minted item mix uniform 7-label on every hull
  (hull-invariant by construction), pan take-fraction 0.33→0.31,
  per-serving dose ~2e5 flat. No countervailing mechanism exists in
  the lot chain; the real one is background reported-case growth.
- Mega arming: `common_source_mode` defaults `"on"` and fires on
  mega_cruise_5000 — local forced-mint smoke minted 1
  `provisioned_lot` per voyage (bakery, SpecRest_B, 80 srv,
  titre ~1467, exhausted; 23 cs_food on the 0.025 rung; none posted
  against wires ≥147 pax / ≥63 crew). Landed complement:
  NORO-MEGA-IMPACT-01 (926 zips) armed cs on mega, 0/20 canary lots,
  0/926 posts, food lifts only the reach tail.
- Mega admissible-window extrapolation: p*_mega ≈ 0.09–0.25, outside
  the powered U(0.02,0.15) mint-rate grid — mega needs the
  venue-provisioned-lot mechanism leg, not a grid seat.

Named gap (instrument not built): `reported_cases_by_dominant_route`
in run summaries — would make cases→reported direct rather than
counterfactual-inferred against same-arm unminted voyages.
