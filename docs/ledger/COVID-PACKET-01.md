# COVID-PACKET-01
**Date:** 2026-09-29
**Commit:** 29a15344
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 29a15344

First measurement of the dose-arrival *packet* structure — the
granularity a cooperative (non-independent-action) dose law lives on,
one level below the host-level accrued-dose field of COVID-VULN-01. The
question it settles for the cooperative hypothesis (COVID-COOP-01): does
the far-field pool ever deliver a carrier packet holding ≥ n virions to
one cell — or is the measured ~1-virion-per-carrier emitted soup
preserved all the way to deposition?

## Instrument

`tools/covid_takeoff_attribution.py --packet-arrivals` (opt-in;
default output byte-identical): on each epoch, every dosed host's
post-efficiency per-channel dose increment is recorded —
`mechanism.packet_arrivals = {by_epoch_channel, by_channel,
by_host_channel}` (host/channel increments as declared log10
histograms; dose units, susceptibility-free). The droplet pathway's
post-efficiency dose is split into the declared rings by naive shares —
same `channel_dose_post` basis as the onset rows.

`tools/covid_packet_analytic.py` convolves the emitted field with the
declared COVID-COOP-01 packet model: delivered RNA copies = dose ×
`EMISSION_BRACKET_COPIES_PER_EPOCH` [4.2e3, 5.8e7] (Grade B, never a
point); carrier occupancy K ~ Poisson(μ_class) — dry far-field
(zone_pool, hvac_airborne, other) μ ∈ [0.004, 0.1] copies/carrier (the
measured ≤5 µm spectrum), wet rings (cabin_mate_ring, dining_ring,
near_field_plume) μ ∈ [0.04, 500] (declared envelope for the 20–100 µm
class); E[packets ≥ n] = copies × P(K ≥ n)/μ, reported over bracket ×
μ-range corners plus the interior μ grid (E is nonmonotone in μ).

## Measurement (covid.H3 declared replay, Θ 2.37e11, seed 20200205 — the
takeoff-conditioned anchor cell; recorded onsets 1,928, infections
3,581, 3,710 dosed hosts)

Arrival structure: zone_pool reaches ~15 hosts per epoch over 574
epochs (42,374 increments, Σ dose 2.3e-3); near_field_plume 547 epochs
bursting to 253 hosts (20,411, 4.5e-2); cabin_mate_ring 171,816
increments (6.2e-2); dining_ring 13,519 (2.5e-2); hvac_airborne 14,026
(1.0e-5); contact 60,388 (6.2e-8). Max single host-epoch increment
1.1e-2 dose units (near-field) → [45, 6.3e5] copies under the bracket.

Expected packets ≥ n copies per cell, [bracket-lo, bracket-high] ×
declared-μ envelope:

| channel | n ≥ 2 | n ≥ 3 | n ≥ 5 |
|---|---|---|---|
| hvac_airborne | [8.4e-5, 27] | [1.1e-7, 0.90] | [9.0e-14, 4.5e-4] |
| zone_pool | [0.019, 6.2e3] | [2.6e-5, 206] | [2.1e-11, 0.10] |
| near_field_plume | [0.38, 6.9e5] | [0.049, 5.1e5] | [3.9e-6, 2.5e5] |
| cabin_mate_ring | [0.52, 9.6e5] | [0.068, 7.0e5] | [5.4e-6, 3.5e5] |
| dining_ring | [0.21, 3.9e5] | [0.027, 2.8e5] | [2.2e-6, 1.4e5] |

Expected hosts ever seeing a ≥ n-copy packet follow the same interval:
at the favorable corner ~450 hosts see a zone_pool ≥2 packet, ~230–375
a wet-ring one; at the dry low end essentially none do.

## Read

1. **The far field's packet floor is n*-resolved, not a blanket
   zero.** HVAC airborne is dead to cooperativity at every corner
   (≤0.9 packets ≥3 cell-wide); the zone pool reaches thousands of
   ≥2-copy packets only at bracket-high, collapses to ≤206 at n ≥ 3
   and ≤0.1 at n ≥ 5. A cooperative law with threshold n* ≥ 3 makes the
   entire far field inert on this field — the exact regime the
   takeoff-residual argument needs (PCR-load without infectivity); at
   n* = 2 the pool stays live at the bracket's high end and the
   mechanism only partially suppresses.
2. **The wet rings are the only guaranteed multi-copy carriers** —
   "the closest circles": cabin-mate, dining, and plume channels hold
   ~10⁵–10⁶ ≥2-copy packets at the favorable end of their declared
   loading, reaching ~200–450 hosts. A cooperative law suppresses
   everywhere *except* the persistent-partner rings — a genuinely
   different mechanism family than the cohorting/lever candidates of
   COVID-TAKEOFF-ATTR-01, because it carves by carrier structure, not
   by contact bookkeeping.
3. **Copies are the unit; complete virions are the gap.** Every
   packet count is a strict upper bound on the cooperative-relevant
   count — a packet of K copies carries ≤ K complete virions, and the
   complete-genome fraction of emitted virions is unbounded
   (COVID-COOP-01 `?nr-term`). The n* ≥ 3 far-field death is robust to
   that gap (upper bound already ~0); the n* = 2 zone-pool interior is
   not — it could shrink with the complete fraction.
4. **One cell, one seed, one ship class.** The instrument result —
   channel-resolved packet mass, bracket-width-dominated at n* = 2 —
   is a measured field, but the fleet claim (whether the pool's
   packet tail varies across classes/seeds enough to change the
   verdict) needs the conditioned array.

## What this buys

The discriminating axis for the A/B is now measurable rather than
assumed: a cooperative-law arm needs only (a) the packet model as
declared here and (b) a dose-response that zeros conversion below n*
per carrier. Before spending an array on it, the n* = 2 vs n* ≥ 3
branch point and the complete-fraction `?nr` bound decide whether the
mechanism can move the takeoff residual at all — the analytic check on
this field is cheap and should run per-cell at array scale only if the
single-cell read survives.
