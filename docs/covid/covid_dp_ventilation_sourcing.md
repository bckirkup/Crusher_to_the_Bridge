# Diamond Princess ventilation and the confinement leak — sourcing note

**Status:** sourcing and audit complete; no constant adopted
**Pathogens:** sars_cov2_resp
**Session:** 2026-09-21

Why this note exists: the COVID arm cannot reproduce the Diamond Princess
post-quarantine turn. Three independent lines point at during-quarantine
transmission rather than at the import geometry or the dose scale:

- `COVID-FIT-01` (`a686114`, 1,180 cells): matching the early onset count
  overshoots the voyage total by 3-6x on every Theta row; its own conclusion is
  "leak first, roster second, imports last".
- `QUAR-ATTR-V2` (`d62f10d`, 240 cells): the two load-bearing during-quarantine
  channels are crew confinement (-74%) and cross-zone pathogen pool transport
  (-66%); near-field air is not load-bearing (+19%).
- Trajectory shape over the 200 `covid_theta_screen_v10` cells (this session):
  no cell reproduces the turn; the cells nearest the observed onset total are
  late-takeoff curves still rising when the voyage ends.

Nothing in this note is adopted as a constant yet. Values are recorded with
their location in the paper and their access class, per
`.agents/skills/model-parameter-provenance` and the org literature rule.

## 1. The quantity the model should be scored on

| Quantity | Value | Source | Location | Grade |
|---|---|---|---|---|
| Effective reproduction number, DP, **before** passenger quarantine | 3.8 (SD 0.9) | Azimi et al. 2021, PNAS 118(8):e2015482118, DOI 10.1073/pnas.2015482118 | Results, Fig. 3B (text of Results quoting the figure) | B — model-derived estimate over 132 accepted iterations, not a direct measurement |
| Effective reproduction number, DP, **after** passenger quarantine | 0.1 (SD 0.2) | same | same | B — same |
| Share of cases transmitted before / after quarantine start | 58% (SD 5) / 42% (SD 5) | same | Results, Fig. 3A | B — same |

