> **Status:** Living — external analysis record (received from the owner 2026-11-17), pinned revision `c93fa32fbe05440e797de8b551a2781b236d7e43`. Executed localization of the greg_mortimer and spirit_cruise_3000 pressure problems with bounded one-at-a-time controls. All controls noncanonical; not an approved repair. Committed as the canonical in-repo copy.

# Greg Mortimer and Spirit: executed localization of current pressure problems

## Conclusion

I localized two different input/representation problems with bounded, one-at-a-time controls. Greg Mortimer lacks a pressure-responsive make-up route into its service/crew compartment cluster. Spirit's large flowing-room pressure differences are driven primarily by prescribed cabin-to-public transfer fans working against a small-opening return network. Neither finding requires changing the NIST CONTAM solver or tuning the two transport lanes to agree.

I also found a concrete transport-interface omission while closing room air budgets: nonzero duct-terminal flows in the exported project are absent from the path map consumed by the field transport adapter. This matters before interpreting current source-to-receptor differences as complete CONTAM transport.

These are directly executed findings for two hulls, not a fleet-wide pressure certification. All controls remain noncanonical. I made no repository, GitHub, AWS, or epidemiological changes.

## Identity and methods

I used repository revision `c93fa32fbe05440e797de8b551a2781b236d7e43` [1], a focused independent snapshot at `source/`, and the existing official ContamX 3.4.0.3 Linux executable. Its SHA-256 is `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`.

Every copied source/input file was checked against the pinned Git blob hash. All 19 imported project modules were subsequently checked again against the pin (`executed_imports.json`); none came from the old snapshots. The early snapshot handoff is `SNAPSHOT_READY.md`, and full input accounting is in `snapshot_manifest.json`.

I completed nine preserved pressure solves: five Greg Mortimer cases and four Spirit cases. Four additional baseline diagnostic solves reproduced the commissioned/design results before these controls. The nine preserved cases took 11.88 seconds of summed driver wall time, including export, solve, reading, and selected transport calculations; this is not CPU time, billed cost, or solver-only timing.

“Commissioned” means fresh export with per-room declared ventilation terminals; “design” means the exporter's alternative uniform group terminal allocation. The latter is a mechanism control, not an equally validated operating condition. Heating, opening geometry, wind, and schedules otherwise retain the pinned inputs, including the assumed 1 m/s headwind. An air-handling system (AHS) is the model's grouped mechanical supply/return network.

I treat historically operational service/closure modes—not current museum conditions—as the intended interpretation for museum-plan hulls. These two cases are cruise models. Enterprise fiction and the parallel norovirus work were outside this computation.

## Executed pressure results

| Hull and control | Largest path pressure difference, Pa | Largest flowing passive/ducted interior difference, Pa | Room gauge-pressure range, Pa |
|---|---:|---:|---:|
| Greg Mortimer, current commissioned | 44,878.2 | 6.67 | −44,814.4 to 0.11 |
| Greg Mortimer, design terminals | 934.4 | 6.62 | −6.52 to 930.7 |
| Greg Mortimer, zero three service sanitary exhaust heads | 496.5 | 6.67 | −6.67 to 494.1 |
| Greg Mortimer, remove galley transfer/exhaust pair | 54,605.6 | 1.80 | −54,605.7 to 0.11 |
| Greg Mortimer, add service make-up route | 12.25 | 6.67 | −12.37 to 0.11 |
| Spirit, current commissioned | 550.2 | 539.45 | −30.10 to 519.34 |
| Spirit, design terminals | 756.9 | 741.78 | −9.74 to 745.27 |
| Spirit, remove cabin-relief fans | 34.74 | 23.31 | −34.40 to 0.11 |
| Spirit, map corridors as doorways | 45.88 | 45.88 | −24.45 to 23.12 |

Exact values are in `summary.csv`; every mapped path and room appears in `paths.csv` and `rooms.csv`. Pressure differences include local stack/wind reference effects and need not equal differences between reference-height room gauge pressures. I did not use 374 Pa, or any other universal number, as an acceptance rule. The figure `localization_controls.png` shows maximum path differences on logarithmic axes; controls are diagnostic, not approved alternatives.

## 1. Greg Mortimer: a missing make-up route, not inadequate dining-louvre size

The passive-opening network has an 11-room service/crew component: MainGalley, Laundry, Engine_Room, CrewMess, four crew-cabin groups, and three sanitary compartments (`HD_0E_M`, `HD_2C_M`, `HD_2C_F`). No declared ambient opening enters this component. The dining louvre is in the other component. The DiningRoom-to-MainGalley connection is a fixed-flow fan, not a pressure-responsive passage that can admit additional service sanitary make-up air. Internal duct spines do not supply a boundary connection into this service cluster.

The three sanitary heads withdraw 0.239279 kg/s. The galley transfer brings in 1.672357 kg/s and the hood removes 1.649845 kg/s, leaving only a 0.022512 kg/s surplus; nominally equal volumetric fan settings do not imply identical mass flow at their different source temperatures. Consequently the service cluster needs 0.216767 kg/s through its eleven tiny envelope-reference leaks. It reaches this only with a large negative pressure. The cluster mass budget closes to 5.6×10⁻⁹ kg/s without an omitted cross-cluster duct contribution (`cluster_cut_budgets.csv`).

