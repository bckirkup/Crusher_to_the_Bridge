# Fleet CONTAM vs native solver comparison

**Status:** measured — first fleet sweep, 2026-10-28 (80 platforms, 9 arms,
2 scenarios, 3 repeats, 12 epochs). Generated table:
[contam_fleet_compare_table.md](contam_fleet_compare_table.md).
Ledger entry: `docs/ledger/CONTAM-FLEET-01.md`.

## What this is

`tools/contam_fleet_compare.py` sweeps every platform in `data/platforms/`
through the respiratory / chemical-tracer scenario pair and nine operational
knob arms, running the native `ContamTransportEngine` and ContamX
(`third_party/contamx/contamx3`) side by side. Arm/scenario definitions are
committed at `data/config/contam_compare/fleet_arms.json`; the spec, arm
op vocabulary, and injection-site selector are covered by
`tests/test_contam_fleet_compare.py`.

Lanes:

- **native** — `ContamTransportEngine` built from the platform's
  `air_flow_paths.json` (mutated per arm).
- **contamx (export)** — the same mutated airflow exported via
  `export_prj_with_path_map(..., ahs_terminal_mode="commissioned")`, solved by
  `contamx3`, and propagated by `ContamXTransportEngine`. This is the honest
  knob pairing: the identical mutation reaches both engines.
- **contamx_committed (baseline arm only)** — the authentic
  `contam/platform.prj` where one exists (75/80 platforms). It anchors how
  much of the divergence is *authoring* (the authentic model's own network)
  vs *solver* (same exported field).

Headline metric per knob is **response parity**: does each solver move the
same zones, in the same direction, by the same size, arm vs its own
baseline — not whether the baseline fields match.

## Measured (working tree a35eb254 + this change, repeats=3)

### Speed

| quantity | small hulls (<80 zones, n=60) | large hulls (≥80 zones, n=19) |
|---|---|---|
| native traj / contamx traj ratio | median 0.96 | median 1.07 |
| ContamX field solve (export + subprocess + SIM read) | median ~90 ms | max 588 ms |
| native engine build | ~0–5 ms | ~5 ms |

Propagation wall-clock is a wash — ContamX is ~7% slower on the largest
networks. The real ContamX cost is the **field solve**: a subprocess +
steady-state solve each time the airflow JSON mutates (once per arm, ~90 ms
median). Engine-level knobs (`oa_fraction`, `filter_efficiency`,
`natural_decay_rate`) apply post-solve in the Crusher bridge and cost
nothing extra on either side. Fleet wall-clock: ~13 min for
80 platforms × 9 arms × 2 scenarios.

### Baseline divergence

| lane | median dose-L1 vs native | p10 | p90 | max |
|---|---|---|---|---|
| contamx (export twin) | 23.8 | 4.9 | 1590 | 2670 |
| contamx_committed (authentic .prj) | 620 | — | — | 33,809 |

The authentic committed prjs diverge ~26× further from native than the
exported twin does. Most of a "native vs CONTAM" gap is therefore
**authoring** — the hand-traced prj network differing from the JSON airflow —
not solver numerics. Retained injected fraction at epoch 12 is near zero
both sides (native median 7e-4, ContamX ~0); ContamX drains injected mass
into plenum/exhaust paths slightly more completely.

Worst export-lane divergences: `gordon_gunter_r338` (2669),
`enterprise_galaxy_tng` (2470), `castle_class_corvette` (2318),
`fletcher_class_destroyer` (2306), `pt_564` (1829). Best: `texas_bb35`
(1.9), `new_york_bb34` (2.0), `lyon_ap71` (1.8) — divergence is a hull
property, not a size property.

### Knob-response parity (respiratory; sign-agreement median across 79 hulls)

| arm | median sign agreement | hulls where native moved 0 zones | hulls where ContamX moved 0 |
|---|---|---|---|
| ahu_casualty | **0.16** | 5 | 0 |
| zone_isolation | 0.61 | 4 | 0 |
| hatches_closed | 0.62 | 3 | 0 |
| night_setback | 1.00 | 5 | 0 |
| ach_surge | 1.00 | 0 | 0 |
| outdoor_air | 1.00 | 8 | 0 |
| full_recirc | 1.00 | 0 | 0 |
| filter_merv13 | 1.00 | 8 | 0 |

- **AHU casualty is the standout disagreement.** ContamX moves dose in 92–120
  zones on the large cruise hulls; native moves 0 zones on five hulls
  (`aeolus_arc3`, `idaho_bb42`, `missouri_bb63`, `new_jersey_bb62`,
  `wisconsin_bb64`) and moves *opposite-signed* on most of the rest —
  killing the injection zone's own AHU removes its return leg in the native
  star topology, so retained mass goes **up** (destroyer +0.68) while
  ContamX's symmetric field edges barely change retained (−5e-5). The two
  solvers do not agree on what losing an AHU does; this is the knob where a
  ship-operations claim would flip depending on which engine you ran.
- Isolation-type knobs (`zone_isolation`, `hatches_closed`) agree on which
  zones move ~6/10 — partial sign agreement means both engines quarantine
  but disagree on secondary effects.
- All continuous knobs (duty, ACH, OA, recirc, filter) agree on sign 1.00
  where both engines respond; magnitudes differ by 10²–10⁶× on large hulls
  (ContamX's denser field propagates deltas much further).
- Chemical-tracer rows track respiratory rows almost exactly — decay does
  not interact with any knob's effect direction.

## Expressibility gaps (measured / inexpressible)

1. **Per-zone NBC citadel filtration is inexpressible**: `nbc_filter_*`
   platform fields feed no code path; `filter_efficiency` is one global
   scalar. Only 2/80 hulls (`legend_class_nsc`, `san_antonio_class_lpd`)
   declare citadel fields at all, and neither has a committed prj.
2. **Committed authentic prjs cannot see JSON-side knob mutations**: duty,
   ACH, OA, and link edits live in `air_flow_paths.json`; knob arms must
   use the export lane. The committed lane therefore only runs at baseline.
3. **Non-hobbyist export hard-codes `oa_frac=0.2` and `filter_nr=0`**
   (`tools/contamw34_prj.py`): declared per-platform OA only reaches a
   *solved field* under `hobbyist=True` exports; the bridge still applies
   `oa_fraction` post-solve, so declared-oa≠0.2 hulls get a field whose
   AHS legs assume 0.2.
4. **Bridge `oa_fraction` is a single scalar** — no per-AHU granularity on
   either engine.
5. **olympia_c6 has zero zones** — a degenerate platform; the ContamX
   export solve hung (300 s timeout) and the platform is recorded as an
   error row, not a measurement.

## Reading the report

`telemetry_buffer/contam_fleet_compare/fleet_compare_latest.json`
(gitignored) carries per-cell detail: timing, retained fractions,
`dose_per_zone`, `response_parity` (zones moved / sign agreement /
magnitude ratio), and the applied `edits` per arm. Reproduce:

```bash
python3 tools/contam_fleet_compare.py --platforms all \
  --out telemetry_buffer/contam_fleet_compare \
  --md-out docs/contam_fleet_compare_table.md
```

## Open questions for a next stage

- Which of the five native-moved-0 hulls is sparse-coupling (the casualty
  never reaches injected mass in 12 epochs) vs a native duty-read gap —
  needs a reachability probe per hull, not just dose diffs.
- Whether the committed prj's ~26× authoring delta concentrates in
  specific path classes (AHS legs vs leakage paths) — a path-inventory
  diff, not a dose diff.
