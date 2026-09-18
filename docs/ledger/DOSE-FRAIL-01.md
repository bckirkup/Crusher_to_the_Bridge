# DOSE-FRAIL-01
**Date:** 2026-09-18
**Commit:** 1c6dce8
**Pathogens:** sars_cov2_resp
**Status:** open

## Defect

The Θ fit arm replaced the profile's dose-response with
`{"model": "exponential", "k": Θ}`. In that branch
`TransmissionCore._dose_response_susceptibility` returns `k` itself, so every
host on the arm carried one identical susceptibility (one distinct value across
3,711 hosts). The profile's own shipped dose-response is beta-Poisson with a
per-host `Beta(alpha, beta)` draw, so the fit arm was the only arm in the
repository with no host frailty at all — and the arm the Θ grid was scored on.

This is visible in the AERO-NEAR-02 crew-mess trace: 242 occupants, 2 shedders,
139 hosts receiving one identical far-field dose, `Θ·dose ≈ 1.1`, and therefore
`P ≈ 0.67` for all of them at once. A roomful either clears threshold together
or not at all, which is the mechanism behind the extinction-or-burn behaviour of
the v6 Θ grid: no point on five decades both ignited from one index case and
matched the Diamond Princess trajectory.

## Declaration-based fix

Θ no longer replaces the dose-response model. The arm keeps the profile's
beta-Poisson shape (`alpha`, `beta` inherited, not fitted here) and Θ enters as
`susceptibility_scale`, a positive multiplier on each host's persistent
`Beta(alpha, beta)` draw:

    susceptibility_scale = Θ · (alpha + beta) / alpha

so the arm's **mean** host susceptibility is Θ, while the shipped coefficient of
variation of the frailty distribution is preserved. Susceptibility and dose
still enter only as their product, so the same scale applied to dose in the
population-level beta-Poisson mean response is the identical operator, and there
is still one fitted number on the arm.

`susceptibility_scale` defaults to `1.0`, so every arm that does not declare it
— every non-Θ arm in the repository — draws bit-identical susceptibilities to
before (`test_default_beta_poisson_draws_are_bit_identical`).

## Provenance

The frailty shape is **not** newly fitted. `Beta(0.18, 58)` is the shipped
profile shape and is retained as-is; the change only stops the fit arm from
discarding it. Two literature notes bound what may be claimed here:

- Miura et al. 2023 (human coronavirus challenge re-analysis) rejects
  homogeneous susceptibility against heterogeneous alternatives by a large
  margin (homogeneous-model ΔAIC reported in the hundreds). This supports
  *having* frailty on the arm; it does not supply a SARS-CoV-2 shape. The exact
  ΔAIC and its location in the paper are carried over from an earlier retrieval
  and are not re-verified here — no number from it is installed anywhere.
- Published SARS-CoV-2 human-challenge data do not identify a quantitative
  individual-susceptibility shape parameter. Gomes et al. 2022's inferred
  susceptibility CV is not admissible here: it is inferred from epidemic curves
  that overlap the attack-rate information this fit is scored against.

No constant was chosen to move a scored anchor. No attack rate was consulted in
writing this change.

## What this invalidates

- **The AERO-NEAR-02 "roomful of identical hosts" characterisation of the
  crew-mess far field no longer describes the Θ arm.** Its numbers (`7d8b0d2`)
  were measured with identical hosts and are superseded on this arm pending
  remeasurement; they remain valid as a record of the defect.
- **The v6 / v6c Θ grid and the imports × Θ sweep are not recoverable by
  rescaling.** They were already withdrawn (`docs/covid/covid_open_ledger.md`
  §1); this change adds a second reason. The shape of the Θ response surface,
  not only its location, is expected to move: frailty spreads the threshold that
  previously fired for a whole room at once.
- **Change-detector cell.** The COVID hull cell moves
  `(14, 3, 217, 18, 10) → (1, 1, 217, 4, 0)` on CPython 3.12 and
  `(14, 5, 217, 19, 7) → (1, 1, 217, 4, 0)` on CPython 3.11 (read from CI job
  105760985675, fast tier 3.11 shard 3, on this branch), attributed to the
  restored per-host draw: the cell's hosts are no longer identically
  susceptible, and a concave marginal response over a right-skewed frailty
  distribution yields fewer infections than the same mean applied to
  identical hosts. The two interpreters now agree on the reading, which is
  itself evidence the move is interpreter-independent rather than RNG-stream
  divergence.

## Not settled by this entry

- **The incubation dose reference.** `dose_reference_log10` is re-referenced to
  `ln 2 / Θ`, i.e. to the *mean* host. `Beta(0.18, 58)` is strongly
  right-skewed, so the median host sits well below the mean and a typical
  infection no longer occurs at the reference dose. Whether the reference
  belongs at the mean, the median, or the dose at which the arm's realised
  infections occur is an open provenance question, not a fit choice.
- **Whether an admissible Θ now exists.** Restoring frailty removes one reason
  the grid could not both ignite and match; it does not establish that a
  non-airborne between-cabin route is unnecessary
  (`docs/covid/covid_first_look_readout.md`). No Θ is claimed by this entry.
