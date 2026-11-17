> **Status:** Living — external analysis record (received from the owner 2026-11-17). Independent QA of the Greg/Spirit localization at pinned revision `c93fa32fbe05440e797de8b551a2781b236d7e43`: static inspection and scalar accounting of saved outputs only, no new solves. Committed as the canonical in-repo copy.

# Focused independent QA of the Greg Mortimer and Spirit localization

## Assessment

I confirm the **narrow interface finding with high confidence**: the saved CONTAM pressure projects contain nonzero auxiliary duct-terminal flows that are not read or reconstructed by the pressure-field transport adapter at revision `c93fa32fbe05440e797de8b551a2781b236d7e43`. This is not the expected elimination of the separate simple air-handling system (AHS). I also find both pressure localizations well supported **within the authored operating scenarios**. Neither finding establishes real-vessel ventilation adequacy.

I inspected the pinned local source, project records, drivers, and reductions, and independently decoded the existing binary SIM airflow outputs. I performed only static inspection and scalar accounting: no export, pressure solve, transport propagation, model tests, network access, or canonical edits.

## 1. Strongest alternative: does the AHS bridge already reconstruct these ducts?

**No, not these flows.** `source/engines/contamx_transport.py:164–191` passes only `path_map_entries` to both direct field conversion and AHS synthesis. `source/engines/contamx_ahs_bridge.py:76–113` reads only mapped entries with an AHS number and the kinds `ahs_return`, `ahs_supply`, and `ahs_recirc`. The declared-outdoor-air fallback at lines 164–182 reconstructs simple-AHS recirculation; it never reads auxiliary duct junctions, duct segments, or their SIM records.

The exporter builds the auxiliary spines separately at `source/tools/contamw34_prj.py:1664–1727`: room-connected terminal junctions joined sequentially within selected ventilation groups. They are not connections to the simple-AHS return/supply phantom rooms. Lines 2185–2246 write them to the project without extending the path map. Therefore these are additional pressure-responsive room-to-room routes in the solved pressure network, not another encoding of the mapped AHS terminal record numbers. The simple AHS remains represented; the extra duct-spine transport does not.

**Important qualification:** this proves pressure/transport representation mismatch, not that the auxiliary spines are physically justified or should be added on top of intended ventilation. They may themselves be an unintended parallel network. Do not repair this by adding every terminal as an ambient sink, or by counting terminal throughput again as additional AHS supply/return. Choose whether the auxiliary network belongs in the coupled physics; if retained, reduce its directed junction mixing consistently. The source does not establish an intentional equivalent reduction already in place.

## 2. Independent reconstruction excludes indexing and parser artifacts

I decoded the saved SIM bytes independently of the project reader, using embedded record numbers and room numbers from each saved project—not spatial-layout list position. For terminal junction \(j\), the working SIM record is `npath + ndct + j`; segment \(d\) uses `npath + d`. I checked both room balances and independent duct-junction balances, including all nine preserved cases.

| Current commissioned case | Mapped paths | Extra segments / terminals | Maximum mapped-only room residual, kg/s | With terminals, kg/s | Reversed terminal sign, kg/s | Terminal index shifted by one, kg/s |
|---|---:|---:|---:|---:|---:|---:|
| Greg Mortimer | 368 | 23 / 31 | 0.0835116 | 4.28 × 10⁻⁷ | 0.167023 | 0.160276 |
| Spirit | 1,311 | 67 / 84 | 0.641617 | 2.05 × 10⁻⁶ | 1.283234 | 0.981102 |

All **491 terminal rows** in `unmapped_duct_terminals.csv` agree exactly with the independently decoded flows. Maximum duct-junction residuals are 3.73 × 10⁻⁹ and 2.98 × 10⁻⁸ kg/s for the two commissioned baselines. Their terminal sums are essentially zero, confirming internal redistribution rather than omitted net outdoor supply. Extra records have zero second-direction flow in these files. Across all nine cases the largest reconstructed room residual is 1.72 × 10⁻⁵ kg/s, reproducing the reported Spirit fan-removal case. These checks strongly reject an off-by-one offset, reversed sign, phantom-room indexing error, or missing second-direction contribution as the explanation.

