# CONTAM pressure localization — external analysis record (2026-11-17)

> **Status:** Living — committed record of third-party analysis received from the owner on
> 2026-11-17. Findings are pending owner engineering decisions; the documents are evidence,
> not approved repairs. Nothing here certifies real-vessel ventilation adequacy.

## Provenance

Three reports produced by parallel analysis tasks against pinned repository revision
`c93fa32fbe05440e797de8b551a2781b236d7e43` (an ancestor of current `main`; the six hulls'
platform data — greg_mortimer, spirit_cruise_3000, midway_cv41, pope_ap110, aeolus_arc3,
olympia_c6 — is byte-identical between the pin and current main, re-verified by the
coordinator on 2026-11-17). Official ContamX 3.4.0.3, SHA-256
`d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`.

| Document | Content | Originating task |
|---|---|---|
| `findings.md` | Executed localization of greg_mortimer + spirit_cruise_3000 pressure problems (nine preserved solves, bounded one-at-a-time controls) | analysis task `7a52359a-2f0a-4710-ad1a-8e5297fb72fc` |
| `qa.md` | Independent QA of the Greg/Spirit localization (static inspection + scalar accounting of saved SIM outputs; no new solves) | analysis task `f786874c-f88c-4b30-9c96-dc5c49126016` |
| `localization_review.md` | Synthesis: six-hull localization table, naval/Olympia controls, duct-interface finding, prioritized engineering decisions | analysis task `87becd58-8374-439b-a4c7-269bb15c672c` |
| `evidence/` | Naval/Olympia evidence subset: census and cut-budget CSVs, class witnesses, Olympia self-link records, reproduction scripts, solver stdout, source manifests, bibliography | same naval/Olympia task |

`localization_review.md` carries "Distribution A (26-140): approved for public release;
distribution is unlimited."

## What is NOT committed, and why

- The raw executed packages (per-case `platform.prj`/`platform.sim`/`platform.xlog`,
  `paths.csv`, `rooms.csv`, `unmapped_duct_terminals.csv`, `solves/` trees, and the pinned
  source snapshots) remain with the originating analysis tasks — several tens of MB of
  binary solver output. The committed CSV/JSON summaries plus the reports' exact numbers
  are the in-repo record. The Greg/Spirit path-level tables were not part of the naval
  evidence package received by the owner.
- `evidence/current_local_paths.csv` (1.2 MB per-path table), `evidence/olympia_runs/`
  solve artifacts, and the reproduction scripts (`reduce_olympia.py`,
  `localize_naval*.py` — third-party style, would fail the repo's ruff gate) are excluded;
  regenerate from the reports' reproduction instructions or re-run the diagnostic tools on
  current main.

## Tree correction (verified 2026-11-17)

`localization_review.md` describes Olympia's four same-room paths as "two boiler rooms and
two sanitary rooms". The tree shows all four are boiler rooms: `PF_Boiler_Port`,
`PF_Boiler_Stb` ("BOILER rooms, port/starboard pair") and `HD_Boiler_Port`,
`HD_Boiler_Stb` ("BOILER room bottoms, port/starboard") — two decks × port/starboard. The
mechanism (overlapping `VENT_Machinery`/`VENT_Uptakes` group expansion emitting room→itself
paths) and the four-path count are unaffected. Per `docs/AGENTS.md`, the tree wins.

## Findings → program mapping

| Finding (report section) | Status in this repository |
|---|---|
| Olympia self-pair solver stall (review §Olympia; `evidence/OLYMPIA_FINDING.md`) | Fix in flight: skip `fr == tr` at cross-zone expansion emission in `tools/contamw34_prj.py` and `engines/py_contam_bridge.py`; ledger `CONTAM-OLYMPIA-SELFPATH-01`. Olympia's separate make-up problem (≈27.6 kPa envelope from 4,491 m³/h sanitary make-up; open-forecastle scenario → 23.52 Pa) becomes the olympia stage-4 weather-exposure follow-up after the fix merges. |
| Greg Mortimer missing service-cluster make-up route (findings §1; review row 1) | Authoring session launched (ultra): defensible service intake / mechanical make-up branch / pressure-responsive connection per findings' fix location; NOT the DiningRoom louvre, NOT exhaust reduction. Ledger `CONTAM-GREG-SERVICE-MAKEUP-01`. |
| Spirit cabin-relief loop vs 0.02 m² corridor template (findings §2; review row 2) | Authoring session launched (High): edge-by-edge adjudication of the eight `Cabin_Relief_D4..D11` declarations and corridor adjacencies; no global template change as the fix. Ledger `CONTAM-SPIRIT-CABIN-RELIEF-01`. |
| Midway / Pope / Aeolus grouped-weather cases (review rows 4–6; `evidence/grouped_weather_exclusions.csv`) | Audit/proposal session launched (doc-only): per-hull representation decisions feeding the owner's pending grouped-weather-zone question. Stage-4 scope rule (zero-outdoor-exchange zones only) is unchanged until the owner rules. |
| Auxiliary duct-spine/transport interface omission (findings §3; qa.md §1–2; review §"Additional transport-interface issue") | Audit/proposal session launched (doc-only): fleet inventory, authoring-intent determination, represent-vs-remove contract options. No transport claims from affected field-adapter runs should be read as complete CONTAM contaminant transport until this is reconciled. |

## Standing caveats (from the reports and QA, preserved here)

- Huge pressure values are diagnostic signs of inadequate represented operating
  conditions, not credible vessel pressures or validated flow predictions. No universal
  pressure cutoff was used; fan, envelope, flowing-interior and blocked-opening
  differences have different meanings.
- The Greg louvre and Spirit doorway template are localization witnesses, not evidence of
  real opening areas or door states. "Closed cabins" is an interpretation, not a verified
  operating requirement.
- The duct-terminal flows are internal redistribution (terminal sums ≈ 0), not omitted
  outdoor supply; they must not be reinterpreted as independent room-to-ambient sinks, and
  terminal throughput must not be double-counted as additional AHS supply/return.
- None of this extends to a native-engine defect, a stock-CONTAM concentration failure, a
  measured receptor-error magnitude, or a fleet-wide result.
