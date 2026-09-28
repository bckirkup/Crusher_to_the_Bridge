# Non-scored arms — literature audit and draft anchor specs

**Status:** audit deliverable. Measurement-by-reading only — no simulation
runs, no model or constant changes. The measurement set audited against is
[CABIN-FLOOR-02](../ledger/CABIN-FLOOR-02.md) (commit `fbad8738`, confined-pair
probe, seeds 8105/8106). Candidate spec shape follows
`telemetry_buffer/observation_model/anchor_measurement_spec.md`; shipboard
influenza sources are assembled in
[tranche 20](consensus_tranche_20_shipboard_influenza_anchors.md) and register
§3.3.1. Grades follow `docs/sourcing_protocol.md`; every anchor below is a
*likelihood candidate* — no parameter may be chosen to reproduce one.

Terms: **measured** = a number in this repository's ledgers or a value read
from the cited paper; **inferred** = arithmetic on shipped constants (no run);
**hypothesis** = mechanism speculation requiring a run or a read this pass did
not reach.

## 1. Per-arm anchor specs

The measurement surface column names what the engine or the confined-pair
probe would emit. "Scorable when" is the blocking condition, not a plan.

### 1.1 `influenza_a` — scorable set exists; the richest arm

| # | anchor | literature quantity (source, grade) | sourced interval | measurement surface | scorable when |
|---|---|---|---|---|---|
| F1 | confined cabinmate SAR | household secondary infection risk, RT-PCR-confirmed, 13-study spread (Lau 2012, *Epidemiology* 23:531, DOI 10.1097/ede.0b013e31825588b8); symptomatic febrile SIR 4–37% over 20 studies | **[0.03, 0.38]** PCR SIR point-estimate spread, B (meta-analysis, household not ship setting) | confined index pair, mate's first infection inside the confined window — exactly the `CabinPairChallengeLedger` surface | **now** — probe exists; conditioning on susceptible mates is vacuous on the active arm (`base_susceptibility` 1.0, no immunity axis) |
| F2 | voyage NAT-confirmed infection, passengers | Ward 2010 (EID 16:1697, PMC3294517): pdm09 3.9% + H3N2 5.0% + 0.1% both = **8.9%** of 1,970 pax — measured **under** case treatment + crew prophylaxis | [0.05, 0.15] declared band around 8.9% pending a replication, C | per-voyage passenger infection incidence vs a declared intervention manifest (`pharmaceutical_interventions`) | intervention manifest populated (§3.3.2 axes) — unscoreable on a no-pharmacology arm, by construction |
| F3 | MAARI attack, pax and crew | Millman 2015 (J Travel Med, PMC4869710): pax **3.7%** / **6.2%**, crew **3.1%** / **4.7%** — under empiric treatment + contact prophylaxis | pax [0.037, 0.062]; crew [0.031, 0.047], B/C (two ships, one outbreak pair) | `observation_model` MAARI reporting — emitted as its own rung, not fused with NAT | same as F2; also needs the reporting vector declared, never fitted (§3.3) |
| F4 | pax:crew case ratio | Millman 2015 both ships | **[1.19, 1.32]**, B | ratio of observed pax to crew MAARI rates | with F3; note this is lower than noro A5's ~2.9–3.5 — a ship-model contrast, not a pathogen constant |
| F5 | infirmary capture fraction | Ward 2010 same-voyage internal contrast: 0.7% presenting vs 8.9% NAT-confirmed | **≈0.08**, C | reported episodes / true infections | observation model only; an internal-consistency check, not a standalone anchor |

Recorded negatives (already in register §3.3): **no VSP anchor** — the
posting rule is gastrointestinal; **no fleet-count likelihood** — influenza
reporting is voluntary with a 1.38 ILI/1000 traveler-days threshold, a
different functional form.

### 1.2 `measles_virus` — anchor exists; blocked on a susceptibility surface

