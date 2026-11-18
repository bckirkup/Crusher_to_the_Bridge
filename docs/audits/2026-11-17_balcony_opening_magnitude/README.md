> **Status:** Evidence note for the ambient-exposure stage-6 balcony-opening gate. This note authors no openings, platform data, constants, schedules, or behaviour change.

# Balcony opening magnitude evidence (ambient-exposure stage 6)

## Scope and pins

- Repository: `bckirkup/Crusher_to_the_Bridge`; branch base `origin/main` `4a3d7a55cb654309a72b2089dbe06cb97d85973c`.
- Governing plan: `docs/proposals/ambient_exposure_audit_and_fix_plan.md` stage 6 (`CONTAM-AMBIENT-BALCONY-01`) and decision D3: the balcony airflow mechanism is gated on a sourced magnitude before it can replace the transmission-side balcony factor.
- Balcony-hull roster named by that plan: `mega_cruise_5000`, `diamond_princess`, `spirit_cruise_3000`, `classic_cruise_1900`, `expedition_cruise_450`, `greg_mortimer`.
- Retrieval rule followed: `consensus-literature-retrieval` plus `searching-literature-evidence`; every Consensus `search` call below passed `include_full_text_chunks: true` and named the quantity and unit in the query.

## Retrieval log

Consensus searches run on 2026-11-17, all with `include_full_text_chunks: true` and `page_size` 20 unless noted:

1. `cruise ship balcony door air exchange rate ACH ventilation m3/h`
2. `ship cabin balcony door ventilation rate air changes per hour`
3. `cruise ship balcony door open closed at sea passenger behavior`
4. `cruise ship cabin balcony door leakage airflow m3/h`
5. `"balcony door" "cruise ship" ventilation air change rate`
6. `cruise cabin balcony natural ventilation air change rate CFD`
7. `ship cabin balcony door leakage rate air changes per hour`
8. `Quantifying natural ventilation cruise ship cabin opening configurations frontal opening area ACH wind direction` (`page_size` 5)
9. `passenger ship balcony opening air change rate ACH door open`

Separate web/industry searches were used only for the operating-state question because cruise-line operating practice is not literature-indexed material.

## Candidate magnitudes found

None of the retrieved numbers is a measurement or defensible model input for **cruise-ship balcony opening airflow at sea**. The closest items are recorded below so the negative result is auditable.

| Source | Quantity reported | Value and unit | Setting / relevance | Grade for balcony-opening use | Access class | Read location |
|---|---|---:|---|---|---|---|
| Luo, Li et al. 2026, *Physics of Fluids*, DOI `10.1063/5.0350831` | Air change rate in a cruise-ship cabin under natural-ventilation configurations | 23.39–104.38 h⁻¹ against wind; 61.78–333.65 h⁻¹ side wind | Cruise-ship cabin CFD with varying wind directions and natural-ventilation configurations; the abstract does not identify the openings as balcony doors, give opening area, give a door-open duty cycle, or measure a real vessel | **C — not admissible for D3-B**: simulation, not measurement; opening configuration and operating state are not commensurable with a balcony-door opening at sea | Peer-reviewed journal; abstract/publisher page | Abstract only |
| Cheung et al. 2025, *Science of the Total Environment*, DOI `10.1016/j.scitotenv.2024.178286` | Cabin ventilation rate and air change rate on a sailing cruise ship | Cabins VR >20 L s⁻¹ person⁻¹; dining ACH examples 2.3 h⁻¹ pub and 0.8 h⁻¹ restaurant | Measured IAQ/CO₂ decay in three cabins and public venues; ACH is defined as total outdoor air entering the space and is not separated into balcony-door leakage versus HVAC | **C — not admissible for D3-B**: measured cruise-ship cabin ventilation, but not balcony-opening airflow | Peer-reviewed journal; Consensus full text | Abstract; Methods §2.5 for ACH definition |
| Almilaji & Thomas 2020, *Aerosol and Air Quality Research*, DOI `10.4209/aaqr.200495` | Balcony-door access/ventilation context on Diamond Princess | No airflow magnitude; ~30% cabins described as interior cabins without balcony access; outer cabins had balcony doors, and winter conditions left balcony passengers dependent on HVAC | Deck-plan/HVAC outbreak analysis; useful only as context that balcony doors are not a universal fresh-air path | **C — context only** | Peer-reviewed journal; Consensus full text | Results excerpt |
| Hayati, Mattsson & Sandberg 2018, *International Journal of Ventilation*, DOI `10.1080/14733315.2018.1435027` | Wind-tunnel air-change ratios through open doors | Cross-flow airing 4–20× single-opening; windward door about 53% higher than leeward; draught lobby −27%; higher turbulence +38% | Generic building door experiment, not a ship cabin or balcony door at sea | **C — not commensurable** | Peer-reviewed journal | Abstract only |

