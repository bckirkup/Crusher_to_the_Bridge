# Ambient exposure audit and fix plan (open decks, balconies, hatches)

> **Status:** Partly implemented. Landed: stage 1 (`ambient_openings` schema
> and native/export machinery, `CONTAM-AMBIENT-OPENING-SCHEMA-01`), stage 2
> (outward opening flow as a field-lane boundary sink,
> `CONTAM-AMBIENT-OPENING-BOUNDARY-01`), and the cruise half of stage 3
> (`makeup_louvre` records on the six cruise hulls,
> `CONTAM-AMBIENT-MAKEUP-CRUISE-01`). Still proposed: stage 3 for the fiction
> hulls and stages 4+. The audit below was measured against
> `origin/main` `15beae6b` (post-#1250/#1251). Audit ledger:
> [`../ledger/CONTAM-AMBIENT-EXPOSURE-01.md`](../ledger/CONTAM-AMBIENT-EXPOSURE-01.md).
> This document lives in `docs/proposals/` because the representation it
> proposes is not in-tree; its audit findings are measured, but it is not
> documentation of current behaviour. Governing context:
> [`contam_field_adjudication_audit_and_fix_plan.md`](contam_field_adjudication_audit_and_fix_plan.md)
> (this plan refines its stage 6 and does not decide its stage 3).

**Evidence vocabulary.** *Measured* = computed this session from the tree at
`15beae6b` with committed tools and the local ContamX binary
`third_party/contamx/contamx3` (steady state, no seeds, no AWS). *Cited* =
taken from a prior ledger without re-derivation. *Inferred* = reasoned from
code, not run. *Hypothesis* = neither.

**Owner hypothesis under test (Benjamin, 2026-11-16).** "open decks, for
example, are probably not being modeled as exposed, as well as active
ventilation and routinely open hatches".

## 1. Fleet inventory and verdicts

### 1.1 Definitions

The inventory uses committed classifiers only, so it is reproducible
(Appendix A):

- **Weather zone** — `tools.hull_audit._is_exterior`: spatial zone of type
  `Free` whose id contains an exterior hint (`tools/hull_audit.py:81-84`,
  `:190-192`). This is a lexical classifier on zone ids. It is the
  repository's own definition of "exterior"; it is not a survey of the
  drawings, and the per-zone list in the ledger is the thing to correct if a
  zone is misfiled.
- **Balcony zone** — spatial zone with
  `cabin_ventilation_type == "balcony_partial"`. These are cabin-corridor
  blocks, not individual staterooms.
- **Opening edge** — `adjacency` entry in `air_flow_paths.json` whose `type`
  is one of `open_deck`, `deck_walkway`, `open_front`, `open_area`,
  `hangar_door`, `hatch`, `service_hatch`.
- **Ambient link** — `cross_zone_links` entry with an `ambient` endpoint.
- **Outdoor exchange (1/h)** — the only ambient coupling a zone has today:
  its HVAC group's `ach × duty × oa_fraction` (or `ach` for the duty-0,
  `oa_fraction` 1.0 extract branch). Ungrouped zones have none.

### 1.2 Fleet totals (measured, 82 platforms)

| Class | Count | Hulls | Current ambient coupling |
|---|---|---|---|
| Weather zones | 243 zones, 505,255 m³ | 78 | 112 ungrouped; 124 have zero outdoor exchange; the rest get it only through an HVAC group (`VENT_Weather` `ach` 1.0 on 17 hulls gives 0.5/h at duty 0.5; `AHU_Weather` on 4 hulls declares `ach` 0.0) |
| Balcony zones | 153 zones, 157,340 m³ | 6 | All in an HVAC group; outdoor exchange is the same group OA an interior cabin block gets. No balcony path |
| `open_deck` edges | 17 | 6 | Zone-to-zone only |
| `deck_walkway` edges | 24 | 15 | Zone-to-zone only |
| `open_front` edges | 11 | 5 | Zone-to-zone only |
| `open_area` edges | 3 | 1 | Zone-to-zone only |
| `hangar_door` edges | 3 | 2 | Zone-to-zone only |
| `hatch` edges | 35 | 9 | Zone-to-zone only |
| `service_hatch` edges | 28 | 15 | Zone-to-zone only |
| Ambient links | 12 | 11 | All `zone → ambient` prescribed exhaust sinks; none has `ambient` as a source |