| # | anchor | literature quantity | sourced interval | measurement surface | scorable when |
|---|---|---|---|---|---|
| M1 | confined cabinmate SAR among **susceptible** mates | "~90% attack rate in susceptible household contacts" (Patel 2019, MMWR 68:893, DOI 10.15585/mmwr.mm6840e2, citing the classic household studies); register floor [0.75, 0.90] is consistent | **[0.75, 0.90]**, B (consensus figure across decades of household studies; secondary vaccine-failure cases transmit at 0–6.25% per Tranter 2024, EID 30:9 — a different case class) | probe attack rate conditioned on a **susceptible** mate | **blocked**: the arm carries no immune state — `innate_nonsusceptible_fraction` 0.0, `nonsusceptible_mechanism "none"`, and `base_susceptibility` 0.08 attenuates *dose* for every mate rather than marking ~90% of the population immune. An unconditioned attack conflates coverage with transmission; the anchor is scorable only once the probe can condition on a susceptible/immune mate state (a population axis, not a constant) |

Caveat on the CABIN-FLOOR-02 verdict: measured 1/3 = 33.3% vs the [0.75, 0.90]
floor is "miss low" directionally, but n = 3 — the exact 95% interval on 1/3
is roughly [0.01, 0.91] and contains the floor. The miss is **measured but
statistically weak**; the blocker above is the substantive finding.

### 1.3 `clostridioides_difficile` — two-tier anchor; the ~5% floor needs restating

| # | anchor | literature quantity | sourced interval | measurement surface | scorable when |
|---|---|---|---|---|---|
| C1 | confined mate **carriage conversion** | Loo 2016 (ICHE, DOI 10.1017/ice.2016.178): 67 household contacts — probable transmission **1.5%**, possible **7.5%**, any culture positivity **13.4%** (PFGE-matched); only 1/67 developed CDI | **[0.015, 0.134]** two-tier (confirmed-to-any), B− (single prospective study) | mate's first infection event in the confined window, with "infection" read as colonization — the profile's `never_symptomatic_fraction` 0.9 says carriage is the dominant state | **now**, once the probe labels whether its "infection" event is carriage or CDI — a surface-definition task, not a model change |
| C2 | household clinical CDI attack | Pépin 2012 (J Infect 64:2, DOI 10.1016/j.jinf.2011.12.011): spouses **4.71/1000**, children **5.99/1000**, elevated ~3 months post-index; Miller 2020 (JAMA Netw Open 3:e8925): family-exposure IRR **12.5**, ~0.48% of population CDI attributable to family exposure | **[0.0005, 0.015]** CDI disease over a household-exposure window, B (large case-control + prospective pair) | symptomatic/CDI secondaries among confined mates over voyage + tail | **now** on the same conditioning note; expect the arm to sit near the top of this band because ship cohorts skew elderly/antibiotic-exposed (declared, not measured) |

CABIN-FLOOR-02's "~5%" floor sits inside C1's band but above its
transmission-confirmed end. The measured 0/143 has a 95% upper bound ≈ 2.1% —
**measured**: consistent with Loo's confirmed-transmission rate, inconsistent
only with readings ≥~2%. "Miss low vs ~5%" should be restated as "below the
pooled colonization midrange"; the channel is not dead on the literature.

### 1.4 `legionella_pneumophila` — the confined-pair surface is the wrong instrument

The probe's "vacuous" verdict is **structural and correct**: the profile's
shedding curve is identically zero and person-to-person transmission is
effectively unmeasured in the literature (a single probable P2P case report
exists; standard texts treat it as zero). Hosts are a dead end by design — the
modelled route is `environmental_source` weight 1.0, i.e. the ship's water.
Scorable anchors must be **source-conditioned**, not mate-conditioned.

