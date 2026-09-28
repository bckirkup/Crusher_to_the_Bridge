# EXPO-CAP-01: per-shedder per-epoch exposure-reach budget on the pooled-air routes

> **Status:** **Implemented, on by default** — `transmission.exposure_cap` in
> `engines/transmission_core.py`; `enabled: false` is the labelled baseline.
> The bound introduces **no new magnitude constants**: it reuses the
> CONTACT-ARCH-01 per-activity contact rates (and the POLYMOD 13.4/day control
> when that block is undeclared), which carry their own sourcing.
> Apply-scope: the catalogued cruise classes only (the same platform gate as
> SHIP-RHYTHM-02); naval hulls and legacy platforms are unchanged either way.

## 1. The defect

The two pooled-air routes dose every susceptible in the air unit:

- `_droplet_unit_doses` — the far-field share of a shedder's continuous
  emission enters the unit's well-mixed pool and every susceptible occupant
  inhales it.
- `_apply_hvac_downstream_doses` — mass transported out of a source unit
  reaches every susceptible in each downstream air unit.

Under this contract a shedder's per-epoch reach is bounded only by air-unit
occupancy. The rhythm-era measurement that motivates this item is
COVID-TAKEOFF-ATTR-01/-RERANK: the takeoff residual is challenge-count-shaped
(dosed-set median ~650/epoch on the 10-cell seed family,
`challenged_share` saturating at 1.0 under any per-epoch partition) — the
per-epoch exposure set was zone-scale, not contact-scale. The ~50–100
hosts/epoch bound implied by the 197-record is context for what a
contact-realistic reach looks like, **not** a fit target for any constant.

## 2. Why the bound is per-host, not per-venue

Two admissible bounding mechanisms were on the table; the sourced
contact-structure evidence selects the per-host one:

- **Per-venue capacity bound — rejected.** A capacity cap would only bind
  where a venue hosts more occupants than it can hold; the model's zones are
  already sized so occupancy ≤ capacity, and the dosed set is per-epoch
  susceptible count, not cumulative occupancy. A capacity bound at or above
  the zone's already-modelled occupancy moves nothing. Below it, the bound
  would be fitted to the instrument — prohibited.
- **Per-host contact budget — adopted.** Pung et al. 2022 (Nat Commun
  13:1956, cruise-ship wearable close-contact network) measures the budget
  directly: passengers median ~20 unique close contacts/day (IQR 10–36),
  crew ~10 (IQR 6–18). POLYMOD (Mossong et al. 2008) supplies the control-arm
  rate of 13.4/day already shipped as `POLYMOD_CONTACTS_PER_DAY`. Shirreff
  et al. 2024 shows the aggregate contact rate does not scale with venue
  occupancy (frequency-independent), which is the measurement that rules
  venue capacity out as the operative bound and makes the per-host budget
  the declared mechanism.

## 3. The mechanism

When `transmission.exposure_cap.enabled` is true **and** the platform carries
a rhythm catalog:

- For each (epoch, pathogen, emitting shedder) a budget
  `K ~ Poisson(mean)` is drawn on a dedicated `_exposure_cap_rng` stream
  (spawned via `seed_seq.spawn` only while the cap is active). The mean is
  the shedder's own per-epoch contact rate: the CONTACT-ARCH-01 activity rate
  for the shedder's unit this epoch — saturation-adjusted where the block
  declares `saturation_hours` — or `POLYMOD_CONTACTS_PER_DAY` when the block
  is undeclared; both multiplied by `voyage_contact_multiplier`.
- In each air unit and HVAC downstream job, each emitting shedder samples
  `min(K_remaining, n_susceptible)` of the unit's susceptibles without
  replacement. The union over shedders is the unit's dose-forming cohort.
- A susceptible **inside** the cohort receives the pooled dose exactly as
  before. A susceptible **outside** receives zero from the pooled term —
  the droplet concentration chain is zeroed for the target, and the HVAC
  job skips the target entirely.
