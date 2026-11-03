# NORO-PROVISIONED-VENUE-02 — design of record

Edison Phase-2 calibration: scale the `station_zone_pin` mechanism
piloted in NORO-PROVISIONED-VENUE-01 (merged #1147, extraction
`first_paper_scalar/1.4.0`) into stable conditional distributions for
the paper — **4 hulls × 3 venue conditions × the full 1,000-seed q30
set per hull = 12,000 runs**, `q_source = 0.003`, norovirus only,
delivered to Edison with receipts.

## §0 The reuse question — settled by measurement

Edison asked whether the delivered 4,000 q30 runs (1k/hull,
`campaign/noro_provisioned_source_01/fl_*_12d_scr_q30/`) could serve
as the `mixed_venue` arm. **Measured 2026-11-03 across all 4,000
runs** (`_scan_rows/fl_*_12d_scr_q30.jsonl` → `census.lot_objects`
zones; 575 lots over 529 lot-carrying voyages): the default census
contributes exactly 7 item-line stations per served venue, each
station minting i.i.d. Bernoulli(q) — so realized shares are
~uniform over served venues, not capacity-proportional:

| hull | venue (seats) | measured % | capacity % | Δ pp |
|---|---|---|---|---|
| exp | MainDining(300) | 33.8 | 58.8 | −25.0 |
| exp | CasualDining(150) | 32.3 | 29.4 | +2.9 |
| exp | CrewMess(60) | 33.8 | 11.8 | +22.0 |
| cls | MainDining_L(400) | 18.3 | 28.0 | −9.7 |
| cls | MainDining_U(400) | 17.4 | 28.0 | −10.6 |
| cls | LidoBuffet(350) | 17.4 | 24.5 | −7.1 |
| cls | Specialty(80) | 22.6 | 5.6 | +17.0 |
| cls | CrewMess(200) | 24.3 | 14.0 | +10.3 |
| spr | MainDining_L(500) | 11.2 | 24.2 | −13.0 |
| spr | MainDining_U(500) | 10.6 | 24.2 | −13.6 |
| spr | LidoBuffet(400) | 10.6 | 19.3 | −8.7 |
| spr | PizzaGrill(120) | 13.8 | 5.8 | +8.0 |
| spr | SpecialtyA/B/C(80) | 14.9/9.0/10.6 | 3.9 each | +11.0/+5.1/+6.7 |
| spr | CrewMessMain(250) | 10.1 | 12.1 | −2.0 |
| spr | CrewMessOff(60) | 9.0 | 2.9 | +6.1 |
| meg | Windjammer(1600) | 12.6 | 23.4 | −10.8 |
| meg | MainDining_L(1400) | 9.7 | 20.4 | −10.7 |
| meg | MainDining_U(1100) | 9.7 | 16.1 | −6.4 |
| meg | Crew_Mess_Main(700) | 9.2 | 10.2 | −1.0 |
| meg | SpecRest_A(450) | 13.5 | 6.6 | +6.9 |
| meg | SpecRest_B(400) | 8.2 | 5.8 | +2.4 |
| meg | CrewMess_Fwd(350) | 8.2 | 5.1 | +3.1 |
| meg | Pool_Bar_Grill(300) | 10.1 | 4.4 | +5.7 |
| meg | ComedyClub(300) | 9.2 | 4.4 | +4.8 |
| meg | CafeBakery(250) | 9.7 | 3.6 | +6.1 |

Declared tolerance tested: any venue's measured share within ±5 pp
of its capacity share on every hull. **Verdict: FAILED on all four
hulls** — the q30 cohort is the *distributed* arm and cannot proxy
`mixed_venue`. All three conditions run fresh: 12k cells.

## §1 Arms

- `crew_venue` — all provisioned lots re-map onto documented
  crew-mess aliases (verbatim from VENUE-01).
- `passenger_venue` — all re-map onto the spec-pinned largest
  passenger dining venue (verbatim from VENUE-01).
- `mixed_venue` — proportional allocation across **every served
  dining venue weighted by seat capacity** (`max_occupancy`), the
  realistic upstream-distribution default. The pin covers the whole
  served-venue census; `station_zone_pin_weights` carries the seat
  counts and placement is a per-station weighted draw.

