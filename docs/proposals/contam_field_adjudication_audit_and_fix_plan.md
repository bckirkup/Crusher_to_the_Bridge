# Contam native-vs-field adjudication and fix plan

> **Status:** Proposed audit; no fix has landed. Measured against
> `origin/main` `78a023b6` (post-#1241/#1242). Audit ledger:
> [`../ledger/CONTAM-FIELD-ADJUDICATION-01.md`](../ledger/CONTAM-FIELD-ADJUDICATION-01.md).
> This document lives in `docs/proposals/` because the fixes it versions are
> not in-tree; its audit findings are measured, but it is not documentation of
> current behaviour.

**Evidence vocabulary.** *Measured* = computed this session from the tree at
`78a023b6` with the committed paired diagnostic and compare/flow tools, or
from the local ContamX 3.4.0.3 binary `third_party/contamx/contamx3`.
*Inferred* = follows from measured facts plus the cited code path.
*Hypothesis* = not tested. `file:line` references are to `78a023b6`.

**No constant is proposed, chosen or adjusted here to make any model output
match any other.** The question is mechanism/spec adjudication: which lane is
representing what, and which differences are defects versus declared
representation choices.

## 1. Verdict table

| # | Preserved difference | Verdict | One-line reason |
|---|---|---|---|
| a | Expedition service hatch solves `MainGalley -> MainDining` ≈ 2,120 m³/h versus native fixed 8 m³/h each way | **Legitimate representation difference**; magnitude rides on (d) | Native adjacency is a prescribed-rate exchange; the field exports the same adjacency as a pressure-driven `plr_orfc`, whose sign and magnitude are solver outputs |
| b | Pool deck solves ≈ 2,127 m³/h `PoolDeck -> CasualDining` plus ≈ 1,891 m³/h `ObsLounge -> PoolDeck` versus native ≈ 400 m³/h declared opening | **Authoring gap** | The field is faithfully solving pressure openings, but the authored opening set (duplicate doorway + `open_deck` mapped to a 10 m² promenade) is not the same physical declaration as the native 400 m³/h link |
| c | Galley release remote material-time ≈ 12× in the field lane | **Legitimate representation difference** (downstream of a/b) | Remote mass-time is larger because the field carries galley mass through the solved hatch/opening network that native represents as fixed small exchanges |
| d | Solved pressure drops remain extreme after the #1241 laminar probe | **Authoring gap** | ContamX is solving the authored PRJ; the implausible ΔP is produced by envelope/make-up/AHS authoring, not by the transport kernel consuming flows |
| e | Destroyer authored field has two outward envelope leaks totalling 0.5403 m³/h that are ignored as contaminant paths | **Needs owner decision** | Envelope leaks are pressure-boundary elements (`crusher_transfer: false`, lane-skipped); whether outward leakage should also be a contaminant sink is a boundary-semantics choice, not a proven defect |
| f | Authored-project vs commissioned sanitary head whole-hull material-time (`HD_5P_M` 0.231018 vs 0.0517565 h) | **Authoring gap** | Committed authored bundles are `ahs_terminal_mode="design"` historical annotations; `commissioned` mode is the declaration-faithful terminal encoding |

**Code-defect check.** No class was proven to be a defect in
`ContamTransportEngine`, `ContamXTransportEngine`, or the paired diagnostic.
The closest calls are (d), where the pressure field is implausible, and (f),
where the default `design` terminal mode does not reproduce declared per-branch
flows; both are authoring/spec gaps with versioned proposals below, not evidence
that the exact propagator is wrong.

## 2. Evidence base

The committed paired diagnostic is the source of the material-time numbers:

```bash
PYTHONPATH=. .venv/bin/python tools/diag/contam_paired_diagnostic.py \
  --out telemetry_buffer/contam_paired_diagnostic/field_adjudication_results.json
```

This session regenerated 42 cells at `78a023b6` and reproduced the
`CONTAM-PAIRED-RECOMPARE-01` post-fix commissioned `pulse_t0` values to the
ledger's precision (for example Expedition `MainDining` 0.1912604906581144,
`HD_5P_M` 0.051756484614901455, `PoolDeck` 0.7740977157007225, `MainGalley`
0.1068440991137111; destroyer `Mess_Hall` 0.3252110940500446, `HD_MAIN_M`
0.05168714306011469, `Bridge` 0.4165951917194409). The full table remains in
[`../ledger/CONTAM-PAIRED-RECOMPARE-01.md`](../ledger/CONTAM-PAIRED-RECOMPARE-01.md);
the regenerated JSON is a local check and is not committed.

