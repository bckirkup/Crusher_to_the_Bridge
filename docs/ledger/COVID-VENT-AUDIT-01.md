# COVID-VENT-AUDIT-01
**Date:** 2026-09-21
**Commit:** #645
**Pathogens:** sars_cov2_resp
**Status:** open

## What this entry records

An audit of the Diamond Princess **confinement leak** — the model's inability
to reproduce the post-quarantine turn — against the sourced ventilation record,
and the one code change it licensed: a graded outdoor-air / recirculation axis.
No epidemiological constant is changed and no value is adopted. The paired-seed
measurement this axis exists to support has **not** been run; it is the open
decision below.

Full sourcing note and audit: `docs/covid/covid_dp_ventilation_sourcing.md`.

## Why the confinement leak, and not import geometry or dose scale

Three independent lines converge on during-quarantine transmission:

- `COVID-FIT-01` (`a686114`, 1,180 cells, imports 1-20 x Theta 3.16e6-3.16e8):
  matching the early onset count overshoots the voyage total by 3-6x on every
  Theta row; its own conclusion is "leak first, roster second, imports last".
  The requested import x Theta campaign is therefore **closed as negative**, not
  outstanding.
- `QUAR-ATTR-V2` (`d62f10d`, 240 cells): the two load-bearing during-quarantine
  channels are crew confinement (median 829.5 -> 212.5, -74%) and cross-zone
  pathogen pool transport (348.5 -> 119, -66%); near-field air is not
  load-bearing (+19%).
- Trajectory shape over the 200 `covid_theta_screen_v10` cells (`a9b4f1f`, this
  session, read-only): no cell reproduces the turn; the cells nearest the
  observed onset total are late-takeoff curves still rising when the voyage ends.

Independently, imports > 1 is not licensed by the record: Sekizuka et al. 2020
PNAS (DP whole-genome sequencing, all isolates carry G11083T) concludes a single
introduction before quarantine. A multi-import sweep would fit a scenario
geometry the record fixes at one.

## The anchor this arm has been missing (measured elsewhere, sourced here)

Azimi et al. 2021, PNAS 118(8):e2015482118 (Results, Fig. 3B; grade B,
model-derived over 132 accepted iterations): DP effective reproduction number
**3.8 (SD 0.9) before** passenger quarantine, **0.1 (SD 0.2) after**, with
58% / 42% of cases transmitted before / after. The target is not arrest — 42%
of DP's cases were transmitted after 5 Feb — it is a specific sourced decay to
Re ~ 0.1. This arm has never carried Re after quarantine as an observable.

## Audit findings (measured against the code at `28441bd`)

1. **The transport operator is not the defect.** `ContamTransportEngine` applies
   `expm((A0 - lambda I) dt)` of a probed linear operator exactly each epoch;
   `scipy` is required and never approximated
   (`engines/py_contam_bridge.py:215-660`).
2. **`hvac.filter_efficiency = 0.50` is unsourced and the era-correct value makes
   the leak worse.** Its own definition comment records that 0.50 is above every
   pre-2020 filter (Healthy Sail Panel: MERV 8 = 0.30, MERV 13 = 0.90) and that
   the intended pre-2020 sweep is [0.0, 0.30]. Moving eta 0.50 -> 0.30 multiplies
   arriving ducted mass by 1.4. Recorded, not changed.
3. **Confinement strength is set entirely by unlabelled literals** —
   `confinement_isolation_factor` 0.05 (dose and emission, ~400x on a confined
   pair), `corridor_direct_contact_factor` 0.15,
   `NON_MATE_CONFINEMENT_CONTACT_FACTOR` 0.01 — none carrying a source or grade.
4. **Crew are exempt from the quarantine the runs apply** (SOP-017
   `exempt_classes`, all four crew classes), matching the record and the
   QUAR-ATTR-V2 -74% channel.
5. **No graded recirculation knob existed.** `hvac.pathogen_pool_transport` was
   binary (`airflow` | `none`), and `oa_fraction` lived in platform JSON no
   `config_overrides` path can reach — which is why QUAR-ATTR-V2 could only test
   cross-zone recirculation by deleting it entirely. This is the gap the change
   closes.

## The change (#645)

`hvac.outdoor_air_fraction_override`, absent by default. Set to a float in
[0, 1], it replaces every HVAC zone's declared `oa_fraction` at operator-build
time and touches nothing else (`hvac_duty`, `ach`, cross-zone links, passive
adjacency unchanged). `1.0` is fully outdoor air (no recirculated mass returns
through the plenum), `0.0` full recirculation. Default preservation is guarded
by two tests asserting the built operator matrix is exactly equal to today's
with the key absent, and exactly equal again under an override of `0.2` (the
value `mega_cruise_5000` already declares). This is an override of
platform-declared geometry, not a sourced physical constant.

## Status of the evidence

- **Measured:** the audit findings and the sourced anchor above.
- **Inferred:** that a graded recirculation reduction is the most likely single
  lever to bend the during-quarantine Re toward 0.1, because it is the one
  load-bearing channel (QUAR-ATTR-V2, -66%) that had no graded axis. Not yet
  demonstrated.
- **Hypothesis, explicitly not established:** that any single ventilation value
  reproduces DP's turn. The literature splits (Azimi assumed *no* recirculation
  and still got 59% aerosol; Almilaji and Thomas 2020 found during-quarantine
  symptomatic rates in cabins *with* a prior case not significantly higher than
  those without, i.e. a shared-air route into untouched cabins — evidence
  against deleting the coupling). Choosing a value by which one makes the DP
  trajectory come out right is not licensed.

## Single open decision

Merge #645, then run the paired-seed ventilation bracket — as-shipped
(`oa_fraction` 0.2) vs Azimi's no-recirculation case (`override` 1.0) vs
intermediate points, at fixed Theta on matched seeds, scored on the
during-quarantine Re against 0.1 (SD 0.2) with the criterion frozen in a
`declared` design file before any cell runs — canary first, then stop and report.