## §2 Per-hull venue sets (verified 2026-11-02; unchanged from VENUE-01)

| hull | platform | crew pin | pax pin | mixed pin = served Dining venues (seats) |
|---|---|---|---|---|
| exp | expedition_cruise_450 | `CrewMess` | `MainDining` | MainDining(300) CasualDining(150) CrewMess(60) |
| cls | classic_cruise_1900 | `CrewMess` | `MainDining_L` | MainDining_L/U(400) LidoBuffet(350) Specialty(80) CrewMess(200) |
| spr | spirit_cruise_3000 | `CrewMessMain`+`CrewMessOff` | `MainDining_L` | MainDining_L/U(500) LidoBuffet(400) PizzaGrill(120) SpecialtyA–C(80) CrewMessMain(250) CrewMessOff(60) |
| meg | mega_cruise_5000 | `Crew_Mess_Main`+`CrewMess_Fwd` | `MainDining_L` | MainDining_L(1400) MainDining_U(1100) Windjammer(1600) SpecRest_A(450) SpecRest_B(400) Pool_Bar_Grill(300) ComedyClub(300) CafeBakery(250) Crew_Mess_Main(700) CrewMess_Fwd(350) |

## §3 Seeds — seed-paired across arms and to baseline

The full delivered q30 seed set per hull, verbatim:
**exp 8000–8999; cls/spr/meg 8105–9104** — 1,000 seeds each, so every
arm pairs seed-for-seed with the delivered q30 baseline and with the
other two arms. Canary seeds are each hull's highest-lot q30 seed
(exp 8169, cls 8169, spr 8152, meg 8152 — 2 lots each).

## §4 Mechanism seam

`provisioned_source.station_zone_pin` (list of zone names) re-maps
each minted station's zone after the Bernoulli census draws, and the
new **`provisioned_source.station_zone_pin_weights`** (parallel list
of finite positive numbers) switches placement from deterministic
round-robin to a per-station weighted pick on a dedicated placement
stream — a `SeedSequence` parallel to the census stream on the same
voyage entropy (spawn_key `(0xF00D, 0xFE11E)`). No ` _cs_rng` draws
are consumed and `_cs_seed_seq`'s spawn counter is never shifted, so
n_lots and the shared draw stream stay seed-paired with the unpinned
baseline arm. Malformed weights are inert at runtime (round-robin
fallback); the sanity checker is the gate that errors. Witness gains
`station_zone_pin_weights` alongside `station_zone_pin`,
`source_venue_arm`, `n_lots_placed`, `actual_venues_used`.

## §5 Extraction

`first_paper_scalar/1.4.0` — carries `source_venue_arm`,
`actual_venues_used`, `n_lots_placed` range-read from
`summary.mechanisms.provisioned_source`. Return via the standard
reducer path (campaign_reduction.yml → collect/ingest/ack) per
`reducer-dispatch-pins`; cohort-sized bounds per the red-fps01-qgrid
delivery (sources-manifest byte cap, COMMIT/MANIFEST readback cap,
ingest timeout).

## §6 Gates

- Local smoke: all three arms on one hull — (a) `actual_venues_used`
  ⊆ pin set, (b) `n_lots_placed` equals the unpinned q30 lot count on
  the same seed, (c) `_cs_contaminated_stations` identical pinned vs
  unpinned, (d) mixed-arm venue shares across seeds approach the
  declared weights.
- Batch canary: 1 max-lot seed × 3 arms × 4 hulls (12 cells), read
  out before the array; `n_lots_placed` vs `n_contaminated` drops
  required (a pin to a venue that never serves inside the embarkation
  span drops lots — report immediately, do not submit).
- Report immediately if a pin label is absent from a hull's
  served-venue census or n_lots cannot hold seed-paired.

## §7 Admissibility criteria frozen pre-run (Rule A)

- Deliverable: 12,000 completed runs + `first_paper_vectors` on
  1.4.0 delivered to Edison + receipts + committed run report.
- Report-only quantities (never selected on): per-arm venue-share
  distributions, trigger/posting rates, per-role attack rates —
  Edison/Kosmos owns all paper-facing acceptance analysis vs the
  empirical postings.
- No acceptance analysis vs the empirical 194/182 postings in this
  campaign; raw per-arm distributions only.
