# NORO-MINT-RATE-01
**Date:** 2026-10-15
**Commit:** #998
**Pathogens:** norwalk_gi
**Status:** declared

Frozen evaluation design — the bracket on the mint-rate axis that
NORO-FOOD-SHAPES-01 identified as the operative margin on the object
grammar: the provisioned_lot voyage gate `lot_object_probability`
between its shipped U(0.001, 0.02) — D1 in-band on exp (+0.60 pp
marginal) but vacuous at ~6 minted voyages per 1,000 — and the powered
U(0.02, 0.15) `mint` override, which over-posts (+7.2–7.6 pp) while
carrying the full `ind`-level signature on every hull. The campaign
locates the gate where the D1 posting marginal lands in the 0.4–0.9 pp
band per hull, and measures whether the D2/D3/D4 signature survives at
that rate. The margin is linear in E[voyage presence]
(`_cs_plan_objects`, `engines/transmission_core.py` ≈:12538 — one
Bernoulli on the per-voyage gate draw, posture-free under shipped
`lot_posture_coupling: false`; `extra_lot_probability` contributes
only a ×1.163 object-multiplicity tail), so the rungs are declared
scalar gates: `p005`/`p008`/`p012`/`p017`/`p024`, declared arm
configuration — no provenance-register rows.

Arm set (9): `off`/`ind` baselines (floor; per-hull signature
denominator — `ind` itself misses the 0.04 posted-AR edge on cls
0.0352 and spr 0.0310, so D2 reads mint-vs-`ind` per hull);
`ship`/`mint` bracket anchors and bit-identity bridges to the
SHAPES-01 cells at `45b2bf18`; the five scalar rungs. 3 hulls ×
1,000 seeds = 27,000 voyages on the SCORE-01 seed lists and fixed
coordinates (exp 8000–8999, cls+spr 8105–9104; mega excluded).
Expected in-band windows (design §3.3, from measured P(post|minted)
0.93/0.58/0.36 on exp/cls/spr): exp ≈[0.004, 0.010] (`p005`/`p008`
in), cls ≈[0.007, 0.015] (`p008`/`p012`), spr ≈[0.011, 0.025]
(`p012`/`p017`/`p024`) — `p012` is the only rung in-band on two
hulls; no single gate lands in-band everywhere (hull compression is
measured, not a defect). Scalar rungs gate on the same stream
position per seed — minted sets must nest by gate value (integrity
gate); rungs <20 realized minted voyages/hull report thin-flagged
(vacuity rule). Canary = 116 cells on exp, then STOP.

Frozen admissibility (D1–D4, mint-vs-`ind` per hull), six integrity
gates (witness echo incl. verbatim scalar values, titre band, nested
mint sets, presence census tracks the gate, bit-identity bridges,
zero-lot bookkeeping), vacuity rule and canary-then-STOP in
`docs/norovirus/noro_mint_rate_01_sweep_design.md`; package
`campaigns/noro/mint_rate_01/` (manifest
`noro_mint_rate_01_manifest.json`, 27 tiers, 33 blocks). Carries no
numbers; nothing submitted under this design until the user gates
image build, canary and each wave.
