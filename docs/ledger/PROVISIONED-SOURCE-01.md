# PROVISIONED-SOURCE-01
**Date:** 2026-10-15
**Commit:** f7bbec40
**Pathogens:** norwalk_gi
**Status:** declared

Frozen mechanism design + frozen evaluation design — the
venue-provisioned-lot (supply-side) channel. The fiat mint gate
(`lot_object_probability` voyage Bernoulli + `extra_lot_probability`
geometric tail in `_cs_plan_objects`, `engines/transmission_core.py`
≈:12538) is replaced by a derived draw: every voyage provisions
`N_lots` lots — one per (served Dining venue, item line) station —
each contaminated independently with upstream prevalence `q_source`.
Contaminated lots mint `provisioned_lot` objects through the shipped
realization path (station-bound zone/item; everything else — day
window, servings, titre, take-share, shelf-life, mix — unchanged);
clean lots mint nothing. The mechanism is platform-neutral by
construction: `N_lots` derives from the platform's venue tree
(`data/platforms/<p>/spatial_layout.json` — 21/35/63/70 on
exp/cls/spr/mega, 7 `COMMON_SOURCE_LOT_ITEM_LINES` per served venue),
`q_source` is hull-invariant (the supply chain does not know which
ship it feeds), and `source_id` is the scenario covariate naming the
provisioning source — a cruise embarkation port, an airport caterer,
an institution; cruises are the first consumer. Ships default-ON
(`lot_mint_model: "provisioned_source"`); `"fiat"` is the labelled
baseline mode, bit-identical to pre-mechanism main. Worker-seeded
objects (`ill_handler`/`ill_diner`) stay mechanistic; the census
splits them by `source_kind`, which object rows already carry.

The testable claim (the campaign's headline): the venue-station
census scales like the measured required-object scale (21:35:63 vs
the MINT-RATE-01 required E[objects] ratios ≈1:1.6:2.4), so ONE
`q_source` puts all three small hulls in the D1 posting band
simultaneously — the admissible region becomes hull-free in q, and
the fiat model's p*(hull) ladder is revealed as `p* ≈ N(hull)·q`.
Frozen prediction: `q_source ≈ 3e-4` lands +0.59/+0.61/+0.68 pp on
exp/cls/spr. Mega joins the hull set explicitly: `N_mega = 70` lands
~0.02 objects/voyage at the common q (near-absent); its own in-band
window extrapolates to q ≈ [1.5e-3, 4.1e-3] (p* ≈ 0.09–0.25 on the
compression law) — where the measured window lands vs that
extrapolation, and whether multi-lot voyages (P(K≥2) = 0.017/0.14/0.39
of minted voyages at q08/q15/q30 on N=70) pull it below, is the second
headline.

Campaign: scalar q rungs 1e-4/2e-4/3e-4/5e-4/8e-4/1.5e-3/3e-3
(`q01`–`q30`) + `ps_ship` (shipped-default interval [2e-4,5e-4] via
source `generic_cruise_port`) + `off`/`ind` baselines + `ship`/`mint`
fiat bit-identity bridges (small hulls only) — 3 small hulls × 12
arms + mega × 10 arms × 1,000 seeds = 46,000 cells + ~128 canary on
the SCORE-01 seed lists and fixed coordinates. Contaminated-station
sets nest by q per seed (scalar rungs consume zero voyage-rate
uniforms — the MINT-RATE-01 stream-layout precedent); fiat bridges
are bit-identity gates to landed cells; E[objects] = N·q per hull is
a declared expectation gate. `q_source` rung values are declared arm
configuration, not register rows; the shipped default interval is
Grade C pending a sourcing leg (source types named — FDA/state
facility inspection, MMWR foodborne surveillance, VSP supplier
posture, EU RASFF — no citations invented). Required new witnesses:
voyage block `common_source.provisioned_source`
(source_id/q_source_drawn/n_stations/n_contaminated),
`provisioned_source_id` on provisioned_lot rows, and summary block
`reported_cases_by_dominant_route` (the NORO-HULL-SCALE-01 named gap —
per reported case, its infection episode's dominant route plus an
`imported` bucket, summed to `cumulative_reported_cases` per role).

Rejected and recorded: a consumption-throughput N_lots derivation
(no config carries a restock cadence — invented, not derived; needs
multi-object-per-station semantics; and it *moves* the hull-free
claim since required objects are not ∝ complement) and
`rng.binomial` for the contamination draw (variable internal uniform
consumption — no nested-set gate). The mechanism doc records the
throughput derivation as the fallback if the hull-free claim fails.

Design-of-record: `docs/provisioned_source_01_design.md` (mechanism
contract — config schema, RNG/stream contract, witness fields,
integrity gates); `docs/norovirus/noro_provisioned_source_01_sweep_design.md`
(frozen eval — arm table, D1–D4 + integrity gates, canary/wave plan).
Package: `campaigns/noro/provisioned_source_01/` +
`campaigns/noro/provisioned_source_01_mega/` (the AGE-FOOD memory
split — mega tiers at `memory: 8192` pending canary rss). The
campaign does not submit until the implementation leg lands the
mechanism + witness fields and the image pins a SHA containing them;
canary then STOP.
