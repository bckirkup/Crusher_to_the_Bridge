# Toilet-flush aerosolisation: the emission, its five decades of uncertainty, and the sweep that measures it

> **Status: design and declared uncertainty for a change in progress.** The
> mechanism described in §3–§6 is being built default-off; §8 declares the
> sweep before it runs. No value in this document may be chosen against VSP,
> A4, A9, MIDRS, Park or any attack rate — see
> `.agents/skills/model-parameter-provenance/SKILL.md`. Every dose figure in
> the repository is void pending refit (`norovirus_open_ledger.md`).

## 1. Why this route, and why now

Ledger item 40 deleted the droplet route's continuous emission share for
norovirus: the record supports no continuous respiratory emission, so an
`emesis_conditioned` arm has none. Item 41 measured the consequence — a 31–49×
collapse in secondaries per import and posting no longer resolvable above A9 —
and left the model **under**-producing outbreak size given a posting.

That deletion leaves a specific hole. Norovirus hosts in this model have
diarrhoea far more often than they vomit (`stool_events_per_day` 5.63
diarrhoeal against a handful of emesis episodes per illness), and the
diarrhoeal pathway has **no air source at all**: a defecation event
recontaminates the host's hand and nothing else. Kirby's review lists flush
aerosolisation as unresolved rather than excluded, and it is the one air source
conditioned on the symptom norovirus hosts actually have.

Item 42 then measured the venue. The shared heads added in #538 execute — 3.98
visits per person-day, a shedder's stool event landing on a head in 57–100% of
voyages, susceptible pickups in 29–96% — and are **epidemiologically inert**,
because ingestion per pickup is 0.004–0.14 particles against an N50 of 16,871.
The heads are the room a flush term needs; without an emission they only move
hand-borne mass between fixtures.

## 2. The unit finding that governs the whole design

The internal emission unit is genome copies. `get_pathogen_shedding` returns
`10^(shedding_curve_log10 − adj)` per epoch, where `adj` is
`environmental_faecal_release_log10_g_per_epoch` — **−log10 of the grams of
stool released to the environment per epoch**, currently 4.0. The curve is
copies per gram, so the product is copies per epoch and the declared release
mass is `10^-4 g` — a tenth of a milligram of stool per infected host per hour.

A defecation event puts **107 g** into the bowl (Rose 2015, via Boles 2021).
The flush route therefore acts on a faecal mass **six orders of magnitude
larger** than the continuous environmental release the rest of the enteric
model runs on. Two consequences, both load-bearing:

1. The flush emission must be derived from the bowl deposit in copies and must
   **not** be rescaled by `10^−adj`. The two quantities are different physical
   masses: `adj` is smear onto the environment, the bowl deposit is the stool
   itself. Applying the release offset to a flush would divide a measured
   deposit by an unsourced scalar the ledger has already voided.
2. Because the mass is six decades larger, even the smallest sourced aerosol
   fraction produces a non-trivial air load. At `f_aero = 1e-9` — the bottom of
   Johnson's droplet-nuclei range — a peak-shedding host emits
   `10^11 copies/g × 107 g × 1e-9 ≈ 1.1e4` copies, which in a 6.2 m³ single-
   fixture head is ~1,700 copies/m³ before ventilation. Boles' own exposure
   arithmetic (≈20 inhaled copies per 5-minute visit) lands in the same place.
   **This is why `f_aero` may not be adopted as a point value at either end:**
   the span is the result, and a value chosen inside it is a fit.

## 3. The mechanism

A flush is the emesis route with a different trigger, and it reuses the emesis
machinery exactly rather than introducing a parallel one.

```
stool event (existing Poisson draw in _replenish_hand)
  → venue = _sanitary_venue(zone, agent)        # existing structural rule
  → bowl_deposit = 10^curve[idx] × host_mult × FLUSH_STOOL_MASS_G
  → aerosol_load = bowl_deposit × f_aero        # swept, §8
  → pending[venue] += aerosol_load              # drained to the zone reservoir once
  → emitted[venue].append((agent, aerosol_load))# same-epoch dose in the room itself
```