Flow-level evidence uses the committed compare tool on the committed authored
bundles, plus a one-off parse of the ContamX `.SIM` path records for ΔP (the
`SimFrame` reader stores `Flow0`; this session read the sibling `dP` field at
the same record stride for diagnosis only):

```bash
PYTHONPATH=. .venv/bin/python tools/contam_flow_compare.py \
  --platform expedition_cruise_450 --run-contamx \
  --output telemetry_buffer/contam_flow_compare/expedition_authored.json
PYTHONPATH=. .venv/bin/python tools/contam_flow_compare.py \
  --platform destroyer_baseline --run-contamx \
  --output telemetry_buffer/contam_flow_compare/destroyer_authored.json
```

The two compare outputs are local diagnostics, not committed artifacts. Where a
number below is a flow or ΔP it is *measured* from those runs at `78a023b6`;
Edison's preserved pre-fix figures are quoted only as the class definitions he
supplied.

## 3. Class adjudications

### (a) Service-hatch reverse flow — legitimate representation difference

**Measured.** Authored Expedition `path_nr` 57 (`kind: service_hatch`,
`MainGalley -> MainDining` in `path_map` orientation) solves
`Flow0 = +2120 m3/h`, i.e. `MainGalley -> MainDining`, at `dP = +446.5 Pa`;
Edison preserved 2119.93 m3/h. The fresh commissioned export solves the same
path at 2483 m3/h, `dP = +612.6 Pa`, so #1241 changed the magnitude but not the
sign or mechanism. Native has two fixed adjacency links,
`adj_MainDining_MainGalley` and `adj_MainGalley_MainDining`, each 8 m³/h.

**Mechanism (inferred from code).** Native adjacency is not a physical opening;
it is a prescribed-rate bidirectional exchange:
`engines/py_contam_bridge.py:638-658` maps `service_hatch` to 8 m³/h and emits
both directions. The ContamW exporter instead emits one adjacency path per
declared adjacency and chooses an orifice element by adjacency type:
`tools/contamw34_prj.py:821-853` (`_adjacency_element_for_type`,
`_add_adjacency_paths`). For Expedition, `service_hatch` is overridden to the
`hatch` catalog entry (`data/platforms/expedition_cruise_450/contam/hobbyist_overrides.json:3-17`),
whose area is 0.36 m² (`data/contam_hobbyist/orifice_catalog.json:25-34`). A
`plr_orfc` path's flow sign is a pressure-solution output, not an input; native
has no analogous solve.

**Verdict.** The existence of a large reverse flow is what a pressure-driven
opening does when the solved ΔP points that way; it is not an exporter defect.
The *magnitude* is not adjudicated here as physical: it is driven by the same
implausible pressure field as (d). If the owner wants service hatches to remain
fixed exchanges rather than pressure openings, that is a data/mechanism decision
(§5, stage P3), not a transport-kernel fix.

### (b) Pool-deck openings — authoring gap

**Measured.** Authored Expedition solves three relevant paths in the same
direction: `p048 open_deck ObsLounge -> PoolDeck` at 1891 m³/h (`dP = +0.006372 Pa`),
`p050 doorway` at −1151 m³/h in `path_map` orientation `CasualDining -> PoolDeck`,
i.e. `PoolDeck -> CasualDining`, and `p133 CasualDining_Open_Doorway` at −975.9 m³/h,
also `PoolDeck -> CasualDining`. The two PoolDeck→CasualDining paths sum to
2126.9 m³/h at `dP = −8.221 Pa`; Edison preserved 2126.61 m³/h. Native declares
`CasualDining_Open_Doorway` as a 400 m³/h bidirectional pressure-opening link
(`data/platforms/expedition_cruise_450/air_flow_paths.json:277-286`) plus the
separate adjacency doorway/open-deck entries (`:431-446` and the adjacency list).
PoolDeck volume is 1050 m³, so the field's direct PoolDeck→CasualDining
coefficient is 2126.9/1050 = 2.025 h⁻¹ versus ≈0.4 h⁻¹ for the native 400 m³/h
declaration. Edison's dining receptor concentration-time ratio was 208×.