Balcony zones per hull: `mega_cruise_5000` 54, `diamond_princess` 32,
`spirit_cruise_3000` 28, `classic_cruise_1900` 26, `expedition_cruise_450` 8,
`greg_mortimer` 5. The 12 ambient links are listed in the ledger. The
per-hull table and the per-zone list (hull, zone, `spatial_layout.json`
line, volume, HVAC group, outdoor exchange) are in the ledger, sections
"Per-hull table" and "Per-zone inventory".

No adjacency edge in the fleet has an `ambient` endpoint. Every opening
edge, whatever its type, connects two modelled zones.

### 1.3 Current treatment, both lanes

| Element | Native bridge | ContamX export |
|---|---|---|
| Weather zone | An ordinary finite-volume zone. Contaminant leaves only by HVAC return (`engines/py_contam_bridge.py:453-474`: full room flow to the plenum, `room_flow * (1.0 - oa)` back) and by adjacency to other zones. An ungrouped weather zone has no removal to ambient at all | An ordinary zone with one envelope-leak orifice to ambient like every other zone (`tools/contamw34_prj.py:791-819`), area 0.0001 m² (`data/contam_hobbyist/orifice_catalog.json:136-140`, element built at `tools/contamw34_prj.py:562-565`). Wind pressure is applied to that leak only |
| Balcony zone | Same HVAC path as an interior cabin block. `cabin_ventilation_type` is not read by the bridge | Same as any zone; the field is not read by the exporter |
| `open_deck` and other untyped opening edges | Fixed 10 m³/h in each direction between the two named zones: `passive_rates` has four keys and everything else takes the default (`engines/py_contam_bridge.py:638-658`; mirrored at `tools/hull_audit.py:62-68`) | A pressure-driven orifice between the two zones (`tools/contamw34_prj.py:821-846`), element from `resolve_orifice_type` (`tools/contam_hobbyist.py:86-98`): `open_deck` 8 m², `open_front` 6 m², `promenade` 10 m² (`orifice_catalog.json:80-87`, `:105-107`). Seven cruise/fiction hulls override `open_deck → promenade` (`data/platforms/*/contam/hobbyist_overrides.json`, line 13 or 15) |
| `hatch`, `service_hatch` | `service_hatch` fixed 8 m³/h each way; `hatch` takes the 10 m³/h default (`engines/py_contam_bridge.py:639-649`) | 0.36 m² orifice (`orifice_catalog.json:25-32`) on the `HatchOccasionalW` schedule (`data/contam_hobbyist/schedule_templates.json:125-126`), zone-to-zone |
| Ambient link | One-way sink path, `sink=True` (`engines/py_contam_bridge.py:588-617`); mass leaves, nothing is returned (`:693-717`) | Constant-flow fan to ambient node −1 (`tools/contamw34_prj.py:905-931`). `ambient` as a source is rejected (`:937-941`) |
| Outward envelope leak | Not represented | Removes contaminant under `boundary_sink` (#1247; `engines/contamx_transport.py:184-188`, `:222-229`) |

### 1.4 Verdict on the owner hypothesis, per class

| Class | Verdict | Basis |
|---|---|---|
| Open/weather decks, 124 zones with zero outdoor exchange | **Confirmed** (measured) | Sealed finite rooms natively; in export, coupled to ambient through 0.0001 m² only |
| Open/weather decks, 119 zones in an HVAC group with OA | **Partial** (measured) | They do exchange with outdoors, but as a mechanically ventilated room at a declared `ach` (typically 0.5/h), not as an open deck. Not "unexposed"; exposed by the wrong mechanism and at an unsourced rate |
| Balconies | **Confirmed** for the airflow layer (measured) | No airflow path in either lane; the only balcony effect is the transmission-side factor (§3) |
| Routinely open hatches, weather doors, hangar doors | **Confirmed** (measured) | Every such edge is zone-to-zone. No hatch or door reaches ambient, and where the far zone is a weather zone that zone is itself not exposed |
| Active ventilation — supply side | **Refuted** (measured) | HVAC outdoor air is modelled in both lanes: native `oa_fraction` dilution, export AHS outdoor-air and exhaust legs |
| Active ventilation — exhaust make-up | **Confirmed** (measured, §5) | The 12 prescribed exhaust sinks have no make-up path except the 0.0001 m² envelope leaks |

The hypothesis is therefore refuted for one sub-class only (mechanical
outdoor-air supply) and partial for weather zones that sit in an HVAC group.

## 2. Representation design

### 2.1 Requirements

1. Bidirectional: clean ambient air in **and** contaminant out, in both
   lanes, from one authored record.
2. Additive: hulls with no new record behave exactly as today.
3. No change to any existing `flow_rate_m3h` value.
4. ContamX must be free to solve direction and magnitude; the native lane
   must not need a pressure solve.

### 2.2 Proposed data model

A new top-level list in `air_flow_paths.json`, `ambient_openings`, separate
from `adjacency` (which stays zone-to-zone) and from `cross_zone_links`
(whose `ambient` endpoint stays a one-way prescribed sink):

```json
{"zone": "PoolDeck", "type": "open_deck", "area_m2": 40.0,
 "exchange_m3h": null, "azimuth_deg": null, "schedule": "always_open"}
```

`type` names a catalog entry (open deck edge, balcony door, weather hatch,
weather door, hangar door, make-up louvre). `area_m2` is geometry read from
the drawing. `exchange_m3h` is optional and is the native-lane rate; when
null it is derived from the declared axis in §4.

Overloading `adjacency` with `to: "ambient"` was rejected: both lanes skip
or mis-handle an adjacency whose endpoint is not a zone
(`tools/contamw34_prj.py:836-837` drops it; the native builder would create
a path into a non-existent node), and it would silently change hulls
authored against today's semantics. Reusing `cross_zone_links` was
rejected because that record means "prescribed one-way fan".

A second option for weather zones, **aliasing the zone to ambient** (the
deck is not a zone at all), is listed as an owner decision (§7, D2). It is
simpler but removes the deck as a place where near-field exposure and
occupancy are tracked.

### 2.3 Native bridge

The native operator is fixed-flow and linear, with no pressure solve and no
ambient concentration state. Exchange at rate Q with ambient air at zero
concentration contributes `−(Q/V)·C` to the zone and nothing else: the
inflow leg carries no contaminant. So bidirectional exchange with clean
ambient is exactly the existing sink path at flow Q
(`engines/py_contam_bridge.py:602-617`, `:693-717`). The clean supply does
not need a source term; it needs a statement in the path record that the
sink is an exchange, so mass-balance audits do not read it as net
extraction.

Change required: one new builder that turns each `ambient_openings` record
into a `sink=True` path of type `ambient_exchange_<type>`. This is
additive. (Inferred from code; not implemented or run.)

This equivalence fails if ambient is ever given a non-zero concentration
(for example re-entrainment of exhaust into a balcony). That is out of
scope and is stated so nobody assumes it later.

### 2.4 Exporter and path_map

Each record becomes one two-way orifice between the zone and ambient node
−1, built the way the envelope leak already is
(`tools/contamw34_prj.py:791-819`): element sized from `area_m2` through
`orifice_params_for_area` (`tools/contam_hobbyist.py:75-83`), wind profile
and wall azimuth attached, opening schedule from the type. The path_map
entry gets a new `kind`, `ambient_opening`, with `from`/`to` as for
`envelope_leak`. The rejection of `ambient` as a `cross_zone_links` source
(`tools/contamw34_prj.py:937-941`) stays.

Change required: one new emitter and one new path_map kind. Additive.

### 2.5 ContamX transport semantics and #1247

ContamX solves the flow through the opening. The field lane must then treat
it as a boundary path:

- **Outward flow** removes contaminant. This is the #1247 `boundary_sink`
  rule, which today matches `envelope_leak` only
  (`engines/contamx_transport.py:222-229`). The predicate must be widened
  to `ambient_opening`. This is the one non-additive line in the design: it
  extends an existing predicate rather than adding a path type.
- **Inward flow** brings clean air. In the field lane this needs no
  contaminant term, but the zone's total outflow must include the air that
  came in, which it already does because ContamX conserves mass.
- **Two-way flow through one large opening.** A single ContamX orifice
  carries one net flow. A large opening with near-zero net pressure
  difference would report near-zero flow although turbulent exchange is
  large. ContamX has two-way opening elements; whether the exporter should
  emit one, or two orifices at different heights, is an open design point
  to be settled in the first implementation PR with a witness, not here.

### 2.6 Parity between lanes

The native lane uses a declared exchange rate; the ContamX lane solves a
flow from area, wind and pressure. They will not agree by construction.
`tools/contam_flow_compare.py` should report the two side by side per
opening; agreement to within the declared axis width is the acceptance
criterion, not equality.

## 3. Transmission-layer reconciliation — OWNER DECISION

Today the balcony effect lives entirely in the transmission layer:

- `BALCONY_AEROSOL_REDUCTION = 0.5` (`engines/transmission_core.py:1196-1197`),
  applied by `_aerosol_ventilation_factor` to any zone declared
  `balcony_partial` (`engines/transmission_core.py:5787-5792`), whichever
  transport engine is running.
- `DEFAULT_CONFINED_CABIN_ABSENCE_HOURS_PER_DAY = 1.0`
  (`engines/transmission_core.py:1232-1238`), a declared axis whose
  rationale includes "balcony cabins had open balcony air on demand".

If an airflow-side balcony opening is added, the zone concentration already
falls because of outdoor exchange, and the 0.5 factor then halves exposure
again. That is a double count. The absence-hours axis overlaps more weakly:
it removes the occupant from the cabin air, it does not dilute it.

This session does not decide. Both constants are epidemiological; changing
either needs the `model-parameter-provenance` skill and an owner decision.

| Option | What changes | Consequence |
|---|---|---|
| A. Keep both, add nothing airflow-side for balconies | Nothing | No double count. Balcony stays a transmission-only scalar; ContamX lane never sees it |
| B. Airflow-side opening replaces the factor | Factor becomes 1.0 where an `ambient_openings` balcony record exists | Single mechanism, visible to both lanes. Moves every balcony-hull baseline; needs paired-seed attribution |
| C. Keep the factor, add the opening, accept the overlap | Opening added | Double count, declared. Not recommended |
| D. Split by engine | Factor applies only when the transport engine has no balcony opening | No double count, but two code paths to keep in step |

Recommendation: A now, B as the target once §4 gives a sourced exchange
magnitude. See D3 in §7.

## 4. Literature basis plan for magnitudes

Retrieval followed `consensus-literature-retrieval`: every query passed
`include_full_text_chunks: true` and named the quantity and unit. Five
queries were run on 2026-11-16. Where each number was read is recorded.
Nothing below is adopted as a constant by this PR.

| Source | What it reports | Read from |
|---|---|---|
| Hayati, Mattsson, Sandberg 2018, *Int. J. Ventilation*, DOI 10.1080/14733315.2018.1435027 | Wind-tunnel tracer gas through open doors: cross-flow airing 4–20 times single-opening; windward door about 53% higher than leeward; draught lobby −27%; higher turbulence +38% | Abstract only |
| Jiang, Kobayashi et al. 2022, *Building and Environment*, DOI 10.1016/j.buildenv.2022.109248 | Orifice equation "works well when the wind pressure coefficient difference is higher than 0.1" | Abstract (full text available, not needed for this statement) |
| Gough, Barlow et al. 2019, *Building and Environment*, DOI 10.1016/j.buildenv.2019.106556 | Full-scale 6 m cube, 1% porosity opening, nine months: four single-sided models, including Warren and Parkins 1985, underestimated 30-minute mean ventilation rates by a factor of 10 | Abstract |
| Albuquerque, O'Sullivan, Carrilho da Graça 2021, *Energy and Buildings*, DOI 10.1016/j.enbuild.2021.111060 | Window geometry and wind direction change single-sided flow by up to a factor of four upward and 23% downward | Abstract only |
| Luo, Li et al. 2026, *Physics of Fluids*, DOI 10.1063/5.0350831 | CFD of a naturally ventilated cruise cabin: 23.39–104.38 h⁻¹ against the wind, 61.78–333.65 h⁻¹ in side wind; effectiveness set by flow-path organisation more than opening area | Abstract only; simulation, not measurement |
| Cheung, Kumar et al. 2025, *Sci. Total Environ.*, DOI 10.1016/j.scitotenv.2024.178286 | CO₂ monitoring on a sailing cruise ship: pub 2.3 h⁻¹, restaurant 0.8 h⁻¹ (mechanical; context only) | Abstract |
| Roberts, Adzic et al. 2025, *Building and Environment*, DOI 10.1016/j.buildenv.2025.113847 | Seven semi-outdoor marquees over 80 events: mean CO₂ under 800 ppm with peaks to 1200 ppm; "not inherently low-risk" | Abstract; no air-change rate given |

Consensus URLs are in the ledger.

**What the literature can bound.**

- *Openings in a wall (balcony doors, weather doors, hatches).* The orifice
  equation with a wind pressure coefficient is supported where the
  coefficient difference exceeds 0.1, which is what the exporter already
  does for envelope leaks. Area is geometry. The exchange for a single
  opening is uncertain by about an order of magnitude (Gough 2019) and
  varies 4–20 times with cross-flow (Hayati 2018). Grade C at best.
- *Retrieval miss, not a null.* The Warren and Parkins single-sided
  coefficients were named in an excerpt's table reference but the table was
  not rendered. They must be read from the paper before use and are not
  quoted here.

**What it cannot bound.**

- *Exchange rate of an open weather deck treated as a zone.* No measured
  air-change rate for a ship's open deck, flight deck or fantail was
  retrieved. The concept is model-dependent: an open deck has no envelope,
  so its "volume" is an authoring choice.
- *Ship balcony-door exchange, measured.* Only a CFD study was found.
- *Hatch opening duty.* How often a weather hatch is open is an operational
  record, not in any literature index.

**Proposal for the unbounded values: declared axes, not constants.**

| Axis | Applies to | Proposed treatment |
|---|---|---|
| `weather_zone_exchange_ach` | Native lane, weather zones | Declared swept axis, Grade C origin I. Lower bound the current value (0); the upper end is to be set by the owner. No default is proposed here |
| `ambient_opening_duty` | Both lanes, hatches and doors | Declared axis on [0, 1] per opening type, reusing the schedule templates |
| Opening area | ContamX lane | Geometry from drawings; where no drawing dimension exists, a declared per-type catalog area flagged as such |

For orientation only (inferred, not sourced): a deck volume of length L
swept by relative wind U is flushed at about U/L, which for 10 m/s over
100 m is several hundred per hour — two to three orders of magnitude above
the 0.5/h most grouped weather zones have today. This is a scale argument
and must not be entered as a constant.

## 5. Exhaust sinks: magnitude error or missing make-up?

**Cited (stage 1, `CONTAM-FIELD-PRESSURE-REVIEW-01`).** Cruise and fiction
hulls are implausible on both lanes; with zero AHS imbalance the exhaust
sinks alone give 1.25e5–7.2e5 Pa.

**Discriminating measurement.** If the sink magnitudes were the error, the
pressure would stay implausible whatever the make-up area. If missing
make-up is the cause, pressure must collapse when make-up area is added
with the sinks untouched. The existing diagnostic was run on the design
lane with the shared envelope-leak area overridden **in memory**
(Appendix B). No file was changed.

**Measured at `15beae6b`.** Max envelope |ΔP| in Pa; prescribed exhaust
sink flow unchanged in every column.

| Hull | Exhaust sink m³/h | 0.0001 m² (as committed) | 0.01 m² | 1 m² |
|---|---|---|---|---|
| `classic_cruise_1900` | 12,003.0 | 4.85e5 | 197 | 3.37 |
| `diamond_princess` | 18,000.0 | 2.91e5 | 48.8 | 3.39 |
| `expedition_cruise_450` | 8,008.8 | 7.16e5 | 145 | 1.54 |
| `greg_mortimer` | 4,943.6 | 3.36e5 | 157 | 1.72 |
| `mega_cruise_5000` | 15,002.8 | 1.76e5 | 34.2 | 2.91 |
| `spirit_cruise_3000` | 15,002.6 | 3.95e5 | 1,530 | 5.92 |
| `enterprise_constitution_tos` | 5,000.0 | 1.67e5 | 52.3 | 1.47 |
| `enterprise_galaxy_tng` | 8,000.0 | 1.25e5 | 415 | 4.95 |

The 0.0001 m² column reproduces the stage-1 design-lane values, which
validates the override path. `expedition_cruise_450` was also run on the
commissioned lane: 9.82e5, 174 and 1.54 Pa. Interior prescribed-link |ΔP|
at 1 m² is 1.1–5.9 Pa on all eight hulls.

**Verdict: symptom (measured, 8 of 8 hulls).** The same sinks are
unremarkable once the hull has make-up area. The implausibility is the
0.0001 m² envelope being the only inward path. A further sign: |ΔP| near
1e6 Pa against ambient is below zero absolute pressure, which no real
exhaust fan can produce.

**Limits.** This shows the pressures are caused by missing make-up area. It
does not show the sink magnitudes are right; they keep their existing
provenance and are not re-examined here. One uniform area per zone is a
diagnostic, not a proposed fix: real make-up enters through specific
louvres and openings, which is what §2 provides. Steady state, one solve
per cell, no stochastic element.

The question was discriminated without data changes, so no diagnostic PR is
proposed.

## 6. Staged rollout

One PR per mechanism, per hull class. Each has its own ledger entry,
`Pathogens: all`. Nothing below is started by this PR.

| # | Stage | Suggested ledger ID | Hull class | Changes behaviour? |
|---|---|---|---|---|
| 0 | This audit and plan | `CONTAM-AMBIENT-EXPOSURE-01` | — | No — docs only |
| 1 | Schema + native builder + exporter emitter for `ambient_openings`; no platform declares one | `CONTAM-AMBIENT-OPENING-SCHEMA-01` | — | No — additive, empty by default; witness is byte-identical export and native paths on all 82 hulls |
| 2 | Widen `boundary_sink` to `ambient_opening` | `CONTAM-AMBIENT-OPENING-BOUNDARY-01` | — | No until a hull declares an opening |
| 3 | Make-up openings for prescribed exhaust sinks | `CONTAM-AMBIENT-MAKEUP-CRUISE-01`, `-FICTION-01` | Cruise (6), fiction (2), separately | Yes — data per hull |
| 4 | Weather-zone exposure | `CONTAM-AMBIENT-WEATHER-<CLASS>-01` | Cruise first, then naval by class | Yes — data per hull; needs D1/D2 |
| 5 | Weather hatches and doors | `CONTAM-AMBIENT-HATCH-<CLASS>-01` | Naval by class | Yes — data per hull; after the stage-3 service-hatch decision of the governing plan |
| 6 | Balcony openings | `CONTAM-AMBIENT-BALCONY-01` | Six balcony hulls | Yes — only after D3 |

Stage 3 here is the make-up half of stage 6 of the governing plan
(`CONTAM-FIELD-ENVELOPE-MAKEUP-01`); the owner should say whether it keeps
that ID (D6).

**Before/after witnesses for every behaviour-changing PR.**

- `tools/diag/contam_pressure_balance_diagnostic.py` — per-path ΔP, envelope
  direction and flow, boundary balance. Acceptance: design-lane max |ΔP| in
  the stage-1 naval design range (0.5–374 Pa, cited) and balance residual
  unchanged.
- `tools/contam_flow_compare.py` — native versus field per-path flows and
  the new opening rows.
- `tools/diag/contam_paired_diagnostic.py` — material-time matrix, same
  cells before and after.

**Frozen.** Phase 1 and Phase 2 campaign directories
(`campaigns/contam/phase1_hvac_tracer_01`,
`campaigns/contam/phase2_cruise_contrasts_01`), their S3 prefixes, the
`_v1` field caches, committed readouts, all existing ledgers, and the
frozen legacy deploy layout.

**Design versioning.** Adding an opening changes a hull's path count and so
breaks frozen-design pins. Follow the `_v2` pattern of #1236/#1248: the
as-run design, source-pool and campaign files stay untouched and a new
`_v2` (or next) design id, files and field-cache prefix are added alongside.
No cache is produced and nothing is uploaded by a data PR.

## 7. Open decisions for the owner

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Data model for ambient exposure | (a) new `ambient_openings` list; (b) `adjacency` with `to: "ambient"`; (c) extend `cross_zone_links` | (a) — keeps both existing records' meanings fixed |
| D2 | Weather zones | (a) keep as finite zones with an ambient opening and a declared exchange axis; (b) alias to ambient, zone removed from transport; (c) leave as is | (a) — keeps occupancy and near-field exposure on deck; (b) only if the owner wants decks to carry no airborne pool at all |
| D3 | Balcony double count (§3) | A keep transmission factor only; B opening replaces factor; C both; D split by engine | A now, B once a sourced magnitude exists |
| D4 | Native-lane magnitude for openings | (a) declared swept axis per opening type; (b) one fleet constant; (c) derive from ContamX solve and cache | (a) — literature cannot bound a single value |
| D5 | Upper bound of the weather-zone exchange axis | Owner-set value; or defer to a ContamX-derived range per hull | Defer to the ContamX-derived range from the first cruise hull |
| D6 | Stage numbering | (a) this plan's stage 3 is the governing plan's stage 6 under its existing ID; (b) new IDs | (a) |
| D7 | Zones the lexical classifier misfiles | (a) correct the per-zone list by hand before stage 4; (b) add an authored `exposure` field to `spatial_layout.json` | (b) — makes exposure a declared fact, not an id match |
| D8 | Two-way exchange through one large opening in ContamX (§2.5) | (a) single orifice; (b) two-way opening element; (c) paired orifices at two heights | Decide in stage 1 with a witness on one hull |

The stage-3 service-hatch decision of the governing plan is untouched.

## Appendix A — inventory reproduction

Run from the repo root at `15beae6b` with the locked `.venv`. Read-only;
writes nothing.

```bash
PYTHONPATH=. .venv/bin/python - --zones --hulls <<'PY'
import collections, re, sys
from tools.hull_audit import PLATFORMS_DIR, _is_exterior, load_platform

OPENING_TYPES = ("open_deck", "deck_walkway", "open_front", "open_area",
                 "hangar_door", "hatch", "service_hatch")
rows, edges, links = [], collections.Counter(), []
hulls = sorted(p.parent for p in PLATFORMS_DIR.glob("*/air_flow_paths.json"))
for root in hulls:
    b = load_platform(root)
    air, hull = b.airflow, root.name
    text = (root / "spatial_layout.json").read_text(encoding="utf-8").splitlines()
    line = {m.group(1): i for i, t in enumerate(text, 1)
            if (m := re.search(r'"id":\s*"([^"]+)"', t))}
    group = {r: g for g in air.get("hvac_zones", []) for r in g.get("rooms", [])}
    d_oa = float(air.get("oa_fraction", 0.2))
    d_duty = float(air.get("hvac_duty", 1.0))
    for z in b.spatial.get("zones", []):
        cls = ("balcony" if z.get("cabin_ventilation_type") == "balcony_partial"
               else "weather" if _is_exterior(z) else None)
        if cls is None:
            continue
        g = group.get(z["id"])
        oa_ach, gid = 0.0, "-"
        if g:
            ach, oa = float(g.get("ach", 6.0)), float(g.get("oa_fraction", d_oa))
            duty = max(float(g.get("hvac_duty", d_duty)), 0.0)
            oa_ach = ach if (duty <= 0 and oa >= 1) else ach * duty * oa
            gid = g.get("id", "?")
        rows.append((cls, hull, z["id"], line.get(z["id"], 0),
                     float(z.get("volume_m3", 0)), gid, round(oa_ach, 3)))
    for e in air.get("adjacency", []):
        t = e.get("type", "passageway")
        if t in OPENING_TYPES:
            edges[(t, hull)] += 1
    for k in air.get("cross_zone_links", []):
        if "ambient" in (k.get("from"), k.get("to")):
            links.append((hull, k.get("from"), k.get("to"), k.get("flow_rate_m3h")))

print(f"hulls {len(hulls)}")
for cls in ("weather", "balcony"):
    rs = [r for r in rows if r[0] == cls]
    print(cls, "zones", len(rs), "hulls", len({r[1] for r in rs}),
          "ungrouped", sum(r[5] == "-" for r in rs),
          "zero_outdoor_exchange", sum(r[6] == 0 for r in rs),
          "volume_m3", round(sum(r[4] for r in rs)))
for t in OPENING_TYPES:
    print("adjacency", t,
          "edges", sum(n for (tt, _), n in edges.items() if tt == t),
          "hulls", len({h for (tt, h) in edges if tt == t}))
print("ambient_links", len(links), "sources", sum(k[1] == "ambient" for k in links))
for k in links:
    print("  link", *k)
if "--hulls" in sys.argv:
    per = collections.defaultdict(lambda: [0, 0, 0])
    for r in rows:
        per[r[1]][0] += r[0] == "weather"
        per[r[1]][1] += r[0] == "weather" and r[6] == 0
        per[r[1]][2] += r[0] == "balcony"
    for h in sorted(per):
        print("| " + " | ".join([f"`{h}`", *map(str, per[h])]) + " |")
if "--zones" in sys.argv:
    for r in sorted(rows):
        print("| " + " | ".join(str(x) for x in r) + " |")
PY
```

Expected head of output:

```text
hulls 82
weather zones 243 hulls 78 ungrouped 112 zero_outdoor_exchange 124 volume_m3 505255
balcony zones 153 hulls 6 ungrouped 0 zero_outdoor_exchange 0 volume_m3 157340
adjacency open_deck edges 17 hulls 6
adjacency deck_walkway edges 24 hulls 15
adjacency open_front edges 11 hulls 5
adjacency open_area edges 3 hulls 1
adjacency hangar_door edges 3 hulls 2
adjacency hatch edges 35 hulls 9
adjacency service_hatch edges 28 hulls 15
ambient_links 12 sources 0
```

## Appendix B — make-up area sweep reproduction

Runs the committed stage-1 diagnostic with the shared envelope-leak area
overridden in the in-process hobbyist pack. `load_hobbyist_pack` is
`lru_cache`d on its argument, so the override must be applied to the object
returned by `load_hobbyist_pack(None)`, which is the call the exporter
makes (`tools/contamw34_prj.py:1353`); the no-argument call is a different
cache entry and has no effect. The diagnostic only writes inside the repo
root, so output goes to an untracked scratch directory; delete it afterwards
and do not commit it.

```bash
mkdir -p telemetry_buffer/ambient_sweep
PYTHONPATH=. .venv/bin/python - <<'PY'
import contextlib, io, json
from tools import contam_hobbyist as hobby
from tools.diag import contam_pressure_balance_diagnostic as diag

HULLS = ("classic_cruise_1900", "diamond_princess", "expedition_cruise_450",
         "greg_mortimer", "mega_cruise_5000", "spirit_cruise_3000",
         "enterprise_constitution_tos", "enterprise_galaxy_tng")
pack = hobby.load_hobbyist_pack(None)
for hull in HULLS:
    for area in (1e-4, 1e-2, 1.0):
        pack["orifice_catalog"]["envelope_leak"]["area_m2"] = area
        out = f"telemetry_buffer/ambient_sweep/{hull}_{area:g}.json"
        with contextlib.redirect_stdout(io.StringIO()):
            diag.main(["--hull", hull, "--lane", "design", "--out", out])
        row = json.load(open(out))["rows"][0]
        by = row["dp"]["by_class"]
        print(hull, area, round(row["boundary"]["exhaust_sink_out_m3h"], 1),
              {k: float(f"{v['max_abs_dp_pa']:.3g}") for k, v in by.items()})
PY
```
