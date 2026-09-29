# NORO-GENO-01
**Date:** 2026-09-29
**Commit:** 19035a51
**Pathogens:** norwalk_gi
**Status:** open

The genogroup declaration the `dose_response.alpha`/`beta` register row was
waiting on. Decision record, not a measurement: it settles *how* strain-level
heterogeneity is declared, adopts the
[pathogen-class ruling](../proposals/pathogen_class_structure_decision.md) as
the structure, and records the external-typing shares tranche 49 sourced.
**No constant moves, no profile value changes, nothing is fitted.** Every
dose figure remains void per the open ledger.

## Declaration

**The `norwalk_gi` arm declares the pooled GII genogroup.** The profile's
genotype list (GII.4/GII.17/GII.2), its pooled-GII incubation row, and its
GII-derived symptom and titre constants already say GII everywhere except the
dose-response pair, which is Teunis 2008's disaggregated **GI.1** fit
(α = 0.111, β = 32.81). The declaration makes the arm self-consistent:

- The **α ∈ [0.072, 0.161] GII interval stands** — the shipped pair stays as
  the declared point inside it and α remains queued into the screen box,
  pending the class mechanism below.
- The **Atmar 2014 retarget is out of scope**, as the register already
  ruled: Atmar challenged GI.1, and on a GII arm the shipped pair is ~30×
  too *sensitive* against GII.2 challenge (Rouphael 5.1e5), not 6–13× too
  insensitive — the GI-vs-GII comparison was never a demonstrated model
  error.
- **GI.1 is a scenario arm, not a class.** It is the largest documented
  contrast in the system (near-absolute secretor exclusion ~4,000×, ID50
  ~1.3–2.8×10³ gEq vs GII.2's ~10⁵), so a mono-genotype GI.1 cell is a
  legitimate sensitivity axis — but tranche 49 found no typing support for
  a non-trivial GI.1 share in cruise boarding pools, so it does not enter
  the mixture.

## Class structure adopted

Per the 2026-09-04 ruling: **two classes — GII.4 pandemic lineages vs
non-GII.4 (GII.2/GII.17)** — drawn **per-founder**, because strain
variability is between-voyage (a voyage seeds from few importations facing
the same cloud draw), not between-agent. The boundary is earned by a second
independent quantity on the same split: secretor-negative relative
susceptibility 0.10 vs 0.45 (Kambhampati ORs 9.9 vs 2.2).

The three prohibitions stand and bind every downstream change:

1. No genotype-indexed dose-response table — the class is the unit.
2. No class share fitted to VSP — the anchor is genotype-blind (0 of 428
   postings name a genogroup), so shares are declared from external typing
   and swept; only the mixture-marginal is estimable from anchors.
3. No widening of β to stand in for strain spread — heterogeneity enters
   at the founder, where it is mechanically what it claims to be.

## Class shares — declared from external typing (tranche 49)

Uniform `prior_genotype_distribution` (1/3 each) is recorded as an unsourced
placeholder superseded by era-resolved declared intervals, to be wired when
the class mechanism lands:

| era | GII.4 class share | basis |
|---|---|---|
| `pre` | ~0.60, **[0.47, 0.75]** | CaliciNet US 58–72% (Vega 2013, Cannon 2017); Chhabra non-pandemic by-country 47–73% |
| post-2020 | ~0.15, **[0.05, 0.30]** | GII.17 succession: US outbreaks 5.0% → 74.8% by 2024-25 (Barclay 2025/2026); predominant on VSP cruise postings 2022–25 (Preston 2026) |

Both are sweep intervals sourced on the external-typing denominator
(genotyped outbreaks), never fitted. The China GII.2[P16]-dominant record
(69%) is recorded as a geographic bound, not a cruise input.

## Mechanism wiring — implemented

Landed as `6e1da4ae` (branch `devin/…-geno-class-mechanism`); the founder
genotype draw already existed and now mints the *class phenotype* — where
it previously registered every class at `Phenotype()` offsets 1.0
(identity without difference). Both hooks the ruling named are wired:

- **split secretor gate**: `genotype_classes.<class>.
  secretor_negative_relative_susceptibility` — shipped 0.10 (0.04–0.26)
  GII.4 vs 0.45 (0.24–0.83) non-GII.4, the Kambhampati ORs 9.9 / 2.2 — is
  applied **per challenge** in `_merge_pathogen_doses` as the
  dose-share-weighted class rel over the strain ledger's contributors
  (the exact linear fold: identical math to scaling each contributor's
  dose by its class factor). The FUT2 flag still draws at init — the
  trait is a host property — but the init-time flat bake is skipped when
  a class gate is declared, and the flat
  `secretor_negative_relative_susceptibility` stays as the fallback for
  challenges with no resolvable strain mix (untracked path, unresolved
  bin, empty ledger). A profile with no class gate keeps the legacy
  init bake as the labelled baseline. This narrows the [0.04, 0.83]
  screening interval: its width was the unresolved composition problem.
- **`transmissibility_multiplier`** on `StrainState` minted per-founder
  from the class declaration — shipped at the declared-neutral 1.0 as
  the swept axis. The ID50 table cannot set it (tranche 49 §Q2), so the
  mono-class canary cells sweep it.
- **era-resolved shares**: `prior_genotype_distribution_by_era` +
  `genotype_share_era` replace the unsourced uniform placeholder on the
  shipped profiles (`pre` ships: GII.4 0.60 / GII.17 0.15 / GII.2 0.25;
  `post_2020` declared 0.15/0.75/0.10 — within-class genotype splits are
  declared conveniences; the class is the measured unit). The explicit
  `prior_genotype_distribution` field is the sweep override path —
  a mono-class arm is `{"GII.4": 1.0}` etc.
- **`dose_reference_log10` resolved analytically — fixed reference, no
  code change.** The incubation model reads the *delivered inoculum*
  (`inf["acquired_particles"]` → `sample_days`), and the class
  `transmissibility_multiplier` already enters that inoculum through the
  emission factor — class differences reach incubation through dose,
  which is the physically correct coupling. A class-dependent reference
  would have double-counted the multiplier.
- **Not widened:** the mutation window stays [0.05, 20] (±0.1 log can't
  generate a 2.6-log cloud; importation owns that work).

## Differential evidence now on record

The classes-behave-differently question is answerable by measurement, not
fitting — and tranche 49 found the class difference already measured on the
cruise denominator: GII.4 outbreak cases run heavier vomiting (aOR 1.67 for
>10 episodes) and longer duration (aOR 1.43–1.73) than GII.17 cases
(Preston 2026, 2,618 VSP cases). Per-class attribution belongs in the
canary readouts once the mechanism lands; mono-class arms are the
discriminating cells.

## Next

- Implementation session: founder-level class draw → split secretor gate +
  declared `transmissibility_multiplier` axis; resolve
  `dose_reference_log10`; era flag for the share intervals.
- Canary: mono-class cells (pure GII.4 vs pure non-GII.4 founders, same
  seeds) + one mixture cell on the frozen fl_spr_12d block, reporting
  per-class acquisition attribution.
- This entry moves to `measured` when the canary reads out.