The second row is the anchor this arm has been missing. The model's failure is
not that it transmits during confinement — 42% of DP's cases were transmitted
after quarantine started — but that it transmits with **Re > 1** during
confinement (COVID-FIT-01's trace: ~540 infections/day on day 25) where the
record's Re collapses to ~0.1. "Arrest" is the wrong target; the target is a
specific, sourced decay.

## 2. What the ship's air system actually did

The literature is genuinely split here, and the split is load-bearing for any
change we make.

| Quantity | Value | Source | Location | Grade |
|---|---|---|---|---|
| Fresh-air fraction supplied to passenger cabins, DP design practice | ~30% outside air (i.e. ~70% recirculated), cabins sharing a duct, mixed with fresh air, filtered, recirculated | Kosako and Shiiyama 2008, on the DP's central HVAC design, **as quoted by** Almilaji and Thomas 2020, medRxiv 10.1101/2020.07.08.20148775 | Secondary — read in Almilaji §3 Results and Discussion, quoting Kosako and Shiiyama | C — secondary citation of a design-practice statement; not a measurement of the ship's operating state during the outbreak |
| Interior cabins with no access to outside air | ~30% of cabins | Cruise Deck Plans 2020, via Almilaji and Thomas 2020 | Secondary, §3 | C |
| HVAC filtration standard | "comparable to those used by land-based hotels, resorts and casinos"; the operator did **not** state that HVAC was stopped or run at 100% fresh air during quarantine | Princess 2020 corporate statement, via Almilaji and Thomas 2020 | Secondary, §3 | D — an absence of claim, not a specification |
| Ventilation assumption in the accepted DP mechanistic model | high ventilation rates and **no air recirculation**, stated as a deliberately conservative assumption | Azimi et al. 2021 | Abstract and Discussion | B — an assumption of that model, not a finding about the ship |

These two rows disagree about the same ship. Azimi assumed recirculation away
and still attributed 59% (mean) of transmission to aerosols; Almilaji argues
recirculation is what carried virus into sealed cabins.

## 3. The one empirical discriminator found

Almilaji and Thomas 2020 compared symptomatic infection rates during the
quarantine period in cabins **with** a previously confirmed case against cabins
**without** one, and found the former **not significantly higher** (Abstract,
Results; count data from the onboard clinic to 20 February 2020). Grade C —
preprint, not peer reviewed, count data with no individual-level adjustment
beyond the age check they report.

Read plainly, that is evidence *against* within-cabin spread being the dominant
during-quarantine route and *for* a shared-air route reaching cabins that never
held a case. It therefore argues that a cross-cabin air coupling belongs in the
model, and that deleting the leak outright would be the wrong repair.

## 4. What this licenses, and what it does not

**Licensed:** declaring the ventilation geometry the model is currently
assuming, sourcing an outdoor-air fraction and a filtration efficiency for it,
and scoring the during-quarantine Re against 0.1 (SD 0.2).

**Not licensed:** choosing the outdoor-air fraction, the filter efficiency, or
any recirculation knob by which value makes the DP trajectory come out right.
Re after quarantine and the onset curve are anchors this arm is scored on;
tuning a ventilation constant against them is the defect archetype the
provenance skill names, and `COVID-FIT-01` already shows how easily this
surface produces a number that matches one anchor and misses another.

**The question the audit in section 5 was run to settle:** whether the model's
cross-zone pathogen pool transport carries an implicit, undeclared ventilation
assumption. It does not carry an implicit one — outdoor-air dilution and
filtration are both present and declared — but three of the four numbers that
govern the during-quarantine regime are unlabelled literals, and none of them
is reachable as a graded axis from a campaign config.

## 5. Audit of the model against these values

Audited at `main` = `28441bd`.

**The transport operator is not the defect.** `ContamTransportEngine` builds
`dM/dt = A0 M` by probing each zone with unit mass and applies
`expm((A0 - lambda I) dt)` exactly each epoch; `scipy.linalg.expm` is required
and never approximated (`engines/py_contam_bridge.py:215-660`). Per-pathogen
pools are transported with `natural_decay_rate=0.0` because each pool already
ages by its own airborne half-life
(`picard_framework/simulation/ship_simulation.py:953-980`). There is no
numerical leak here to repair.

**Geometry.** The Diamond Princess scenario runs on `mega_cruise_5000`, whose
`air_flow_paths.json` declares `oa_fraction: 0.2` and `hvac_duty: 0.5`, nine
per-deck passenger AHU stars (all nine cabin corridors on a deck share one
plenum), and ducted deck-to-deck trunks at 1,200 m3/h. Cabins therefore couple
to each other through a shared AHU and across decks — the geometry Almilaji
argues for. Against the sourced ~30% fresh air, the model's 20% recirculates
*more*, by a factor of 1.14 on the recirculated share. That is not a leak
explanation.

**Finding 1 — the filter constant is unsourced, and the sourced correction
makes the leak worse.** `hvac.filter_efficiency` defaults to 0.50
(`crusher_labs/config.yaml:368-375`) and its own definition comment
(`py_contam_bridge.py:56-66`) records that this is unsourced and above every
pre-2020 filter: the Healthy Sail Panel puts MERV 8 at 30% removal over
3-10 um and MERV 13 at 90% over 0.3-1 um, and the comment's own intended
pre-2020 sweep is [0.0, 0.30]. The Diamond Princess sailed in February 2020
with filtration its operator would describe only as comparable to land-based
hotels. Moving eta 0.50 -> 0.30 multiplies arriving ducted mass by 1.4: the
era-correct value **increases** during-quarantine transport. It is recorded
here as a provenance defect, and its direction is stated because an
era-correct repair that worsens the anchor is evidence about the mechanism,
not a reason to leave the constant unsourced. eta is applied on the ducted
supply leg only (`py_contam_bridge.py:477, 530-531`), never on returns or
passive paths, and is a global scalar rather than per-zone.

**Finding 2 — confinement strength is set entirely by unlabelled literals.**
None of these carries a source or an evidence grade at its definition:

| Term | Value | Where | Effect |
|---|---|---|---|
| `confinement_isolation_factor` | 0.05 | `data/platforms/mega_cruise_5000/spatial_layout.json:9`; code default `transmission_core.py:875` | scales both inhaled dose and emission for a confined cabin host, so a confined-to-confined pair is suppressed ~400x |
| `corridor_direct_contact_factor` | 0.15 | `spatial_layout.json:10`; `transmission_core.py:884-885` | corridor encounters in cabin corridors |
| `NON_MATE_CONFINEMENT_CONTACT_FACTOR` | 0.01 | `transmission_core.py:878` | non-cabin-mate contact with a confined host |
| `BALCONY_AEROSOL_REDUCTION` | 0.5 | `transmission_core.py:873-874` | inhaled dose in `balcony_partial` zones |

Confinement gates on `_cabin_confinement_active` — quarantined **and**
currently in a `Cabin_Corridor` zone (`transmission_core.py:3409-3413`). A
confined passenger still receives 5% of the cross-zone transported pool
(`_apply_hvac_downstream_doses`, l.4988-4992: AERO-CABIN-04 made it 5%, not
0), cabin mates are exempted back to full strength, and confined hosts are
excluded from fomite deposit and pickup entirely.

**Finding 3 — crew are exempt from the quarantine the runs apply.** SOP-017
declares `exempt_classes` for `crew_general`, `crew_medical`,
`crew_engineering` and `crew_galley` (`data/config/protocols.json`), scoped to
the declaring protocol by QUAR-EXEMPT-01. Days 16-30 the crew circulate
unconstrained while passengers are confined. This matches the record — DP's
crew kept working — and QUAR-ATTR-V2 measured it as the largest single
during-quarantine channel (-74%).

**Finding 4 — there is no graded recirculation knob.**
`hvac.pathogen_pool_transport` is binary (`airflow` | `none`), and
`oa_fraction`, `hvac_duty` and `ach` live in platform JSON that no
`config_overrides` path can reach — `ship_graph.air_flow_paths`
(`run_spec.py:140-143`) can only swap in a different file. This is why
QUAR-ATTR-V2's A2 arm could only test the recirculation path by deleting it
outright, which is a 66% effect of unknown shape: nothing between "as shipped"
and "no cross-zone transport at all" has ever been evaluated.

## 6. Conclusion of the audit

The confinement leak is not a defect in the airflow physics. It is that the
entire during-quarantine regime of this model is governed by four undeclared
numbers — one explicitly unsourced (eta = 0.50) and three unlabelled (0.05,
0.15, 0.01) — none of which has ever been compared against a sourced value,
and none of which is reachable as a graded axis from a campaign config. The
sourced target they should be scored against, Re after quarantine = 0.1
(SD 0.2), has never been an observable in this arm.

