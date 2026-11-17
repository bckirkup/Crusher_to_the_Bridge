> **Status:** Living — external analysis record (received from the owner 2026-11-17), pinned revision `c93fa32fbe05440e797de8b551a2781b236d7e43`. Synthesis of the Greg/Spirit executed localization, the naval/Olympia controls, and the independent duct-accounting QA. Distribution A: approved for public release, unlimited. Findings pending owner engineering decisions. Committed as the canonical in-repo copy.

# Localizing the remaining native–CONTAM hull problems

Distribution A (26-140): Approved for public release; distribution is unlimited.

## Result and scope

I localized concrete, separable causes rather than finding a need for a general change to CONTAM. The remaining work is not confined to two cruise hulls: current targeted checks also reveal unresolved naval boundary conditions, an export-topology cause for Olympia's timeout, and a pressure-network/transport-interface mismatch.

Museum-plan models are interpreted as historically operational vessels. Their drawings establish geometry provenance, not present-day museum ventilation. Enterprise remains an explicitly fictional life-support scenario, judged for internal coherence; it is not empirical evidence about real ships.

Source revision: `c93fa32fbe05440e797de8b551a2781b236d7e43` [1]. The official NIST ContamX 3.4.0.3 executable was unchanged, SHA-256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`. Current-code source identities were checked for executed modules. All interventions were in isolated diagnostic copies. No canonical edits, AWS campaigns, epidemiological retuning, or CONTAM-internal changes were made.

This is a complete static census of 82 current airflow inputs plus targeted solves, not a new current-version fleet-wide pressure certification. The report combines the Greg/Spirit execution package [2], the preserved naval/Olympia controls [3], and independent duct-accounting QA [4].

## Hull-by-hull localization

| Hull | Current diagnostic | Discriminating control, not an approved repair | Localized issue |
|---|---|---|---|
| Greg Mortimer | 44,878 Pa maximum; only 6.67 Pa across flowing interior passive/ducted paths | Add service-cluster make-up route: maximum 12.25 Pa. Remove galley transfer/exhaust pair instead: maximum rises to 54,606 Pa | Service/crew cluster lacks a pressure-responsive boundary route; dining louvre cannot supply additional demand across a fixed-flow fan |
| Spirit 3000 | 550 Pa maximum; 539 Pa across a flowing interior opening | Remove cabin-relief fans: maximum 34.74 Pa. Keep fans but use existing doorway template for corridor-type edges: 45.88 Pa | Prescribed cabin-to-public transfer has an overly restrictive represented return network |
| Olympia C6 | Current export stalls | Remove only four room-to-itself paths: direct solve completes in 0.406 s | Overlapping group expansion emits invalid self-connections; a separate make-up problem remains after this topology control |
| Midway CV41 | Current commissioned envelope maximum 1.344 million Pa; flowing interior maximum 14.64 Pa | Explicit flight-deck opening scenario: envelope maximum 33.04 Pa, interior 27.88 Pa, extraction demand unchanged | A grouped weather deck has mechanical outdoor exchange but no represented pressure-responsive exterior opening |
| Pope AP110 | Current commissioned envelope maximum 1.355 million Pa; interior 58,552 Pa | Adding openings to all three explicitly open decks leaves envelope maximum 806,284 Pa and raises interior maximum to 804,136 Pa | Exterior access alone is insufficient; internal compartment connectivity/closure and demand distribution require adjudication |
| Aeolus ARC3 | Envelope maximum 953 Pa; interior 435 Pa | Zero sanitary extraction control: maximum 3.10 Pa | Sanitary make-up demand is forced through small-reference-flow group connections via Cable Tanks |

Huge pressure values are diagnostic signs of an inadequate represented operating condition, not credible vessel pressures or validated flow predictions. A fixed global pressure cutoff was not used: fan, envelope, flowing interior and blocked-opening differences have different meanings.

### Greg Mortimer: repair the route, not simply the louvre size

An 11-room service/crew passive-opening component contains MainGalley, Laundry, Engine Room, Crew Mess, four cabin groups and three sanitary rooms. No explicit ambient opening enters it. The dining louvre is in a different component, connected by a fixed-flow dining-to-galley fan. The three sanitary heads withdraw 0.239279 kg/s. The galley transfer/hood mass-flow difference provides only 0.022512 kg/s surplus, leaving about 0.216767 kg/s to enter through restrictive leaks. Nominally equal volumetric settings do not guarantee equal mass flows at different temperatures.

Reducing the three sanitary exhausts localizes their contribution but is not a proposed physical repair. Removing the galley pair makes the extreme pressure worse. A separate service make-up witness, using the existing demand/face-velocity convention, collapses the pressure problem without removing intended extraction. The actual historical/operational intake or transfer route and its dimensions still require justification. [2]

### Spirit: define cabin relief and its compensating return path

Eight cabin-relief declarations prescribe 12,000 m³/h from cabin groups toward public midship spaces. Cabin mechanical supply and return otherwise balance. The imposed transfer therefore needs a return route. The current global `corridor` mapping uses a 0.02 m² cabin-relief opening template. At the largest flowing drop, Small Lounge sends 1,293 m³/h toward a cabin group across 539 Pa, opposing the prescribed transfer.

Both removing the imposed transfer and increasing return capacity independently reduce the problem. The doorway control does not show that actual cabin doors are open: it establishes demand/capacity interaction. Distinguish closed-cabin undercuts, open circulation and actual transfer ducts edge by edge rather than globally changing all corridor areas. [2]

### Olympia: timeout and ventilation are two different issues

The overlapping `VENT_Machinery` and `VENT_Uptakes` groups generate four same-room paths for two boiler rooms and two sanitary rooms. The original current project and a control retaining one self-link stall; deleting only those four paths, with consistent renumbering, permits a sub-second direct solve. Numerical-setting controls did not resolve the stall. The minimum exporter correction is to omit self-pairs and add a regression check; redistribution of the total link rate is a separate decision.

After removing self-links, the commissioned model still has approximately 27.6 kPa envelope pressure due to 4,491 m³/h sanitary make-up demand. An explicitly open forecastle scenario leaves that demand unchanged but reduces envelope maximum to 23.52 Pa and flowing interior maximum to 16.39 Pa. This shows a candidate structural route, not a measured historical opening area. [3]

### Wider naval implication

The current inventory contains 154 open-deck records on 34 hulls and 17 make-up records on eight, but some grouped weather spaces were intentionally left without openings. Midway and Pope are current measured counterexamples to assuming that a mechanically ventilated weather group is already adequately connected to the exterior. Pope also shows why adding an opening to every weather-labelled space is not a sufficient repair: internal communication can remain the controlling bottleneck.

Aeolus's 1,066 m³/h extraction demand drives roughly 792 m³/h through a weather-to-Cable-Tanks connection and roughly 797 m³/h onward toward machinery, with drops around 343 and 435 Pa. These are group links based on 50 m³/h reference declarations, not documented large passage capacities. Its intended operational routes need identification. Natural-ventilation labels occur on 142 groups across 61 hulls; labels alone should not be read as independent evidence that a particular active supply system operates. [3]

## Additional transport-interface issue: auxiliary duct networks

The current pressure solve contains auxiliary duct segments, junctions and terminal flows not represented by the ordinary path map consumed by the field transport adapter. These are distinct from the simple AHS recirculation reconstruction.

For Spirit, 1,311 mapped paths coexist with 1,462 airflow records, including 67 duct segments and 84 terminals. Reconstructing the omitted room-terminal flows closes room air budgets:

| Hull | Maximum mapped-only room imbalance, kg/s | Including actual duct terminals, kg/s |
|---|---:|---:|
| Greg Mortimer | 0.083512 | 0.000000428 |
| Spirit | 0.641617 | 0.00000205 |

Independent QA decoded all 491 supplied terminal rows across the saved controls exactly; sign reversal and index shifts fail the accounting check. No auxiliary duct crosses the diagnostic component/cabin cuts, so this does not invalidate the pressure localization. [2,4]

This is a pressure/transport representation mismatch, not evidence of CONTAM failing to balance. The choice is to represent and reduce duct mixing/terminal transport consistently, or to remove unintended auxiliary duct physics from the pressure representation. Individual terminals must not be reinterpreted as independent outdoor sinks. The existence of a duct network in the generated project does not by itself establish that it is intended vessel physics.

Until that contract is reconciled, full source-to-receptor differences from the affected field adapter should not be described as complete CONTAM contaminant transport. Internal contaminant conservation can still hold in an incomplete represented network. This is why a global closure metric alone cannot establish interface completeness.

## Prioritized engineering decisions

1. **Olympia self-pair guard:** a localized exporter correction with a reproducible stall/success witness. Keep its separate make-up issue visible.
2. **Duct contract:** reconcile pressure and transport networks on Greg and Spirit before expanding quantitative receptor interpretation.
3. **Greg service boundary and Spirit relief loop:** identify intended physical routes/closure state and encode those, retaining declared extraction unless there is separate evidence it is wrong.
4. **Grouped-weather cases:** include Midway and Pope as distinct controls; the former is largely exterior access, the latter additionally internal topology. Aeolus tests the small group-link capacity class.
5. **After engineering changes:** repeat the small saved pressure/cut-budget controls, then current source-to-receptor integrals. Do not force lane agreement or rerun the historical campaigns just to absorb changed inputs.

The framework is useful enough to locate these issues precisely. The defensible conclusion is not that the remaining fleet is certified, nor that all residuals are one missing-leak parameter. We now have a small set of testable representation decisions and concrete repair locations.

## Evidence and reproduction

[1] Benjamin Kirkup, *Crusher to the Bridge*, source revision `c93fa32fbe05440e797de8b551a2781b236d7e43`. https://github.com/bckirkup/Crusher_to_the_Bridge/tree/c93fa32fbe05440e797de8b551a2781b236d7e43. Accessed 2026-11-17. Full source BibTeX entries accompany the evidence packages.

[2] Executed Greg Mortimer/Spirit package: `greg_spirit_executed/findings.md`, `summary.csv`, `paths.csv`, `rooms.csv`, `unmapped_duct_terminals.csv`, verified source snapshot, scripts and saved official solver outputs. Analysis task 7a52359a-2f0a-4710-ad1a-8e5297fb72fc.

[3] Naval/Olympia evidence: `residual_inventory/current_fleet_input_census.csv`, `current_local_solve_summary.csv`, `current_local_paths.csv`, `group_cut_budgets.csv`, `OLYMPIA_FINDING.md`, `executed_source_verification.json`, and preserved projects/SIM/XLOG files. Eleven successful naval control solves are recorded, in addition to the direct Olympia reduction and bounded stalled controls. Source inspection covers 82 airflow input files. Initial analysis task 87becd58-8374-439b-a4c7-269bb15c672c completed numerical work; report assembly was recovered from its persisted files after it stalled in an unrelated recursive bibliography lookup.

[4] Independent duct-accounting QA: `qa/qa.md`, task f786874c-f88c-4b30-9c96-dc5c49126016. Existing saved outputs only; no second set of airflow solves.
