# CAREGIVER-V1
**Date:** 2026-10-02
**Commit:** a8effdb2
**Pathogens:** norwalk_gi, sars_cov2_resp, influenza_a
**Status:** declared

## Question

The party structure shipped under NORO-CAREGIVER-01 is pathogen-neutral —
bookings, berths, service duties — but the caregiver role is not: "the party
mechanism remains but the caregiver roles are different." What is the shared
grammar the per-pathogen caregiver roles live under, and which declared
factors does each role carry?

## Declaration

`docs/caregiver_v1_spec.md` — three roles on one grammar:

- **R1 `cleanup`** (`episode` mode): responder moves toward an emesis event;
  norwalk_gi instantiation already shipped (#855, default-ON, `off` labelled
  baseline).
- **R2 `tending`** (`course` mode): one designated caregiver from
  `party_member_ids ∪ cabin_mate_ids` binds to a symptomatic host for the
  illness window; sustained cabin co-presence upgrade on cabin-air /
  near-field / droplet routes. Declared for sars_cov2_resp and influenza_a.
- **R3 `service`** (`service` mode): crew cabin-service contact per meal
  delivery to a confined host — the crew-service channel `meals_to_cabin`
  currently re-routes tokens without creating. Declared for all pathogens.

Reallocation semantics: R2/R3 tending hours are drawn from the responder's
non-ring contact budget (`budget_mode: reallocate` default; `additive` is
the labelled attribution arm), so the mechanism concentrates the caregiver's
exposure rather than adding ship-level contact.

Decisions taken 2026-10-03 (Benjamin): one designated caregiver; U-shaped
host-age response bands (children + elderly elevated); adult-weighted
responder draw; crew participation matrix — R1 steward channel with
`responder_protection_factor` (gloved cleanup < family napkin bolus), no
crew in R2, R3 crew-only; R1 episode trigger is location-agnostic (public
emesis included); R3 confined-only, cabin-service function first, stamps
the host. Remaining opens live in spec §11.

## Factor table

Per-pathogen intervals and grades are frozen in the spec's §5. Noro cells are
incorporated by reference from NORO-CAREGIVER-01's frozen constants and are
**provisional**: the funnel re-measurement campaign in flight is licensed to
refine them. Respiratory cells are Grade C declarations bounded above by the
Kordsmeyer 2022 cabin-mate aOR 3.27 check (tranche-35 rule: a reproduction
check, never a fit input).

## Supersession

V1 owns the `transmission.caregiver.*` grammar, `party_id`, route label
`caregiver`, `via: caregiver`, and the telemetry namespace. NORO-CAREGIVER-01
remains the authoritative noro implementation and converges to the role
layout on next touch; no immediate refactor. Anything noro-side beyond
episode mode is declared in V1's scope, not the sibling session's.

## Implementation (2026-10-03)

All three roles landed in `engines/transmission_core.py` on the
`transmission.caregiver.{cleanup,tending,service}` grammar; NORO-CAREGIVER-01's
flat keys parse as the cleanup role's shorthand (spec §7 convergence).

- **R1 deltas**: host-age multiplier on both response draws (family and
  steward, capped at 1.0); adult-weighted member pick (a child-only ring
  cannot answer — the steward channel does); `responder_protection_factor`
  discounts only the responder's own pickup, not the mass leaving the
  surface; family presence gate — the ring member must be in the event's
  compartment (same stateroom for a cabin emesis, same zone otherwise),
  else the steward channel answers (§11.3).
- **R2 `tending`**: one-time designation draw at the first symptomatic epoch
  of a presenting course; family-only pool, susceptible members,
  adult-weighted; `reallocate` default relocates the tending caregiver into
  `host.home_zone` for the tending epoch and absorbs them out of the
  standard occupancy pools (their dose arrives under route `caregiver`,
  no double-count); `additive` is the labelled arm; per-epoch tending draw
  `hours/(awake_epochs × hours_per_epoch)`; the pair dose is the cabin-mate
  channel math computed explicitly (compartment pool + withheld-emission
  addback at `min(1, copresence×mult)`, near-field plume at
  `min(1, awake_plume_share×mult)`); report stamp once per designation.
- **R3 `service`**: one delivery per Meal token a confined host's raw
  schedule carries (the rhythm re-route creates no crew contact — this is
  the role that closes it); cabin-service function classes first,
  uniform-crew fallback; respiratory dose is the pair dose at the 5-minute
  epoch share, emetic dose is bounded touches off the cabin's emesis
  patches; stamp at the service report probability on a presenting case.
- Resolved-config echo `delivery.caregiver` in the hull payload and
  `caregiver.resolved` in the funnel payload (spec §8.2 conformance).

Default-ON per the universal-vocabulary rule; `transmission.caregiver.mode:
off` reproduces the pre-V1 draw stream as the labelled baseline. The
greg_mortimer_2020 COVID hull golden moved as the intended mechanism
(attribution and repin in the implementing PR).

## Scope

No campaign, no constant fitting, no Θ refit. The frozen per-pathogen
constants table lives in `parameter_provenance_register.md` §3.11.
Next stage: the NORO-CHANNEL-04 funnel re-measurement canary on the merged
SHA reads what the presence gate, age axis, steward discount and R3 move in
the two broken links; the respiratory arms are live but unmeasured.