The scalar-reader implementation is `scalar_check.py`; machine-readable results are `scalar_checks.json`. I corrected an initial four-byte offset error in my independent decoder before accepting these checks. The retained script additionally asserts complete consecutive embedded path and node identifiers.

## 3. Pressure localization remains separate and supported

**Greg Mortimer: high confidence in a missing effective service make-up route in this model.** Including the explicit duct segments, I recover exactly the stated 11-room pressure-responsive service component, with no ambient opening. The dining connection is a prescribed fan, not a pressure-responsive passage. No duct segment crosses this service cut. The independent baseline budget is 0.239279 kg/s sanitary withdrawal minus 0.022512 kg/s net galley-pair surplus, requiring 0.216767 kg/s inward through reference leaks. The cut closes to about 6 × 10⁻⁹ kg/s. Thus the strongest counterargument—an uncounted duct route supplying this cluster—does not hold. The saved maximum pressure differences reproduce 44,878 → 496 Pa when sanitary extraction is removed, 54,606 Pa when the galley pair is removed, and 12.25 Pa with the added make-up witness. This supports the route diagnosis, not the physical location/area of the witness. The extreme-pressure baseline is a diagnostic of the authored network, not a credible vessel operating prediction.

**Spirit: high confidence in prescribed transfer demand opposed by restricted return capacity; qualify “closed cabins.”** The eight declarations prescribe 12,000 m³/h outward from passenger-cabin ventilation groups. The independent cabin cut has 4.013658 kg/s outward prescribed transfer, balanced AHS terminals, 3.990766 kg/s net inward passive transfer, and 0.022892 kg/s inward reference leakage. No duct segment crosses that cut; its omitted terminals sum to −1.82 × 10⁻⁸ kg/s. Saved maxima reproduce 550.20 → 34.74 Pa on removing those fans, and 45.88 Pa when corridor openings use doorway capacity. The passive 539.45 Pa drop reported in `paths.csv` independently supports a restriction, rather than a harmless fan pressure allowance.

However, “closed-cabin demand” is an interpretation of the small relief-opening scenario, **not an independently verified door state or historical operating requirement**. Changing the corridor template affects all corridor adjacencies, not just cabin doors. Prefer: **“Prescribed cabin-to-public transfer drives large pressure differences against the authored small-opening return network.”** The design-terminal cases change ventilation allocation and are diagnostic alternatives, not validated fixes.

## Recommended qualified conclusion

“The current pressure-field adapter includes simple-AHS reconstruction but omits transport through a separate auxiliary duct-spine network present in these two pressure projects. Independent saved-output accounting verifies the missing records and their room connections. The pressure controls localize Greg Mortimer’s service make-up deficit and Spirit’s transfer-demand/return-capacity interaction, without establishing real-vessel opening sizes or operating states.”

Do not extend this to a native-engine implementation defect, stock-CONTAM concentration failure, a measured receptor-error magnitude, or a fleet-wide result. The native lane need not reproduce an unintentionally added auxiliary pressure network. Existing source/receptor discrepancies remain diagnostic pending the network-contract choice; I did not recompute them.

## Evidence and analytical decisions

All evidence paths above are relative to `/workspace/projects/c69f97eb-d07f-4d0d-9fb9-71e426d53523/research/localization_20261117/greg_spirit_executed`. Exact primary artifacts are `findings.md`, `code_anchors.json`, `localization_driver.py`, `reduce_results.py`, `paths.csv`, `rooms.csv`, `unmapped_duct_terminals.csv`, and `solves/<hull>/<case>/platform.prj`, `platform.sim`, `path_map.json`, `air_flow_paths.json`, and `overrides.json`. My additional control-difference and cut checks are in `accounting_and_controls.json` in this QA directory. Existing software citations remain in the findings' `references.bib`; I fetched no external sources.

- I used mass-flow rather than density-converted volume balances to avoid a temperature/density conversion explanation.
- I checked all nine already-saved cases because their small scalar tables provide a stronger indexing test without another model run.
- I separated internal duct redistribution from simple-AHS reconstruction and from outdoor make-up; zero aggregate terminal flow does not imply zero room-level transport.
- I treated the two intervention families as mechanism witnesses, not physical calibration or pressure acceptance thresholds.