**Mechanism (inferred).** The 400 m³/h link is exported as a pressure-opening
orifice sized for design flow at 1 Pa (`tools/contamw34_prj.py:644-646`,
`933-990`), while the adjacency doorway is a second, separately catalogued
orifice (`doorway`, 1.8 m²; `data/contam_hobbyist/orifice_catalog.json:10-14`).
Expedition's `open_deck` adjacency is overridden to `promenade`, area 10 m²
(`data/platforms/expedition_cruise_450/contam/hobbyist_overrides.json:13`;
`data/contam_hobbyist/orifice_catalog.json:109-112`), always on the shaft/open
schedule (`data/contam_hobbyist/schedule_templates.json:136-145`). Under the
solved pressure field all three openings carry the same direction, so the
field does not preserve the native "400 m³/h declared opening plus small fixed
adjacency" statement.

**Verdict.** This is an authoring gap, not a proven code defect: the lane is
faithfully solving the authored openings, but the authored opening set is not
the physical declaration the native lane encodes. The likely repairs are
data-side (deduplicate or right-size the doorway/open-deck declarations and
re-check the `open_deck -> promenade` override) and are versioned in §5.

### (c) Galley release remote material-time — legitimate representation difference

**Measured.** In the committed paired diagnostic (`pulse_t0`, filter 0.3,
decay 0.1/h, 12 h), Expedition `MainGalley` remote material-time is
0.0016680483135042468 h native, 0.024046017210102237 h commissioned, and
0.01838404161683253 h authored. The current authored/native ratio is 11.02× and
commissioned/native is 14.42×; Edison's preserved 12.34× sits inside this same
structural gap. Whole-hull `MainGalley` is 0.08684638875591909 native,
0.1068440991137111 commissioned, 0.10355204832358522 authored.

**Mechanism (inferred).** Remote material-time is the mass-time credited to
zones other than the source's AHU group. The field lanes connect `MainGalley`
to `MainDining`/public spaces through the solved service-hatch/opening network
((a)/(b)) and through AHS synth paths, while native's galley remote reach is
dominated by the fixed 8 m³/h hatch plus prescribed exhaust/make-up links.
There is no separate galley-source defect in the exact propagator; the
committed diagnostic's per-trajectory closure stays at machine precision
(ledger `CONTAM-PAIRED-RECOMPARE-01`).

**Verdict.** Legitimate representation difference downstream of (a)/(b); no
independent fix beyond the authoring reviews in §5.

### (d) Air-balance plausibility — authoring gap

**Measured.** From the same local ContamX `.SIM` parse at `78a023b6`:

| Lane / hull | Largest |dP| path | ΔP | Flow |
|---|---|---:|
| Expedition authored | `p001 envelope_leak MainDining -> ambient` | −7.157e5 Pa | −235.8 m³/h |
| Expedition commissioned | `p001/p002/... envelope_leak` | ≈ −9.82e5 Pa | ≈ −276 m³/h each |
| Expedition authored | `p097 Galley_Hood_Exhaust MainGalley -> ambient` | −7.152e5 Pa | 8009 m³/h |
| Expedition authored | `p057 service_hatch` | +446.5 Pa | 2120 m³/h |
| Destroyer commissioned | `p001/p002/... envelope_leak` | ≈ −8.156e4 Pa | ≈ −79.7 m³/h each |
| Destroyer authored | `p006 envelope_leak Berthing -> ambient` | +0.953 Pa | +0.270 m³/h |

Negative `Flow0` on a `zone -> ambient` `envelope_leak` path means the solved
direction is ambient→zone; the sign convention is the path-map orientation plus
`Flow0` (`tools/contam_flow_compare.py:184-199`). These ΔP values are many
orders above plausible HVAC pressure drops (order Pa, not 1e5 Pa).

**Mechanism (inferred).** Envelope leaks are emitted for every real zone to
ambient with the tiny catalog area 0.0001 m² (`tools/contamw34_prj.py:791-819`;
`data/contam_hobbyist/orifice_catalog.json:136-140`), and AHS terminals/fans are
written from declared ACH/duty/OA (`tools/contamw34_prj.py:1154-1219`). The
transport lane only consumes `path_volumetric_flow_m3h`; it does not choose or
repair the pressure solution (`engines/contamx_transport.py:150-183`).