New route key `flush_aerosol`, registered in `DEFAULT_ROUTE_EFFICIENCY` and
`PATHWAY_EFFICIENCY_KEYS` at 1.0, so route attribution can separate it from
`fomite` and `emesis_aerosol` in exactly the way item 39's attribution
separated droplet from fomite.

### Dose, and why it is dwell-weighted and ventilation-weighted

A head is not occupied; it is visited. A visitor is in it for
`SANITARY_DWELL_SECONDS` (155 s, ×1.22 female), a 4.3% share of a 1-hour
epoch, and arrives at a uniformly random time after the flush. The
concentration it meets is therefore the time-average of a decaying pool, not
the initial value:

```
C0    = aerosol_load / V_head
f_vent = (1 − e^(−ACH·T)) / (ACH·T)          # mean over a uniform arrival in T
dose_i = C0 × f_vent × inhaled_air_volume_m3_per_epoch × share_i
```

`ACH` comes from the provisioning derivation already shipped —
`SANITARY_EXHAUST_M3H_PER_WC` 118.9 over `SANITARY_FLOOR_AREA_M2_PER_WC` 2.7 ×
`SANITARY_CEILING_HEIGHT_M` 2.3 = **19.2 ACH**, independent of block size
(ASHRAE 62.1 Table 6-5, 70 cfm per water closet). At `ACH·T = 19.2` this is
`f_vent = 0.052`: a ~19× reduction against a naive `mass/V`, and the *reason*
it is in the formula is that omitting it would silently treat a code-ventilated
head as a sealed box. Johnson's experimental water closet ran at ~18 ACH, so
the measured setting and the modelled head are ventilation-comparable without
anything being arranged to make them so.

This is also the one place the emesis route is **not** copied: emesis doses a
whole-epoch occupied room with no ventilation removal, which is the right
approximation for an hour in a cabin and the wrong one for 155 s in a head.

## 4. Where a flush happens

The existing structural rule, unchanged and with no tunable "fraction away from
cabin": at home the venue is the host's own cabin fittings, otherwise the head
block serving its current zone, matched on sex. Both emit.

The **cabin** emitter inherits ledger item 31: no platform declares a cabin
bathroom volume, so the compartment volume falls back to 100 m³ and dilutes a
flush ~40× against a real ~2.5 m³ bathroom. That biases the cabin arm's dose
**down** and is recorded, not corrected — inventing a 2 m³ bathroom now would
be an unsourced volume choice that happens to raise the dose.

The **shared-head** emitter is the load-bearing one, and is the reason this
change follows #538 rather than preceding it: a public head concentrates many
short visits into 6–62 m³ that a diarrhoeal host flushed into minutes earlier.

## 5. Dependency on the visit mode

Flush emission requires `sanitary_visit_mode != "none"`. Sanitary zones have no
whole-epoch occupancy — nobody is *in* a head except through a visit — so with
visits off a shared-head flush would emit into a room no one ever enters. The
engine records the venue at every stool event regardless of mode (the venue
resolution is deterministic and consumes no RNG, so this is rng-neutral) and
the two consumers gate independently; the sweep runs every arm with
`dwell_weighted`.

## 6. Constants introduced

| Constant | Value | Grade | What was measured, where |
|---|---|---|---|
| `FLUSH_STOOL_MASS_G` | 107 | **B** | Mean stool mass per defecation, adult; Rose et al. 2015 (*Crit Rev Environ Sci Technol*) via Boles 2021's own exposure arithmetic. Origin: `Sec`. Not a titre — the titre is the profile's own `shedding_curve_log10`. |
| `FLUSH_AEROSOL_FRACTION` | **swept, no default value adopted**; mechanism default **off** | **C** | The whole uncertainty. §7. |
| `FLUSH_AEROSOL_FRACTION_BOUNDS` | `[1e-9, 1e-3]` | — | Frozen interval, dated at this document, spanning both primary measurements end to end. A refusal band, not a prior. |

`FLUSH_STOOL_MASS_G` is a mass, not an epidemiological rate, and it multiplies
a titre the profile already declares — so the flush load inherits the profile's
own shedding curve, host multiplier and strain multiplier rather than
introducing a second, incommensurable titre.

## 7. The five decades, and why neither end may be adopted

