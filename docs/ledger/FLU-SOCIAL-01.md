# FLU-SOCIAL-01
**Date:** 2026-10-03
**Commit:** 8c03e9d7
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** 8c03e9d7

Re-census of the frozen FLU-RHYTHM-01 cells on the social-mechanics
engine: CAREGIVER-V1 (#859, R2 tending / R3 service declared for
influenza_a, default-ON) + PROPENSITY-V1 (#860, per-party contact
propensity, default `party`, rhythm-gated), delivered on the shared
campaign-stack image (#861) with the `_emit_emesis` wrapper-drift fix
(#862). Same manifest, same 800 cells, fresh prefix
`campaign/flu_social_01/`; baseline = the `flu_rhythm_02` census at
`1ab8dd98` recorded above in `FLU-RHYTHM-01`. Arm caveat: `off` disables
rhythm, which gates propensity — so the off arm still carries caregiver;
the on − off pair isolates propensity, and any old → new delta on the
off arm bundles caregiver with the other engine commits in
`1ab8dd98..8c03e9d7`. Full tables: `docs/flu/flu_social_01_readout.md`.

**Execution:** image `picard-campaign@sha256:825a52e8e80c8f9f048a55b346761b88ce3dd69d633587425b4b671728b0720e`
(tag `campaign-8c03e9d7`, ENGINE_GIT_SHA `8c03e9d7`), jobdef
`picard-flu-rhythm-ab:4`, queue `picard-campaign-queue` (Spot, ~55 min).
Canary gate passed (20 on-arm expedition cells). Arrays `48f04534` (off)
and `800a0cc7` (on): **800/800 SUCCEEDED, 0 FAILED.**

## Measured verdict

**The social mechanics fire and attribute on the flu arm — and the
confined endpoint does not move.** Confined cabinmate SAR at `8c03e9d7`
pooled across classes and arms is **5.1–13.3%**; every per-class point
estimate sits inside its `1ab8dd98` Wilson band and inside the
CABIN-FLOOR-03 corrected band (declared-k expected SAR 3.7–12.1%
pooled; the expedition off-arm reads above the pooled top exactly as it
did at `1ab8dd98`). Per-slot delivered confined dose is flat old → new
(p50 1.3–30 copies, same aggregation both censuses); voyage attack moves
≤ +0.001–0.0013 in both arms (unscored).

**Both mechanisms left measurable traces:**

- `caregiver:influenza_a` now appears in confined `slot_rows[].pathway_dose` —
  the first in-cell witness of caregiver dose on this pathogen: ≥1
  caregiver-touched slot in 14–86% of cells (class-dependent, tracking
  crew/service scale), but only ~0.0007–0.41 copies/cell summed — 2–4
  orders below the per-slot delivered dose it lands beside (~1.3–30
  copies).
- Challenged share (`n_challenged/n_aboard`) lifted on every class in
  **both** arms: off-arm +3.5–8.5 pp vs `1ab8dd98` (caregiver layer plus
  the inter-census commits — not a clean isolation), propensity marginal
  (paired on − off) +3.0–5.2 pp, mean ≈ median. The social layer
  enlarges the dosed population; it does not enlarge the confined
  converted population at flu's k/susceptibility.

**Why the endpoint is flat (inferred, consistent with the measured
channels):** confined cabinmate SAR here is carried by the cabin
droplet/plume/pool chain (~1.3–30 copies per slot); caregiver dose is
~1e-4–1e-3× that, and propensity reshapes community co-presence — which
feeds the challenged-share counter — not the confined slot's dose
composition. Matches the FLU-RHYTHM-01 finding that rhythm is
scheduling-inert on this endpoint.

**Verdict:** influenza under the social mechanics is live, attributed,
and non-degenerate — a measured null on the confined endpoint, a real
+3–8 pp widening of the challenged population, and a quantified
(marginal) caregiver dose channel. No band exit; nothing rescored — flu
carries no scored anchor. No constant touched. The interesting
follow-up is whether the challenged-share lift converts on a
community endpoint on a scored pathogen arm (covid/noro), where the
channel actually posts; on flu it does not.
