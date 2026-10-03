# CAREGIVER-V1
**Date:** 2026-10-02
**Commit:** a8effdb2
**Pathogens:** norwalk_gi, sars_cov2_resp, influenza_a
**Status:** declared — spec only, no engine code

## Question

The party structure shipped under NORO-CAREGIVER-01 is pathogen-neutral —
bookings, berths, service duties — but the caregiver role is not: "the party
mechanism remains but the caregiver roles are different." What is the shared
grammar the per-pathogen caregiver roles live under, and which declared
factors does each role carry?

## Declaration

`docs/proposals/caregiver_v1_spec.md` — three roles on one grammar:

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

## Scope

Spec only. No engine code, no campaign, no constant fitting, no Θ refit.
Next stage: respiratory (COVID/flu) design doc + implementation arm, or the
noro funnel readout landing first and refining the provisional cells.