| # | anchor | literature quantity | sourced interval | measurement surface | scorable when |
|---|---|---|---|---|---|
| L1 | LD attack rate among exposed to a contaminated source | Doebbeling 1987 (Semin Respir Infect 2): Legionnaires' attack rate **2–7%** among exposed; Hamilton 2018 review of 136 outbreaks consistent (median outbreak attack ≈7%, range 1–40%) | **[0.02, 0.07]**, B− (textbook-epidemiology consensus, no pooled CI) | infections among occupants with a registered exposure to a contaminated water/aerosol source, divided by that exposed set | **blocked**: needs an environmental source scenario term (spa/plumbing emission) **and** an exposure register attributing dose to the source window — neither is a constant, both are surfaces |
| L2 | exposure–response gradient | Jernigan 1996 (Lancet 348, DOI 10.1016/s0140-6736(96)91137-x): cruise-ship whirlpool outbreak, OR **16.2** for spa exposure, risk +64% per hour in spa water | gradient, not a rate | dose–response slope across exposure-duration bins in a spa scenario | with L1's source term |
| L3 | Pontiac-fever attack rate | PF outbreaks run **75–100%** among exposed (Fenstersheib 1990: 82%; Friedman 1987: 78%; Doebbeling: 95–100%) | [0.75, 1.0] validation-only | mild non-pneumonic syndrome fraction | the arm's `illness_probability.eta` 0.05 models LD-severity illness only; L3 is a shape check, never a scored rung |

### 1.5 `vibrio_cholerae_parahaemolyticus` — split anchors; the "~0" floor is wrong for the cholera half

| # | anchor | literature quantity | sourced interval | measurement surface | scorable when |
|---|---|---|---|---|---|
| V1 | attack rate among consumers of the implicated item | McLaughlin 2005 (NEJM 353:1463, DOI 10.1056/nejmoa051594): cruise-ship oyster outbreak, **29%** of oyster consumers (17% of interviewed pax); Daniels 2000 (JID 181, DOI 10.1086/315459): median **56%** across 40 outbreaks among consumers of implicated seafood | **[0.29, 0.56]**, B (one shipboard + 40-outbreak median) | fraction of consumers of a contaminated food batch who become infected/ill — `food_contamination.enabled` already true | **blocked** on a contaminated-batch scenario and a consumer register; both are scenario surfaces, not constants |
| V2 | household/close-contact infection risk | *parahaemolyticus*: no person-to-person measure found — all retrieved outbreaks are foodborne (effectively ∅lit for P2P). *cholerae*: Sugimoto 2014 (PLoS NTD 8:e3314, DOI 10.1371/journal.pntd.0003314) — direct household exposure infected **3.7–8.2%** of contacts over an 11-day infectious period (Ogawa 4.9% [0.9–22.8%]) vs 2.5% community, in **endemic** Dhaka | **[0.0, 0.082]** combined arm; cholera component [0.037, 0.082] (household direct exposure, includes shared water/food — an upper bound on pure contact) | confined-pair attack (probe surface) | **now**, on the restated band |

CABIN-FLOOR-02's "~0" floor is an **interval error** for the combined arm —
corrected to [0, 0.082] by V2. The measured 1/6 = 16.7% sits above the band
but n = 6 (95% interval ≈ [0.004, 0.64]): **measured, statistically weak**.

### 1.6 `andes_hantavirus` — contact-class-conditioned anchor

