# CONTAM-SPIRIT-CABIN-RELIEF-01
**Date:** 2026-11-17
**Commit:** bed09e97
**Pathogens:** all
**Status:** measured
**Measured at:** bed09e97

## Scope

Spirit `spirit_cruise_3000` cabin-relief loop only. Evidence base:
`docs/audits/2026-11-17_contam_pressure_localization/` (committed in parallel),
with the pinned finding that eight `Cabin_Relief_D4`–`Cabin_Relief_D11`
declarations prescribe 12,000 m³/h cabin-group → `AHU_Public_Mid` and expand to
288 room-pair fan paths against a small-opening return network. Machinery:
`CONTAM-AMBIENT-OPENING-SCHEMA-01`, `CONTAM-AMBIENT-WEATHER-CRUISE-01`,
`CONTAM-AMBIENT-MAKEUP-CRUISE-01`.

Adjudication (Grade C where assumed; no drawing was read):

- The eight `Cabin_Relief_D*` links remain the prescribed relief/transfer legs;
  their existing `flow_rate_m3h` magnitudes are unchanged.
- Each gets a compensating `Cabin_Return_D*` link, `AHU_Public_Mid` →
  `AHU_Pax_D#`, `oneway`/`prescribed_flow`/`filtered`, `is_hvac_ducted: true`,
  at the same declared 1,500 m³/h per deck branch. This is the authored
  return/make-up route for the imposed loop, not a capacity test and not a
  change to the relief demand.
- The 54 `corridor` adjacency edges are open circulation (cabin-corridor
  blocks, public/service corridors), not individual closed-cabin undercuts;
  Spirit's hobbyist `orifice_type_map` now maps `corridor` → catalog
  `corridor` (3.0 m²) instead of `cabin_relief` (0.02 m²). No adjacency `type`
  was silently left as a cabin undercut; `cabin_relief` is reserved for an
  explicitly closed-cabin undercut, of which this layout declares none.

## Records

`data/platforms/spirit_cruise_3000/air_flow_paths.json`: descriptions added to
the eight relief links and eight new return links; no existing
`flow_rate_m3h` value changed. `contam/hobbyist_overrides.json`: only
`orifice_type_map["corridor"]` changed (`cabin_relief` → `corridor`). The
Spirit Contam bundle was regenerated with
`scripts/generate_platform_contam_prj.py --platform spirit_cruise_3000
--hobbyist --ahs-terminal-mode commissioned`; path_map 1,311 → 1,599 entries
(the +288 are the return room-pair paths; +0 adjacency count change). Other
hulls' bundles are byte-identical (`git diff --name-only origin/main --
data/platforms` shows only `spirit_cruise_3000`). The Phase 2
`contam_phase2_cruise_contrasts_02` successor design is generated from the
current platform JSONs, so its Spirit `path_map_entries` is repinned
1,311 → 1,599 and the campaign contract expectation moves with attribution;
the frozen `_01` design/pools/campaign/readouts and caches are untouched.

## Witnesses

Pressure diagnostic (`tools/diag/contam_pressure_balance_diagnostic.py`, local
`third_party/contamx/contamx3`), exact max `|dP|` in Pa:

| lane | before | after |
|---|---:|---:|
| commissioned, all paths | 550.2048950195312 | 24.167022705078125 |
| commissioned, interior flowing | 539.4534301757812 | 22.147014617919922 |
| design, all paths | 756.8825073242188 | 9.68641185760498 |
| design, interior flowing | 741.7789306640625 | 4.880223274230957 |

The collapse is with the authored topology: the eight relief fans remain and
the return route is explicit. `tools/contam_flow_compare.py --platform
spirit_cruise_3000 --inject MainDining_L --inject MainGalley --run-contamx`:
native 1,433 paths; ContamX path_map 1,599 with fates kept 1,113,
bridge_input 359, boundary_sink 4, skipped 123; crusher_paths 1,313; zero-flow
real candidates 4 (pre-existing sanitary/nightclub orifices); connectivity
gaps for `MainDining_L`/`MainGalley` are not isolated. The 576 kept links
sharing 41.6739 m³/h are the 288 relief + 288 return room-pair prescribed
fans, not a SIM join fault.

`tools/diag/contam_paired_diagnostic.py --hull spirit_cruise_3000 --source
MainDining_L --source MainGalley` (12 cells; `pulse_t0`/`split_t0_t1`):
whole-hull material-time hours are native 0.175 vs commissioned/authored
0.189 for `MainDining_L`, and native 0.093 vs commissioned/authored 0.096 for
`MainGalley`; commissioned equals authored because the committed bundle was
regenerated in commissioned mode. Local/remote splits are close
(`MainDining_L` 0.124/0.064 field vs 0.104/0.071 native; `MainGalley`
0.091/0.006 field vs 0.092/0.000 native). Timing cells are identical between
`pulse_t0` and `split_t0_t1` for every lane.

## Validation

`check-jsonschema` on the Spirit `air_flow_paths.json`: ok.
`python3 tools/sanity_checker.py --from-config`: VALIDATION PASSED with 2
warnings. `python3 -m pytest tests/ -m 'not slow' -n auto`: 8,758 passed,
9 skipped; `tests/test_ledger_entries.py` passes.
`python3 campaigns/contam/phase2_cruise_contrasts_01/design/build.py --check`:
OK (1,200 trajectories / 60 blocks / 32 fields). `pre-commit run --files`
on the changed files is clean; `python3 scripts/sonar_guard.py
tests/test_contam_phase2_cruise_contrasts_campaign.py` is clean; the scoped
`ruff check` on that test file passes. The known CmdStan wastewater
comparison did not fail in this local run; CI remains authority if it drifts
elsewhere.