Two primary measurements disagree by four to five orders of magnitude **because
they measure different aerosol fractions**, not because either is wrong:

- **Johnson et al. 2013** (flushometer, fluorescent-microsphere surrogate, 5 m³
  water closet, large droplets allowed to settle so only true droplet *nuclei*
  are counted): generation rate ≈ **1e-9 – 8e-8** of bowl load per flush
  (Tables 2–3). Grade B, surrogate particle, analogous setting. This is
  precisely the room-persistent fraction the inhalation route in §3
  represents. Johnson's own caveat: aerosolisation is **not** proportional to
  bowl loading, so treating it as a fraction is an approximation in kind.
- **Boles et al. 2021** (*Sci Rep*, DOI 10.1038/s41598-021-02938-0; murine
  norovirus surrogate, RT-ddPCR, flushometer, 0.15 m above the rim shortly
  after flush): 383–684 copies/m³ from a bowl seeded at 2.18e5–9.65e6 copies
  back-calculates to ≈ **1e-4 – 1e-3**. Grade B, the only norovirus-surrogate
  measurement. It is higher because it captures near-field larger droplets, not
  only nuclei, and because its bowl was 2–3 logs *under*-loaded against a real
  human deposit — Boles state their figure is an underestimate.

Neither is the other's refutation, and the model's route is closer in
definition to Johnson while the only norovirus evidence is Boles. **Therefore
no point value is taken and the full frozen span is swept.** A value picked
inside it — including "the only norovirus number" or "the definitionally
matching number" — would be the same move that let one fitted scalar absorb
five mechanism errors for a year.

### Four documented sources of variation that keep the span wide

1. **Vacuum blackwater versus gravity/flushometer.** Every virus or surrogate
   measurement available (Boles, Johnson, Best 2011 *C. difficile*, Wilson
   2020) is gravity or flushometer. **Cruise ships use vacuum systems**, whose
   ejection physics — a brief high-velocity pressure differential rather than a
   siphonic swirl — has no virus measurement at all; the nearest datum is
   aircraft-lavatory particle counting (Li 2022: 8,498 ± 1,918 particles
   >0.3 µm per flush), which counts particles, not virus, and cannot be
   converted without the bowl load. **This is the single strongest reason the
   span may not be narrowed**, and it is why the sweep reports which decades
   matter rather than proposing a value.
2. **Lid and door state, which in a shared head does not exist.** Best 2011's
   lidless-versus-lidded finding is the analogue of a lid term (lidless emits
   15–47 droplets per flush; closing the lid cuts it sharply). A public head is
   *doorless by design* — VSP 2025 §36.2 explicitly permits hands-free entry —
   so for the shared-head emitter the escape term is ventilation and traffic,
   already in §3, and there is nothing to sweep. For the private cabin emitter
   the real variation is open/open, open/closed and closed/closed behaviour,
   which cannot be represented while the cabin bathroom has no volume of its
   own (ledger item 31): the model has one air volume where reality has two.
   Enumerated here; not implemented, because implementing it would require
   inventing the volume first.
3. **Head geometry and traffic.** Blocks run 6–62 m³ and their high-touch
   hardware area is a Grade C declared quantity
   (`SANITARY_HIGH_TOUCH_AREA_M2_PER_WC` = 0.5 m²/WC). Fomite pickup goes as
   1/area, so it scales head pickup directly; the register already marks it a
   swept axis for this change. §8 keeps it out of the primary grid and sweeps
   it as a corner.
4. **Bidets and seat-washers.** Out of scope by direction. Iyo 2022 finds only
   trace faecal indicators in maintained spray water, so the spray itself is
   low-risk; the seat-wash step would be a distinct aerosol event and is not
   modelled.

## 8. The sweep, declared before it runs

Matched seeds, one image, arms differing only in the swept field — the
instrument from #527 and items 41–42, which resolves a paired difference two to
four orders finer than an unpaired comparison.

