# NORO-PROVISIONED-VENUE-01 — design of record

Edison **PHASE2_PILOT_SPEC** (approved scope): does relocating
provisioned food-source lots from crew-mess venues to the largest
passenger dining venue reverse the crew-heavy threshold-crossing
pattern? 4 hulls × 2 placement conditions × 4 seeds = 32 runs on the
q30 (`q_source = 0.003`) provisioned-source spec, extracted via
`first_paper_scalar/1.4.0`, delivered to Edison with receipts.

## §1 Arms

`crew_venue` (all provisioned-lot objects placed in documented
crew-mess aliases) and `passenger_venue` (all placed in the largest
passenger dining venue). Placement-only intervention (spec §2.7):
source count, seeded epoch timing, dose and kind stay fixed — same
per-station contamination draws, each minted station's zone re-mapped
onto the pin set; the census is never restricted so n_lots cannot
shrink.

## §2 Per-hull venue sets (served-venue × item-line census verified 2026-11-02)

| hull key | platform | crew_venue pin | passenger_venue pin | served Dining zones (seats) |
|---|---|---|---|---|
| exp | expedition_cruise_450 | `CrewMess` | `MainDining` | MainDining(300) CasualDining(150) CrewMess(60) — 21 stations |
| cls | classic_cruise_1900 | `CrewMess` | `MainDining_L` | MainDining_L/U(400) LidoBuffet(350) Specialty(80) CrewMess(200) — 35 |
| spr | spirit_cruise_3000 | `CrewMessMain`+`CrewMessOff` | `MainDining_L` | MainDining_L/U(500) LidoBuffet(400) PizzaGrill(120) SpecialtyA-C(80) CrewMessMain(250) CrewMessOff(60) — 63 |
| meg | mega_cruise_5000 | `Crew_Mess_Main`+`CrewMess_Fwd` | `MainDining_L` | incl. MainDining_L(1400) MainDining_U(1100) Windjammer(1600) Crew_Mess_Main(700) CrewMess_Fwd(350) — 70 |

**Documented substitutions/observations (spec §1 rule):**

- The spec names `expedition_cruise_300`; `CrewMess`/`MainDining`
  exist verbatim only on **expedition_cruise_450** (the 300 platform
  carries `Crew_Mess`/`Main_Dining_Room`), and the delivered 38k
  baseline ran on 450 — resolved to 450 so seed pairing holds.
- On mega, `Windjammer` seats 1600 > `MainDining_L` 1400, but the
  spec explicitly pins `MainDining_L` — kept as written.
- Multi-zone crew pins (spr, meg) re-map minted stations
  round-robin in census order — deterministic, count-preserving.

## §3 Seeds

4 per hull, drawn from delivered q30 native crossers
(`posted=true` rows of `_scan_rows/fl_<hull>_12d_scr_q30.jsonl`),
nearest the posting-conditional medians — rule and per-seed rows:
`SEED_MANIFEST.json`. Pool sizes: exp 63, cls 60, spr 47, meg 19 —
all ≥ 4.

## §4 Mechanism seam

`provisioned_source.station_zone_pin` (list of zone names) re-maps
each minted station's zone after the Bernoulli census draws —
no extra RNG, no census restriction → n_lots and the non-placement
draw stream stay seed-paired with the unpinned q30 arm (the
labelled baseline, unchanged). `source_venue_arm` labels the arm.
Voyage witness gains `station_zone_pin`, `source_venue_arm`,
`n_lots_placed`, `actual_venues_used` (also echoed via
`parameters_json`).

## §5 Extraction

`first_paper_scalar/1.4.0` — 1.3.0 + 3 additive fields:
`source_venue_arm`, `actual_venues_used` (JSON list),
`n_lots_placed`, range-read from
`summary.mechanisms.provisioned_source.norwalk_gi`.
Return via the standard reducer path (campaign_reduction.yml →
collect/ingest/ack) per `reducer-dispatch-pins`.

## §6 Gates

- Local smoke: crew_venue + passenger_venue on one hull — (a)
  `actual_venues_used` ⊆ pin set, (b) `n_lots_placed` equals the
  unpinned q30 arm's lot count on the same seed, (c) no RNG-stream
  shift beyond the remap (`_cs_contaminated_stations` identical).
- Batch canary: 1 cell/hull × 1 seed × both arms (8 cells), read
  out before the 32-cell submit; witness `n_lots_placed` vs
  `n_contaminated` = 0 drops required (a pin to a venue that never
  serves inside the embarkation span drops lots — report
  immediately, do not submit).
- Report immediately if a pin label is absent, the crosser pool
  < 4 on a hull, or n_lots cannot hold.