The interventions discriminate this mechanism:

* Setting only the three service sanitary groups' air-change rates to zero removes the dominant deficit and reduces the peak from 44.9 kPa to 496 Pa. The residual positive service pressure is consistent with the remaining fan-pair mass surplus; this is not a recommended service mode.
* Removing the galley transfer and hood together does **not** fix the problem: the peak rises to 54.6 kPa because the small transfer surplus has also disappeared. This rules out the galley pair as the dominant cause of the extreme underpressure.
* Adding one hypothetical make-up louvre at MainGalley, without reducing any exhaust, reduces the maximum path difference to 12.25 Pa. Its 0.0792889 m² area comes from the already declared 713.6 m³/h service sanitary make-up demand divided by the existing 2.5 m/s face-velocity assumption—not from a target pressure. The new opening carries 0.213493 kg/s into the component, leaving 0.003274 kg/s to the reference leaks.

**Fix location:** `data/platforms/greg_mortimer/air_flow_paths.json`, specifically the service component's boundary/transfer authoring. Supply it through a defensible service intake, mechanical make-up branch, or genuine pressure-responsive connection to a supplied compartment. Do not simply enlarge the DiningRoom louvre: it is on the wrong side of the fixed-flow connection. The demonstrated louvre is a localization witness, not evidence that a real vessel has an opening at this location or of this area. Preserve the sanitary exhaust function.

The design-terminal case is not a solution: it eliminates the sanitary groups' net exhaust by giving them balanced supply and return, thereby changing the intended operating semantics.

## 2. Spirit: a prescribed relief loop working against a small-opening network

The eight passenger-deck links `Cabin_Relief_D4` through `Cabin_Relief_D11` prescribe a total 12,000 m³/h from cabin groups to the public-midship group. They expand to 288 room-pair fan paths. Passenger cabin AHS supply and return are balanced, so this imposed outward flow needs a compensating return path.

The cabin-room cut shows 4.013658 kg/s leaving through these prescribed links, offset by 3.990766 kg/s through passive openings and 0.022892 kg/s through reference leaks. Net mapped cut residual is 5.8×10⁻⁹ kg/s; internal duct terminals have essentially zero net contribution across this particular cut. This is a transfer-loop demand, not a whole-hull lack of outdoor make-up air.

The model maps every adjacency called `corridor` to the 0.02 m² `cabin_relief` template. The largest current flowing drop is 539.45 Pa from SmallLounge toward the `PC_D6_P_F` cabin group, carrying 1,293.36 m³/h against the authored cabin-to-public fan transfer. ArtGallery reaches +519.34 Pa while the lowest room is −30.10 Pa. The 550.2 Pa maximum is on a prescribed fan path; the 539.45 Pa passive-opening drop independently shows that this is not merely a large fan pressure allowance or a shut check valve.

Two distinct controls isolate the demand/capacity interaction:

* Removing only the eight cabin-relief fan declarations reduces the largest difference to 34.74 Pa, retaining the sanitary exhaust and galley sink.
* Retaining those fans but changing only the `corridor` override from the existing 0.02 m² relief template to the existing 1.8 m² doorway template reduces the maximum to 45.88 Pa. This changes all corridor-type adjacencies, so it is a capacity/closure witness, not a proposal to leave every cabin door open.

**Fix locations:** `data/platforms/spirit_cruise_3000/air_flow_paths.json` for relief-flow demand and topology; `data/platforms/spirit_cruise_3000/contam/hobbyist_overrides.json` for the global `corridor → cabin_relief` mapping. Decide which edges represent closed-cabin undercuts, open corridors, or mechanical transfer/return ducts. If closed cabins are intended, keep their residual leakage interpretation and author the actual return/make-up route for the imposed loop. If an adjacency represents an open circulation space, do not silently convert it to a cabin undercut. Changing a global type mapping is not a historically or physically justified repair by itself.

## 3. A bounded additional interface finding: duct terminal airflow is not carried into field transport

Fresh hobbyist exports also create duct junctions, segments, and terminal openings. These are real active airflow routes in the official solve, but the generated `path_map.json` covers ordinary airflow paths only. The field adapter iterates that map; it does not reconstruct the appended duct segments/terminals [1; code anchors in `code_anchors.json`].

For Spirit's current commissioned project there are 1,311 mapped paths but 1,462 airflow records: 67 additional duct-segment records and 84 terminal records. Greg Mortimer also has nonzero omitted terminal flows. I decoded the terminal-to-room links from the preserved project junction declarations and matched the SIM terminal ordering against room mass closure, rather than trusting its unusable zero-filled cross-reference tables.