| # | anchor | literature quantity | sourced interval | measurement surface | scorable when |
|---|---|---|---|---|---|
| H1 | non-intimate cabinmate SAR | Ferrés prospective household cohort, via Pennisi 2026 systematic review (*Viruses* 18:699, DOI 10.3390/v18070699): overall household SAR **3.4%**, **non-sexual household 1.2%**; supporting zeros: Castillo 0/20, Kofman 0/53 | **[0.012, 0.034]**, B− (one prospective cohort in a 33-study review) | confined-pair attack among non-intimate mates | **now**, if the probe tags pair contact class |
| H2 | intimate/sexual-contact SAR | same review: sexual partners **17.6%** | ~[0.10, 0.30] declared around 17.6%, C | confined-pair attack among intimate partners — real on a cruise (couples' cabins) | the engine/probe must distinguish pair contact class; currently uninstrumented |

Chubut 2018–19 superspreading (R > 2 pre-control) is a shape observation, not
a rate anchor. The measured 1/3 = 33.3% vs [0.012, 0.034] is **measured high
but n = 3**; if the confined pair was an intimate pair the H2 band partly
absorbs it — the conditioning gap is the finding, as on measles.

## 2. Influenza overshoot read-through

CABIN-FLOOR-02 measured 56.9% (active) / 56.2% (Edison) confined attack vs the
15–25% floor band — overshoot on both bundles. Lau 2012's full PCR-SIR spread
is 3–38%, so both bundles sit above even the widest literature read.
(The 15–25% band was the norovirus Wikswo/Chimonas cabinmate pair reused
generically; on flu it is withdrawn — the corrected band is derived from the
declared k, `docs/confined_attack_floor_spec.md`, CABIN-FLOOR-03.) Below:
each shipped constant against its register interval, then the structural
remainder. Constants are as shipped at `fbad8738`.

### 2.1 Constant-by-constant

| constant | active | Edison | register interval | verdict |
|---|---|---|---|---|
| `dose_response.k` | 0.18 | 0.18 | [0.07, 1.2] declared, ⊘ joint, "unresolved citation spread" | **inside its declared interval — but the interval is unit-mismatched**: its endpoints derive from aerosol ID50 0.6–3 **TCID50** (Alford 1966) while the engine applies k per emitted **copy** (`_dose_response_hazard` = −expm1(−k·dose), dose in released copies). RNA:TCID50 in paired clinical samples runs ≥~10³ (Van Wesenbeeck 2015, OFID, DOI 10.1093/ofid/ofv166: baseline VL GM 5.61 log₁₀ copies/mL vs TCID50 near 2–3 log₁₀) — converted, the sourced bound is k ≈ **2e-4 – 1e-3 per copy**, and shipped 0.18 is ~2 orders high. **Inferred**, not measured |
| implied N50 | ln2/0.18 = **3.85 copies** | same | — | at k = 0.18, infection probability is 99% at ~26 delivered copies. The Edison incubation note itself states `dose_reference_log10` is "in model units" — the unit gap is acknowledged in-tree but the register interval was never re-expressed. Inferred |
| peak emission | 10^(7.2−0.82) = **2.4e6 copies/day** | 10^(7.2−1.5) = **5.0e5/day** | register emission row `—` | **measured rate, hypothesis duty cycle**: the active value is Yan 2018's exhaled GM (3.8e4 + 1.2e4 per 30 min) × 48 — i.e. a 30-minute supervised-breathing/coughing sample extrapolated to 24 continuous hours. An honest duty cycle (sleep, quiet hours) plausibly lowers it severalfold, but Edison emits 5× less and still reads 56.2% → emission level is **not the binding term** in this overshoot |
| incubation | logN median 1.4 d, [0.5, 7.0] | identical | Lessler 2009 sourced | inside; identical in both bundles |
| `presymptomatic_shedding_days` | 1.0 | 1.0 | [0.5, 2] Ip 2017 | inside, both bundles |
| shedding duration | `shedding_duration_days` 7 explicit | absent → `recovery_day` 5 fallback | [3, 8] declared | inside; the two-clock split already landed on the active arm |
| `symptomatic_fraction` | 0.669 | 0.669 | Carrat CI [0.583, 0.745] | inside, at the source point estimate |
| airborne emission share | `airborne_emission_fraction` 0.76 | `surface_deposition_fraction` 1e-3 (deprecated alias) | [0.76, 0.92] B | active inside at the floor; **Edison's 1e-3 is 760× below the interval floor — outside the sourced band on its face**, but the register already marks the field "must not be loaded", and Edison still overshoots at 56.2% → the airborne share is **not binding** |
| `base_susceptibility` | 1.0 | 0.65 | [0, 1] declared | not binding (0.65 on a saturating dose is still saturating) |
| `transmission_route_weights` | absent (mechanistic routes) | 0.2/0.35/0.3/0.15 read as per-route multipliers | "must not be loaded" | Edison damps **every** route 3–5× and still overshoots → route apportionment is not binding |
| droplet aerosol fraction | `DROPLET_AEROSOL_FRACTION` 0.05 hardcoded for continuous arms | same | documented open item | structural, minor share of dose |

### 2.2 Where the overshoot lives

- **Measured:** both bundles 2–3× over the floor band; Edison's config is
  strictly *less* transmissive on every emission/route axis and reads the same
  56%. Within this audit there is **no shipped constant outside its declared
  register interval on the active bundle**; the only literal out-of-interval
  value is Edison's `surface_deposition_fraction` 1e-3, in a field already
  marked unloadable.
- **Inferred (the candidate diagnosis):** the overshoot is a **units-of-dose
  defect**, not route geometry or emission magnitude. The k interval's
  citations are per-TCID50; the engine consumes per-copy; converted, the
  sourced interval is ~2–3 orders below the shipped k, and N50 = 3.85 copies
  means any confined mate who receives ~25+ copies is saturated. Every
  non-binding axis above (emission 5×, airborne share 760×, routes 3–5×,
  susceptibility 0.65×) is consistent with that single explanation.
  **Resolved by FLU-DOSE-01** (ledger entry): confined-mate dose is measured
  at median 2–9 copies — at the shipped N50, *not* above the 26-copy
  saturation point — and implied SAR tracks observed attack. The unit
  mismatch is confirmed as the operative term, but correcting k alone would
  flip the arm to a ~0% MISS low: the delivered dose is ~2–3 orders below
  the ~700–3,500-copy scale a per-TCID50-calibrated hazard needs. The arm
  carries two compensating defects, not one.
- **Hypothesis:** the Yan GM×48 duty-cycle extrapolation inflates emission
  severalfold on the active arm; the hardcoded 0.05 droplet fraction is a
  further minor term. (FLU-DOSE-01 measured emission level as non-binding
  for *confined* delivery — the under-delivery defect sits downstream of
  emission, in the delivery chain — but neither term is excluded as a lever
  on non-confined transmission.)
- **Structural overshoot: none identified as binding.** Onset geometry,
  shedding duration, and symptomatic fraction all sit inside sourced bounds;
  the floor miss does not require a confinement-mechanics explanation.

## 3. Register hygiene applied in this PR

- `dose_response.k` (§3.3): interval cell annotated — endpoints are per-TCID50,
  the engine applies per emitted copy, converted bound ≈ 2e-4–1e-3/copy; state
  unchanged (⊘ joint), defect queued rather than silently re-intervalled.
- §3.3.1 candidate-anchor table: Lau 2012 household-SIR row added (the F1
  confined-cabinmate anchor).
- §3.5 rows were re-read against the audit; no boarding bound moved, so those
  rows are unchanged. Vibrio's person-to-person floor (~0 → [0, 0.082]) and
  c.diff's (~5% → two-tier [0.0005, 0.015] disease / [0.015, 0.134] carriage)
  are ledger-floor corrections recorded in §1.3/§1.5 here; CABIN-FLOOR-02 is a
  measurement record and is not retroactively edited.

### Retrieval ledger

Consensus was the only route (one E1 pass per arm; queries in session
history). All intervals above were sourced this pass except Ward/Millman/
Brotherton (tranche 20, §3.3.1) and the flu constant internals (register
§3.3). No `?nr` was earned this pass — every anchor quantity returned a value
on the first differently-phrased attempt. Not retrieved: a direct copies-per-
TCID50 for exhaled influenza *aerosol* specifically (Van Wesenbeeck is NP-swab
paired data — the conversion bound is marked as such).