**Verdict.** Authoring gap: the envelope/make-up/AHS authoring produces a
pressure solution that is mathematically solved but physically implausible.
This is exactly the review Edison flagged; it is not evidence against the #1241
laminar fix or the paired diagnostic.

### (e) Envelope-leak boundary handling — needs owner decision

**Measured.** Destroyer authored `.SIM` has two outward envelope leaks:
`p004 Engine_Room -> ambient` +0.2701 m³/h and `p006 Berthing -> ambient`
+0.2702 m³/h, total 0.5403 m³/h; the other authored envelope leaks are about
−0.135 m³/h (ambient→zone). In the commissioned destroyer export all envelope
leaks solve ≈ −79.7 m³/h ambient→zone. `path_map.json` marks every
`envelope_leak` `crusher_transfer: false`, and both the compare fates
(`tools/contam_flow_compare.py:79-107`) and the transport filter
(`engines/contamx_transport.py:150-153`) skip them as contaminant paths.

**Mechanism.** Envelope leaks exist so ContamX has a pressure reference to
ambient; they are not declared Crusher transfer paths. If an outward leak
carries room air across the hull boundary, a mass-conserving contaminant model
would treat it as a sink; the present lane treats it as pressure-only. The
authored outward magnitude is small (0.5403 m³/h) but the decision is semantic.

**Verdict.** Needs owner decision. If the owner rules that outward envelope
leakage is a contaminant sink, the fix is additive path_map/lane semantics for
boundary sinks (proposal §5, stage E1), not a change to declared inter-zone
airflow.

### (f) Authored-project vs commissioned sanitary terminal — authoring gap

**Measured.** Expedition `HD_5P_M` (volume 31.05 m³) is declared as an
exhaust-only sanitary branch: `AHU_HD_5P_M` has `ach: 19.2`,
`oa_fraction: 1.0`, `hvac_duty: 0.0`
(`data/platforms/expedition_cruise_450/air_flow_paths.json:164-171`), with
`Sanitary_Makeup` `AHU_Public_Fwd -> AHU_HD_5P_M` at 594.7 m³/h
(`:354-363`). Paired diagnostic `pulse_t0` whole-hull material-time is
0.05181347150259067 h native, 0.051756484614901455 h commissioned, and
0.23101756975413998 h authored — a 4.46× authored/commissioned gap. The same
pattern appears on destroyer sanitary heads (`AHU_HD_MAIN_M` ach 19.2,
oa 1.0, duty 0 at `data/platforms/destroyer_baseline/air_flow_paths.json:35-42`).

**Mechanism.** `_DEFAULT_TERMINAL_MODE = "design"`
(`tools/contamw34_prj.py:77-85`). Design mode writes each AHS terminal as the
historical uniform `ach × ΣV / n` split on the duty schedule and does not use
the commissioned per-room `ach × V_room × duty` encoding; `commissioned` mode
writes supply 0 / return `ach × V_room` for duty-0 exhaust-only heads on a
constant schedule (`tools/contamw34_prj.py:1154-1219`, `1221-1243`). Native
implements the exhaust-only convention directly for `hvac_duty <= 0` groups
declared `oa_fraction` 1.0 (`engines/py_contam_bridge.py:508-558`, with the
`duty0_terminal_mode="extract"` default at `:71-72` and parser at `:175-183`).

**Verdict.** Authoring gap. The committed authored bundle is a design-mode
artifact; the commissioned lane is the declaration-faithful check. The fix is
to decide whether design-mode bundles remain a supported lane or whether
committed bundles should be re-authored/re-versioned in commissioned mode
(§5, stage A1).

## 4. What is not a defect

- The paired diagnostic reproduces the committed post-#1241 ledger and its
  per-trajectory closure is machine-precision; methodology is sound.
- Native and authored lanes are bit-identical across #1241, as the ledger
  records; the only lane that moved was commissioned `plr_bdq` export.
- No class requires changing `air_flow_paths.json` merely to force native and
  field agreement; several classes are resolved by deciding which representation
  is authoritative for a given purpose.

## 5. Versioned fix proposals

Each stage is its own future PR with its own ledger entry, `Pathogens: all`.
This PR is stage 0 only.

