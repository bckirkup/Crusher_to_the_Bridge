# Tranche 28 — measured airborne norovirus, and what it can and cannot check (#39/#40/#24, item C7)

Status: **evidence record, 2026-09-05.** Track C item C7 of
[`../proposals/defect_resolution_plan.md`](../proposals/defect_resolution_plan.md) §5.
No constant moves. The register row this tranche annotates is
[`../parameter_provenance_register.md`](../parameter_provenance_register.md) §3,
`airborne_emission_mode = emesis_conditioned` / `emesis_aerosol_fraction_range`.

The emesis aerosol path was rebuilt (R4): the norovirus arm no longer carries a
continuous airborne fraction at all, it emits to zone air **per emesis event**,
drawing log-uniformly across the whole declared interval
**[7.2e-7, 2.67e-4]** of the expelled bolus. The old Alsved check was written
against the continuous fraction, so its conclusion does not transfer — the
quantity it checked no longer exists. This tranche re-does the check against the
mechanism that does exist, and records what the measurement is able to decide.

**It is a check, not a source.** Nothing here licenses a point inside
`EMESIS_AEROSOL_FRACTION_RANGE`; Tung-Thompson 2015 remains the only measurement
of that fraction, and the airborne concentrations below are an *outcome* of the
mechanism, not an input to it.

## 1. What is measured, in whose air

| Source | Setting | Concentration | n | Origin | Grade |
|---|---|---|---|---|---|
| Alsved 2019, *Clin Infect Dis*, DOI 10.1093/cid/ciz584 | Air sampled repeatedly beside **26 hospital patients** with norovirus infection | **5–215 copies/m³** | 21 of **86** samples positive, from **10** patients | **Ab** (Results section of the abstract, verbatim: "The concentrations of airborne norovirus ranged from 5-215 copies/m3") | **B** |
| Bonifait 2015, *Clin Infect Dis*, DOI 10.1093/cid/civ321 | **48** samples in **8** healthcare facilities during GII outbreaks; 1 m from patient, room doorway, nurses' station | **1.35 × 10¹ – 2.35 × 10³ genomes/m³** | positive in 47% of samples, 6 of 8 centres | **Ab** | **B** |
| Rupprom 2024, *Sci Rep*, DOI 10.1038/s41598-024-73369-w | Tertiary-care hospital, Bangkok; BioSampler, hospital-wide | GII **3.4 × 10¹ – 5.0 × 10³**, GI **6.0 × 10²** copies/m³ | 13 of 60 samples | **Ab** | **B** |

So the measured envelope across three independent studies is roughly
**[5, 5 × 10³] copies/m³**, about three decades wide, and Alsved's own range is
the *low* end of it.

Alsved's second result is the one that matters mechanistically and is the one
the rebuilt path already encodes: positivity is associated with **vomiting
within the previous 3 hours** (odds ratio **8.1**, P = .04), and RNA appears in
particles **<0.95 µm** as well as **>4.51 µm**. That is the evidence for
`airborne_emission_mode = emesis_conditioned` — an event-conditioned emission —
and against a continuous share of shedding.

## 2. The check, as implemented

`scripts/alsved_airborne_check.py` reads the shipped profile and engine
constants and computes no fitted quantity:

```bash
python3 scripts/alsved_airborne_check.py \
  --out reports/c7_alsved_airborne_check.json
```

Per-episode aerosolised mass, from the shipped intervals
(`EMESIS_TOTAL_SHED_GEC_RANGE` 1e5–1e8 GEC per illness, partitioned over
`EMESIS_EPISODES_RANGE` 1–7 episodes, times the aerosol fraction):

| | GEC to air per episode |
|---|---|
| interval floor | **1.03 × 10⁻²** |
| interval ceiling | **2.67 × 10⁴** |

That span is **6.4 decades**, because it compounds three measured intervals.
Averaged over Alsved's 3-hour window at the shipped
`airborne_half_life_hours = 1.1`, the mean-to-peak factor is **0.449**, and the
receiving volume is a shipped `mega_cruise_5000` `Cabin_Corridor` zone
(**900–1200 m³**, from `data/platforms/mega_cruise_5000/spatial_layout.json`),
with the balcony ventilation factor **0.5**:

| Zone | 3-h mean, interval floor | 3-h mean, interval ceiling |
|---|---|---|
| 1200 m³ | 1.9 × 10⁻⁶ copies/m³ | **5.00 copies/m³** |
| 900 m³ | 2.6 × 10⁻⁶ copies/m³ | **6.66 copies/m³** |

## 3. What that decides, and what it does not

1. **The ceiling of the mechanism lands at the floor of the measurement.** At
   the top of the declared interval the model's 3-hour mean in a corridor is
   **5.0–6.7 copies/m³**, against Alsved's floor of 5 and Bonifait's floor of
   13.5. The mechanism can reach the measured band; it does not exceed it
   anywhere in the interval. There is no evidence of over-emission to correct.
2. **The measurement cannot discriminate inside the interval.** The interval is
   6.4 decades wide and the measured envelope is 3 decades wide, so all but the
   top ~1 decade of the interval produces concentrations below any published
   detection. A concentration comparison therefore constrains
   **fraction × total shed ÷ volume** jointly and identifies none of the three.
   Inverting the comparison makes this explicit: reproducing 5–215 copies/m³
   from the interval's endpoints requires a receiving volume anywhere from
   **2.1 × 10⁻⁵ m³ to 2.4 × 10³ m³** — five decades, i.e. no constraint.
3. **The settings differ in the direction that matters.** Alsved and Bonifait
   sampled within 1 m of a patient in a hospital room, not a 900–1200 m³
   well-mixed ship corridor; the model's zone is the dilution volume, so the
   comparison is a **bounding** check on a coarser volume, not a like-for-like
   validation. Recorded as Grade **B**, analogous setting.
4. **The 3-hour association is reproduced structurally, not numerically.** The
   drain in `TransmissionCore.drain_emesis_aerosol` puts the whole event mass
   into the zone in the epoch of the event, and the shipped legacy clock is one
   epoch = 24 h, so the model cannot resolve a 3-hour window at all. The
   odds-ratio result is therefore evidence for the *mode*, and the window
   itself is **not representable** on the shipped clock. That is a clock-grain
   finding, not a parameter finding.

## 4. Consensus queries run for this tranche, including the nulls

| Query | Result |
|---|---|
| `airborne norovirus concentration copies per cubic meter hospital patient rooms room volume air sampling` | Returned Alsved 2019, Bonifait 2015, Rupprom 2024 (§1) plus respiratory-virus air-load papers. **Null on the room volume**: no returned abstract states the volume of the sampled room, so measured concentration cannot be converted to a released mass, and the implied-volume calculation in §3.2 stays an inversion rather than a comparison |
| earlier passes on the continuous fraction (recorded in [tranche 13](consensus_tranche_13_airborne_fraction.md) §3.1, six unfiltered queries) | **∅ null-confirmed**: no study reports emission to air as a fraction of a host's shedding, for any pathogen. Not re-run here; the rebuilt mode makes the quantity moot for norovirus |

Do not re-run either search for this quantity. The gap is that no design
measures a subject's shed total, the aerosolised fraction, and the room volume
in the same subjects; a third airborne-concentration paper does not close it.