The governing plan already reached the same literature boundary on 2026-11-16: generic open-door physics exists, but "Ship balcony-door exchange, measured" was not found; only a CFD study was found. This pass re-checked that boundary with balcony-specific queries and found no newer direct measurement.

## Operating-state evidence: closed versus open at sea

The task premise that cruise-ship balcony doors are "typically closed" is **not forcefully established** by the retrieved evidence, and it is also **not refuted as a universal rule**:

- Carnival's brand ambassador is quoted in industry press saying passengers may sleep with the balcony door open; the only cabin-level effect is that the cabin's own air conditioning shuts off, not neighbouring cabins (CruiseHive, 2025-06-05, `https://www.cruisehive.com/carnival-clears-the-air-on-sleeping-with-balcony-doors-open/176604`). Access class: industry press; read location: article full text.
- Other industry/travel coverage reports line- and ship-specific behaviour: some ships interlock cabin AC when a balcony door is open or unlocked, and some forward-facing balcony cabins are sold as port-only or have doors secured in strong weather (Islands, 2024-10-03, `https://www.islands.com/1677555/balcony-door-lock-cruise-cabin-significantly-cooler-air-conditioning/`; Cruise Critic community threads are anecdotal and were not used as authority). Access class: industry/web; read location: article/forum full text.
- No government, classification-society, cruise-line engineering, or peer-reviewed operational dataset was found that gives a fleet-wide balcony-door open fraction, open hours per day, or airflow at sea.

Consequence: the operating state is mixed and unmeasured. It cannot supply the missing magnitude by assumption, and the literature does not justify authoring a nonzero opening as the default.

## Finding

**No defensible source found** for a cruise-ship balcony opening airflow magnitude at sea. The only cruise-cabin natural-ventilation magnitude retrieved is a CFD air-change-rate range that is not identified as balcony-door flow, is not measured on a vessel, and lacks opening area and door-open duty cycle. No m³/h value for a balcony opening was retrieved; ACH values cannot be converted without a commensurable cabin volume and opening configuration.

## Recommendation

**Rule out stage 6 as documentation.** Do not proceed with magnitude X: no X meets the D3-B sourced-magnitude gate. `CONTAM-AMBIENT-BALCONY-01` should not author `ambient_openings` records for balcony zones on `mega_cruise_5000`, `diamond_princess`, `spirit_cruise_3000`, `classic_cruise_1900`, `expedition_cruise_450`, or `greg_mortimer`. Keep the existing transmission-side balcony representation (`BALCONY_AEROSOL_REDUCTION` and the declared absence-hours axis) as the only balcony mechanism unless the owner later supplies direct evidence.

What would reopen the stage: a direct tracer-gas, pressure, or airflow measurement on a balcony-hull cabin with the balcony door explicitly open and closed at sea, or cruise-line engineering data for balcony-door open fraction and effective opening area. Until then, any nonzero balcony `exchange_m3h` would be an unfounded constant, not a sourced magnitude.

## Validation

- Docs-only change: one new `docs/audits/2026-11-17_balcony_opening_magnitude/README.md`.
- No `data/`, engine, exporter, schema, test, ledger, or campaign file is changed.
- No ledger entry is created, so `tests/test_ledger_entries.py` is not implicated.
- Pre-commit is run on the changed file before PR.
