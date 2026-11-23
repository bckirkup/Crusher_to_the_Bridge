# NORO-EXTERNAL-SEQUESTER-01
**Date:** 2026-11-23
**Commit:** #1407
**Pathogens:** norwalk_gi
**Status:** measured

EXTERNAL-SEQUESTER (D2′′) campaign per
`docs/norovirus/hand_external_sequester_spec.md` (PR #1404),
implementation PR #1407. NORO-TOUCH-PATCH-01 measured the binding
stage as hand-reservoir → mouth conversion: item encounters deliver
ordinary-fomite mass to hands (16/18 cold cells) but ~1–4% of it
reaches a mouth — the accessible reservoir sheds ~96–99% to pad
inactivation and washes within ~1–3 epochs. This campaign tests the
retention hypothesis directly: `hand_sequester_fill: "any_load"`
admits acquired load to the wash-proof protected compartment (per-host
capacity from the shipped `logU(50, 3200)` draw) and
`hand_residual_mouthing: "per_epoch"` re-exposes residual load to the
mouth each epoch under `discrete`.

## Frozen decision criteria (campaigns/noro/noro_external_sequester_01/LEDGER.md)

- Two arms × 20 seeds (8000–8019), stacked on
  `fomite_representation: item_instances` + `contamination_solver:
  discrete`: arm **S** = attribution control (`per_epoch` +
  `stool_only`), arm **S+R** = full mechanism (`per_epoch` +
  `any_load`).
- Hot-cell floor: Σhazard ≥ 1.1 (seed 8105 take-off floor; 8000/8006
  are known-hot, so the gate reads the 18 previously-cold cells).
- **Ignites :=** ≥9 of 18 previously-cold cells reach Σhazard ≥ 1.1.
- Audit invariants per cell: len-288 epoch ledger; hand partition
  `sources = sinks + residual` ≤ 1e-9 rel; migration/settle/leak
  witnessed as internal flows; resolved-arm stamps; provenance
  witness (every protected/pending holder traced to a fill event).

## Result — both arms, seeds 8000–8019 (Measured at: f357dd16)

Batch arrays `e15d50cd-0a5f-4184-886b-8d7ef8577731` (S) and
`66d64d2f-a680-4ee5-9ff0-7131fa15ca0a` (S+R), jobdef
`picard-noro-external-sequester-01:3`, image
`sha256:d92f1d4c1a440ff0e46a045621d0db8bd5cccfccb157093834c43d8324c78abb`,
288 epochs. **All 40 cells passed the frozen audit** — len-288
ledgers; partition closure ≤1.2e-14 rel on every cell; provenance
209–1617 holders per S+R cell, zero violations.

- **The retention mechanism fired everywhere mass existed.** S+R:
  migrated mass into the protected compartment on every cell with
  delivered mass (up to 188k GEC on 8006, median ~1–10k on cold
  cells); pending + protected balances stayed nonzero for all 288
  epochs on 19/20 cells; 209–1617 protected holders per cell.
- **Mouth dose rose — materially, on most cold cells.** S+R vs S
  mouth mass on representative cold cells: 8016 1.2k → 71.7k;
  8012 713 → 3.6k; 8013 17 → 275; 8017 14 → 336; 8019 34 → 159;
  8007 97 → 209; 8014 244 → 460. (Seeds are not paired-comparable:
  `any_load` draws capacity from `engine.rng`, so the arms' streams
  diverge — directional read, per the spec's declared caveat.)
- **Take-off did not cross the gate on either arm.** Cold cells ≥1.1
  Σhazard: arm S **3/18** (8002: 1.84, 8009: 2.87, 8018: 1.37);
  arm S+R **1/18** (8018: 2.09). Hot cells behaved as expected under
  both arms (8000: ~34–37; 8006: ~130–141).

## Verdict under the frozen rules

**Mouth dose rose but take-off does not** — spec §6 third arm: the
sequester+resampling arms demonstrably hold acquired mass for days
and convert up to ~60× more of it into mouth dose, and cold cells
still sit under the hazard floor. The binding stage is now downstream
of mouth dose itself: mouth-dose → infection conversion — the
dose-response/challenge floor, or hazard concentration onto hosts
whose frailty already absorbs the dose.

Caveats (recorded, not attributed): RNG divergence between arms
(capacity draws) means per-seed S-vs-S+R pairing is noisy — e.g.
8018's mouth fell (24.9k → 14.5k) while its hazard rose (1.37 →
2.09); the aggregate gate is the verdict, not any single cell. Arm S
alone adds per-epoch residual exposure over the TOUCH-PATCH arm —
its cold-cell mouth percentages stayed ~0.4–4% of delivered because
residual mass without sequestration still decays/washes within
~1–3 epochs; per_epoch only pays when mass persists, consistent with
the mechanism reading.

## Consequence

The measured chain now stands: encounter structure fixed (TOUCH-PATCH
moved requests) → delivery to hands fixed → retention fixed → mouth
dose rose → still no take-off. The next proposal lives at
mouth-dose → infection: the dose-response/challenge floor measured
~99% conversion in earlier ledger work, and where the mouth dose
lands per host. D1′ (carrier donor eligibility), D3′ (rhythm A/B),
and the challenge-floor re-read remain parked; held seeds 8105/8106
stay held.
