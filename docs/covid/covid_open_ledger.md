# SARS-CoV-2 fit: open ledger

> **Status:** Living. Head commit of record: `ea9550ef` (fill with the
> `main` SHA this file was authored against). If that is not the current head,
> treat every number here as unverified.

What is currently withdrawn on the `sars_cov2_resp` arm, what the last
measurement of record is, and what is outstanding. The permanent defect record
for shared mechanics is `docs/ledger/` (entries tagged `sars_cov2_resp` or
`all`) together with the frozen numbered history in
`docs/norovirus/norovirus_open_ledger.md`; readouts live in `docs/covid/`.

Read this before quoting any Θ, attack-rate, onset-curve or route-share figure
for the COVID arm.

---

## 1. Currently withdrawn

**CABIN-OCC-01 + ROOM-AIR-01 move every airborne-route dose figure on any
hull that declares AHU rates, and every confined-cabinmate figure.** Every
room-pool inhalation route now doses the epoch-mean of a pool exchanging
at the zone's declared `ach × hvac_duty` (plus the stateroom
bathroom-exhaust adder), and cabin-mate plume/addback/confined-contact
channels gate on time-partitioned co-presence (ledger `CABIN-OCC-01`,
`ROOM-AIR-01`). Airborne dose figures and confined-pair readings measured
before this PR's merge SHA are historical at their own `Measured at`
entries — `sealed`/`off` reproduce them bit-identically for attribution.

**REINFECT-01 voids every `infections_before/during/after_quarantine`
figure measured at or before `861a0b9` as a count of hosts infected in the
window.** A cleared host acquired no immunity without a strain registry and
its second infection overwrote the record, so the truth channel dated the
latest episode (`docs/ledger/REINFECT-01.md`, measured at `861a0b9`): 32% of
the Θ 1e9 `A0` during-quarantine count and 96% in the saturated seed
`20200205` were reinfections; 37.6% of infected hosts in the probe cell were
infected twice. **Fixed at `7f105a7`** (unlabeled clearance immunity +
refractory protection without a registry, episode bookkeeping, syndromic
onset re-dating); the paired in-image canary moved `A0` seed `20200205`
during-quarantine counts 455 → 198 (Θ 1e5) and 973 → 43 (Θ 1e9), so all
`861a0b9` during-quarantine figures — including every arm count in the
`covid_quarantine_attribution_v1` campaign — are superseded as first-infection
windows. `infections_total`, `attack_rate` and `recorded_onsets` counted
distinct hosts and stand in count. The "outbreak continues through enforced
quarantine" reading at truth-channel scale (handoff §12, v9 readout §6) is
superseded by `docs/covid/covid_quarantine_attribution_v1_readout.md` §4–6.

**QUAR-EXEMPT-01 moves every post-`1a25c24` confinement-sensitive figure.**
`exempt_classes` is now scoped to the protocol that declares it
(`docs/ledger/QUAR-EXEMPT-01.md`); symptomatic crew are confined by
`SOP-008`/`010`/`016` while `SOP-011` is active, where the old union never
confined them. THETA-SCREEN-V9 figures stay valid at their own `Measured at`
SHA `0fb186b` and are not re-run; the same cells at HEAD are a different
trajectory. S3 cells reproduce only inside the campaign image
(`python:3.11-slim`, numpy 2.4.6), not on a CPython 3.12 / numpy 2.5.0 host.

**AERO-NEAR-02 invalidates prior near-field-sensitive COVID figures.** The
QUAR-ORDER-01 burning and intermediate-cell figures are superseded by the
AERO-NEAR-02 measurement (§2). The two diagnostic cells are not paired with
their QUAR-ORDER-01 runs: per-meal table dealing consumes RNG, so the same seed
follows a different trajectory.

**AERO-SPLIT-01 supersedes every figure produced under the unbounded
droplet far field.** The droplet pathway's zone pool now carries only the
declared `far_field_share` (0.175, midpoint of [0.05, 0.30], Grade C) of
continuous emission; the rest reaches a partner-bounded proximity ring at
plume concentration, bounded by the CONTACT-ARCH-01 activity rates
(`docs/ledger/AERO-SPLIT-01.md`, `docs/droplet_field_split_spec.md`,
`transmission.droplet_field_split`, labelled pre-change baseline `mode:
off`). Every measured figure whose mechanism was the well-mixed room pool —
the v11 stage-2 ~17.7× onset overproduction and ~0.96 attack on takeoff
seeds, the assay-1 arm table and its ~68%-day-0–2 route attribution, every
Θ surface and admissible set on this arm, and all droplet route shares —
is superseded pending remeasurement on the partition tree. `off` is
bit-identical to the pre-change engine (no proximity draws on the shared
stream), so paired-seed contrasts stay attributable.

**DOSE-FRAIL-01 invalidates every Θ-arm figure measured on identical hosts.**
The Θ arm previously installed an exponential dose-response, which gave every
host the same susceptibility; it now scales the profile's own per-host
`Beta(0.18, 58)` draw so that the arm's mean susceptibility is Θ
(`docs/ledger/DOSE-FRAIL-01.md`). The AERO-NEAR-02 crew-mess trace below, and
every Θ-arm figure of record, were measured with identical hosts and are
superseded on this arm pending remeasurement. A rescaling will not recover
them: frailty spreads a threshold that previously fired for a whole room at
once.

**Every fitted Θ is void pending a refit on the repaired airborne subsystem.**
The fits of record (`covid_first_look_v1`–`v6`, the 1b boarding screen, and the
three-stage imports × Θ sweep) were all measured before at least one of:

- `AERO-CABIN-04` (#583): HVAC-downstream inhalation ignored cabin confinement.
- `AERO-CABIN-05` (#588): each room's standing air was inhaled once per upstream
  shedding zone (measured mean 5.2×, up to 82×) instead of once per epoch.
- `AERO-CABIN-06` (#591): the airborne reservoir was keyed on the whole cabin
  block, so a confined shedder's aerosol reached every stateroom on the block.

`v6` (#565) additionally carried `AERO-CABIN-03` (#561) and the two realistic
air defaults, but not 04–06. Its selected Θ = 3.16e11 and every earlier
Θ (3.16e7 on pooled air, v4/v5) belong to the air model they were measured on
and are not carried forward.

Every prior Θ figure and the v6 readout were also measured with the voluntary
FRED draw applied to scheduled SOP-017, so they are void pending remeasurement
under the authority-enforced quarantine declaration.

*Update (2026-09-26, `6a7dfe4e`, `COVID-REBASE-01`): the void Θ window was
re-screened on the post-721 base over a 16-point union lattice × 200 seeds —
**the admissible set is EMPTY**; the v11 band {3.16e10, 4.22e10, 5.62e10} fails
the fleet-shape median floor everywhere (interior medians pinned at 0.00027),
and the window is bracketed in (1e11, 1e12). The conditional clause still
fails at all three band points in the same ~17× mass class, but its
before_share halved to 0.45–0.66 (v11: 0.77–0.92, target 0.173). The boarding
axes are now measured: at the declared geometry the day-0→5 index window is a
median 0.5% of takeoff-class infections (clean index-only bound median 3), so
boarding structure is not the takeoff burn; co-primaries reach majority scale
only at count ≥ ~8 and saturate by 32
(`docs/ledger/COVID-REBASE-01.md`,
`docs/covid/covid_rebase_01_readout.md`).*

*Update (2026-09-27, `f42901aa`, `THETA-SCREEN-V12`): the bracketed window
was bisected to eighth-decade resolution — **the fleet-shape admissible set
is {1.33e11, 1.78e11, 2.37e11, 3.16e11, 4.22e11}** (medians 0.00054–0.0062
inside the H3 band; 1e11 fails the floor, 5.62e11+ fails the ceiling). But
the conditional clause fails at every admissible Θ in the same ~17× mass
class: all 20/20 takeoff seeds per row saturate at ~2,200–3,580 recorded
onsets (the q05 floor alone is 11–15× the record's 197) and before_share
medians run 0.70–0.96, rising monotonically with Θ. The clause's only pass
is the Θ1e9 anchor — a fleet-shape-inadmissible boundary row. **No Θ inside
the admissible window fits; the Θ axis in the bracket is exhausted and the
residual is mechanism-shaped** (`docs/ledger/THETA-SCREEN-V12.md`,
`docs/covid/covid_theta_screen_v12_readout.md`).*

*Update (2026-09-28, `edb7fc41`, `THETA-SCREEN-V13`): the same lattice and
declared replay re-ran under capped reach (COVID-EXPOCAP-01 default-on).
**The fleet-shape admissible set shifts one notch up at each edge —
{1.78e11, 2.37e11, 3.16e11, 4.22e11, 5.62e11}** (1.33e11 now fails the
floor, 5.62e11 now clears the ceiling; the budget flattens outbreak tails
so the mean cap never binds). But the conditional clause again fails at
every admissible Θ in the same magnitude class: takeoff-seed q05 floors
sit at 1,770–2,024 recorded onsets (9–10× the record's 197) and
before_share medians run 0.81–0.94 rising with Θ; the only pass is the
Θ1e9 boundary anchor (before_share 0.175 ≈ 0.173). **The cap moved where
the window sits, not what takeoff trajectories do inside it — no Θ is
admitted and the residual remains mechanism-shaped**
(`docs/ledger/THETA-SCREEN-V13.md`,
`docs/covid/covid_theta_screen_v13_readout.md`).*

*Update (2026-10-02, `6efec855`, `COVID-THETA-V15`): the same lattice
and the declared replay re-ran under the repaired presentation spend
(PRESENT-SHARE-01 `once_per_course` shipped default-ON, PR #825 —
the v14 stage-2 enumeration never executed, so this is the first
post-repair replay surface; it pairs against v13's `edb7fc41` cells).
**The fleet-shape admissible set reverts to the v13 coordinates —
{1.78e11, 2.37e11, 3.16e11, 4.22e11, 5.62e11}** — 1.33e11 falls back
under the floor (0.00040) and 5.62e11 clears the ceiling again
(0.00687): with ~31% of courses never presenting, recorded counts sit
lower at fixed Θ so the floor needs one notch more transmission. The
conditional clause still fails at every admissible Θ in the same mass
class: takeoff-seed q05 floors 1,444–1,743 recorded onsets (7–9× the
record's 197), before_share medians 0.73–0.96 rising with Θ; the only
pass is the Θ1e9 boundary anchor. **Seed-paired vs v13, the repair
removed ~750–940 median recorded onsets per ignited seed — the largest
mechanism-level move the replay surface has registered — and the
failure still stands by ~10×: the presentation channel was a real
defect and is not the DP residual** (`docs/ledger/COVID-THETA-V15.md`,
`docs/covid/covid_theta_screen_v15_readout.md`).*

*Update (2026-09-28, declared): two mechanism assays on the v13 residual
are declared — **COVID-RINGCAP-V1** (`transmission.exposure_cap.
include_fixed_rings`: the cabin-mate and same-table rings spend the
shedder's per-epoch budget first, pool draws the remainder; the measured
top suspect since ROUTE-ATTR-V1 read ~98% of dose weight ring-side) and
**COVID-SUSCPOOL-V1** (hard non-susceptible fraction on the shipped
secretor-negative grammar at {0.25, 0.5, 0.75} — bounds the ~2x+ truth
overshoot SERO-CHANNEL-V1 factorized). Each runs the v13 stage-2 replay
cells verbatim at the admissible band plus a coarse generic-voyage
fleet-shape response check; a clause PASS triggers a re-screen design on
that arm, never an adoption (`docs/ledger/COVID-RINGCAP-V1.md`,
`docs/ledger/COVID-SUSCPOOL-V1.md`).*

*Update (2026-09-28, canary measured at `472cdf13`, image
`covid-mech-v1-472cdf13`, jobdef rev 31): both declared canaries clean —
120/120 children, 0% failures, audit invariant 1.0 on every arm row —
and both mechanisms produced a **clause PASS at the Θ1e9 anchor row**:
`rings_first` (takeoff n 6, q05–q95 [133–3146] ∋ 197, before_share
0.128) and `f050` (n 5, [81–1466] ∋ 197, 0.213). `cap_on`/`declared`
reproduce the v13 anchor bit-for-bit (0.373, FAIL); `f025` fails with
its q05 floor above 197; `f075` leaves only 3 takeoff seeds — below the
≥5 floor, not the every-row trigger. Boundary-endpoint PASSes only: the
full arrays decide whether either survives the admissible band
(`docs/covid/covid_mech_v1_canary_readout.md`).*

*Update (2026-10-02, `def39066`, anchor canary re-measured under
`once_per_course` — the `472cdf13` readings above are STALE and
superseded): both assays' Θ1e9 anchor rows re-ran on the v15-paired
designs (PR #850; image digest `sha256:516b0b57…`, jobdef rev 46,
120/120 cells, 0 audit failures, `cap_on`/`declared` reproduce the v15
stage-2 parent seed-for-seed). **rings_first's premise collapsed —
the anchor clause now FAILs on both legs (takeoff n 11, q05–q95
405–2460 does not contain 197, before_share 0.343). f050's premise
survives — the only PASS still standing under the repaired draw
(n 6, 169–1193 ∋ 197, share 0.150).** `f025` fails the count leg high
(227 > 197, same direction as the stale run); `f075` now contains 197
on the count leg (61–553) but fails the share leg (0.410). The
mechanism-arms do move the rows vs v15 (6–10 takeoff-class flips each),
so these are measured deltas, not dead wiring — the payload now carries
`delivery.exposure_cap_include_fixed_rings_engine` and a
`secretor_negative` declared/resolved/realized block proving the
overrides landed. Whether f050 survives the admissible band awaits the
full-array decision (`docs/covid/covid_mech_v2_canary_readout.md`).*

*Update (2026-10-02, `def39066`, full arrays measured — both assays
DEAD): per the user's surviving-arms decision, SUSCPOOL replay
{declared, f050} × 5 admissible θ × 20 seeds (200 cells) and fleet
{declared, f050} × 5 θ × 50 seeds (500 cells) ran on jobdef rev 46 —
700/700 SUCCEEDED, 0 audit failures, declared reproduces v15 stage-2
seed-for-seed at all six θs. **f050 fails the clause at every
admissible θ** (takeoff q05 floors 411–1329 vs 197; before_share
0.69–0.90 vs 0.173±0.10) — its anchor PASS was a boundary-endpoint
phenomenon, so SUSCPOOL-V1 is dead under the current engine, and
RING-CAP-V1 was already dead by premise collapse. The fleet check is
the interesting survivor: f050 sags the cross-ship surface INTO the
covid.H3 window at 4/5 admissible θs where the declared band runs hot
— a real fleet-shape response mapped for any successor pool-fraction
design, but unreachable for the replay leg. Readout:
`docs/covid/covid_mech_v2_band_readout.md`.*

**The declared index case is repaired — earlier text here was stale.**
The record's index boarded 20 Jan already symptomatic (onset 19 Jan) and left
at Hong Kong on 25 Jan (Yamagishi 2020). Declared per-agent departure exists
(`docs/ledger/INDEX-GEOM-01.md`: `departure_epoch` gates transmission and
every aboard denominator through `LOCATION_DEPARTED`), and every stage-2
replay since v11 declares the record's geometry verbatim —
`onset_day: -1.0`, `departure_day: 5.0`, `infection_age_days: 6.8`
(bookkeeping only; under a declared `onset_day` the age axis is a measured
null, COVID-SEED-GEOM-01). Verified live on the v15 cells:
`index_onset_day = -1.0`, `index_departed_epoch = 120`, shedding at day 0 in
100% of seeds (audit invariant; a deviation invalidates the cell). The
seeding-geometry axis itself is measured `geometry_incapable`
(SEED-GEOM-V1): onset-epoch / placement / co-primary / departure arms at
every Θ sit at medians ~3,461–3,612 — the residual does not move with index
geometry. Declared omissions remaining: the 22 Jan Kagoshima excursion (out
of scope, aboard-side) and off-ship progression of the departed host
(cosmetic). Figures predating INDEX-GEOM-01 (v11 and earlier) scored a
curve that kept him aboard all 32 days.

*Update (2026-09-26, `4e0032a0`, `COVID-SEED-GEOM-01`): under a declared
`onset_day`, `infection_age_days` is now a measured null axis — the 6.8 vs
3.3 age pair is bit-identical on seeds 20200205/06 @48ep, because shedding,
onset timing and clearance all anchor to `onset_time_infected`. The open
geometry question that survives is onset/departure geometry, not the age
field: one peak-shedding index aboard 5 days seeds {3…2494} aboard-window
acquisitions (median 91; clean index-only bound median 30) across 5 seeds at
Θ×1.0, predominantly via the droplet far-field pool (median near-field dose
share 0.006), and the fresh-index contrast arm collapses it to a median of
3.*

**The upstream AGID attack-rate fit may not be quoted as validation of this
port's arrest layer or dose scale.** Ledger `AGID-UPSTREAM-AR-01` settles the
provenance question: the upstream paper (PNAS 10.1073/pnas.2422574123) does
report a Diamond Princess fit — 18.6% against the observed 19%, RMSE 23.73 on
the daily series — but that run carries no arrest layer, while DP's 19.2% is a
post-quarantine outcome, and upstream's own Isolation arm on the same
parameterisation lands at 4%. The published engine
(`bckirkup/infection-dynamics` `8d159f4`) also has no active environmental
route, caps transmission at one to two proximity targets per shedder per 20
minutes, and decides infection by a deterministic `P > 0.5` threshold on the
source's shedding, so its attack rate is a contact-opportunity count that
pathogen quantity cannot move. Neither its fit nor its calibration transfers to
a summed-dose engine with shared-air routes. The same applies to the VSP-shadow
monograph (`docs/reports/05_vsp.tex`), whose attack-rate band is post-response
norovirus at `dose_adjustment` 10.6, not a COVID fit.

## 2. Last measurement of record

`CREW-WINDOW-02`, measured at `2df542ff` (`docs/ledger/CREW-WINDOW-02.md`,
`docs/covid/covid_crew_window_02_readout.md`): the interior of the CW-01
crew-duty cliff — fractional/activity-scoped crew confinement via
`exempt_work_zones` (essential-zone lists NARROW 11/34, WIDE 19/34) and
`exempt_fraction` (sticky draws 261/523/784 of 1,045), {Θ1e6, Θ7.9e6} ×
{D0, ZONE_NARROW, ZONE_WIDE, FRAC_25/50/75} × 20 seeds, 240/240 cells.
**CHANNEL-LANDED — FRAC_25 (during median 301) and ZONE_NARROW (334)
land [150,350] at Θ7.9e6 with the before phase seed-paired unmoved**;
all other arms under-attenuated (ZONE_WIDE 504, FRAC_50 482, FRAC_75
622.5); during medians monotone in realized exempt share (~0.25–0.31
working-crew share brackets the band's interior). Crew share moves only
marginally (0.973/0.978 vs D0 0.992, record 0.29) — confined crew are
fed by R3 steward delivery (no starvation) and residual infections stay
crew-on-crew, so the channel lands the mass without resolving the
attribution; at Θ1e6 three arms land the band with share 1.000
(IN-BAND-INCOMPLETE). CW-01 D0 drift witness pairs at Δ0.0. Next legs:
source the landing complement (~25–31% essential working share — record
essential-service complement / VSP manning), and the crew-share gap
itself is now the open sub-question on this channel. **Open item
(unruled):** the frozen D0 `realized_exempt_share ≈1` invariant flagged
4 big before-phase seeds (0.68–0.87 — isolation-path confinement, not
the order gate); whether the expectation is amended or kept strict is
recorded in `docs/covid/covid_crew_window_handoff_2026_10_06.md` §8.

Prior measurement — `CREW-WINDOW-01`, measured at `ea9550ef` (`docs/ledger/CREW-WINDOW-01.md`,
`docs/covid/covid_crew_window_01_readout.md`): the working-crew-channel
attenuation screen — {Θ1e6, Θ7.9e6} × {D0_declared, CREWDUTY,
EXEMPT_ENGMED, EXEMPT_ESSENTIAL, MESS_0P5, MESS_0P25} × 20 seeds,
240/240 cells, 0 audit failures, first campaign on the `campaigns/`
harness. **CLIFF-STRUCTURE — no declared arm lands [150,350].**
CREWDUTY (sourced symptomatic-crew removal) fires ~660 hosts/seed and
moves nothing (758 vs 739); the exempt-set axis is a binary carried by
`crew_general` alone (exempt ~740 ↔ confined ~70, and ENGMED/ESSENTIAL
are bit-identical — galley's exempt status never reaches a draw,
resolved 2026-10-05: the DP replay instantiates only
`passenger_general` + `crew_general`, so both arms confine the entire
crew identically — ALLHANDS-equivalent — and the "cliff" is the hull's
class vocabulary, not an attenuation function); MESS
far-field attenuation is a non-lever. The record band sits inside the
70↔739 step; the discriminating follow-up is a *fractional*
general-crew axis — on this hull best expressed activity-scoped
(essential duty activities keep running, cabin service stops), since
the record's "essential service" distinction lives inside the single
`crew_general` class — and if that also skips the band the suspect leaves
this channel for the onset-dating channel (map legs D1–D3).

Before that — `DP-BELIEF-01`, measured at `78f52a58`/`8f49652f`/`8f926382`/`3eae8a2f`/`b932d0e9`
(`docs/ledger/DP-BELIEF-01.md`,
`docs/covid/covid_believability_map_v1.md`): the Diamond Princess
believability map — every checkable record feature scored on the 420
synced cells of record, no new cells. **BELIEVABILITY-DIVERGENT — three
orthogonal divergences, none θ-shaped.** Mass is reachable
(`infections_total` in the serology band [712,960] at *both* clause-leg
crossings); the timing is inverted (infections-before-quarantine share
0.08–0.25 vs the record's majority — onset peak day 21–27 vs ~18,
during-quarantine dated mass ~95% crew vs the record's 29%); and the
dating channel overshares ~3× flat (`recorded/lab` 0.79–0.87 on every
row vs the record's 0.277 — θ- and mechanism-independent). The
clause-passing CG_OFF surface is itself unbelievable (2,342 infections,
2.8× the band). Head-of-record for the DP believability question; the
needs-cells legs (route-tagged dated onsets D1, cabin-cluster tallies
D2, acquisition-date scoring D3, quarantine-phase suppression arm D4)
are designed in the map §4. **D3 measured (addendum
2026-10-04):** the phase fix is not a global shift — at Θ7.9e6 the
acquisition curve already has the record's *shape* (peaks ~day 15,
declines during quarantine) but splits mass ~25/75 instead of ~65/35
because days 0–8 are nearly empty while the day-16+ tail is fat;
conforming needs BOTH early front-loading (days ~5–12 — the
caregiver/co-presence window; CG_OFF at 1e9 removes the early hump,
0.902→0.579) AND harder quarantine-tail suppression (D4's read).
**D4 measured (addendum 2026-10-04):** the during-quarantine tail is
~92–96% the crew exemption — SOP017_ALLHANDS collapses
`infections_during_window` med 678→27 (Θ1e6) and 730→105 (Θ7.9e6),
overshooting the record-informed band [150,350], while
`infections_before_quarantine` is bit-identical seed-for-seed; the
residual is a confined-cabin channel still ~52–61% crew. Verdict
CONFINEMENT-CHANNEL; the tail fix is channel placement, not amplitude
(`docs/covid/covid_quar_suppression_v1_readout.md`, 80/80 cells at
`6ea3093d`).

Before that — `CG-FLOOR-01`, measured at `3eae8a2f` (`docs/ledger/CG-FLOOR-01.md`,
`docs/covid/covid_cg_floor_v1_readout.md`): the R2 factor-box corner
probe — {Θ1e6, Θ7.9e6} × {`D0_declared`, `CG_LOW`} × 20 seeds, 80/80
cells, 0 audit failures, D0 rows bit-identical to the floor/bracket
cells. **DELIVERY-STRUCTURAL**: seed-paired deltas at the declared dose
floor (`tending_copresence_multiplier` 1.5, `tending_hours_per_day`
2.0) are median-zero on every scored leg, and the caregiver
aboard-window tally is unmoved (105→104, 138→135). The clause's
disjoint leg map is not reachable by detuning the declared dose
constants — the suspect narrows to the mechanism's
designation/discovery shape (`tending_response_probability`,
`tending_report_probability`, the existence of a days-0–4 designation)
or to where the clause is scored. The chain is now θ-shaped? no →
anchor-shaped? no → factor-shaped? no → **structure-shaped**.

Before that — `ANCHOR-DERIVE-01`, closed at `ed7925f3`
(`docs/ledger/ANCHOR-DERIVE-01.md`,
`docs/covid/covid_anchor_derivation_v1.md`): verdict (b) — the 197/0.173
clause targets are measured-direct record quantities
(mechanism-independent), so the clause legitimately fails under shipped
defaults; suspect moved to the mechanism's pre-quarantine delivery
strength (pooled aboard-window 105–248 monotone in Θ,
during-quarantine 0 structural).

Before that — `THETA-REFIT-01` floor falsifier + bracket refine, measured at `8f49652f`
/`8f926382` (`docs/ledger/THETA-REFIT-01.md` addendum,
`docs/covid/covid_theta_refit_floor_v1_readout.md`,
`docs/covid/covid_theta_refit_bracket_v1_readout.md`): the downward closure
of the shipped-default Θ lattice — 120/120 cells, 0 audit failures. The
Θ1e6 floor row **falsified the projected mechanism-shaped count floor**:
the count leg passes there ([149, 760] ∋ 197, `mass_near_197` 0.474)
while the timing leg fails below-side (before_share 0.051 < 0.073).
The five interior rows then certified **WINDOW-EMPTY-ORDERED**: the
count-leg crossing θ_c ∈ (1e6, 1.4e6) sits *below* the timing-leg
crossing θ_t ∈ (5.62e6, 7.9e6) — the legs' admissible half-planes are
disjoint, so the v11 clause passes nowhere on [1e6, 1e9] under shipped
defaults (15 measured rows, ~3 decades). The residual is refined to
**clause-shaped**: the two legs demand mutually exclusive transmission
rates, and the open question is the anchor itself under CAREGIVER-V1
(the 197 figure, the 0.173 share, the takeoff-conditional scoring).

Before that — `THETA-REFIT-01` lattice, measured at `78f52a58`
(`docs/ledger/THETA-REFIT-01.md`,
`docs/covid/covid_theta_refit_v1_readout.md`): the shipped-default Θ refit
— 9-row quarter-decade lattice on [1e7, 1e9] × 20 seeds, 180/180 cells, 0
audit failures. **NO-ADMISSIBLE**: every row fails the count leg on the
same side (takeoff q05 ≥ 523 > 197 at every Θ, recorded medians floored
at ~700 even at 1e7) — the boundary projection read mechanism-shaped;
the floor falsifier above refined it to clause-shaped. No admissible Θ
exists for the v11 clause under CAREGIVER-V1. The Θ1e9
row is bit-identical to the attribution D0 row and vs CG_OFF reproduces
the +698/+0.329 fill-in exactly. The open follow-up moves off Θ onto the
clause/anchor itself under the mechanism.

Before that — `CAREGIVER-ATTR-01`, measured at `b932d0e9` (`docs/ledger/CAREGIVER-ATTR-01.md`,
`docs/covid/covid_caregiver_off_v1_readout.md`): the Θ1e9 anchor-drift
attribution — 40/40 cells, 0 audit failures. `caregiver.mode: off` on the
propensity-off tree restores the v15 clause pass (takeoff 11/20, q05 10,
band ∋197, before_share 0.200); seed-paired CG_OFF − v15 = −46 median
onsets, so the drift measured at PROP_OFF in #868 (+1,634 median, takeoff
10→20) is the CAREGIVER-V1 channel. The D0_declared replication arm is
bit-identical to the `e0d43979` canary on all 20 seeds.

Before that — `QUAR-ATTR-V2`, measured at `d62f10d` (`docs/ledger/QUAR-ATTR-V2.md`,
`docs/covid/covid_quarantine_attribution_v2_readout.md`): the same 240 cells
re-run post-REINFECT-01. On the now-valid frozen criterion at Θ 1e9, crew
confinement (−74%, n = 12) and pool-transport removal (−66%, n = 8) are each
load-bearing, near-field air is not (+19%, n = 8); the combined arm (−50%,
n = 7) also suppresses takeoff 12 → 8. Nothing decidable at Θ 1e5 (3/20
takeoff). `infections_during_quarantine == ledger_events_during` in 240/240
cells. The v1 reading (`861a0b9`, `docs/ledger/QUAR-ATTR-V1.md`) that no
channel is load-bearing is superseded — its measure counted second
episodes; its post-hoc ledger shifts are confirmed. Removing all shared air
still collapses takeoff (0/20, 1/20). Conditional-on-takeoff attack rate is
0.79–0.90 across A0–A4 at 1e9 (A1 0.824 vs A0 0.865; A2/A4 move the all-seed
AR by suppressing takeoff, not the taken-off voyage). No Θ is
fitted; A1–A5 score no anchor. Successor prompt for the Θ re-screen:
`docs/covid/covid_theta_handoff_2026_09_19.md` §16.

Before that — `AERO-NEAR-02`, measured at `7d8b0d2` (`docs/ledger/AERO-NEAR-02.md`): seed
`20200206`, Θ = 3.16e7 — 2 infections (extinction); seed `20200210`, Θ = 1e9 —
1,390 infections (37.5%), 952 of them in the two crew messes after 5 Feb, 303
in confined passengers, Windjammer 0. One crew-mess epoch (242 occupants, 2
shedders) infected 140 hosts at one identical far-field dose: the roomful-at-once
behaviour is now the well-mixed far field on identical hosts, not the near
field or the dining topology.

Prior to that — local burning cell, seed `20200206`, Θ = 3.16e7, full voyage, after
`AERO-CABIN-06` (#591): 2,759 infection events, 2,732 distinct hosts infected,
final attack 73.6%; HVAC-route infections in confined cabin hosts 32 (was 1,591
before `AERO-CABIN-04`). Six-seed probe at the same Θ: 3, 2,759, 2,011, 1, 4,
2,009 — still extinction-or-burn; at Θ = 1e9 two intermediate cells appear
(48 and 347). Change-detector cell: CPython 3.12 `(105, 51, 217, 118, 20)`.

## 3. Outstanding

- **`COVID-HAND-AB-01` (v14) is the declared Diamond Princess re-approach
  under the repaired hand line — three designs, one gate.** The hand
  reservoir gained practice variability + drying under PR #804
  (`NORO-HAND-PRACTICE-01`, merged `d0466064`), then the wash-resistant
  protected compartment + own-environment pool under PR #811
  (`NORO-HAND-CARRIAGE-01`, merged `1c94de2d`; `hygiene_cycle` shipped
  default-ON throughout, `wash_reuptake`/`spike_decay` labelled
  baselines). The re-approach ladder: (1) `covid_hand_ab_v1` — the 60-cell
  canary, declared replay at Θ 2.37e11 × 3 arms (hygiene_cycle baseline,
  wash_reuptake = RESERVOIR-01 marginal, spike_decay = v13-era marginal)
  × 20 seeds @20200205, scored on per-seed recorded_onsets/infections_total
  /before_share, takeoff q05–q95 vs the 197/0.173 record, route
  re-split and during-quarantine share, plus seed-paired arm deltas —
  its readout is `tools/covid_hand_ab_readout.py` and it doubles as the
  stage-2 campaign canary; (2) `covid_theta_screen_v14` — the verbatim
  stage-1 lattice (9 Θ eighth-decade × 200 seeds @20201001 generic
  voyages) × 2 arms (hygiene_cycle vs spike_decay, so every row pairs
  against the v13-era physics bit-comparably), 3,600 cells, with a
  120-cell arm-bracket verification gate (arm pairing off by one index
  would silently re-lattice the screen); (3) `covid_theta_screen_v14_
  stage2` — the verbatim stage-2 declared replay (10 points × 20 seeds
  @20200205, 768 epochs), gated on the stage-1 surface. Design files
  under `picard_framework/runs/`; cells are auditable by
  `delivery.hand_reservoir_mode` echo and the `arm` column now carried
  by `tools/covid_theta_screen_csv.py` (parent-cell pairing stays keyed
  on (theta, age, seed) so armed rows still pair to armless v13 cells).
  **The `covid_hand_ab_v1` canary is measured (60/60 cells at
  `1c94de2d`, `docs/ledger/COVID-HAND-AB-01.md`,
  `docs/covid/covid_hand_ab_v1_readout.md`): verdict
  `hand_line_replay_neutral`** — all arms burn ~96% attack, the two
  baselines are byte-identical on this scenario (their contrast lives
  on the stool-event path the COVID arm never exercises), every arm
  delta sits inside the stream-reorder band, and pooled
  during-quarantine routes show fomite = 0 on all 60 cells — the hand
  reservoir is not the during-quarantine carrier on this hull. Stage-1
  decision resolved to **single-arm `hygiene_cycle`, 1,800 cells** —
  the measured neutrality says the spike_decay pairing sees nothing at
  these coordinates, so the v14 stage-1 lattice ran the hygiene_cycle
  half only. **v14 stage 1 is measured (1,800/1,800 cells at
  `02740187`, zero audit/child failures): the admissible band slides
  one lattice notch down to {1.33e11 … 4.22e11}** — 1.33e11 lifts off
  the floor (0.00054 vs v13 0.00027), 5.62e11 tips over the ceiling
  (0.00808 vs 0.00781); seed-paired medians vs v13 sit at 0.0 delta
  everywhere with takeoff flips 17–30/200 — no suppression shape, no
  frozen trigger fired (`docs/ledger/COVID-THETA-V14.md`,
  `docs/covid/covid_theta_screen_v14_readout.md`). Stage 2 (declared
  replay at the admissible set + flanks {1e11, 5.62e11} + Θ1e9 anchor)
  is eligible under the frozen rule, gated on this verdict.
  **Execution state:** the array was held on the prior mechanism after
  the PRACTICE-01 `still_starved` census, then resumed on the
  `1c94de2d` image under a fresh prefix —
  `campaign/covid_hand_carriage01/` (58-child array
  `e503114d-9164-4bbb-a1f1-248156ca64b3` covering cells 0–57 — jobdef
  `:43`'s command map lacks `--index-offset` so the submitted
  `index_offset` parameter was silently dropped — plus 2-child tail
  `df330100-9cd9-42ea-b0af-55bc88b0ee56` for cells 58–59 via
  `--container-overrides`; cells 0–1 ran as the canary).
  The earlier prefix `campaign/covid_hand_ab_v1/` keeps the two
  prior-mechanism canary cells as the *recorded* baseline — labelled
  by their own `delivery.hand_reservoir_mode` echo, not voided.
- **`COVID-COOP-V1` measured the full conditioned array + fleet companion
  and stands negative: the cooperative-packet dose law does not produce
  the record at any declared point.** 480-cell conditioned lattice
  (n* {2,3,5} × carrier_loading corners + interior, θ {1e11, 2.37e11,
  1e12}, seeds 20200205–14, 480/480) + 2400-cell fleet-shape companion
  (2400/2400), measured at `a2586422` (`docs/ledger/COVID-COOP-03.md`,
  design `picard_framework/runs/covid_coop_v1_design.json`, Batch
  job-def rev 32, image digest `sha256:316b27ee…`). Every scored row
  (≥5 takeoff seeds) fails the count leg — suppression floor ~3× the
  record (lowest scored median 647); the under-scored n5_{dry:lo}
  corners bracket the count at the anchor (n5_lolo s20200208 = 194,
  n5_hilo = 218 on the same seed) but at n = 2/10 takeoffs and
  before_share .07–.08 vs the record's .173 — the law's suppression
  delays onsets past the split day, so count and timing legs are
  structurally opposed, and the same corners collapse fleet takeoff to
  0/50 at every θ. Mechanism fires as designed (n*-graded suppression,
  nonmonotone wet-loading peak, bolus untouched) but is **retired as an
  explanation of the 197/0.173 record**; standing suspects stay the
  fixed ring structure, index day-0 exposure geometry, and the
  observational channel (ROUTE-ATTR-V1). Complete-virion bound and
  stage-2 refinement both ruled out by the opposed legs.
- **`AERO-SPLIT-01` shipped and its paired-seed probe is measured
  (`docs/ledger/AERO-SPLIT-01.md`, `e20008d`).** `transmission.droplet_field_split`
  defaults to `partition` (spec `docs/droplet_field_split_spec.md`): the room
  pool carries `far_field_share` = 0.175 of continuous droplet emission
  (declared interval [0.05, 0.30], Grade C, swept-never-fitted) and the near
  share reaches only a partner-bounded proximity ring at the AERO-NEAR-02
  plume concentration. On the takeoff seed the early spike survives
  (3574 -> 3561 events, day-0–2 68.7% -> 57.1%) — the plume's per-partner
  concentration keeps each ring infection near-certain, so ~2 partners/h
  still branches at this Θ; on the non-takeoff seed the sustained phase
  halves (3548 -> 1675) and the residual concentrates in the crew messes
  and confinement exposure. Follow-on work, in order: re-run the
  declared replay at the fleet-admissible Θs (done — `THETA-SCREEN-V12`
  stage 2, `f42901aa`: saturates at ~3,400–3,570 recorded onsets at all
  five fleet-admissible Θs), re-run `covid_sensitivity_assay_v2`
  (it was stood down for this change), and a declared `far_field_share`
  sweep over [0.05, 0.30] — none of it fitted to 197.
- **`PARTNER-RATE-V1` measured its canary arm and stood down: the ring is not
  reach-limited.** At `rates_per_hour` ×0.25 (the bottom of the declared
  sweep), all 20 takeoff seeds still record 1,275–3,525 onsets (q05 2,457 /
  median 3,474 / q95 3,518) vs the record's 197 — inside the partition tree's
  shipped-rate band (~3,470–3,520, cross-campaign contrast). The assay's
  declared counterfactual fired: four times fewer partner draws does not move
  the conditional mass, so the ~18× gap is bounded by per-partner plume dose
  (β) or the ring's definition, not by reach. The response-curve arms (R0,
  R2–R7, R8 witness, 160 cells) are unmeasured and stood down; reopening is a
  new decision (`docs/ledger/PARTNER-RATE-V1.md`,
  `docs/covid/covid_partner_rate_assay_v1_readout.md`, measured at `37dc215`,
  Batch job-def rev 19, image digest `sha256:7528dcd1…`).
- **`PLUME-DOSE-V1` measured its full array and stands negative on both
  axes: the conditional gap is not borne on the sampled proximity ring at
  all.** The dose sweep (β {4080, 2040, 816, 408} = dose ×{0.05–0.50} under
  the partition's 1/β scaling, D0 shipped β 204) leaves conditional recorded
  mass flat at medians 3,435–3,486 across the 20× range (log-log elasticity
  0.004); no arm's q05–q95 contains 197 anywhere on the grid — no dose-only
  closure scale exists — and the takeoff gate never collapses (lowest dose
  still 19/20). The four per-activity ring knockouts (dining, work,
  cabin+corridor, leisure) are equally flat (medians 3,441–3,492, 20/20
  takeoff each): no single sampled venue's ring is load-bearing, and the
  pool witness (3,517 vs D0 3,486) says the partition architecture itself
  is not the carrier. Per the design's declared counterfactual the standing
  suspects are, in order, the **fixed ring structure** (cabin-mate and
  meal-table rings that survive every knockout), the **seeded index's
  day-0 exposure geometry**, and the **observational channel** — consistent
  with before_share ~0.95 vs the record's 0.173 (most recorded mass is
  pre-quarantine burn the record never dated as onsets). Next assay, if
  pursued: knock out the fixed rings or interrogate onset-dating — the
  sampled-ring grammar is exhausted. 200/200 cells, 0% failures
  (`docs/ledger/PLUME-DOSE-V1.md`,
  `docs/covid/covid_plume_dose_assay_v1_readout.md`, measured at `2bcdeb7`,
  Batch job-def rev 20, image digest `sha256:aca8d6b8…`).
- **`ROUTE-ATTR-V1` measured the whole-voyage routes and the observation
  channel on the declared replay.** `tools/covid_route_attribution.py`
  attributes every infection event (not just the during-quarantine slice):
  the saturating seed burns 99.8% pre-quarantine, 90% droplet, in `other`
  venues + crew mess; the slow seeds re-centre during quarantine on cabin
  zones — the confinement channel. The droplet dose reaching infected
  agents is ~98% ring-side (near-field plume 60–69%, cabin-mate addback
  30–40%, far-field pool ~2%), bimodal per-agent — both channels sit above
  the infection threshold for most hosts, which is why every sampled-ring
  knob measured flat. The observation channel confirms ~76% of infected and
  dates 93–100% of confirmed datable-course cases at exact onset — vs the
  record's 197 of ~712 (0.28); 85–89% of the dated mass is mild, the
  stratum a real investigation dates worst. Dating ascertainment alone is
  ~3.4× of the ~18× gap. Remaining declared suspects: the cabin-mate
  addback / fixed rings (now the largest measured channel, ~⅓ of dose
  weight, inexpressible in the current arm grammar), the index's day-0
  exposure geometry, and an ascertainment arm that would split channel vs
  transmission shares of the gap
  (`docs/ledger/ROUTE-ATTR-V1.md`,
  `docs/covid/covid_route_attribution_v1_readout.md`, measured at
  `be121a0` locally on CPython 3.12).
- **`LAMBDA-CROSS-V1` is measured (140 cells, `8649d31`): the hazard-rate
  scale binds the gap but cannot close it alone.** The Θ sweep
  ({1.0 … 0.001} × 4.22e10, 20 seeds) bends the conditional recorded
  median 3,486 → 624 over three decades — log-log elasticity **0.216**
  vs the dose axis's flat 0.004 — and re-centres the burn into the
  quarantine window (median before_share 0.646 → 0.084, crossing the
  record's 0.173 near θ ×0.01). The response is a shallow bend plus
  bimodal extinction (takeoff 20 → 8 of 20), not the hypothesized λ ≫ 1
  sigmoid: per-challenge λ was already tiny, so Θ works through
  aggregate challenge volume and cascade survival. Rows θ ×0.03, ×0.01,
  ×0.001 satisfy the conditional clause (band ∋ 197 + before_share
  within 0.10 of 0.173) — the first rows to do so — but no row
  closes_the_gap: every conditional median stays above [98.5, 394].
  Verdict `lambda_bound_but_short`: the residual lives in seed/index
  structure or the observational channel
  (`docs/ledger/LAMBDA-CROSS-V1.md`,
  `docs/covid/covid_lambda_cross_v1_readout.md`,
  `picard_framework/runs/covid_lambda_cross_v1_design.json`).
- **The import x Theta axis is closed as negative, and the confinement leak is
  the live defect (COVID-VENT-AUDIT-01, `#645`).** `COVID-FIT-01` (`a686114`,
  1,180 cells) already swept imports 1-20: matching the early onset count
  overshoots the voyage total by 3-6x on every Theta row, and imports > 1 is not
  licensed by the record (Sekizuka 2020, single introduction before quarantine).
  The audit adds the anchor this arm never carried — DP's effective reproduction
  number **0.1 (SD 0.2) after** quarantine against 3.8 (SD 0.9) before (Azimi
  2021, grade B) — so the target is a sourced decay, not arrest. It also records
  that `hvac.filter_efficiency` = 0.50 is unsourced and its era-correct value
  (0.30) *increases* during-quarantine transport by 1.4x, and that
  `confinement_isolation_factor` 0.05, `corridor_direct_contact_factor` 0.15 and
  `NON_MATE_CONFINEMENT_CONTACT_FACTOR` 0.01 are unlabelled literals that govern
  the whole during-quarantine regime. `#645` adds the graded
  `hvac.outdoor_air_fraction_override` (absent by default) so the recirculation
  channel QUAR-ATTR-V2 measured at -66% can be evaluated between "as shipped"
  and "off"; the paired-seed bracket itself is **not run**
  (`docs/ledger/COVID-VENT-AUDIT-01.md`,
  `docs/covid/covid_dp_ventilation_sourcing.md`).
- **Missing intermediate attack rates.** The route trace (QUAR-ORDER-01,
  AERO-NEAR-02) placed the burn in public dining, not in a leak through
  confinement. With enforced quarantine and dining tables in place, what
  remains is the well-mixed venue far field clearing threshold for a roomful
  of hosts whose susceptibilities now differ (DOSE-FRAIL-01). No constant is to
  be moved to produce a 19% attack rate.
- **Crew-mess seating structure.** Crew-mess tables are now dealt within
  department (DINE-CREW-01), while the venue far-field pool is unchanged.
  AERO-NEAR-02 figures are pending remeasurement
  (`docs/ledger/DINE-CREW-01.md`).
- **Windjammer 100× pool-mass jump at 1 → 2 shedders** (QUAR-ORDER-01 trace):
  the trajectory did not recur under AERO-NEAR-02; mechanism untraced.
- **Incubation dose reference on the Θ arm.** Host frailty is restored
  (DOSE-FRAIL-01), but `dose_reference_log10` is referenced to the mean host,
  `ln 2 / Θ`. `Beta(0.18, 58)` is strongly right-skewed, so the median host sits
  well below the mean; whether the reference belongs at the mean, the median, or
  the realised infecting dose is unresolved.
- ~~**795 repeat infection events at Θ = 1e9.** Hosts re-enter the susceptible
  pool; lifecycle not yet traced.~~ Traced: REINFECT-01 (§1). The open
  decision is whether to fix it before any further COVID campaign
  (`docs/ledger/QUAR-ATTR-V1.md`).
- **Index-case geometry.** Declared per-agent departure shipped
  (INDEX-GEOM-01): the index disembarks on day 5 per Yamagishi 2020. The
  resolved infection-age × Θ screen has now run (THETA-V7-01, below) and
  exposed the remaining half, which SEED-ONSET-01 then closed: the seed
  channel can now declare the index's *observed onset date* (onset day
  −1, grade A), making the implied incubation a consequence of the record
  rather than a free draw.
- **`covid_theta_screen_v7` ran; the admissible region is empty.** The
  pre-registered Θ × infection-age screen on the repaired arm (host frailty
  restored, index departing day 5;
  `picard_framework/runs/covid_theta_screen_v7_design.json`, 11 half-decade
  Thetas × 7 ages × 40 seeds) completed 3,080/3,080 cells with zero failures at
  `main` = `e32272d`. **No Θ is admissible**: zero of 77 cells satisfy index
  geometry, covid.T1 and covid.T3 jointly, and none satisfy geometry and T1
  together at any Θ (`docs/ledger/THETA-V7-01.md`,
  `docs/covid/covid_theta_screen_v7_readout.md`). Outstanding from it
  (geometry rows superseded by SEED-ONSET-01, which makes the onset day
  declared rather than drawn — every `index_geometry_pass_fraction` on the
  v7 surface is an artifact of the free incubation draw and is void, so the
  empty admissible region is not a statement about Θ):
  - ~~the explicit-seed channel cannot declare the index's observed onset
    date~~ — fixed by SEED-ONSET-01: `ExplicitSeed.onset_day` stamps the
    declared onset and the symptomatic history directly;
  - the asymptomatic share caps at 0.43 median anywhere on the surface and falls
    with Θ, against covid.T4 0.50 and held-out covid.H2 0.81 — it is emergent
    from delivered dose rather than a natural-history parameter;
  - covid.T3 is non-discriminating on this hull (specimens saturate at
    ~1,600–3,063 across five decades of Θ) and must not carry selection weight
    in a successor design;
  - Θ 3.16e7–3.16e9 at index ages 0–5 d remains the nearest region as a
    fleet-shape observation — eleven cells passing covid.T1 (four of them
    covid.T3), reproducing DP-sized takeoffs and the covid.H3 fleet shape —
    but its geometry pass fractions are void with the others; under a
    declared onset the gate is satisfied by construction at the record's
    geometry.
  Stages 2–3 of the design are gated on a non-empty shortlist and were not run.
- **`covid_theta_screen_v8` is declared and not yet run.** The successor screen
  re-screens the Θ 3.16e7–3.16e9 corner (seven half-decade Θ from 1e7 to 1e10 ×
  six index infection ages × 40 matched seeds = 1,680 cells) with the index
  geometry true by construction under SEED-ONSET-01, `covid.T1` as the sole
  selection criterion verbatim from v7, and covid.T3 demoted to a diagnostic on
  v7's own saturation evidence
  (`picard_framework/runs/covid_theta_screen_v8_design.json`,
  `docs/ledger/THETA-SCREEN-V8.md`). Three probe cells at `main` = `4721b5b`
  confirm the invariant end-to-end (`index_onset_day == -1.0`,
  `index_shedding_at_day0` true, departure at epoch 120 in all three), **and say
  the grid is mis-centred**: every probe burns the ship (2,843–3,099 recorded
  onsets of 3,711 against covid.T1's 197) including the Θ 1e7 floor, consistent
  with v7's 40-seed cells wherever its index was in fact symptomatic aboard
  (median attack 0.709 at Θ 1e7, age 11 d). The v8 array should therefore **not**
  be submitted as declared; an admissible Θ, if one exists, lies below 1e7, where
  no screen has been, and the successor should declare a coarse wide downward
  recentring screen first with covid.T1 and the geometry invariant verbatim.
- **`covid_theta_screen_v9` is declared and supersedes v8, which was never
  submitted.** The successor re-centres on the quiet region v8's probes missed:
  ten decade Θ from 1e1 to 1e10 × three index infection ages (3.3 / 6.8 /
  12.8 d) × 20 matched seeds = 600 cells, with covid.T1 and the geometry
  invariant verbatim plus a reported-only `onset_mass_near_target` diagnostic
  (share of seeds inside [0.5×, 2×] the T1 onsets target) that separates a real
  hit from the v7 bimodal pass
  (`picard_framework/runs/covid_theta_screen_v9_design.json`,
  `docs/ledger/THETA-SCREEN-V9.md`).
- **`covid_theta_screen_v9` ran (600/600 at `main` = `0fb186b`); the
  infection-age axis is inert and the one covid.T1 pass is vacuous.**
  Measured (`docs/ledger/THETA-SCREEN-V9.md`,
  `docs/covid/covid_theta_screen_v9_readout.md`): (i) every (Θ, seed) payload is
  byte-identical across the three declared ages — with `onset_day` declared,
  `_apply_one_seed` sets incubation = age + onset_day − seed_day and stamps the
  history from `elapsed_since_onset`, so the age cancels exactly. **Every
  infection-age contrast on `diamond_princess_2020` under a declared
  `onset_day` is void**, including the age axes of v8 (never run) and v9; v9 is
  a 10-Θ × 20-seed locator. (ii) Under covid.T1 verbatim the admissible set is
  {Θ = 1e9}, interior, but it passes by its p10–p90 interval spanning 197 from
  8 extinct seeds to 12 burning seeds; `onset_mass_near_target` = 0.00 there
  and ≤ 0.10 everywhere. (iii) Θ sets the takeoff probability (0 at ≤ 1e3 →
  0.85 at 1e10), not the outbreak size (conditional-on-takeoff median onsets
  1,582–3,391 from 1e6 up); there is no near-critical band in [1e1, 1e10] for
  one declared import. **Θ = 1e9 may not be quoted as a fit or a selected
  value.** The pre-committed stage 1b (half-decade, 40-seed, six-age
  refinement) is withdrawn as a plan; the open decision is the criterion
  (trajectory under T1 with import geometry as the next axis, vs takeoff
  probability against covid.H3 with onsets scored conditional on takeoff),
  to be declared in a v10 design file before any cell runs.
- **covid.T1 as declared is satisfiable without mass near the target.** All
  eleven T1-passing cells on the v7 surface passed by spanning 197 between an
  extinction floor (`recorded_onsets_p10` = 0) and a burn ceiling (p90 316 to
  3,405), with attack q50 = 0.0000 in seven of them. No criterion is rewritten on
  that basis here: readouts must report the per-seed distribution beside the
  interval, and any tightening must be declared in a design file before its cells
  run. Session state of play, including what may not be reopened:
  `docs/covid/covid_theta_handoff_2026_09_19.md`.
- **`covid_theta_screen_v10` is fully measured — 200 of 200 cells — and the
  whole v9 Θ surface survives the repaired engine unchanged.** Measured at
  `main` = `a9b4f1f` on AWS Batch (`docs/ledger/THETA-SCREEN-V10.md`,
  `docs/covid/covid_theta_screen_v10_readout.md` §6): 200/200 children
  succeeded; takeoff fraction identical to v9 at every decade (0 at ≤ 1e3,
  0.10 / 0.15 / 0.10 / 0.20 / 0.35 / 0.60 / 0.90 at 1e4–1e10); **no seed of
  200 changes takeoff class**; `onset_mass_near_target` identical on every
  row; `infections_total` byte-identical to v9 on 154/200 cells including
  every extinct seed but one; `covid.T1` passes only at 1e9 in both. **Every
  v9 row is confirmed on the repaired engine, and the v10 surface CSV
  (`docs/covid/covid_theta_screen_v10_surface.csv`) supersedes the v9 CSV as
  the surface of record.** The v9 structural readings above —
  extinction-or-burn at every decade, Θ moving takeoff probability rather
  than size, no near-critical band — now stand at `a9b4f1f`, not `0fb186b`.
  The canary detail follows. Canary (Θ 1e9 × 20 seeds): the
  shared seed 20200205 reproduces the QUAR-ATTR-V2 `A0_declared` record exactly
  (3458 / 0.9318), takeoff is 0.60 on the same twelve seeds as v9 with
  `infections_total` moving ≤ 2.1% on any takeoff seed and identically zero on
  the eight extinct ones, and the conditional median attack rate is 0.865 in
  both. So QUAR-EXEMPT-01 and REINFECT-01 together do **not** move this row:
  consistent with the reinfection inflation having lived in the
  quarantine-window counts, which the screen payload never carried. Θ 1e9
  still may not be quoted as a fit. The `covid.T3` verdict on this row flips
  fail → pass on the same bimodal interval-span mechanism as covid.T1 and
  changes nothing. The screen payload has no episode or quarantine-window
  fields, so this campaign does not re-read those gates. Next decision (the
  criterion declaration): `docs/covid/covid_theta_handoff_2026_09_21.md` §8.
- **`covid_theta_screen_v11` stage 1 has run: empty admissible set on the
  decade lattice; the covid.H3 window is bracketed between Θ 1e10 and
  1e11** (`7660392`, array `33482fcc-7954-4566-928d-7052d62b83ee`,
  1,600/1,600 cells; readout
  `docs/covid/covid_theta_screen_v11_readout.md`, ledger
  `docs/ledger/THETA-SCREEN-V11.md`). Unconditional covid.T1 is measured
  vacuous (interval-span at 1e9, `onset_mass_near_target` 0.00), so the
  v10 `stage_2_fleet_shape` block is the stage-1 selector on generic 7-day
  voyages (8 decade Θ, 1e4–1e11, × 200 voyages, seed base 20201001);
  P(takeoff) climbs 0.00 → 0.575 and the recorded-attack median jumps
  0.0003 → 0.0158 across the last decade, straddling the H3 window
  [0.0005, 0.008] without a lattice point inside it — nearest cells 1e10
  (median misses floor 1.85×) and 1e11 (median/mean overshoot). Per the
  design, stage 2 does not run and the conditional read is quoted from v10
  (1,582–3,391 vs 197); generic takeoffs independently give DP-order
  recorded mass (median 175 at 1e10) in a 7-day voyage. **covid.H3 stays
  out of the held-out set for this screen**; covid.H1/H2 on
  `greg_mortimer_2020` remain held out (gated stage 3). In-flight
  user-approved amendment (#655): generic mode drops the DP's
  `molecular_ascertainment.start_day` — the day-14 historical testing
  start — so the recorded channel is live on generic voyages; the declared
  replay keeps it. The interior refinement
  `covid_theta_screen_v11_refine` ran at eighth-decade spacing
  ({1.33…7.5}e10 × 200 seeds, `79a3ac3`, array
  `45cfb31d-eb50-4042-9d6d-17499d9a3934`, 1,400/1,400 cells): **the
  stage-1 admissible set is non-empty — Θ ∈ {3.16e10, 4.22e10,
  5.62e10}**, an interior band ~0.25 decades wide (median-floor failures
  below, median+mean overshoot at 7.5e10). Stage 2 then ran
  (`covid_theta_screen_v11_stage2`, `8cda4c7`, 100/100 cells): **the
  conditional clause fails at every row — takeoff-seed recorded_onsets
  ~3,470–3,520 vs the record's 197 (~17.7×), onset-mass-near-target
  0.00, before_share 0.77–0.92 vs 0.173 — so the admissible set is
  empty** and the screen's question is answered: a Θ reproducing the
  covid.H3 fleet shape exists but cannot keep a conditioned declared
  voyage near the record; the deficit is conditional outbreak size (the
  during-quarantine arrest gap of COVID-VENT-AUDIT-01), not takeoff.
  Stage 3 does not run (nothing selected). Readouts
  `docs/covid/covid_theta_screen_v11_refine_readout.md` and
  `docs/covid/covid_theta_screen_v11_stage2_readout.md`, ledgers
  `docs/ledger/THETA-SCREEN-V11-REFINE.md` and
  `docs/ledger/THETA-SCREEN-V11-S2.md`.
- **`covid_sensitivity_assay_v1` is measured — all arms inert except the
  all-shared-air bound, which collapses takeoff**: 240/240 cells at
  `b88e0ad` (canary A0 + A11, array
  `f3065d9e-a605-456d-86b6-b097bbb7ac43`). On the frozen paired-seed
  metric every arm moves the conditional recorded-onset median <20%
  (largest mover: A11 arrest bound, −17.4% → 2,868 vs the record's 197)
  except `A5_all_shared_air_off` (3/20 takeoff → `takeoff_collapse`) —
  so the ~18× gap is measured unreachable inside the transmission layer
  and lives in the observational channel or natural history, per the
  declared decomposition (~4.7× over-burn × ~3.5× dated-onset
  bookkeeping). Structural finding: ~89% of recorded mass lands before
  the day-17 split (median 3,509 before vs 53 during), and the VSP-3%
  counter already confines ~87% of the ship by day 12 — the residual
  burn rides the unconfineable channels (cabin-mate full-dose addback,
  shared-corridor air, presymptomatic shedding). A10 first-report
  confinement was vacuous (bit-identical to A0 on all 19 paired seeds):
  the dense report stream trips both thresholds on the same schedule —
  conundrum, not bug. Readout
  `docs/covid/covid_sensitivity_assay_v1_readout.md`, surface
  `docs/covid/covid_sensitivity_assay_v1_surface.csv`, ledger
  `docs/ledger/SENS-ASSAY-V1.md`.
- **`covid_sensitivity_assay_v2` is declared, stood down
  pre-execution** (assay-1 now measured in full): v1's A11 arrest bound still records
  ~2,868 onsets on takeoff seeds vs the record's 197 under crew
  confinement + pool off + day-12 quarantine + perfect confinement +
  contact ×0.25 — the gap is not reachable inside the transmission
  layer, so v2 interrogates the observational channel (a subclinical/
  datable-onset bookkeeping arm) and natural history / mixing reach
  (symptomatic fraction, infectious window, shedding dispersion,
  effective-susceptible pool via secretor_negative_fraction,
  activity-contacts reach and CONTACT-ARCH-02 saturation). 11 arms × the
  same 20 seeds at Θ 4.22e10, 220 cells, plus a zero-cell observational
  annex scoring the dated-onset-equivalent on v1+v2 payloads. Design
  `picard_framework/runs/covid_sensitivity_assay_v2_design.json`,
  ledger `docs/ledger/SENS-ASSAY-V2.md`. Held pending droplet
  near-field/far-field route surgery: the v1 §2a attribution showed
  ~99% of the burn rides the well-mixed-room droplet pool, which the
  reach arms (B7–B9, `activity_contacts` only) cannot bound — see the
  stood-down note in `docs/ledger/SENS-ASSAY-V2.md`.
- **`SERO-CHANNEL-V1` is declared and its canary is measured** (period
  arm, Θ ×0.001, 20 seeds at `8ac510b3`, array `f340c7b9`): the
  observational-channel arm of the ~18× hunt. A new held-out-forever
  anchor `covid.H5` (serology-informed true infections ≈ 840, admissible
  band [712, 960], Hung et al. 2020, channel `infections_total`) joins
  the split, and an additive default-off `observation_model.onset_recording`
  channel on `sars_cov2_resp` gates dated onsets to presentations at or
  before the confirming-specimen epoch, times a once-per-case recall draw
  at 0.56. Canary verdict: 7/20 takeoff; takeoff-seed infections q05–q95
  [753, 3025] intersects the band but median 1,025 sits above it;
  recorded_onsets q05–q95 [161, 1,536] contains 197 (median 315) but the
  before_share median 0.020 misses the record's 0.173 ± 0.10. The gate
  lands dating ~0.43–0.53 of confirmed — ABOVE the record's 0.277, so
  the declared recall-only fallback is not engaged; the channel under-
  closes vs the record at this theta. The 20200205 zero-asymptomatics
  anomaly did not recur (110/248 asymptomatic campaign positives).
  On the canary's 7/20 takeoff the user extended the design to 60 seeds
  per cell — 9 θ × 2 channels × 60 = 1,080 cells — and the full array
  ran clean (1,080/1080, zero audit violations, `03a9db9e`, array
  `ee429652`). **Measured verdict: the gap is unreachable on the Θ axis
  under either channel.** Takeoff-conditional infections medians are
  1,584–3,542 at every θ — always above the serology band top — while
  the period channel removes a uniform ~50% of dated mass (seed-paired
  period/declared recorded ratio 0.50–0.54 at every θ) and satisfies the
  trajectory clause at Θ ×0.005 and ×0.001 (closest recorded median 656
  vs 197). The gap factorizes as ~2× channel × ~2×+ truth overshoot the
  hazard axis cannot reach; per the declared counterfactual the suspect
  moves to seed/index structure. Design
  `picard_framework/runs/covid_sero_channel_v1_design.json`, ledger
  `docs/ledger/SERO-CHANNEL-V1.md`.
- **`ASCERTAIN-V1` is measured — the channel-vs-truth decomposition of
  the ~18× count gap is now quantified on the conditioned lattice**
  (270 cells, 9 arms over `observation_model.onset_recording` plus the
  mild-eligibility corners, θ {1e11, 2.37e11, 1e12} × seeds
  20200205–14, takeoff-conditional, measured at `cb519c97`,
  `docs/ledger/ASCERTAIN-V1.md`, job-def rev 33, image digest
  `sha256:f8f56c23…`). The channel shares are multiplicative and
  near-exact: the symptomatic-at-specimen gate is nearly non-binding
  (~0.97 of dated mass), the recall draw tracks p almost exactly
  (0.567 @0.56, 0.28 @0.28), and the mild stratum carries ~0.87 of
  dated mass — deleting it alone (M0) drops the takeoff median to
  ~2.0–2.5× the 197 record, and mild-corner × period channel
  (M0P56) lands the count at 207–270 vs 197 — inside the declared
  ~[150, 250] band at all three θ. But the landing is degenerate: it
  deletes the record's dominant mild stratum (dating rate of confirmed
  collapses to 0.072 vs 0.277), before_share stays 0.60–0.84 vs
  0.173 on every row, and infections_total medians 3,536–3,599 never
  move at any arm or θ — q05–q95 never intersects the held-out band
  [712, 960]. Frozen-grammar verdict `channel_only`: the count leg is
  ~fully observational at the declared corner (mild ≈ 7.5×, recall
  ≈ 1.8×, gate ≈ 1.03×); the residual is truth-level (~3.5–4× the
  serology band plus the timing leg ~3–5× off), reachable on neither
  the θ axis nor the ascertainment axis. Standing suspects narrow to
  seed/index structure — day-0 exposure geometry and ring membership —
  i.e. whatever can move both truth legs at once. Design
  `picard_framework/runs/covid_ascertain_v1_design.json`, ledger
  `docs/ledger/ASCERTAIN-V1.md`.
- **`SEED-GEOM-V1` is measured — index/seed structure is retired as the
  truth-gap suspect: no declared geometry moves both legs, and none
  moves the truth leg at all** (480 cells, 16 arms: onset epoch
  {−6…+6} incl. the silent-aboard P6 corner, placement {ROLE_CREW,
  ROLE_ANY, FR_IN, CREW_FR_IN}, breadth {2, 8, 30}, + D0 baseline +
  REF_M0P56 reference, θ {1e11, 2.37e11, 1e12} × seeds 20200205–14,
  480/480, 0/480 audit failures, measured at `1dfac0e4`,
  `docs/ledger/SEED-GEOM-V1.md`, job-def rev 34, image digest
  `sha256:976993cd…`). Truth leg: every takeoff row medians
  infections_total 3,461–3,612 (~93–97% of aboard) at every θ — the
  once-ignited burn is θ- and geometry-invariant; breadth scaled the
  index's aboard-window acquisitions ~1,000× (3 → 2,991 at CP30) for
  ~0× truth change — the NORO-GENO-02 saturation shape on covid.
  Timing leg: exactly one row median lands in 0.173±0.10
  (FR_IN@anchor 0.205) but seed-paired Δ ≈ 0 — takeoff-set
  composition, not a per-seed shift; 0.173 sits inside D0's own
  cross-seed spread. Count leg: every non-channel takeoff row medians
  1,523–3,590 (REF_M0P56 reproduces 215/234/270 by θ as designed). Closest
  single cell: FR_IN@1e11 s20200207 = 178 recorded / 932 infected —
  inside the band, before_share 0.000, one seed only. Verdict
  `geometry_incapable`: all four suspect axes now measured as unable
  to reach the truth band; the residual is structural — on ignition
  ~96% of aboard burns. Surviving suspect classes: susceptibility /
  effective-population structure (the band ≈ 19–26% of 3,710 aboard)
  or mid-voyage suppression dynamics — not further seed tuning.
  Design `picard_framework/runs/covid_seed_geom_v1_design.json`,
  ledger `docs/ledger/SEED-GEOM-V1.md`.
- **Record-side cooling bound quantified** — the real outbreak ramped
  ~1.2×/day (R₀ lit. 2.28–4.73 at serial interval 5–6 d; infection
  incidence peaked Feb 2–4, AT confinement) vs the model's measured
  ~1.8×/day median ramp; but rate alone cannot land 19–26% attack
  (homogeneous R 2–4 → 80–98% final size), so the record needs a
  susceptibility ceiling (~0.24 ± 0.07 effective share →
  `immune_fraction` ~0.70–0.80) or mid-growth truncation (pooled-route
  force ~×0.12–0.25) or a mix — discriminating observables enumerated
  in `docs/covid/dp_growth_cooling_bound.md`.

- **`SUSCEPT-V1` is measured — susceptibility/effective-population
  structure is retired for the joint record: immune depth reaches the
  serology band only at the 0.75 corner, where it still fails the
  timing and count legs and fizzles half its seeds** (480/480 cells, 16 arms: immune depth {0.10, 0.25, 0.50, 0.75}, placement
  corners IMM25_C0/IMM25_C90/IMM0_C90, frailty α {0.05, 1.0, 2.0} at
  Θ-preserved susceptibility_scale, cap corners CAP_OFF/CAP_FR +
  IMM50_CAPOFF/FRAIL_A05_CAPOFF, + D0_declared + REF_M0P56, θ {1e11,
  2.37e11, 1e12} × seeds 20200205–14, 0/480 audit failures, measured
  at `2e12ccf1`, `docs/ledger/SUSCEPT-V1.md`, job-def rev 36, image
  digest `sha256:966eb54b…`). Truth leg: IMM75 lands takeoff infections
  median 869/877/884 at all three θ — θ-invariant ~24% of aboard —
  the only declared lever in the band; elasticity below it is
  sub-linear (IMM10 ~3,200 → IMM50 ~1,750). Timing leg: IMM75's
  before_share stays 0.90–0.96; the lone TIMING-in-band median
  (CAP_FR@anchor 0.205) is takeoff-set composition on paired seeds.
  Placement carries real mixing (crew-90% at 25% mass cuts truth to
  ~2,000 vs ~2,900 passenger-only) but cannot reach the band alone;
  FRAIL_A05 thins ~1.6–3.6× to ~2,100–2,370, still ~2.5× over the
  band ceiling; cap corners move nothing. Shape leg: no row is
  during-dominant or kinked — IMM75 reads smooth-thinned (kink 0.11–
  0.14 ≈ baseline 0.15–0.27, pooled during stratum 45/5 seeds, no
  cabin/confined concentration). Verdict
  `susceptibility_structure_incapable`: the serology band is reachable
  only by brute sterilizing depth, which cannot also produce the
  0.173 onset split — surviving suspect class is mid-voyage
  suppression dynamics with an earlier/other signature than SOP-017,
  or a combined-structure hypothesis (frailty tail × partial
  protection — non-sterilizing immunity was not on this lattice).
  Design `picard_framework/runs/covid_suscept_v1_design.json`,
  ledger `docs/ledger/SUSCEPT-V1.md`.
- **`HEAT-V1` is measured — pooled-route delivery machinery is retired
  as the truth-gap suspect: `delivery_incapable`** (660 cells, 22
  arms: half-life {0.5, 1.1, 2.0, 4.0}h, droplet/hvac/joint
  efficiency ×{0.5, 0.25, 0.1}, exposure-cap corners {OFF, POLY,
  ACT_HALF, FR, ACT_HALF_FR}, pool transport {none}, the persistence ×
  efficiency corner, + D0 + REF_M0P56, θ {1e11, 2.37e11, 1e12} ×
  seeds 20200205–14, 660/660, 0/660 audit failures, measured at
  `98d0edd2`, `docs/ledger/HEAT-V1.md`, job-def rev 37, image digest
  `sha256:4143ba7c…60d9`). Truth leg: every takeoff row medians
  3,044–3,611; the coldest declared corner (joint ×0.1 + 0.5h) buys
  only ~230 infections seed-paired at the best θ — ×0.1 pooled-route
  efficiency removes <7% of the burn, ~an order too weak vs the
  bound's estimated ×0.12–0.25 sustained-force requirement. Timing
  leg: four row landings (CAP_FR@anchor 0.205; DROP/JOINT_X0P1 + IX
  @1e11 ~0.24) but seed-paired Δbshr ≈ 0 — takeoff-set composition,
  same signature as SEED-GEOM's FR_IN (same mechanism). Route
  decomposition: droplet carries ~99.7% of acquisitions at every θ —
  hvac-efficiency, half-life and pool-transport arms are inert by
  construction (paired |Δinf| ≤ 5); deep droplet cooling *defers*
  ~40% of droplet acquisitions across the quarantine boundary
  (during_share 0.028→0.38, day-16 kink 0.70→2.7, cabin + crew-mess
  late wave) — suppression-shaped, the converse of the record's
  mid-growth-at-confinement. Surviving suspect class narrows to
  susceptibility / effective-population structure or unconditioned
  mid-voyage suppression dynamics. Design
  `picard_framework/runs/covid_heat_v1_design.json`, ledger
  `docs/ledger/HEAT-V1.md`.
- **`SUPPRESS-V1` is measured — scheduled mid-voyage suppression is
  retired: `suppression_incapable`** (630 cells, 15 arms on the
  single scheduled-protocol slot {protocol × window}: SOP-017 retimed
  start {4,6,8,10,12,14}, SOP-009 {10,12}, SOP-017-ALLHANDS {12}
  non-scoring, SOP-011 {10}, SOP-007 {10,12}, SOP-017 {40,45}
  never-binds witness, + D0 + REF_M0P56, θ {1e11, 2.37e11, 1e12} ×
  seeds 20200205–18, 630/630, 0/630 audit failures, measured at
  `99d090b4`, `docs/ledger/SUPPRESS-V1.md`, job-def rev 38, image
  digest `sha256:1281629a…`). Truth leg: the axis floor is the
  deepest corner — SOP017_D4 inf med 1,121–1,197 at all θ (paired
  Δinf ≈ −2,390 vs D0, real ~67% suppression, still ~160 over the
  band top; takeoff halves to 7–9/14) — every shallower window
  degrades monotonically to baseline; D14 ≈ inert; D40 never-binds
  clean. Timing leg: every arm's before_share median 0.51–0.88, no
  in-band landing (best SOP009_D10 0.51 ≈ 2× the top edge). Shape:
  the declared truncation composite (during-dominant + cabin/mess
  >0.5 + crew lag, ≥5 takeoff) fires on five SOP-017 retime rows
  {4,6,8} — genuinely, but degenerately: those rows still carry
  inf ≥1,121 and bshr ≥0.73, so the machinery produces the
  suppression shape only where it also leaks ≥160 over the band.
  Protocol contrast at day 12/anchor: SOP-009 Δinf −377,
  ALLHANDS −471, SOP-017 −333 (the crew-exemption leak ≈ half the
  during-window mass: ALLHANDS during ~174–207 vs SOP-017 459–800);
  SOP-011 ≡ SOP-007 ≡ baseline (Δ +5–19 — symptomatic-only adds
  nothing over the shipped status floor; venue closure alone inert).
  Verdict `suppression_incapable` — not deferral (totals drop, not
  conserved): the scheduled-protocol grammar cannot reproduce the
  record at any corner. Every declared mechanism class is now
  measured-retired — the residual needs a mechanism outside this
  grammar. Design
  `picard_framework/runs/covid_suppress_v1_design.json`, ledger
  `docs/ledger/SUPPRESS-V1.md`.
- **`CONSENSUS-50` (SARS-CoV-2 partial-immunity retrieval, 2020 window)
  returned `recognition_only_no_protection`: the immunity half of the
  surviving combined-structure class is a declaration, not a mechanism.**
  Under the declared 2020-season window
  (`docs/literature/consensus_tranche_50_sarscov2_partial_immunity.md`)
  the retrieval licenses cross-reactive *recognition* in the unexposed
  (T-cell ~[0.20, 0.60]: Grifoni/Braun/Le Bert/Mateus via Sette & Crotty;
  antibody ~[0.05, 0.23]: Ng/Anderson/Song) but **no** acquisition
  protection — Sagar 2020 (similar acquisition, milder disease only),
  Gombar (similar rate and severity), Anderson (~23% Ab bearers not
  protected) all read null, and the sole positive association (Aran
  OR 0.76) is a claims proxy explicitly non-attributable to immunity;
  the prospective protection papers (Swadling, Kundu) are 2021–22,
  outside the window. Age susceptibility licenses a *continuous
  multiplier* only (Davies ~0.5 under-20; Ayoub peaking at 60–69y) —
  adverse direction on this elder-skewed hull, no binary fraction.
  Bounds recorded: the ~15% non-susceptible the deepest corner needs is
  unsourceable, and a time-constant susceptibility floor cannot move
  before_share at all. Register §3.2 carries the three rows.
- **`COMBINED-V1` (frailty tail × partial protection): declined by owner
  decision 2026-10-01.** The tranche-50 retrieval left the protection
  fraction unsourced (∅lit under the declared 2020 window), and
  "sourced or not at all" rules the declared path out. The surviving
  class from SUPPRESS-V1 narrows to what the frailty tail can do
  alone — or a mechanism the grammar has not yet named.
- **`FRAILTY-V1` is measured — the last named class of the SUSCEPT-V1
  surviving set retires: `frailty_structure_incapable`** (140 cells, 7
  arms on the new `dose_response.frailty` surface — γ cv {0.5, 1.0,
  2.0} × ln cv {1.0, 2.0} declared mean-1.0-pinned corners + FRAIL_INERT
  cv-0 binding audit + D0_declared — at the anchor Θ 2.37e11 × seeds
  20200205–24, 140/140, one audit flag explained as small-sample
  scatter on an extinction cell, measured at `c950e57`,
  `docs/ledger/FRAILTY-V1.md`, job-def rev 40, image digest
  `sha256:56536971…`). The binding is proven: INERT is bit-identical to
  D0 on all 20 seeds, and every armed cell echoes the declared draw
  (n ≈ 3,710 challenged hosts, sample mean 0.99–1.01, q95−q05 spread
  1.6→4.8 with cv). Legs: no arm moves any leg — truth medians
  3,373–3,561 vs the [712, 960] band, before_share 0.71–0.89 vs 0.173,
  recorded 3,193–3,495 vs 197, kink 0.117–0.169 vs baseline 0.120.
  Paired deltas vs D0 show the mechanism's signature in the right
  direction only at cv 2 (Δinf med −197, acquisitions pushed later,
  dur 154 vs 93 — frail tail burns early, hardened survivors persist)
  but the magnitude is ~5% of the needed suppression and inside the
  20-seed spread (Δinf q95 +849). Structural incapability: at Θ 2.37e11
  every host's dose sits decades above the hazard kink, so a
  mean-pinned multiplier only reshuffles hazard inside the saturating
  regime — dispersion cannot put hosts below the kink, only removal
  can, and removal was measured incapable under SUSCEPT-V1. D0 drift
  note: truth leg reproduces 2e12ccf1 (3,567 vs 3,558); recorded/before_share
  read higher (3,413/0.742 vs 3,008/0.606) across the intervening
  `hygiene_cycle` default-ON merge — reported as engine drift, all
  contrasts same-image paired. The surviving class narrows to a
  mechanism the grammar has not yet named.
- **`INFO-SUPPRESS-V1` measured the recognition-keyed channel and stands
  `recognition_suppression_real_bshr_composition_only`** (42/42 cells,
  0 audit failures, mechanism `591d21b1`, `docs/ledger/INFO-SUPPRESS-V1.md`,
  job-def `picard-covid-boarding-screen:41`, image `sha256:48be838b…`).
  The channel — suppression on `trigger_status` reaching a declared
  stoplight (voluntary self-isolation under FRED classes, real venue
  cancellation, route scalars), default OFF — fires on every conditioned
  cell (median arming day 9.6, vs the scheduled SOP-017's day-16 slot)
  and suppresses for real: seed-paired vs D0 (n=12) Δrecorded_onsets
  −276 and Δinfections −269 for the full DP arm; −215/−205 on
  isolation-only — mass voluntary isolation (~2,190 of ~2,660
  passengers) carries it, a real ~8% paired cut. But the frozen
  composition check flags the whole timing story: row before_share
  0.742 → 0.63/0.68 while the paired Δbshr (−0.03, band straddling
  zero) marks it takeoff-seed selection, not a lever — and an 8% cut
  ordered at day ~10 cannot span the ~18× count gap or the 0.173 split.
  Where the SOP sweep lands first (two late-recognition seeds), the
  channel admits nobody — parallel machinery confirmed, inert by
  occupation. The information event is a working suppression trigger;
  it is not the timing mechanism the record needs.
- **`COVID-GM-RESCORE-01` measured the held-out hull on the post-#811/#812
  engine and stands `mixed`** (300/300 scoring + 50/50 diagnostic cells,
  0 audit failures, image `591d21b1`, `docs/ledger/COVID-GM-RESCORE-01.md`,
  job-def `picard-covid-boarding-screen:42`, image `sha256:74721d9d…`).
  The stale first-look verdict (P(takeoff) ≤ 0.04–0.06, positives median
  ~3, q95 ≤ 18) is retired: ignition is now the norm — P(takeoff)
  0.76–0.86 across θ {1e11, 2.37e11, 1e12} — and the campaign-positive
  envelope reaches the record's 128 on both arms at the anchor and at
  1e12 (medians 105/96 and 116/111, intervals [1, 131]–[1, 135]). But the
  landing is envelope-only: q05 sits at 1 (ignition-or-bust, ~1-in-5
  seeds fizzle everywhere) and the asymptomatic share misses the 0.81
  record by ~10× on every row (medians 0.026–0.122) — replay is excluded
  under the frozen grammar. Onsets peak day 13–16 with ~85–95% recorded
  before the day-20 screen, matching the record's near-complete-outbreak
  shape. Seed-paired hygiene_cycle↔spike_decay deltas are null (medians
  0–2, intervals straddle zero): the hand-reservoir repair is not
  measurable on the GM leg and the DELTA-REVERSAL clause did not fire.
  The imports:3 diagnostic is the sleeper: P(takeoff) → 1.0 and q05 lifts
  1 → 89 — the residual at imports 1 is an *ignition* defect, not a
  transmission-size defect. Standing residual order: (a) asymptomatic
  composition vs 0.81 (~10×, largest); (b) the imports/early-contact
  fizzle tail; (c) ignited-seed count dispersion (~35–131 interior).
- **`PRESENT-SHARE-01` repairs the share→hazard defect the GM H2
  decomposition surfaced** (`docs/ledger/PRESENT-SHARE-01.md`): the
  declared presentation probability (`symptomatic_fraction`, or the
  `illness_probability` Hill pair) is a share of courses, but
  `_advance_one_infection` re-rolled it once per day of natural history
  while `NOT_ILL` — ~15 draws to shedding clearance — so P(never
  present) ≈ (1−p)^15 ≈ 0 and effectively every infection presented
  within ~1.4 days of incubation. The schema already stated "drawn once
  past incubation"; the mechanism now matches it:
  `presentation_draw_mode: once_per_course` ships **default-ON** (one
  draw at the epoch crossing the host's drawn incubation; a failed draw
  is a never-presenting course), `daily_hazard` keeps the labelled
  pre-change baseline bit-identical — live-verified on the GM detector
  cell, which reproduces (2, 1, 217, 3, 0) exactly under the flag while
  the default moves it to (2, 2, 217, 4, 1) with
  campaign_asymptomatic_positives 0 → 1, the intended direction.
  Engine-wide: sars_cov2_resp (0.69) and influenza_a (0.669) shares void
  entirely under the hazard; the Hill arms carry the same defect
  attenuated to the low-dose tail. `will_present` forced courses are
  untouched in both modes (the flag short-circuits inside the draw).
  Every pre-change anchored score carries the defect — most directly the
  DP recorded-share residual (~10–18× vs 0.173): a channel that every
  infection reaches looks different once ~31% of courses never present.
  Re-scores ride the merged image; no constant, Θ, or anchor moved.
  *The Θ/DP re-score is measured (`COVID-THETA-V15`, `6efec855`): the
  band reverts to {1.78e11…5.62e11} and the clause still fails at every
  admissible Θ — the repair removed ~750–940 median recorded onsets
  per ignited seed but the ~10× residual survives intact
  (`docs/ledger/COVID-THETA-V15.md`).*
- **`CAREGIVER-V1` declares the cross-pathogen caregiver grammar**
  (`docs/caregiver_v1_spec.md`, `docs/ledger/CAREGIVER-V1.md`) —
  three roles on the `party_id`/`transmission.caregiver` tree NORO-CAREGIVER-01
  shipped: R1 `cleanup` (episode mode; noro instantiation shipped), R2
  `tending` (course mode: one designated cabin/party caregiver binds to a
  symptomatic host for the illness window — declared for sars_cov2_resp and
  influenza_a), R3 `service` (crew meal-delivery contact to confined cabins,
  the channel `meals_to_cabin` re-routes tokens without creating; all
  pathogens). Reallocation semantics: tending hours come out of the
  responder's non-ring contact budget, so the channel concentrates the
  caregiver's exposure instead of adding ship-level contact — its declared
  prediction is cabin-clustered (and crew-service) secondaries, not a
  uniform attack-rate lift. For DP this is the mechanism class that moves
  the *shape* leg (cabin clustering, crew split) without touching Θ —
  the leg every measured candidate so far has failed to move. Respiratory
  factors are Grade C declarations bounded above by the Kordsmeyer 2022
  cabin-mate aOR 3.27 check; noro cells stay provisional pending the funnel
  campaign. *Revised 2026-10-03: age axis decided — U-shaped host response
  bands (children + elderly), adult-weighted responder draw; crew matrix —
  R1 steward channel at `responder_protection_factor` (gloved < napkin),
  none in R2, R3 crew-only; R1 trigger location-agnostic (public emesis
  counts). Implemented 2026-10-03 — all three roles live in
  `engines/transmission_core.py` on the `caregiver.{cleanup,tending,service}`
  grammar (flat NORO-CAREGIVER-01 keys = cleanup shorthand), default-ON with
  `mode: off` the labelled baseline; R2 enabled for sars_cov2_resp +
  influenza_a only, R3 for all pathogens. The greg_mortimer_2020 hull
  golden moved as the intended mechanism — attribution via the off arm in
  `test_covid_hull_change_detector`'s pin comment. Frozen constants:
  register §3.11.*

- **`PROPENSITY-V1` declares the missing persistent-propensity term.**
  Three of the four early-COVID model failure modes are already in-tree —
  infectiousness dispersion (`shedding_variance_log10` + FRAILTY-V1
  hazard frailty), voluntary avoidance (INFO-SUPPRESS-V1, measured −8%
  paired but armed ~day 9.6, too late for the ~18× residual). The fourth
  — per-agent attendance heterogeneity — was absent: the rhythm layer
  deals a fresh i.i.d. Bernoulli on `participation_fraction` per agent per
  event per day, so every passenger converges to the same venue exposure
  over the 17-day pre-quarantine window. The Britton/Ball–Trapman term
  (epidemic burns the high-propensity tail, stalls in low-propensity
  survivors) is exactly the shape the dead candidates could not produce.
  Declared as `rhythm.participation_propensity`: a mean-pinned lognormal
  unit draw (cv 0.8 declared, Grade C) keyed per party under the shipped
  `party_id` structure, times a per-agent `age_band_mean` tilt, consumed
  as `min(1, p × propensity)` on discretionary event classes only —
  orthogonal to SUSCPOOL (binary susceptibility gate) and FRAILTY-V1
  (per-challenge hazard) because it moves exposure *frequency*, not dose.
  `mode: off` is the labelled bit-identical baseline; implemented on the
  declaration branch with the `delivery` payload echo; canary + band
  array are the measurement stage, not run there.
  *Measured 2026-10-03 (`e0d43979`, canary `covid_propensity_v1`,
  40/40 cells, 0 audit failures): **clause FAIL on both arms at the Θ1e9
  anchor** — D0 takeoff 19/20, recorded q05–q95 [1,518, 2,445],
  before_share med 0.452; PROP_OFF 20/20, [1,190, 2,443], 0.397. The
  mechanism exercised (≈2,089 party units/cell, off arm drew 0 — the
  bit-identity witness) but its seed-paired footprint is noise (Δ med
  +12 onsets, −0.047 share). The anchor row itself drifted vs v15
  (`6efec855`): PROP_OFF − v15 = +1,634 med onsets, takeoff 10→20 — the
  low tail that carried v15's clause pass is gone on the merged tree, so
  the v15 anchor pass is historical at its own SHA
  (`docs/covid/covid_propensity_v1_readout.md`). The band array is the
  open decision.* `PROPENSITY-CV-01` answered it: *measured 2026-10-03
  (`e0d43979`, screen `covid_propensity_cv_screen`, 120/120 cells, 0
  audit failures) — the cv-response curve is FLAT at every declared
  dispersion*. Clause FAIL on both legs on all six arms; seed-paired
  (arm − PROP_OFF) medians +58/+15/−12/0/+31 recorded onsets across cv
  0.2→2.0 with every interval straddling zero; multiplier q95 widened
  1.35→3.53 on the declared grid, so the dispersion reached the deal and
  the anchor did not respond. The 40 shared-arm cells replicate the
  canary bit-identically (max |Δ| = 0). The propensity family is dead at
  anchor across its entire declared range — retired on its declared
  test; the band array is moot (`docs/covid/covid_propensity_cv_screen_readout.md`).
  *The anchor drift itself is now attributed* (`CAREGIVER-ATTR-01`,
  measured 2026-10-04 at `b932d0e9`,
  `docs/covid/covid_caregiver_off_v1_readout.md`): CG_OFF — caregiver
  `mode: off` on the propensity-off tree — clause-passes both legs at
  Θ1e9 (takeoff 11/20, q05 10, band ∋197, before_share 0.200) and pairs
  to within −46 median onsets of the v15 anchor row seed-for-seed, so
  the +1,634 fill-in is the CAREGIVER-V1 channel (default-ON since
  #859). The clause's only passing cell on the shipped-default tree
  exists on the `caregiver.mode: off` tree; whether the mechanism's
  anchor effect is *correct* is the open follow-up. *THETA-REFIT-01
  sharpened it (§2): no Θ on [1e7, 1e9] restores the clause under
  shipped defaults — the residual is mechanism-shaped, so the follow-up
  is the clause/anchor itself, not the lattice.* *`ANCHOR-DERIVE-01`
  answered it (2026-10-04): both targets are mechanism-independent
  measured-direct record quantities — the clause legitimately fails and
  the open defect is the CAREGIVER-V1 pre-quarantine delivery strength
  (pooled aboard-window 105–248 vs the record's 34 pre-6-Feb dated
  onsets). Next: CG-FLOOR-01, the declared R2 factor-floor probe —
  proposed, not yet run.*

- **`HOST-AGE-01` arms the two age-structure terms the arm was missing —
  the DP crew protection the record shows and the model lacked.**
  (`docs/ledger/HOST-AGE-01.md`) The COVID arm drew susceptibility and
  presentation flat across age while only severity was conditioned
  (#31). Both terms are now shipped default-armed on
  `sars_cov2_resp`, keyed on the agent's `age_band` under the severity
  model's band→decade convention, sourced not declared:
  `dose_response.susceptibility_by_age_band` = Ayoub 2020 decade ladder
  vs 60–69y (Grade B shape, tranche 50's in-register source),
  `symptomatic_fraction_by_age_band` = Wang 2022 Fig. 2 spline over
  38 studies / 14,850 pre-vaccine infections — the only age-resolved
  synthesis of the same screened-denominator quantity the flat field
  reads (F2dig). Deliberately unrenormalised: on DP's composition it
  lands E[mult|crew] ≈ 0.53 vs E[mult|pax] ≈ 0.86 — the young-crew
  protection the record shows (during-window crew share ~29%), and on
  elder-skewed passengers it raises dated onsets per course, both
  recorded as consequences. Both detector cells repinned — GM
  (36,19,217,55,18) → (34,17,217,56,22) and DP (2480,2215,2827,595,542)
  → (2765,2587,2702,398,333) — with the unarmed profile reproducing
  each prior tuple exactly, fully attributed (DP composition: elder
  presentation lift raises onsets, acquisition suppression cuts
  positives). Declared sweep axes: the contested child end of the
  ladder (Davies ~0.5 / Viner OR 0.56 vs Ayoub 0.06) and the vestigial
  flat-0.31 severity asymptomatic entry as consistency debt. *The DP believability consequence is unmeasured —
  this lands after DP-BELIEF-01's head-of-record, so the map's numbers
  stand at its SHA; a replay under the armed arm is the open cell.*