- **Staged design, replacing the flat 8-arm grid.** The analytic per-visit
  dose (§3, §4) is exactly linear in `f_aero`, so the response is computable
  before the campaign runs: with the shipped GII.4 curve, the real head
  volumes (6.21 / 18.63 / 62.1 m³), `f_vent` 0.052, 0.6 m³/epoch breathing
  and a 155 s dwell share, one visit after one peak-shedder flush gives dose
  0.77 at 1e-9, 77 at 1e-7 and ≥7.7×10³ at 1e-5 in a median head — under
  beta-Poisson that is P/visit ≈ 0.3% → 12.6% → ≥46%. **Everything at 1e-5
  and above is saturated**; the interesting crossing is a band
  (~4×10⁻¹⁰…4×10⁻⁶) that moves with titre and head size. Sampling the
  saturated plateau at four decades would spend most of the campaign
  measuring identical outcomes.
- **Stage 1 — bracket.** `flush_aerosol_fraction` ∈ {off, 1e-9, 1e-7, 1e-5},
  each on the **first 100 seeds** of the matched block (`--seeds 100
  --stage-tag s1`) → 4 arms × 6 cells × 100 seeds = **2,400 runs**. The off
  arm is the item-42 visits configuration exactly. The seed set is a prefix,
  never a resample, so stage 1 pairs run-for-run with stage 2 and with the
  item-42 archive; the `_s1` arm tag makes a 100-seed stage-1 arm impossible
  to mistake for a 200-seed stage-2 arm at the same fraction.
- **Stage 2 — locate the crossing.** Half-decade arms either side of the
  crossing stage 1 measures, at the full 200 seeds, chosen from the
  dose-response shape — explicitly **not** from distance to A9, A4, or any
  VSP anchor. The builder already accepts the half-decade spellings
  (`3e-9` … `3e-4`) so stage 2 needs no code change.
- **The declaration is unchanged.** The frozen span [1e-9, 1e-3] is not
  being narrowed by evidence we haven't collected — the band still spans
  Johnson 2013 to Boles 2021 end to end; the staging only decides where
  compute is spent inside it.
- **Cells.** expedition_450, classic_1900, spirit_3000 at declared complement,
  7 and 12 days: the same six cells as items 41 and 42, so the contrast is
  against measured numbers rather than re-derived ones.
- `sanitary_visit_mode = dwell_weighted` throughout (§5),
  `droplet_emission_mode = profile_conditioned` (the post-deletion
  default), no other change.
- **Corner sweeps, only where the primary grid says they matter.**
  `SANITARY_HIGH_TOUCH_AREA_M2_PER_WC` at 0.25 and 1.0 m²/WC, and the cabin
  emitter disabled, both run at the lowest decade whose paired contrast is
  resolvable — not across the whole grid, which would quadruple a campaign to
  answer a question conditional on the first result.

**Stage 2, executed as declared.** Stage 1 measured Δ secondaries straddling
zero in all six cells at 1e-9 and excluding zero in all six at 1e-7, so the
resolvability crossing lies strictly inside (1e-9, 1e-7); stage 2 places
three arms — `3e-9`, `1e-8`, `3e-8` — at half-decade resolution inside that
interval at the full 200 seeds (`flush_sweep_v1_{3e-9,1e-8,3e-8}_s2`,
1,200 runs each, 3,600 total). No arm was selected on distance to A4, A9,
VSP, or MIDRS, and the frozen [1e-9, 1e-3] span is unnarrowed — nothing has
been adopted. The stage-1 measurement and its interpretation are ledger item
43 and `docs/norovirus/flush_sweep_v1_stage1_findings.md`.

**What the sweep may conclude.** Which decades of `f_aero` produce a resolvable
change in secondaries per import, in VSP-style posting frequency, and in
attack rate conditional on posting; and hence whether the sourced span contains
a region where flush aerosolisation is material. **What it may not conclude:**
that the decade which best matches A9 or A4 is the true one. If the answer is
that only the Boles end moves anything, the honest report is that the effect
requires the higher of two disagreeing measurements — which is a statement
about the evidence, not a calibration.

## 9. Not in this change

Bidets and seat-washers; a lavatory micro-zone or any cabin-bathroom volume
(ledger item 31); private-bathroom door states (§7.2); the continuous arms'
`airborne_emission_fraction` inconsistency for COVID and influenza (ledger item
40, still open and still its own measured arm); the food-contamination zero
across 1,800 voyages (item 39, still open); any refit of `dose_adjustment` or
any other voided dose figure.
