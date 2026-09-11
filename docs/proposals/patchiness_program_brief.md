> **Status:** Proposed — a handoff brief for the next working session. Nothing
> here is implemented or adopted; the measurements it cites are in
> `docs/norovirus/norovirus_open_ledger.md` §4 and
> `telemetry_buffer/observation_model/dose_concentration_findings.md`.

# Where the norovirus thread stands, and what a fresh session should pick up

## 1. The state of the anchors

On the expedition hull, across every structural repair from `BERTH-01` through
`CONTACT-ARCH-02`:

| Anchor | Model | Target |
|---|---|---|
| A5 (passenger:crew attack-rate ratio) | 1.5–2.4 marginal; 2.56 / 2.75 / 2.61 stratified by dose regime | ≈3.5 on the reported channel, 4.3 fleet |
| A9 (voyages posting) | 10–19% marginal; 2.5% floor with the environmental route arithmetically dead | 0.42–0.56% per eligible voyage |

No mechanism arm has moved either by more than a fraction of the gap. The only
lever that reached A5 was removing crew from the numerator through the immunity
axis, which is an anchor inversion and was refused.

## 2. The five findings that explain the record

1. **The dose scale is a switch, not a gradient.** Emission is
   `10^(curve − environmental_faecal_release_log10_g_per_epoch)`, and the
   release term is swept linearly over `[4, 24]` — twenty orders of magnitude
   in an exponent. Whole-ship epidemic at `adj ≤ 5`, nothing at all at
   `adj ≥ 7`. ~85% of every campaign's design points ran a ship where
   transmission is arithmetically impossible, so the nulls since `BERTH-01` are
   uninterpretable rather than refutations.
2. **Stratified, the contact arms were diluted ~8×, not null.**
   `CONTACT-ARCH-01`'s high corner is +15.2 pp passengers inside a
   transmitting regime against +2.2 pp marginal. A5's deficit is the same in
   the dead, transitional and burning regimes — so it is missing structure, and
   fixing the dose scale will not produce it.
3. **A9's floor is the hand route's own normaliser, not imports or
   ascertainment.** The hand load is pinned at Liu's 3.86 log10 gc/hand against
   an 11.0 curve peak — an implicit −7.14 log10 g of stool per hand that no
   study measured. That channel runs at an `adj`-equivalent of 7.14 whatever
   the swept axis does, which is why every arm varied the dead channel and left
   the live one fixed.
4. **The evidence on the hand route points away from the anchor.** The
   indicator envelope (E. coli per hand ÷ per gram stool) puts a contaminated
   hand at 10^−6.9…−4.1 g, and Liu's own paired stool titres put the bridge at
   −3.5…−4.4 — both *above* the shipped −7.14. An independently sourced
   replacement raises the posting floor. Separately, only 18/71 rinses from
   symptomatic stool-positive hosts were positive, and post-bathroom hands were
   *lower* than routine ones, so the continuously-held hand is refuted and the
   engine's defecation trigger has the sign backwards. No source anywhere fits
   a power law to faecal amplitude: a heavy tail would be a declaration.
5. **The shipped process is already extremely patchy, and there is no linear
   regime to add variance to.** Curvature utilisation
   `sum(1−exp(−sD))/sum(sD)` is 0.013 / 0.29 / 0.61 / ≥0.993 at `adj` = 4 / 6 /
   7 / 8+. At `adj = 4`, Gini on host-epoch effective dose is 0.997 with the
   top 1% carrying 98.8%. Per-route delivered-vs-flat establishment: direct
   contact 0.034 (saturated on rare host-partner draws — 60 draws with `sD ≥ 1`
   in 59 distinct cells, at most two such hosts in any one cell), fomite 0.762,
   droplet 0.944, food and HVAC ≈ 1.000.

## 3. What that leaves as the open mechanism

Not marginal dose variance. The dose is already concentrated; adding another
mean-preserving lognormal is inert where the model is linear and wasteful where
it is saturated. The unresolved quantity is **coincidence** — whether a
concentrated patch reaches *several* hosts through shared event, cell or
partner structure. The measured cell statistics say it currently does not: the
saturating draws are almost all solitary.

The variance inventory in
`telemetry_buffer/observation_model/dose_concentration_findings.md` records
where the model is mean-field: only the host shedding multiplier, host/pathogen
susceptibility and the shedding curve persist. The within-zone exposure
multiplier is redrawn at exposure, so it is not a spatial hotspot. Environmental
release is a scalar and hand load a deterministic decay — the two places event
structure is wanted.

## 4. Designs written and not built

| Design | Where | State |
|---|---|---|
| `HAND-EVENT-01` — marked contamination arrivals, activity-conditioned kinds, within-host amplitude dispersion, removal, background | `docs/proposals/hand_event_release_spec.md` | Off by default, no value adopted; the shipped arm already reproduces Liu's occupancy (0.249 vs 0.254) and no declaration satisfies both of his moments |
| A toilet-scoped fomite pool distinct from the cabin's high-touch pool | `docs/norovirus/fomite_pool_denominator_reconciliation.md` | Prerequisite for entering the flush evidence at all; the toilet's touchable area is unsourced |
| Event-structured environmental release (titre × stool mass × deposition fraction × event rate) | ledger §4 item 00, tranche 38 | Composes to a ~5-log envelope straddling the switch, against the box's 20; not adopted |
| A per-activity `tau` for service roles | `docs/contact_architecture_spec.md` | A single `tau` saturates a 10-h shift like a one-hour meal; no `tau` adopted on any arm |
| The A5 crew deficit | ledger §4 | Regime-invariant, untouched by anything above |

## 5. Rules the next session inherits

- No parameter may be sourced by which value reproduces an anchor. A frozen
  interval is not widened because a fit fails.
- No golden-target development: goldens are change-detectors, not benchmarks.
- Nothing in §4 above is authorized to be built or run without an explicit
  decision: no hand point process, no heavy-tail law, no new release constant,
  no change to `shedding_variance_log10`, `DEFAULT_HETEROGENEOUS_SIGMA_BY_ZONE_TYPE`
  or the −7.14 hand bridge, and no campaign submission.
- Read `.agents/skills/model-parameter-provenance/SKILL.md` before touching any
  epidemiological quantity, and the ledger before quoting any dose figure —
  every dose figure in the repository is void pending a refit.

## 6. The recurring defect archetype

Every finding above is the same shape: **a well-mixed pool standing in for a
small number of concentrated events.** Direct contact taking a zone average,
fomite mass smeared over a deck footprint, emesis omitted in favour of
continuous shedding, the cabin as one large compartment, dose-response redrawn
hourly, and a scalar release carrying a rare-event tail, a per-use hand load and
a background smear at once. Look for it first.