| Current commissioned hull | Maximum mapped-only room imbalance, kg/s | Maximum imbalance after including actual duct terminals, kg/s |
|---|---:|---:|
| Greg Mortimer | 0.083512 | 4.28×10⁻⁷ |
| Spirit | 0.641617 | 2.05×10⁻⁶ |

The reconstructed terminal tables are in `unmapped_duct_terminals.csv`. Thus the apparent mapped-room imbalance is not a ContamX air-balance failure. It is a mismatch between the full pressure network and the reduced transport interface. The largest full residual over all nine controls is 1.72×10⁻⁵ kg/s, in the fan-removal Spirit control. This does not negate the pressure localization: the named component/cabin cut budgets and controlled pressure responses remain explicit.

**Fix location:** the duct export/path-map contract in `tools/contamw34_prj.py` and field conversion in `engines/contamx_transport.py`. Either represent and reduce duct transport consistently—including junction mixing, terminals, and any actual leakage—or explicitly omit these auxiliary duct networks from the pressure solve when they are not part of the intended coupled transport model. Do not treat individual terminals as independent room-to-ambient sinks. I did not implement either option. Which is scientifically appropriate depends on whether these hobbyist duct spines are intended physics or authoring decoration.

## Transport consequence: useful diagnostic, not agreement tuning

I also evaluated a small 12-hour unit-pulse calculation from selected sources with natural decay 0.10 h⁻¹ and filter efficiency 0.3, retaining the current adapter. Native and pressure-field cases share Crusher's exponential mass propagator; these are **not** independent stock-CONTAM concentration solutions. Exact integrals and closure appear in `source_material_times.csv`.

The Greg service make-up witness leaves native transport unchanged because the new opening has zero declared native exchange. Yet the field MainGalley whole-hull normalized material-time integral rises from 0.059322 to 0.075235 h; native remains 0.057680 h. Correcting the pressure route therefore does not automatically improve native/field agreement, and agreement was not the selection criterion.

For the current Spirit SmallLounge pulse, the adapter reports whole-hull integrals of 0.476319 h native versus 0.499080 h field, but remote-group integrals of 0.014329 versus 0.292739 h. “Remote” here means outside the source's authored AHS group. These are material-time, not human dose or clinical risk. Given the now-demonstrated duct-interface omission, I do not interpret this remote discrepancy as a final physical receptor prediction. It identifies why a whole-hull agreement metric alone is insufficient after the network representation is made coherent.

## Recommended bounded engineering next step

1. Resolve Greg Mortimer's service make-up **route** while retaining intended sanitary extraction. The noncanonical witness shows that a modest explicit route, not reducing exhaust, addresses the extreme pressure.
2. Resolve Spirit's cabin-relief loop **meaning and return path**, distinguishing closed-cabin relief from open circulation. Avoid a global opening-area adjustment made only to lower a maximum.
3. Make the hobbyist duct-network/transport contract explicit and consistent on these same two hulls. Check full room mass budgets and a small number of source/receptor calculations after that choice. There is no need for an immediate broad fleet rerun to decide these local mechanisms.

## Limits and discretionary analytical decisions

* I used matched fresh current exports, not old commissioned bundles or the older large checkout. I kept the design-terminal lane only to discriminate terminal authoring effects.
* I changed one declared mechanism at a time. The Greg added area reused the existing demand/face-velocity convention; the Spirit capacity witness reused a catalog template. Neither is calibrated to ship observations or a pressure cutoff.
* I evaluated pressure by role—envelope, fan, flowing interior, and closed opening—rather than applying a universal pressure ceiling.
* I used mass-flow cut budgets for causal localization. Reported m³/h values follow the existing reader's mean-positive-density conversion, not exact per-path donor-volume conversion; source-temperature effects can make nominally equal volumetric fans differ in mass flow.
* I report direct implementation/solve evidence as strong for these localized mechanisms, but the actual opening areas, wind, service states, and real-vessel adequacy remain assumed or unvalidated. No physical vessel validation or current-fleet equivalence follows.
* I retained the historical campaigns and old snapshots unchanged. No manuscript was assembled.

## Evidence and reproduction

[1] bckirkup, *Crusher to the Bridge*, pinned software and hull inputs, revision `c93fa32fbe05440e797de8b551a2781b236d7e43`: https://github.com/bckirkup/Crusher_to_the_Bridge/tree/c93fa32fbe05440e797de8b551a2781b236d7e43. Full BibTeX for all fetched web sources is in `references.bib`. `sources.json` lists fetched-source records.

Run from any location after supplying the existing official executable:

```bash
python localization_driver.py /absolute/path/to/source /absolute/path/to/output /absolute/path/to/contamx3
python reduce_results.py /absolute/path/to/source /absolute/path/to/output
```

The snapshot includes all project modules imported by those commands. Standard Python dependencies are listed in `requirements.txt`. The official binary is not redistributed. `solves/` retains each fresh project, path map, control inputs, official SIM/XLOG/RST outputs, and exact scalar analysis. Baseline and control commands, binary/input hashes, imported file verification, and source manifest are included. The fixed node-record labels follow the parser's documented `nr, temperature, pressure, density` layout.