| # | Stage | Suggested ledger ID | Depends on | Changes behaviour? |
|---|---|---|---|---|
| 0 | This adjudication and plan | `CONTAM-FIELD-ADJUDICATION-01` | — | No — docs only |
| 1 | Pressure/balance diagnostic: report per-path ΔP, envelope direction/flow, AHS supply/return/return-supply imbalance, and native-vs-field outflow coefficients before any data change | `CONTAM-FIELD-PRESSURE-REVIEW-01` | — | No — diagnostic only |
| 2 | Pool-deck opening authoring review for `expedition_cruise_450` (and any hull the stage-1 report flags): decide whether `CasualDining_Open_Doorway` and adjacency `doorway` are one physical door, and whether `open_deck -> promenade` 10 m² is intended | `CONTAM-FIELD-POOLDECK-OPENINGS-01` | 1 | Yes — data-only if approved; before/after `contam_flow_compare` witnesses required |
| 3 | Service-hatch mechanism decision: keep pressure opening, or declare a fixed/prescribed exchange for `service_hatch` adjacency on affected hulls | `CONTAM-FIELD-SERVICE-HATCH-01` | 1, owner decision | Yes only if owner chooses fixed exchange |
| 4 | AHS terminal-mode decision for committed authored bundles: keep `design` as historical annotation and require `commissioned` for solver-faithful work, or re-export/re-version committed bundles with `ahs_terminal_mode="commissioned"` | `CONTAM-FIELD-AHS-COMMISSIONED-01` | owner decision | Yes for authored lane if bundles re-exported; new field-cache version required |
| 5 | Envelope boundary semantics decision: whether positive outward `envelope_leak` flow is a contaminant sink; if yes, add path_map/lane sink handling for boundary leaks only | `CONTAM-FIELD-ENVELOPE-BOUNDARY-01` | owner decision | Yes — lane semantics on boundary paths only |
| 6 | Envelope/make-up authoring fixes selected from stage 1 (leak area, wind/pressure boundary, make-up pairing) per hull class | `CONTAM-FIELD-ENVELOPE-MAKEUP-01` | 1, 5 if boundary semantics change | Yes — data-only per hull with witnesses |

**Rollout order.** Stage 1 first because it converts (d)/(e) from anecdotes into
a fleet table. Stage 4 can proceed independently once the owner chooses the
authored-lane contract; it is the largest measured effect on sanitary heads
((f)). Stages 2/3/6 are data decisions and should not be batched across hulls:
one PR per hull or per mechanism, each with before/after flow and material-time
witnesses.

**What stays frozen.** Both campaign directories, their S3 prefixes, the
`_v1` field caches, committed readouts, all existing ledgers, and the frozen
legacy deploy layout. No open-ledger note is added by this PR because it
invalidates no recorded measurement; it adjudicates preserved differences.

**Open decisions for the owner.**

1. Is the authored lane intended to be a historical `design` annotation, or a
   solver-faithful Contam model? (Stage 4)
2. Should outward envelope leakage carry contaminant mass out of the domain?
   (Stage 5)
3. Are `open_deck`/`promenade` adjacency openings ever intended to be 8–10 m²
   always-open voids on cruise hulls? (Stage 2)
4. Should `service_hatch` remain a pressure opening, or be a declared
   one-way/fixed exchange? (Stage 3)

## Appendix — reproduction

All commands run from the repo root at `78a023b6` with `PYTHONPATH=.` and the
locked `.venv`. The paired diagnostic and compare tools are committed; the ΔP
parse below is inline and writes nothing into the repository.

**Paired material-time matrix (42 cells).**

```bash
.venv/bin/python tools/diag/contam_paired_diagnostic.py \
  --out telemetry_buffer/contam_paired_diagnostic/field_adjudication_results.json
```

**Authored flow fields and path fates.**

```bash
.venv/bin/python tools/contam_flow_compare.py \
  --platform expedition_cruise_450 --run-contamx \
  --output telemetry_buffer/contam_flow_compare/expedition_authored.json
.venv/bin/python tools/contam_flow_compare.py \
  --platform destroyer_baseline --run-contamx \
  --output telemetry_buffer/contam_flow_compare/destroyer_authored.json
```

**Commissioned fresh export + local ΔP parse.** The script exports
`ahs_terminal_mode="commissioned"` into a temp dir, runs
`third_party/contamx/contamx3`, then reads each path record's `nr`, `dP`,
`Flow0` at the `.SIM` record stride documented in `engines/contamx_runner.py:392-396`.
It prints the largest |dP| paths and the PoolDeck/service-hatch/sanitary paths
quoted above.
