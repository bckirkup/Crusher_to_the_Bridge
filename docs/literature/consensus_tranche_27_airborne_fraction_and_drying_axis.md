# Tranche 27 — `airborne_emission_fraction` is a share of an emission, not of a titre (#42, item C4)

Status: **evidence record, 2026-09-05.** Track C item C4 of
[`../proposals/defect_resolution_plan.md`](../proposals/defect_resolution_plan.md) §5.
No shipped value moves. The rows this tranche updates are
[`../parameter_provenance_register.md`](../parameter_provenance_register.md)
§3.2 `airborne_emission_fraction` (SARS-CoV-2), §3.3 (a new row for the *active*
influenza arm's fine share, which the register never carried), §3.1's
event-conditioned norovirus arm, and §2's drying entry.

Two questions, one per half of C4:

1. Is a *fraction* the right form for the field at all, and if so a fraction of
   **what**? The proposal's own wording — "no study reports emission as a
   fraction of shedding, so the definition is the construction" — is confirmed
   for one denominator and **refuted for another**. Something measurable does
   sit in this shape; it is just not the shape the SARS-CoV-2 arm uses it in.
2. Does the drying axis, which ships neutral over a sourced interval, move
   anything? Answered by a sweep rather than by argument (§5).

## 1. What the field is, read off the engine

`orchestrator_epoch._airborne_emission_fraction` is the whole of it. Per epoch,
per pathogen, per shedding agent:

```
zone airborne mass += 10^(curve[idx] - release offset) x host x strain x fraction
```

so the field is dimensionally a **share of the emission the arm already
computes** — the part of released material small enough to stay in the zone
air, with the remainder implicitly depositing near the source. Three facts
follow, and all three matter for what may be adopted into it:

- `surface_deposition_fraction` is the deprecated alias of the same key. It
  never fed a surface pool; the fomite reservoir is filled by the emesis and
  faecal-release paths in `TransmissionCore`.
- An `emesis_conditioned` arm returns **0.0** from this helper and takes its
  airborne emission per event instead (`emesis_aerosol_fraction_range`), so
  norovirus does not consume the field at all.
- A profile that declares neither key inherits an **unsourced 1e-4** from the
  helper. Both continuous active arms declare the key explicitly, so nothing
  that runs today reads the fallback — this tranche names it at its definition
  and holds that with a test rather than leaving it as a bare literal.

The unit check is the finding. A share of an emission is dimensionless only
when its denominator *is* that emission. Where the level of the curve is a
**nasal specimen titre** rather than a measured release rate, a factor
multiplying it is carrying `copies epoch⁻¹ / (copies mL⁻¹)` — a volume per
epoch, not a fraction — and no size-partition measurement can be adopted into
it without changing what it means.

## 2. What is measured: size shares of a measured emission

All of these are paired measurements of the same subjects' exhaled aerosol,
split by size at ~5 µm, with the fine part being what remains airborne.

| Source | Quantity as published | Fine share | Grade | Origin |
|---|---|---|---|---|
| Yan 2018 (EMIT, *PNAS* 115:1081, DOI 10.1073/pnas.1716561115) | influenza, GM **3.8×10⁴** fine + **1.2×10⁴** coarse copies per 30-min sample; culturable virus in 39% of fine samples; exhaled load **uncorrelated with NP swab load** | **0.76** | B | Yan 2017/2018: **R** for the infectious-fine-aerosol prose, **?nr** for the copies-per-30-min figures |
| Chow 2023 (DOI 10.1093/infdis/jiad414) | influenza, separately measured fine and coarse **aerosol generation rates**; fine viral load ≈ **12-fold** higher than coarse | **≈0.92** implied | B | **Ab** |
| Coleman 2021 (*Clin Infect Dis*, DOI 10.1093/cid/ciab691) | SARS-CoV-2, **85%** of detected exhaled RNA in the fine (≤5 µm) fraction; 63–5,821 copies per 30-min activity, wide between-subject spread | **0.85** | B | **Ab** |

So the field's *form* is measurable: **fine share ∈ [0.76, 0.92]**,
dimensionless, Grade B, three paired size-resolved measurements across two
respiratory viruses, with SARS-CoV-2's own point (0.85) inside it. This is the
one part of C4 that lands as an adopted interval rather than a refusal, and it
lands only on the arm whose level is a measured emission rate.

### 2.1 What is not measured: a share of a nasal-indexed curve

- **Adenaiye 2021/2022** (DOI 10.1093/cid/ciab670) reports SARS-CoV-2 in both
  fine and coarse aerosol by **detection frequency** and by mask effect, not as
  a share of a load, so it cannot supply an endpoint. Recorded as read, not
  usable. Origin **Ab**.
- **Lai 2022** (DOI 10.1093/cid/ciac846) reports variant- and
  vaccination-dependent differences in exhaled-breath viral load. It moves the
  **level**, not the size split. Origin **Ab**.
- **Zhou 2023** (*Lancet Microbe*, DOI 10.1016/S2666-5247(23)00101-5), the human
  challenge study, is the closest anything comes to a fraction-of-nasal-load:
  viral emissions "correlated more strongly with viral load in nasal swabs than
  throat swabs" — so unlike Yan's influenza finding, a nasal index is not
  refuted as a *predictor* on this arm. But no ratio of emission to specimen
  titre is published (**?nr**), and **two of 18 infected participants emitted
  86% of all airborne virus**, with most emission on three days. A single
  scalar cannot represent a quantity that concentrated. Grade B, origin **Ab**.
- **Buonanno 2020** (DOI 10.1016/j.envint.2020.105794) supplies a quanta
  emission rate, which is back-calculated from an assumed infectious dose and a
  ventilation model. It is the composite this register keeps refusing: rejected
  as circular, not merely as low-grade.

**Null recorded:** no study reports emission as a fraction of a same-subject
respiratory specimen titre, for either arm. The proposal's wording holds for
that denominator, and the shipped SARS-CoV-2 `5e-5` is therefore not a
biological fraction — it is the residue of an emission-rate ÷ specimen-titre
conversion, i.e. it belongs to the arm's **level**, which is where #30 already
put the identifiability problem.

## 3. Queries run

Consensus MCP, this pass. Recorded so they are not repeated.

| # | Query | Yield |
|---|---|---|
| 1 | SARS-CoV-2 exhaled breath fine aerosol versus coarse aerosol RNA copies partition Gesundheit sampler | Coleman 2021 (**0.85** fine), Adenaiye 2021 (detection only) |
| 2 | proportion of exhaled viral RNA in fine aerosol fraction respiratory virus Gesundheit II percentage fine versus coarse | Chow 2023 (**12-fold** fine:coarse), Yan 2017 |
| 3 | SARS-CoV-2 Omicron exhaled breath aerosol size fraction viral load fine coarse proportion vaccinated cases | Lai 2022 — level, not share. **Null for a size share** |
| 4 | fraction of SARS-CoV-2 viral load in nasal swab that is emitted into room air per hour ratio emission to specimen titre | Zhou 2023 (correlation, no ratio), Buonanno 2020 (back-calculated quanta). **Null for the ratio** |
| 5 | norovirus finger to surface transfer efficiency wet versus dried inoculum drying time hands | Tuladhar 2013, Sharps 2012 — both endpoints of the drying axis (§4) |
| 6 | residual moisture on hands of infected person continuous recontamination drying state virus transfer efficiency measured | Patrick 1997 (bacterial, post-handwash), Hervé 2024 (drying method, not state). **Null for the shipped question** |

## 4. The drying axis: endpoints measured, position not

`hand_to_surface_drying_multiplier` scales hand → surface transfer efficiency
and ships **1.0**, over a sourced interval **[0.008, 1.0]**, log10-swept.

- **Low endpoint.** Tuladhar 2013 (DOI 10.1016/j.ijfoodmicro.2013.09.018):
  MNV-1 infectivity transfer from finger pads to stainless steel **13 ± 16%**
  on immediate first transfer, falling to **0.1 ± 0.2%** after 10 min of
  drying — a dried/immediate ratio of **0.0077 ≈ 0.008**. Grade B (human finger
  pads, murine surrogate for infectivity; GI.4 and GII.4 gave similar results
  in PCR units). Origin **Ab**.
- **Interior, and evidence the ratio is itself conditional.** Sharps 2012
  (DOI 10.4315/0362-028X.JFP-12-052): GII fingertip → steel and fruit
  **58–60% wet** against **<1% dry** (ratio **<0.017**), while the
  GI/GII/MNV-1 cocktail gave **20–70% wet** against **4–12% dry** (ratio
  **≈0.06–0.6**). So the multiplier's own value depends on matrix and recipient
  surface, and the sourced interval is wide because the measurement is, not
  because the reading is thin. Grade B, origin **Ab**.
- **High endpoint.** Fully wet contact, **1.0**, by construction: the transfer
  efficiency the multiplier scales is itself measured on immediate transfer.
- **Direction.** Patrick 1997 (DOI 10.1017/S0950268897008261) measures residual
  moisture as the determinant of touch-contact transfer (≈68,000 organisms to
  skin from undried hands, decreasing progressively as drying proceeds). It is
  **bacterial** and post-handwash, so Grade C here and adoptable into nothing;
  it is recorded because it establishes that the axis is monotone in moisture
  rather than a two-state switch.
- **Not the question.** Hervé 2024 (DOI 10.1016/j.jhin.2024.03.005) compares
  hand-**drying methods** for aerosolisation and onward transfer. Recorded as
  read and not usable.

**Null recorded:** no study measures the drying state — or the transfer
efficiency at that state — of a hand being **continuously recontaminated by its
own host's shedding**, which is the only state the simulation ever puts a hand
in. The endpoints are measured; the position between them is not. That is why
the register carries the field as a **swept axis and not a value**, and why
shipping 1.0 is stated for what it is: not a neutral biological choice but the
interval's **wet endpoint**, the most transfer-favourable point on the axis.

## 5. What the axis does

`scripts/drying_axis_sweep.py` is a one-factor common-random-number sweep: five
log-spaced points across `[0.008, 1.0]`, eight shared seeds per point, every
other parameter at its shipped profile value. It is **not** the Morris screen
(#36) and **not** the admissible-region gate (#37); it selects nothing, and it
reports each output's span across the axis against the seed-to-seed spread at
the shipped endpoint, so a span smaller than that spread is a factor the
scoring cannot see.

Result — `reports/drying_axis_sweep.json`, `norwalk_gi` on `mega_cruise_5000`,
168 epochs, 450 agents, seeds 500–507:

```bash
python3 scripts/drying_axis_sweep.py --seeds 8 --out reports/drying_axis_sweep.json
```

| Output | Axis low → high (means) | Axis span | Seed SD at the shipped endpoint | Span / SD |
|---|---|---|---|---|
| `attack_rate` | 0.2336 → 0.2797 | 0.0461 | 0.2462 | **0.19** |
| `ever_ill_attack_rate_passenger` | 0.0752 → 0.0910 | 0.0158 | 0.0741 | **0.21** |
| `reported_case_attack_rate_passenger` | 0.0752 → 0.0906 | 0.0154 | 0.0734 | **0.21** |
| `reported_case_attack_rate_crew` | 0.0905 → 0.1222 | 0.0317 | 0.1413 | **0.22** |
| `vsp_posted` (share of seeds) | 0.625 → 0.750 | 0.125 | 0.4629 | **0.27** |
| `peak_epoch` | 158.75 → 166.88 | 8.125 | 0.354 | **22.98** |

Reading, stated as what the numbers do and not as an endorsement of any point on
the axis:

1. **Every prevalence output fails the noise floor.** A 125-fold move on the
   factor buys 0.19–0.27 of one seed's standard deviation on all four attack
   rates and on the posting indicator. The monotone ordering is not even clean:
   `attack_rate` is *lowest* at 0.0268, not at the dried endpoint, because the
   drying multiplier moves a deposit into a pool the same agents then draw from,
   so the CRN pairing does not hold the epidemic's branch fixed. This is the #22
   result (`contact_transfer_fraction` clears no floor anywhere on its interval)
   reproduced on the moisture axis of the same route. **Note added later:** the
   #22 screen entry is withdrawn as aliased against
   `route_efficiency_multipliers["direct_contact"]`
   ([tranche 12](consensus_tranche_12_contact_transfer.md) §10), so the parallel
   is to that factor's *magnitude*, not to a result that still stands. The
   drying-axis sweep above is unaffected: the drying multiplier is the sole
   owner of its axis.
2. **The one output that moves is a timing statistic, and it moves for a reason
   that is not the drying physics.** `peak_epoch`'s 23× span is carried by a
   single seed (506 in the two low-multiplier points) whose incidence peaks at epoch
   110 rather than at the 167-epoch horizon; the shipped-endpoint SD is 0.35
   because there every seed peaks at the horizon. A censored-peak indicator is
   what changed, not the peak's location — the 168-epoch window ends before the
   curve turns over in almost every run, so `peak_epoch` should not be scored on
   this horizon at all. Recorded as a **finding against the output**, not a
   sensitivity of the factor.
3. So the axis is admissible for #36 and #37 to carry, and it will report the
   factor as inert on everything the model is scored against. That is the
   information; it is not a licence to freeze the field at any endpoint, because
   the unmeasured quantity (which drying state a continuously recontaminated
   hand is in) is unchanged by the fact that the model cannot see it.

## 6. What this licenses

| Arm | Field | Result |
|---|---|---|
| `influenza_a` | `airborne_emission_fraction` = 0.76 | **Adopted as an interval**: fine share **[0.76, 0.92]**, Grade B, shipped at the floor. Admissible because this arm's level is pinned to Yan's measured exhaled rate, so numerator and denominator are the same measurement |
| `sars_cov2_resp` | `airborne_emission_fraction` = 5e-5 | **Declared, not applied.** The measured fine share for this virus is 0.85 (Coleman 2021), 4.2 orders from the shipped value, and it cannot be adopted while the arm's level is a nasal titre offset by a stool-mass constant: the shipped factor is a unit-bearing conversion, not a share. What licenses the share is the level fix #30 already identifies, not more sourcing |
| `norwalk_gi` | continuous `airborne_emission_fraction` | **∅ null, and the field is not consumed**: `emesis_conditioned`, per-event `emesis_aerosol_fraction_range` [7.2e-7, 2.67e-4]. No measurement of continuous norovirus aerosolisation between emesis events was found in tranche 5 or this pass |
| helper default | unsourced 1e-4 | Named at its definition, and a test asserts no active profile reads it |
| all arms | `hand_to_surface_drying_multiplier` | **Sourced interval [0.008, 1.0], Grade B, swept not valued** — endpoints measured, position unmeasured, and §5 reports what the axis moves |
