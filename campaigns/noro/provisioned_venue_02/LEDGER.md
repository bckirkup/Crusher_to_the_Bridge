# NORO-PROVISIONED-VENUE-02 — campaign ledger

**Status: declared — design frozen, no cells submitted.** Edison
Phase-2 calibration: stable conditional distributions for the
venue-placement counterfactual piloted in NORO-PROVISIONED-VENUE-01.
4 hulls × 3 arms (crew_venue / passenger_venue / mixed_venue) × the
full 1,000-seed q30 set per hull = 12,000 cells + 12 canary cells.
Mechanism seam: `provisioned_source.station_zone_pin_weights`
(capacity-weighted per-station placement on a parallel SeedSequence)
added alongside `station_zone_pin` + `source_venue_arm` in
`engines/transmission_core.py`; voyage witness gains
`station_zone_pin_weights`. Extraction contract:
`first_paper_scalar/1.4.0`. Mega spec:
`campaigns/noro/provisioned_venue_02_mega/` (same manifest, elevated
memory — VENUE-01 precedent).

**Reuse verdict (measured, decides the arm count):** the delivered
4,000 q30 runs distribute lots ~uniformly across served venues —
measured shares vs capacity shares deviate up to 25 pp (full table
in DESIGN.md §0) — so the q30 cohort is the *distributed* arm and
`mixed_venue` runs fresh on the weighted pin. All three conditions
run: 12k cells, not 8k.

**Grid:** 4 hulls × 3 arms × 1,000 seeds = 12,000 cells + 12 canary
cells (1 max-lot q30 seed × 3 arms per hull: exp 8169, cls 8169,
spr 8152, meg 8152). Seeds = the full delivered
NORO-PROVISIONED-SOURCE-01 q30 sets (exp 8000–8999; cls/spr/meg
8105–9104), seed-paired across arms and to baseline —
`SEED_MANIFEST.json` is the execution manifest Edison verifies.

**Fixed coordinates:** identical to the delivered
NORO-PROVISIONED-SOURCE-01 q30 baseline and the VENUE-01 pilot —
shipped bp 0.0325/0.0185, nsf 0.29, 288 epochs, syndromic_comp65,
dose 7.57, embarkation 2026-01-10, rung shipped. Only delta:
`station_zone_pin` (+ `station_zone_pin_weights` on mixed_venue) +
`source_venue_arm`.

**Submit gate:** PENDING — the weighted-pin seam must merge first;
image `picard-campaign:noro-provisioned-venue02` builds FROM that
merge SHA (campaign-preflight: local smoke → dry-run count → pinned
digest → canary → STOP and report).

## Waves

| wave | blocks | cells | status |
|---|---|---|---|
| canary | 4 hulls × 3 arms × 1 seed | 12 | not submitted |
| 1 | 4 hulls × 3 arms × 1,000 seeds | 12,000 | gated on canary readout + user |

## Readout log

_(none yet)_
