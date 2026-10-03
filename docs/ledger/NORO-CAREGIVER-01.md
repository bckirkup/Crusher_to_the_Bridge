# NORO-CAREGIVER-01
**Date:** 2026-10-02
**Commit:** declared
**Pathogens:** norwalk_gi
**Status:** declared

## Question

CHANNEL-03 measured the conversion gap as two broken links —
infected→symptomatic at 0.17–0.41 (needs ~0.6) and eligible→reported at
0.17–0.32 (needs ~0.4). Grounding (user, this line): people move toward
emesis and diarrhoea — the family member, spouse, or caregiver who
rushes to clean it up — and in the cholera literature (Ewald), caregiver
nursing shifted selection toward severe courses. Does a party-mediated
caregiver mechanism — cleanup exposure + discovery — move both links on
physics rather than fitted constants?

## Mechanism

`party_id` multi-stateroom travelling parties (1–4 contiguous cabins
per booking, passenger classes only); per emesis episode a caregiver
response draw from `party_member_ids ∪ cabin_mate_ids` (plus a VSP-
grounded steward fallback); exposure dose composed from the episode's
own `surface_load` through the existing fomite-pickup and hand→mouth
constants times a sourced cleanup-contact count [9, 34] (Overbey 2021,
Grade B); discovery stamps a report that bypasses the self-report
hazard at the same-epoch syndromic pass with `via: caregiver`
attribution.

`transmission.caregiver.mode: on` shipped default; `off` is the
labelled pre-change baseline. Design + frozen constants:
`docs/norovirus/noro_caregiver_01_design.md`.

## Scope

Mechanism + unit tests only. The funnel re-measurement is the next
stage — canary ≥20 seeds at one CHANNEL-03 cell, then stop and report.

## Report-immediately

- caregiver infection share >10% of transmissions at defaults
- zero responses at response_probability 0.9
- caregiver report on a non-emetic course
