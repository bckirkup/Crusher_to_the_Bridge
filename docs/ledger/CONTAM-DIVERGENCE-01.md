# CONTAM-DIVERGENCE-01
**Date:** 2026-10-16
**Commit:** 1ac4da8a
**Pathogens:** all
**Status:** measured
**Measured at:** 1ac4da8a

Native `ContamTransportEngine` vs ContamX `ContamXTransportEngine` — same
propagator, different airflow field. Full write-up:
`docs/contam_engine_divergence.md`; reproduction:
`tools/_contam_bracket_surrogate.py` over
`tools/_contam_divergence_measure.py`.

**Destroyer ground truth** (real `.sim` fixture, 1e6 injection into Bridge,
η = 0.5, decay = 0, 12 epochs): native retains 42% vs ContamX 98% —
native removes ~2.3× faster; per-epoch L1 ≈ 9% of injected mass; per-zone
outflow ratios 0.75×–30×.

**Mechanism, measured:** `.prj` AHS terminal legs are element-free paths
(`e# = 0`) whose `Fahs` is a design annotation (declared ≈ native
`ach·V·duty`), not an enforced flow — the pressure solve redistributes it.
Destroyer `ahs2`: 878 m³/h through MedBay alone while sibling terminals sit
at ~0. A solver-starved room drops to its adjacency floor: expedition
0.01–0.15/h and classic 0.02–0.14/h vs native `k` 3–14/h — 30–600× longer
airborne dwell. Separately, native `HD_*` sanitary zones are permanent
sinks (zero outflow); ContamX vents them overboard via dedicated exhaust
AHUs. Native parks 1.74% (expedition) / 0.33% (classic) of injected mass in
heads after 12 h.

**Framing:** the twins bracket *design intent vs uncommissioned build*,
not *designed vs as-built*. Native ≈ the commissioned field the sourced
ACHs describe; the ContamX solve ≈ an unbalanced network (no balancing
elements) — the as-built truth sits at a third point only real-ship
sampling sees.

**Bracketed-surrogate permissible-region test** (shunt `s ∈ {0.5,1.0}` to
smallest/largest terminal per AHS; `HD_*` vented at declared rates; 24 h
occupied-class dose integrals on expedition/classic/spirit, four injection
classes each): the prior "difference did not eliminate the permissible
region" endorsement **fails on all three platforms** — occupied-class dose
ratios 0.04×–2320×, retained mass up to 97% vs native ~0.3–17%, residual
anisotropy 1.4–275× (still up to 95× at `s = 0.5`). Required scalar rescale
`r*` swings 0.25×–2000×+ by emission site; the per-venue sign is
unknowable (spirit `LidoBuffet` dining dose 143.9× vs 0.04× across
terminal corners — ~3600× same-venue swing). Only single-class-dominated
anchors stay near-scalable.

**Caveats:** largest ratios are partly low-denominator; surrogate omits
voyage dynamics (quarantine/behavioural feedbacks); terminal choice is
solver-decided — the bracket spans, it does not point-estimate.

**Defensible construction:** hold terminals at design flow (constant-flow
elements or balancing resistances) and let ContamX solve only
leakage/exhaust — divergence then collapses to the HD-vent fix plus
±50%-order adjacency corrections; endorsement plausibly survives.

**Unresolved:** C13b paired zips (`a2_<pathogen>_<platform>_dose*`,
`telemetry_buffer/c13b_contam_airborne_small/`) are gitignored locals; a
recursive scan of `s3://crusherbucket-994254241749-us-east-1-an/campaign/`
returns zero matching keys. Recovered, they bound the unbalanced solve —
not the commissioned field.
