# Exhaust-sink audit and fix plan (sink endpoints, `filtered` carry-through, generator protection)

> **Status:** Partially implemented — the §5.4 G-min generator guards and
> shared sanitary emitter landed as ledger
> `docs/ledger/CONTAM-GENERATOR-PROTECT-01.md`; §3–§4 and the rest of §5–§6
> remain proposed. The audit below is unchanged and was read-only at
> `origin/main` `800a1958` (after the forced-exhaust bundle #1209, #1213,
> #1214, #1216, #1217, #1219, #1220, #1221). It responds to three further
> claims from Edison. Audit ledger: `docs/ledger/CONTAM-EXHAUST-SINK-01.md`.

**Evidence vocabulary.** *Measured* = computed this session from the tree at
`800a1958`, with the reproduction in the Appendix. *Inferred* = follows from
measured facts plus the cited code path. *Hypothesis* = not tested. All
measurements are deterministic (no RNG, no seeds): they read JSON or apply
the exact linear operator. `file:line` references are to `800a1958`.

**No constant is proposed, chosen or adjusted here.** Edison's claims are
treated as a third-party spec: each is checked against the tree, and where
his resolution implies machinery, a minimal path is priced beside it.

## 1. Summary

| # | Edison's claim | Verdict | One-line reason |
|---|---|---|---|
| 1 | `filtered: false` on an internal A→B "once-through exhaust" link increases downstream delivery; Legend / San Antonio medical and galley links still end in berthing / mess rooms | **Verified** (measured) | Downstream material-time rises ×1.8–2.0 on all three links; no link in the fleet can end overboard |
| 2 | `path_map.json` carries only `is_hvac_ducted`; three links have `filtered ≠ ducted`; no double-filtering in airflow-only coupling | **Verified** (measured), count is exactly **3** | 3 links → 9 exported paths; the ContamX lane filters them, native does not |
| 3 | Galley repairs are not protected by recipe generators; sanitary generation is protected; both Enterprise recipes keep the old reversed direction | **Partially verified** — true but understated on galleys, overstated on sanitary | All 7 recipe-generated hulls revert authored links, not 2; the GA importer's sanitary emitter is *not* protected |

Findings beyond the three claims:

- **Regeneration changes non-galley content** (measured, §5.2): it strips the
  explicit S1 fields from 92 further links, drops `hot_bunk_ratio` on 12
  Constitution zones, and adds per-group `oa_fraction` to 7 `mega_cruise_5000`
  HVAC groups.
- **Three committed contam bundles are stale against their own
  `air_flow_paths.json`** (measured, §4.3): both Enterprise hulls (not
  recorded in any ledger) and `mega_cruise_5000` (recorded in
  `CONTAM-FORCED-EXHAUST-DOORS-01`).
- **The exporter silently drops a link with an unresolvable endpoint**
  (`tools/contamw34_prj.py:842`) where native raises
  (`engines/py_contam_bridge.py:665`). No link is affected today.
- **`scripts/build_enterprise_platforms.py` is a live overwrite hazard**
  (measured, §5.1): it rewrites both Enterprise hulls as the legacy 12- and
  16-zone layouts.

**Priority note (owner, 2026-11-14).** The two Enterprise hulls are fiction
bundles that are not load-bearing and are kept up to date on a best-effort
basis. Every Enterprise finding below (stale bundles, recipe drift, the
legacy builder) is recorded for completeness and does not gate any stage.
The load-bearing findings are the three Legend / San Antonio links, the four
cruise recipes and `mega_cruise_5000`.

Counts reconcile (measured): 82 platforms, 1,011 `cross_zone_links`, 77
`contam/path_map.json`, 5 hulls without a contam bundle
(`expedition_cruise_300`, `fletcher_class_destroyer`, `legend_class_nsc`,
`messy_cruise_500`, `san_antonio_class_lpd`).

No frozen artifact is touched or invalidated by this document. Sink
endpoints need no engine redesign: the change is additive in three places
(§3.4).

## 2. Verification of Edison's three claims

### 2.1 Claim 1 — "once-through exhaust" links deliver into occupied rooms

**Verified.**

Code path (inferred from, and consistent with, the measurement below):

- A cross-zone link's endpoints must each resolve to an HVAC group's rooms
  or a room id; anything else raises
  (`engines/py_contam_bridge.py:649-668`). There is no overboard endpoint.
- For every non-plenum path, `filtered` only scales the mass *arriving* at
  the destination by `(1 − η)`; the source loses `q / V` either way
  (`engines/py_contam_bridge.py:670-692`, the scaling at `:686-687`).
- Therefore `filtered: false` removes an attenuation and nothing else. It
  cannot route mass out of the domain.

The three links (measured; all `direction: oneway`,
`mechanism: prescribed_flow`, `is_hvac_ducted: true`, `filtered: false`):

| Hull | `path` | Declared link | Source room → destination rooms | m³/h | Lines |
|---|---|---|---|---:|---|
| `legend_class_nsc` | `medical_exhaust` | `HVAC_Medical` → `HVAC_Enlisted_Fwd` | `Sickbay` → `CPO_Berthing`, `Enlisted_Berthing_Fwd`, `Crew_Mess` | 100 | `air_flow_paths.json:274-284`, groups `:35-48`, `:65-77` |
| `san_antonio_class_lpd` | `medical_exhaust` | `HVAC_Medical` → `HVAC_Crew_Habitable` | `Medical_Ward` → `Ship_Enlisted_Berthing`, `Crew_Mess`, `Passageway_Main` | 200 | `air_flow_paths.json:267-277`, groups `:33-45`, `:61-71` |
| `san_antonio_class_lpd` | `galley_exhaust_to_mess` | `HVAC_Galley` → `HVAC_Crew_Habitable` | `Galley` → the same three rooms | 400 | `air_flow_paths.json:245-255`, group `:72-82` |

Measured effect — exact retained-mass material-time in hours per unit
release in the source room, native lane, 12 h horizon, η = 0.5, decay 0 (the
frozen Phase 1 tracer conditions, as used by
`CONTAM-FORCED-EXHAUST-DUCTED-01`). "Sink" is the same link with its flow
leaving the domain instead of arriving anywhere:

| Link | Variant | Source room | Destination rooms (sum of three) | Whole hull |
|---|---|---:|---:|---:|
| Legend `medical_exhaust` | `filtered: true` (pre-#1221) | 0.140971 | 0.037208 | 0.195341 |
| | `filtered: false` (current) | 0.140994 | 0.073125 | 0.240702 |
| | sink (overboard) | 0.140947 | 0.001304 | 0.149994 |
| San Antonio `medical_exhaust` | `filtered: true` | 0.189626 | 0.017689 | 0.211200 |
| | `filtered: false` (current) | 0.189663 | 0.032918 | 0.229745 |
| | sink (overboard) | 0.189589 | 0.002465 | 0.192662 |
| San Antonio `galley_exhaust_to_mess` | `filtered: true` (pre-#1219) | 0.113976 | 0.029474 | 0.193998 |
| | `filtered: false` (current) | 0.114029 | 0.055105 | 0.225209 |
| | sink (overboard) | 0.113923 | 0.003868 | 0.162817 |

Reading the table:

- The whole-hull figures for the two medical links equal the before / after
  values already recorded in `CONTAM-FORCED-EXHAUST-DUCTED-01`
  (0.195341 → 0.240702 and 0.211200 → 0.229745), so this reproduces that
  ledger rather than contradicting it.
- Current authoring delivers 1.86–1.97× the pre-change mass-time to the
  destination rooms. The source room is unchanged to four decimals.
- A true sink would deliver 13–56× less to those rooms than the current
  authoring.

The #1219 and #1221 ledgers describe the change accurately ("no
recirculation-filter credit", "less arriving mass is attenuated"). What they
do not say is that the direction of the effect is opposite to the physical
regime the link descriptions state. That is the substance of Edison's claim
and it holds.

### 2.2 Claim 2 — `filtered` is not carried through the ContamX-field interface

**Verified. The count is exactly three links** (the three in §2.1), expanding
to nine exported paths.

Reconciliation of the count (measured): over all 1,011 links, resolve
`filtered` with `cross_zone_link_semantics`
(`engines/py_contam_bridge.py:116-127`) and compare with
`bool(is_hvac_ducted)`. Exactly three differ, all `ducted = true`,
`filtered = false`. Zero links have `ducted = false`, `filtered = true`.

Where the field is lost:

- The exporter writes path_map entries with seven keys — `path_nr`,
  `from_zone`, `to_zone`, `is_hvac_ducted`, `kind`, `crusher_transfer`,
  `ahs_nr` (`tools/contamw34_prj.py:734-742`). Cross-zone paths pass
  `is_hvac_ducted=ducted` (`:877`). `filtered` is resolved (`:853`) but used
  only to choose a PRJ filter reference (`:868-871`).
- The ContamX lane rebuilds each path from the entry with
  `is_hvac_ducted=is_ducted` and no `filtered` argument
  (`engines/contamx_transport.py:147`, `:158-165`), so `filtered` defaults to
  the ducted flag (`engines/py_contam_bridge.py:328`).
- The same seven-key entries are what a field cache stores
  (`campaigns/contam/phase1_hvac_tracer_01/cell.py:368-374`) and replays
  (`:105-119`).

Measured on a fresh scratch export (`export_prj_with_path_map`, both
hobbyist modes; nothing written to the repo):

| Hull | `path_nr` | `kind` | path_map `is_hvac_ducted` | Lane `filtered` | Native `filtered` | PRJ `filter_nr` |
|---|---|---|---|---|---|---:|
| `legend_class_nsc` | 79–81 | `medical_exhaust` | true | true | false | 0 |
| `san_antonio_class_lpd` | 105–107 | `galley_exhaust_to_mess` | true | true | false | 0 |
| `san_antonio_class_lpd` | 113–115 | `medical_exhaust` | true | true | false | 0 |

All 58,223 entries in the 77 committed path_maps carry the same seven keys;
none has a `filtered` key (measured).

"No actual double-filtering" — **verified**: the PRJ carries no filter
element on these nine paths (`filter_nr` 0, measured), and the coupling
consumes only solved airflows, applying filtration once in Python.

Not measured: the size of the lane-versus-native transport difference on
these two hulls. That needs a solved ContamX field for each, and neither
hull has a committed bundle or appears in a frozen design. *Inferred*: the
lane attenuates the nine paths by `(1 − η)` where native does not, so on
this channel the lane sits near the `filtered: true` rows of §2.1.

Coordinator's partial verification — confirmed: 77 path_maps; neither #1221
hull has a committed bundle, so the divergence appears only on fresh export.

### 2.3 Claim 3 — generator protection

**Partially verified.**

| Part of the claim | Verdict | Evidence |
|---|---|---|
| Both Enterprise recipes keep the reversed galley direction | Verified | `scripts/enterprise_platform_recipes.py:218-224` and `:515-521` declare `Galley` → `Mess_Hall`; committed data is `Mess_Hall` → `Galley` (`enterprise_constitution_tos/air_flow_paths.json:348`, `enterprise_galaxy_tng/air_flow_paths.json:629-633`) |
| Galley repairs are not protected by recipe generators | Verified, and understated | Regeneration reverts authored links on **all seven** recipe-generated hulls (§5.2), including the four cruise `Dining_Galley_Exhaust` links (`scripts/cruise_platform_recipes.py:401`, `:740`, `:1111`, `:1817`) and one #1220 link on `mega_cruise_5000` |
| Sanitary generation is protected | Verified for the recipe path, **refuted for the GA importer** | `scripts/derive_sanitary_provisioning.py:410-412` emits `direction` / `mechanism` / `filtered`, and all 216 recipe-hull sanitary links regenerate identically (measured). `tools/ship_blueprint_import/synthesize.py:355-366` emits `Sanitary_Makeup` with none of the three fields (code path) |

One qualification on "not protected". The *committed data* is pinned by
tests, so a regeneration cannot land silently:
`tests/test_contam_s1_migration.py:151-169` requires the S1 triple on every
link, `tests/test_forced_exhaust_audit.py:8-20` and `:31-40` pin the 585
sanitary and 9 galley links one-way, and
`tools/sanity_checker.py:1612-1643` rejects an unpinned link into an
exhaust terminal. What is unprotected is the generators: every one of them
now produces output that fails those tests, so they have stopped being
usable as generators without anyone having decided that.

## 3. Exhaust-sink topology and versioned fix proposal

### 3.1 How exhaust to atmosphere is represented today

**Native** (`engines/py_contam_bridge.py`). Mass leaves the domain three ways:

1. *Plenum fold.* Every room in a running HVAC group returns `ach · V · duty`
   to a virtual plenum; supply legs carry back `(1 − OA)` of it, filtered
   (`:736-768`). The OA share and the filter capture leave the domain. A
   group at `oa_fraction` 1.0 is therefore already once-through. 132
   non-sanitary groups are declared that way (measured), for example
   `expedition_cruise_300` `AHU_MedBay_Dedicated`.
2. *Duty-0 extract terminal.* A group with `hvac_duty` ≤ 0 and declared
   `oa_fraction` ≥ 1.0 emits return-only legs at `ach · V` under
   `duty0_terminal_mode: extract` (`:174-193`, `:510-520`, `:530-555`). All
   585 such groups are `AHU_HD_*` sanitary heads (measured); no other duty-0
   group exists.
3. *Natural decay.*

A cross-zone link is none of these. It is always room → room.

**ContamX export** (`tools/contamw34_prj.py`). Ambient is node −1 and is
reached by exactly three path kinds: one `envelope_leak` per zone
(`:748-772`), and per air-handling system an `ahs_oa` intake and an
`ahs_exhaust` (`:957-983`). Commissioned mode writes an exhaust-only branch
as supply 0, return `ach · V` (`:1114-1136`). Cross-zone links are emitted
only as room × room pairs (`:837-884`). The lane's transport skips
`ahs_*` and `envelope_leak` kinds (`engines/contamx_transport.py:150`) and
any path with an endpoint outside the known zones (`:156`); system exhaust
is handled by the synthesized star.

**Schema** (`schemas/air_flow_paths.schema.json:87-125`). `from` and `to` are
"zone or HVAC zone ID" (`:91-98`). There is no reserved sink token, and no
JSON Schema exists for `path_map.json`.

### 3.2 Which exhaust-class links end in occupied rooms

Classified by the committed audit's rule (`exhaust|extract|hood|relief` in
path or description, as in `forced_exhaust_audit_summary.json`). Measured:
637 links = 585 sanitary + 52 `forced_exhaust`.

| Class | Links | Ends in | Sink today? |
|---|---:|---|---|
| `Sanitary_Makeup` | 585 | a duty-0 / OA-1.0 `AHU_HD_*` head group | **Yes** — extract terminal |
| `Cabin_Relief*`, `Corridor_Relief_Exhaust*` | 39 | a recirculating public-space HVAC group | No — declared relief into the HVAC network (reviewed, kept, in #1221) |
| `medical_exhaust` | 2 | berthing / mess rooms | **No — declared once-through** |
| `galley_exhaust_to_mess` | 1 | berthing / mess / passageway | **No — declared no-credit, hood "remains topside"** |
| `Galley_Exhaust_Return` | 1 | `AHU_2_Main` rooms | No — declared a return of non-galley service air |
| `Dining_to_Galley_Transfer` | 2 | `AHU_Dedicated_Service_Exhaust` (duty 0.5, OA 0.2 / 0.3) | No — description says "exhausting odors overboard"; parked in #1221 |
| `Dining_Galley_Exhaust`, `Galley_Service_Exhaust` | 7 | the galley room | No — make-up *into* the exhaust boundary, by design (#1219) |

So 0 of the 52 non-sanitary exhaust-class links ends at a sink. Three state
an overboard regime in their own description and deliver to occupied rooms
instead; two more (`Dining_to_Galley_Transfer`) are candidates already
parked.

A related gap, *inferred* and not proposed for change here: the seven
make-up links push 5,000–18,000 m³/h into a galley whose own group
recirculates (OA 0.15–0.2 on the three hulls checked), so the "galley exhaust runs independent to
atmosphere" in their descriptions has no modelled sink either.

### 3.3 Two paths (Edison's resolution is a proposal; both are priced)

| | Minimal path M | Spec-faithful path S (Edison: explicit sink endpoints) |
|---|---|---|
| What changes | Data only, three links on two hulls: delete the link, declare its source group `oa_fraction: 1.0` | Reserved endpoint `"to": "ambient"`; native, exporter and lane learn it; then re-point the three links |
| Schema | none | one reserved token on `to` |
| Engine / exporter | none | three additive touch points (§3.4) |
| Destination-room mass-time, sum of three rooms (measured) | Legend medical 0.001452; San Antonio medical 0.002146; San Antonio galley 0.003611 | 0.001304; 0.002465; 0.003868 (the "sink" rows of §2.1) |
| Source-room mass-time (measured) | 0.156921; 0.165009; 0.106350 | 0.140947; 0.189589; 0.113923 |
| Keeps the declared 100 / 200 / 400 m³/h | **No** — the extraction rate becomes the group's `ach · V · duty` | Yes |
| Works for a room inside a multi-room group | No — OA is per group | Yes |
| Can address `Dining_to_Galley_Transfer` or galley hoods later | No | Yes |
| Consumer that exists today | native and exporter, unchanged | none until built |
| Pinned tests to update | `tests/test_contam_forced_exhaust_ducted.py` (45-link class), `tests/test_contam_forced_exhaust_galley.py` (9 links) | the same two, plus new invariants |
| Committed bundles affected | none (neither hull has one) | none |

Both paths remove the downstream delivery to within a few 10⁻⁴ h. They
differ in what happens to the source room and in whether the declared flow
survives.

Recommendation: **path S**, because M silently replaces three declared
magnitudes with a derived one and cannot express the next cases. M is a
legitimate stopgap if only these three links matter, and it needs no code.
The choice is the owner's.

### 3.4 Path S — what an explicit sink endpoint requires

**Schema** (`EXHAUST-SINK-S1`, additive).

- `CrossZoneLink.to` accepts the reserved token `"ambient"`. The token
  matches the exporter's existing name for node −1
  (`tools/contamw34_prj.py:764`, `:977`). No zone or HVAC group in the fleet
  is named `ambient` (measured).
- A link to `ambient` must be `direction: oneway`,
  `mechanism: prescribed_flow`, `filtered: false`. `from` may not be
  `ambient`. Enforced in `tools/sanity_checker.py` beside the existing
  exhaust-terminal check (`:1612-1643`).
- Versioning: the data change is fail-loud on old code. A pre-change native
  engine raises on the unknown endpoint (`engines/py_contam_bridge.py:665`).
  The pre-change exporter would silently drop it
  (`tools/contamw34_prj.py:842`); that `continue` becomes a raise in the same
  stage, for every unresolved endpoint, so the two lanes fail alike.

**Native** (`EXHAUST-SINK-N1`).

- `_build_cross_zone_paths` (`:585-613`) emits one path per source room at
  `q / n_source_rooms` with a sink destination.
- `_accumulate_path_rates` (`:670-692`) adds the source outflow and no
  arrival for a sink path. Today it returns early when the destination is
  not a real zone (`:680`), which is why this is an addition and not a
  redesign.
- No config knob. The mechanism is inert until a hull declares `ambient`, so
  every existing operator is unchanged. The labelled baseline for the three
  re-pointed links is the pre-change hull JSON at its SHA, the same
  convention #1219–#1221 used for data authoring. If a runtime baseline
  switch is wanted instead (keep the legacy destination in the file and
  select by `hvac.*` mode), that is a larger design and is listed as an open
  decision in §6.3.

**Exporter and lane** (`EXHAUST-SINK-X1`).

- `_add_cross_zone_paths` (`:837-884`) emits a `fan_cvf` path from each
  source room to node −1.
- The path_map entry carries `to_zone: "ambient"` and a new
  `"sink": true` key (§4.2).
- `ContamXTransportEngine._contamx_field_paths`
  (`engines/contamx_transport.py:135-168`) treats a `sink` entry with
  positive solved flow as outflow-only. Today it would drop it at `:156`.
- `path_map_from_prj` classifies any non-AHS path touching ambient as
  `envelope_leak` (`tools/contamw34_prj.py:1962-1964`). A fan element to
  ambient needs its own kind, or a committed PRJ read without its path_map
  would lose the sink. *Hypothesis*: no committed PRJ contains such a path
  today, so the classifier output is unchanged on all 77; the stage must
  prove it.
- In ContamX the fan depressurises the room and make-up arrives through the
  declared openings, which is the negative-pressure regime the descriptions
  state. Native has no pressure solve and adds no make-up inflow. Whether a
  paired one-way make-up link is authored, as sanitary heads have, is a
  per-hull authoring decision (§6.3).

**Data** (`EXHAUST-SINK-D1`). Re-point the three links of §2.1 to
`ambient`, magnitudes unchanged, with before / after exact-integral rows in
the implementing ledger.

**Tests** (structural invariants, no goldens).

- Operator invariance: on all 82 hulls the decay-free operator is identical
  before and after N1 (the pattern of
  `tests/test_contam_s1_migration.py:190`).
- Conservation: a sink link lowers its source column sum by exactly `q / V`
  and changes no other column.
- Graded response: scaling the sink flow moves source retention
  monotonically and leaves former destination rooms unchanged by that path.
- Lane parity: a hull with a sink link has the same sink path set in native
  and in the lane built from its fresh export.
- Fail-loud: an unknown endpoint raises in both native and exporter.

### 3.5 Impact on frozen artifacts

- **Phase 1 / Phase 2 campaign directories, S3 prefixes, `_v1` field caches,
  committed readouts**: unaffected, by construction. The frozen study hulls
  are `destroyer_baseline`, `expedition_cruise_450`,
  `fletcher_class_destroyer`, `lexington_cv2`, `saratoga_cv3`,
  `missouri_bb63` (Phase 1) and `expedition_cruise_450`,
  `classic_cruise_1900`, `spirit_cruise_3000`, `mega_cruise_5000` (Phase 2)
  (measured from the two design JSONs). None carries any of the three links.
- **Committed contam bundles**: none regenerates for path S or M. Neither
  affected hull has one.
- **Ledgers `CONTAM-PHASE1-*`, `CONTAM-PHASE2-*`,
  `CONTAM-EDISON-RETURN-01`**: untouched.
- **What becomes historical when D1 lands** (not now): the exact-integral
  rows for `legend_class_nsc` and `san_antonio_class_lpd` in
  `CONTAM-FORCED-EXHAUST-DUCTED-01`, and the San Antonio row in
  `CONTAM-FORCED-EXHAUST-GALLEY-01`. The implementing PR adds the
  open-ledger notes; this PR adds none.

## 4. `path_map` `filtered` carry-through

### 4.1 Where the path_map comes from

| Role | Location |
|---|---|
| Entry construction | `tools/contamw34_prj.py:702-746` (`_add_path`) |
| In-memory builders | `build_path_map` (`:224`), `export_prj_with_path_map` (`tools/contam_prj_bridge.py:130`) |
| File writer | `export_platform_to_prj` (`tools/contam_prj_bridge.py:457-508`) |
| CLI for the fiction hulls | `scripts/generate_platform_contam_prj.py:36-41`, `:93-96` |
| Reverse (PRJ → path_map) | `path_map_from_prj` (`tools/contamw34_prj.py:1972-2050`; `is_hvac_ducted` derived from `kind` at `:2044`) |
| Lane reader | `engines/contamx_transport.py:263-290` (file beside the PRJ), `:135-168` (use) |
| Schema | **none** — the format is defined only by `_add_path` |

### 4.2 Proposal (`PATHMAP-FILTERED`)

Two variants; both make the lane read
`entry.get("filtered", entry["is_hvac_ducted"])`.

| | P-min (recommended) | P-full |
|---|---|---|
| Rule | Write `filtered` only where it differs from `is_hvac_ducted` — the same rule the X2 PRJ filter reference already uses (`tools/contamw34_prj.py:868-871`) | Write `filtered` on every cross-zone entry |
| Committed path_maps that regenerate | **0 of 77** (no committed hull has a divergent link) | **all 77** (58,223 entries re-serialised; key added to cross-zone entries) |
| Old caches and path_maps | Read identically: absent key resolves to the alias | Read identically |
| Reader that needs the unconditional key | none | none |

P-full buys uniformity and costs a 77-file diff with no behaviour change.
Its consumer does not exist. P-min is the recommendation.

Add a JSON Schema for path_map entries in the same stage
(`schemas/contam_path_map.schema.json`): the seven existing keys required,
`filtered`, `sink` and commissioned-mode `declared_flow_m3h` optional. Today
its writers and readers agree only by convention.

### 4.3 The three stale committed bundles are a separate row

Measured: 74 of 77 committed path_maps equal a fresh export of the current
hull JSON. Three do not.

| Hull | Stale entries | Committed | Fresh export | Recorded? |
|---|---|---|---|---|
| `enterprise_constitution_tos` | `path_nr` 173 | `Galley` → `Mess_Hall` (`contam/path_map.json:1552-1555`) | `Mess_Hall` → `Galley` | No |
| `enterprise_galaxy_tng` | `path_nr` 320 | `Galley` → `Mess_Hall` (`contam/path_map.json:2875-2878`) | `Mess_Hall` → `Galley` | No |
| `mega_cruise_5000` | `path_nr` 479–482 | `Medical_Center` / `Isolation_Ward` → crew mess | reversed | Yes, `CONTAM-FORCED-EXHAUST-DOORS-01` |

`CONTAM-FORCED-EXHAUST-GALLEY-01` says only the `expedition_cruise_450` PRJ
was regenerated and that its path_map is unchanged. Both statements are
true. It does not record that the two Enterprise bundles were left carrying
the pre-flip sense. That entry is not edited here; the forward reference
lives in `CONTAM-EXHAUST-SINK-01`.

The two Enterprise rows are best-effort (priority note, §1); only the
`mega_cruise_5000` row touches a study hull.

A path_map cannot be regenerated alone. Its endpoints define the sign
convention of the solved flow in the PRJ beside it, so the pair must move
together. *Inferred*: the committed pairs are internally consistent, and
stale only against the hull JSON. Regenerating the pair also pulls in the
X1 element catch-up noted in `CONTAM-FORCED-EXHAUST-GALLEY-01`, and
`mega_cruise_5000` is a Phase 2 study hull, so that regeneration produces a
new P-lane field under a new cache version. It is its own stage
(`BUNDLE-RESYNC`, §6.1), not part of `PATHMAP-FILTERED`.

### 4.4 Field-cache interface versioning

- A field cache stores path_map entries verbatim under `entries`
  (`campaigns/contam/phase1_hvac_tracer_01/cell.py:368-374`), so the cache
  format inherits whatever the path_map carries.
- `_v1` caches stay valid and frozen. Under P-min an absent `filtered` key
  means what it means today.
- `_v2` schema ids and prefixes are already reserved, unproduced, by
  `CONTAM-FORCED-EXHAUST-X1X2-01`
  (`campaigns/contam/phase1_hvac_tracer_01/design/build.py:46-50`,
  `campaigns/contam/phase2_cruise_contrasts_01/design/build.py:28`,
  `:58-59`).
- Proposal: `filtered` and `sink` join the definition of `_v2` if no `_v2`
  cache has been produced when the stage lands; otherwise they define
  `_v3`. Whether a `_v2` cache exists in S3 was **not checked** this session
  (no AWS by scope).
- Rule to carry forward: a cache whose hull set includes a link with
  `filtered ≠ is_hvac_ducted`, or a sink, may not be written under `_v1`.

## 5. Generator protection

### 5.1 Which script authors which links

Fleet split (measured): 68 hulls from the GA importer, 7 recipe-generated,
7 hand-authored (`destroyer_baseline`, `expedition_cruise_300`,
`fletcher_class_destroyer`, `greg_mortimer`, `legend_class_nsc`,
`messy_cruise_500`, `san_antonio_class_lpd`).

| Generator | Hulls | Links it authors | Writes to |
|---|---|---|---|
| `scripts/generate_cruise_platform_layout.py` (`build_air_flow_paths` `:220-368`, `write_platform` `:370-396`) with `scripts/cruise_platform_recipes.py` (`RECIPES` `:1844-1849`) | `expedition_cruise_450`, `classic_cruise_1900`, `spirit_cruise_3000`, `diamond_princess` | recipe `cross_zone_links` verbatim (`:286`); auto `Pax_Trunk_*`, `Crew_Trunk_*`, `Cabin_Relief_*` (`:288-317`); sanitary via `sanitary_airflow_augment` (`:319-327`) | `data/platforms/<id>/` directly |
| `scripts/generate_enterprise_platform_layout.py` with `scripts/enterprise_platform_recipes.py` (`RECIPES` `:533-536`) | `enterprise_constitution_tos`, `enterprise_galaxy_tng` | the same builder | the same |
| `scripts/generate_mega_cruise_cabin_layout.py` (`build_air_flow_paths` `:314`) | `mega_cruise_5000` | renamed copies of `messy_cruise_500`'s links (`:348`), auto trunks and relief, one literal `Crew_to_Engine_Stairwell` (`:381-388`), sanitary | `data/platforms/mega_cruise_5000/` (`:29`) |
| `scripts/derive_sanitary_provisioning.py` (`sanitary_airflow_augment` `:352-420`, `augment_platform_files` `:424-443`) | recipe hulls (called by the generators) and hand-authored hulls | `Sanitary_Makeup`, with the S1 triple (`:410-412`) | in place |
| `tools/ship_blueprint_import/synthesize.py` (`:355-366`, `:371-407`) | the 68 GA hulls | `Sanitary_Makeup` and ladder-well or digest-hint links, **without** the S1 triple | a new platform dir |
| `scripts/generate_platform_contam_prj.py` | `destroyer_baseline`, `mega_cruise_5000`, both Enterprise (defaults `:36-41`) | none — it exports JSON → PRJ + path_map | `contam/` |
| `scripts/build_enterprise_platforms.py` (`main` `:470-479`) | both Enterprise | the **legacy** 4- and 6-link layouts (`:88-117`, `:209-252`); no galley link at all | `data/platforms/enterprise_*/` and two pathogen and two template files |

`scripts/build_enterprise_platforms.py` is imported by nothing (measured by
search). Run into a scratch directory (measured), it writes a 12-zone,
4-link Constitution and a 16-zone, 6-link Galaxy, against the committed 63
zones / 29 links and 127 zones / 53 links. Running it in the repo would
replace both hulls wholesale.

### 5.2 Does regeneration revert #1219 / #1220 / #1221?

Measured by calling each generator's pure `build_spatial_layout` /
`build_air_flow_paths` in memory and comparing with the committed JSON
(nothing written; `git status` clean afterwards).

| Hull | Links | Differ on regeneration | Semantic reversion | Other content that changes |
|---|---:|---:|---|---|
| `expedition_cruise_450` | 17 | 4 | `Dining_Galley_Exhaust` → bidirectional pressure opening (#1219) | — |
| `classic_cruise_1900` | 31 | 14 | the same | — |
| `spirit_cruise_3000` | 48 | 20 | the same | — |
| `diamond_princess` | 53 | 14 | the same | — |
| `enterprise_constitution_tos` | 29 | 10 | `Galley_Service_Exhaust` back to `Galley` → `Mess_Hall`, bidirectional (#1219) | `hot_bunk_ratio: 2` dropped on 12 `EC_D*` zones in `spatial_layout.json` |
| `enterprise_galaxy_tng` | 53 | 16 | the same | — |
| `mega_cruise_5000` | 88 | 21 | `Crew_to_Engine_Stairwell` (`AHU_Crew_Deck_D4`) → bidirectional (#1220) | 7 HVAC groups gain a per-group `oa_fraction` (0.2–1.0) |
| **Total** | 319 | **99** | **7 links** | |

- The other 92 differing links lose only the explicit `direction` /
  `mechanism` / `filtered` keys. Their resolved semantics are unchanged
  (alias-equivalent), but the committed-data test would fail.
- All 216 sanitary links on these hulls regenerate identically.
- #1221 authored only hand-authored hulls, so no generator reverts it.
- The two `mega_cruise_5000` links that #1220 authored by way of
  `messy_cruise_500` survive, because the mega generator copies them from
  the hand-authored hull.

The two non-link drifts predate the forced-exhaust bundle. The
`hot_bunk_ratio` values came in with `e86b73bf` (SCHED-WATCH-01) as direct
data edits. *Hypothesis*: the `mega_cruise_5000` per-group OA difference is
`messy_cruise_500` data gained after mega was last generated; which side is
intended was not investigated, and Phase 2 ran on the committed file.

### 5.3 Fleet-wide check for other generated hulls with authored links

Measured: 17 non-sanitary links carry semantics that differ from the alias
expansion — the full set of authored links at risk.

| Hull class | Links | Protected by a generator? |
|---|---:|---|
| Recipe-generated | 9 (4 `Dining_Galley_Exhaust`, 2 `Galley_Service_Exhaust`, 3 on `mega_cruise_5000`) | 7 revert; 2 survive via `messy_cruise_500` |
| Hand-authored | 8 (`expedition_cruise_300` 1, `fletcher_class_destroyer` 1, `greg_mortimer` 1, `legend_class_nsc` 1, `messy_cruise_500` 2, `san_antonio_class_lpd` 2) | no generator; committed data is the source |
| GA importer | 0 | — |

The GA importer's exposure is the sanitary pin: 252 `Sanitary_Makeup` links
on 68 hulls carry `direction: oneway` in committed data that
`synthesize.py` would not emit. *Inferred* from the code path; a GA hull was
not regenerated because the ship digests are not in the tree.

### 5.4 Proposal (`GENERATOR-PROTECT`)

The existing round-trip tests compare only zone-id and HVAC-id sets
(`tests/test_enterprise_platforms.py:228-242`,
`tests/test_cruise_platform_cabin_corridor.py:58-72`), which is why none of
this was caught.

| | Minimal path G-min | Spec-faithful path G-full |
|---|---|---|
| Idea | Committed JSON is the source of truth; generators are bootstrap-only | Generators stay authoritative and are brought back into agreement |
| Recipe hulls | `write_platform` and the mega writer refuse to overwrite an existing platform directory without an explicit flag | Recipes carry the authored links verbatim; the builder emits the S1 triple on auto links; the two non-link drifts are resolved toward committed data |
| Test | none new beyond the guard | Round-trip tests assert full equality of `cross_zone_links` (then of the whole file) between generator output and committed JSON, for all 7 hulls |
| GA importer | emit the S1 triple on `Sanitary_Makeup` from one shared helper | the same |
| `build_enterprise_platforms.py` | delete, or guard the same way | the same |
| Cost | small; no recipe edits | 6 recipe blocks, the mega generator, two drift decisions |
| Risk left | recipes keep drifting, harmlessly | none while the test holds |

Common to both, and the part that mirrors the sanitary protection: the
emitter itself writes the declared semantics, and a test compares emitter
output with committed data. For sanitary links that means one shared
function used by `derive_sanitary_provisioning.py` and `synthesize.py`, with
a unit test that both return the same key set and `direction: oneway`.

Recommendation: **G-min now** — it removes the overwrite hazard in one small
change — and G-full only if the recipes are going to be used again to build
hulls.

## 6. Rollout order and ledger

### 6.1 Order

Each stage is its own PR with its own ledger entry, `Pathogens: all`.

| # | Stage | Suggested ledger ID | Depends on | Changes behaviour? |
|---|---|---|---|---|
| 0 | This audit and plan | `CONTAM-EXHAUST-SINK-01` | — | No |
| 1 | Generator guard, shared sanitary emitter, legacy builder removed or guarded (G-min) | `CONTAM-GENERATOR-PROTECT-01` | — | No |
| 2 | path_map schema, `filtered` carry-through (P-min), exporter raises on unresolved endpoints | `CONTAM-PATHMAP-FILTERED-01` | — | Lane only, on hulls with a divergent link (two, neither committed nor frozen) |
| 3 | Sink endpoint: schema + sanity check, native, exporter + lane (S1, N1, X1) | `CONTAM-EXHAUST-SINK-02` | 2 | No — inert until authored |
| 4 | Re-point the three links (D1), with before / after rows | `CONTAM-EXHAUST-SINK-03` | 3 | Yes — two hulls; open-ledger notes land here |
| 5 | Re-sync the stale `mega_cruise_5000` bundle (PRJ + path_map together); the two Enterprise bundles ride along best-effort | `CONTAM-BUNDLE-RESYNC-01` | 2 | P-lane field for the re-synced hulls; new cache version |
| 6 | Optional authoring rows: `Dining_to_Galley_Transfer` ×2, galley hood sinks | per row | 3 | Yes — each needs its own standards basis |

Stage 1 goes first because it is the only one that guards work already
merged. Stages 2 and 3 are ordered so that no path_map is ever written with
a sink the lane cannot read. If path M is chosen instead of S, stages 3 and
4 collapse into one data-only PR and stage 6 has no vehicle.

### 6.2 What stays frozen

Both campaign directories, their S3 prefixes, the `_v1` field caches, the
committed readouts, and ledgers `CONTAM-PHASE1-*`, `CONTAM-PHASE2-*`,
`CONTAM-EDISON-RETURN-01`. No existing ledger entry is edited by this PR.
No open-ledger note is added, because no recorded measurement is
invalidated by a document.

### 6.3 Open decisions for the owner

1. Path S or path M for the three links (§3.3).
2. G-min or G-full (§5.4).
3. Whether the sink needs a runtime labelled-baseline switch, or whether the
   pre-change hull JSON at its SHA is the baseline (§3.4).
4. Whether a sink link is paired with an authored make-up link on each hull
   (§3.4). The present links run medical → berthing, the reverse of the
   negative-pressure regime their descriptions state.
5. Which side is right for the `mega_cruise_5000` per-group OA drift (§5.2).

## Appendix — reproduction

All commands run from the repo root at `800a1958` with
`PYTHONPATH=. .venv/bin/python`. None writes inside the repository. The
scripts are inline because this PR is doc-only.

**Counts, the `filtered ≠ ducted` set, and the exhaust-class split (§1, §2.2, §3.2).**

```python
import glob, json, os, re
from engines.py_contam_bridge import cross_zone_link_semantics as sem
EXH = re.compile(r"exhaust|extract|hood|relief", re.I)
files = sorted(glob.glob("data/platforms/*/air_flow_paths.json"))
links = [(f.split("/")[2], l) for f in files
         for l in json.load(open(f)).get("cross_zone_links", [])]
print(len(files), len(links),
      len(glob.glob("data/platforms/*/contam/path_map.json")))
for hull, l in links:
    if sem(l)["filtered"] != bool(l.get("is_hvac_ducted", False)):
        print(hull, l["path"], l["from"], "->", l["to"])
exh = [l for _, l in links
       if EXH.search(l.get("path", "") + " " + l.get("description", ""))]
print(len(exh), sum(l.get("path") == "Sanitary_Makeup" for l in exh))
```

**Exact material-time for the link variants (§2.1, §3.3).**

```python
import copy, json
import numpy as np
from scipy.linalg import expm
from engines.py_contam_bridge import ContamTransportEngine
from engines.sim_clock import SimClock

def operator(spatial, airflow):
    eng = ContamTransportEngine(
        spatial, airflow, filter_efficiency=0.5, natural_decay_rate=0.0,
        clock=SimClock(epoch_duration_hours=1.0, mode="hours"))
    return list(eng._real_zone_ids), eng._build_decay_free_operator(), eng

def mass_time(op, i, horizon_h=12.0):
    n = op.shape[0]
    block = np.zeros((2 * n, 2 * n))
    block[:n, :n], block[:n, n:] = op, np.eye(n)
    start = np.zeros(n); start[i] = 1.0
    return expm(block * horizon_h)[:n, n:] @ start

def variants(hull, path, src):
    d = f"data/platforms/{hull}/"
    sp = json.load(open(d + "spatial_layout.json"))
    af = json.load(open(d + "air_flow_paths.json"))
    link = next(l for l in af["cross_zone_links"] if l.get("path") == path)
    for flag in (True, False):                       # filtered true / false
        a = copy.deepcopy(af)
        next(l for l in a["cross_zone_links"]
             if l.get("path") == path)["filtered"] = flag
        ids, op, _ = operator(sp, a)
        yield f"filtered={flag}", ids, mass_time(op, ids.index(src))
    a = copy.deepcopy(af)                            # sink: link out of domain
    a["cross_zone_links"] = [l for l in a["cross_zone_links"]
                             if l.get("path") != path]
    ids, op, eng = operator(sp, a)
    i = ids.index(src)
    op[i, i] -= link["flow_rate_m3h"] / eng.zone_nodes[src].volume_m3
    yield "sink", ids, mass_time(op, i)
    for g in a["hvac_zones"]:                        # path M: once-through group
        if g["id"] == link["from"]:
            g["oa_fraction"] = 1.0
    ids, op, _ = operator(sp, a)
    yield "path M", ids, mass_time(op, ids.index(src))
```

Cases: (`legend_class_nsc`, `medical_exhaust`, `Sickbay`),
(`san_antonio_class_lpd`, `medical_exhaust`, `Medical_Ward`),
(`san_antonio_class_lpd`, `galley_exhaust_to_mess`, `Galley`).

**Fresh export versus committed path_maps, and the lane's `filtered` (§2.2, §4.3).**

```python
import glob, json
from tools.contam_prj_bridge import export_prj_with_path_map
from engines.contamx_transport import ContamXTransportEngine
for f in sorted(glob.glob("data/platforms/*/contam/path_map.json")):
    d = f.rsplit("/contam/", 1)[0] + "/"
    sp = json.load(open(d + "spatial_layout.json"))
    af = json.load(open(d + "air_flow_paths.json"))
    committed = json.load(open(f))
    _, fresh = export_prj_with_path_map(sp, af)
    stale = [(a["path_nr"], a["kind"]) for a, b in zip(committed, fresh)
             if a != b]
    if stale or len(committed) != len(fresh):
        print(d, stale)
# lane filtered flag for a hull without a bundle:
#   _, pm = export_prj_with_path_map(sp, af)
#   eng = ContamXTransportEngine.from_flow_field(
#       sp, pm, {e["path_nr"]: 100.0 for e in pm if e["kind"] == path},
#       filter_efficiency=0.5, natural_decay_rate=0.0)
#   [(p.path_id, p.filtered) for p in eng.airflow_paths
#    if p.path_type == "contamx_path"]
```

**In-memory regeneration of the recipe hulls (§5.2).**

```python
import json, sys
sys.path.insert(0, "scripts")
import generate_cruise_platform_layout as G
import generate_mega_cruise_cabin_layout as M
from cruise_platform_recipes import RECIPES as CRUISE
from enterprise_platform_recipes import RECIPES as ENTERPRISE
from engines.py_contam_bridge import cross_zone_link_semantics as sem

def compare(pid, spatial, airflow):
    d = f"data/platforms/{pid}/"
    cs = json.load(open(d + "spatial_layout.json"))
    ca = json.load(open(d + "air_flow_paths.json"))
    pairs = list(zip(airflow["cross_zone_links"], ca["cross_zone_links"]))
    print(pid, spatial == cs,
          {k for k in ca if k != "cross_zone_links" and airflow.get(k) != ca[k]},
          sum(g != c for g, c in pairs),
          [c["path"] for g, c in pairs
           if sem(g) != sem(c) or (g["from"], g["to"]) != (c["from"], c["to"])])

for pid, recipe in {**CRUISE, **ENTERPRISE}.items():
    sp = G.build_spatial_layout(recipe)
    compare(pid, sp, G.build_air_flow_paths(recipe, {z["id"] for z in sp["zones"]}))
legacy = json.load(open(M.LEGACY_LAYOUT))
legacy_air = json.load(open("data/platforms/messy_cruise_500/air_flow_paths.json"))
sp = M.build_spatial_layout(legacy)
compare("mega_cruise_5000", sp,
        M.build_air_flow_paths(legacy_air, {z["id"] for z in sp["zones"]}))
```

The legacy Enterprise builder was run with its module-level `DATA` pointed at
a scratch directory outside the repository.