- Budgets are consumed in pathway order: the shedder's own-unit droplet pool
  first, then HVAC jobs in the deterministic sorted order of
  `_hvac_air_units`. A shedder whose budget is spent in its cabin breathes
  no transported dose downstream that epoch — the cabin-mate spending is the
  declared mechanism's first call on the budget.
- The partner-bounded routes are untouched: direct contact draw, near-field
  plume (already partner-bounded by AERO-SPLIT-01), the dining table, and
  the cabin-mate addback (an unconfineable pair mechanism — a cabin mate
  shares breathing air regardless of a contact-count budget). Fomite,
  emesis-aerosol patch, and food routes are structurally bounded already and
  are unchanged.

The claim is about *dose-forming reach*, not the physical presence of aerosol:
the transported mass still exists in the unit; the cap says it does not find a
susceptible's breathing zone outside the shedder's per-epoch contact envelope.
That is the same reading AERO-SPLIT-01 gives the near-field partner draw —
the contact record bounds who the emission reaches, not the mass accounting.

## 4. Flag and RNG hygiene

`enabled: false` is the labelled baseline: `_init_exposure_cap` sets the
engine inert, **no** cap stream is spawned, zero draws are consumed, and a
flag-off run is byte-identical to the pre-change tree on fixed seeds. Because
the spawn is conditional, an on-vs-off contrast isolates the mechanism's
physics rather than a shifted stream (the dedicated stream also keeps cap
draws from perturbing the shared stream when on).

Application is gated by `platform_has_rhythm_catalog(platform_id)` — the
catalogued cruise classes (mega_cruise, contemporary_cruise,
classic_cruise, expedition_cruise, starship_galaxy, starship_constitution).
Naval run specs inherit this `config.yaml` via `legacy_yaml`, so the flag
alone is not sufficient: without the platform gate a naval run would leave
its measured baseline. Legacy hulls (e.g. `messy_cruise_500`) and
platform-less rigs have no catalog and are unchanged either way.

`include_fixed_rings` (default `false`, RING-CAP-V1 labelled arm) changes
what the budget *spends on* rather than whether it binds: when true, each
shedder's pre-committed fixed-ring deals — susceptible cabin mates with a
positive co-presence share this epoch, plus same-table partners (a dealt
meal-table entry, or the fixed dining party while the shedder stands on a
Meal token) — are counted at its first budget draw of the epoch and
subtracted from the draw, so the pooled cohort samples only the remainder.
The rings still dose; unavoidable contacts displace incidental pooled
reach. Adjacent-table deals stay in the pooled reach — that ring is venue
structure, not a pre-committed contact. The accounting is deterministic
(counted, not drawn), so a flag-off run stays byte-identical and no stream
is consumed; it is inert while the cap itself is inactive.

## 5. Expected signature and the bounded re-rank

The cap bounds the two saturating routes; the residual dosed set is then
dominated by the declared partner-bounded channels:

- cabin-mate ring (~135–150/epoch under rhythm, per COVID-TAKEOFF-ATTR-01),
- direct contact (~60–66/epoch),
- near-field plume + dining (~16–20/epoch),
- pooled routes ≈ Σ_shedders K_s, i.e. of order the emitting-shedder count ×
  the per-epoch contact budget (~0.6–0.8 hosts/shedder/epoch at the shipped
  rates).

The bounded re-rank reruns `tools/covid_takeoff_attribution.py` on the
established 10-cell seed family (20200205–20200214) and the NORO placement
metric (`tools/noro_diag/growth_chain_census.py`) on the 11 ignited seeds,
cap-on vs the flagged-off baseline, and records both in the ledger entries
`COVID-EXPOCAP-01` and `NORO-EXPOCAP-01`.

## 6. Out of scope

No Θ or dose-ledger changes; no anchor fitting (the cap magnitude comes from
the sourced contact structure only); no new venues, topology, or capacity
bookkeeping — the only "capacity" consumed is the shedder's own contact
budget; naval platforms unchanged.
