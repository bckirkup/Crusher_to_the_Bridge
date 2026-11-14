# CONTAM-FORCED-EXHAUST-S1-01
**Date:** 2026-11-14
**Commit:** 7dec793c
**Pathogens:** all
**Status:** open
**Measured at:** dfd7d55c

Stage S1 of `docs/proposals/forced_exhaust_audit_and_fix_plan.md` (§5.3 schema,
§5.4 N1 native filtered read, §5.7 step 5 first half). This is an
authoring/schema migration only: it makes the resolved cross-zone link triple
explicit and proves the native transport operator did not move. X1/X2 exporter
work and §5.5 per-link authoring remain parked.

## Schema and alias

`schemas/air_flow_paths.schema.json` `CrossZoneLink` gains optional `mechanism`
(`prescribed_flow` | `pressure_opening`) and `filtered` (boolean). `direction`
stays optional; `is_hvac_ducted` stays as a deprecated alias. The fixed
expansion is:

| `is_hvac_ducted` | `direction` | `mechanism` | `filtered` |
|---|---|---|---|
| `true` | `oneway` | `prescribed_flow` | `true` |
| `false` | `bidirectional` | `pressure_opening` | `false` |

Explicitly declared fields win over the expansion.

## Migration

All 82 `data/platforms/*/air_flow_paths.json` files / 1,011 `cross_zone_links`
received the explicit triple by targeted text edit; `is_hvac_ducted` remains on
every link. The 585 D1 `Sanitary_Makeup` pins keep `direction: "oneway"`; the
other 426 links gained explicit `direction` (`bidirectional` for 316 passive
openings, `oneway` for 110 ducted fan legs). No flow rate,
`DEFAULT_PASSIVE_LINK_MODE`, adjacency, or exporter file changed.

`scripts/derive_sanitary_provisioning.py` now emits the same explicit fields
for newly derived sanitary links; existing platform files were not regenerated.

## Native N1 read

`engines/py_contam_bridge.py` resolves link semantics through
`cross_zone_link_semantics` / `cross_zone_link_filtered`: `filtered` wins when
present, otherwise the `is_hvac_ducted` expansion applies. `ContamAirflowPath`
carries `filtered` (defaulting to `is_hvac_ducted` for hand-built paths), and
the two filtration reads use `path.filtered`. Direction handling is unchanged.

## Operator-identity proof

`tests/test_contam_s1_migration.py` checks, for every link on every platform,
that the migrated resolved `(direction, mechanism, filtered)` equals the
pre-migration resolution from `is_hvac_ducted` plus any declared direction, and
that the decay-free `ContamTransportEngine` operator is exactly equal
before/after (`filter_efficiency=0.37`, `natural_decay_rate=0.0`) on all 82
platforms. The same comparison was run against the pre-migration `HEAD` data
during development: 82/82 platforms, 1,011 links, max operator difference 0.0.
`tools/contamw34_prj.py` is untouched, so the ContamX exporter remains
byte-identical for these inputs.

## Consumers

The only `is_hvac_ducted` reads changed are the two native filtration sites.
The exporter still reads the retained alias. Other hits are producers of new
alias-compatible links, diagnostics on exported path maps, legacy interchange
serialization, or ContamX solved-path handling; they either do not consume the
new fields or resolve through the same alias fallback.

## Status and blast radius

Status stays `open`: this records the landed schema/data/engine change and its
structural operator proof, not a campaign re-measurement. No epidemiological
constant, flow rate, exporter element, or passive-link default changed. X1/X2
and §5.5 authoring remain parked for later stages.
