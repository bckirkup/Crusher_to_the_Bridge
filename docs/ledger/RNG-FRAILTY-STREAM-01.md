# RNG-FRAILTY-STREAM-01
**Date:** 2026-09-19
**Commit:** 707ab14
**Pathogens:** all
**Status:** open

## Defect

A dose-response parameter arm cannot be seed-paired against its baseline,
because changing `dose_response.alpha` or `dose_response.beta` re-phases the
run's entire shared random stream.

`TransmissionCore._dose_response_susceptibility` draws each host's persistent
beta frailty from `self.rng`:

```python
draw = float(
    self.rng.beta(dr.get("alpha", ALPHA), dr.get("beta", BETA)),
)
```

`self.rng` is the run's one shared generator, read at 47 sites in
`engines/transmission_core.py` — the emesis schedule, the fomite pickup terms
and the hand-carriage propensity among them. NumPy's `Generator.beta` is
rejection-based, so the number of 64-bit words it consumes is a function of its
parameters, not a constant:

| α at β = 32.81 | PCG64 words consumed by 2,000 draws |
| --- | --- |
| 0.072 | 8,248 |
| 0.0898 | 8,258 |
| 0.1076 | 8,295 |
| 0.111 | 8,315 |
| 0.1254 | 8,353 |
| 0.1432 | 8,381 |
| 0.161 | 8,401 |

(measured directly off the PCG64 counter at seed 12345, monotone in α.)

Every draw taken after the first frailty therefore lands at a different stream
position on an arm with a different α, and the two arms are different voyages
rather than the same voyage with one parameter moved.

## Evidence

`NORO-SUSCEPT-03` swept α over `[0.072, 0.161]` at β = 32.81 with seeds
8105/8106 fixed, 288 epochs, `classic_cruise_1900`, everything else identical,
and checked a frozen invariance: α scales frailty and cannot touch dose or the
emesis schedule, so at a fixed seed the emesis and fomite witnesses must be
identical across α. They are not.

- Seed 8105, across the seven α cells: `scheduled_episodes` = 3 / 1 / 6 / 3 /
  2 / 1 / 1 and `emesis_events` = 1 / 0 / 2 / 1 / 1 / 0 / 0, with every other
  emesis counter moving too.
- Both seeds: all ten fomite counters move with α, including
  `mass_delivered_to_hands_gec` and `surface_mass_deposited_gec`.
- Total credited dose over the voyage — which α cannot affect, since α scales
  susceptibility and not dose — spans 7.11e-8 to 56.620 GEC across the seven α
  cells at seed 8105, nine orders of magnitude.

The reconciliation chain closes exactly within every cell (worst relative
difference 0.000e+00 over 14 runs), so this is not a dose-accounting defect:
each cell is an internally consistent voyage. What is lost is the pairing
between cells.

## Consequence

Any measurement whose attribution rests on holding a seed fixed while moving
`dose_response.alpha` or `dose_response.beta` reads stream realisation, not the
parameter. The effect size is not subtle — nine orders of magnitude of credited
dose in `NORO-SUSCEPT-03` — and it will swamp the parameter on any statistic
downstream of the first frailty draw.

Not affected:

- Arms that leave `alpha` and `beta` alone. `DOSE-FRAIL-01`'s
  `susceptibility_scale` multiplies the draw *after* it is taken and does not
  change the sampler's parameters, so its bit-identity test
  (`test_default_beta_poisson_draws_are_bit_identical`) still means what it
  says.
- The frailty distribution itself, which is the direct image of the parameters
  rather than a downstream consequence of stream phase. `NORO-SUSCEPT-03`'s
  drawn means track `α/(α+β)` across the interval as predicted.
- Replicate-seed campaigns at fixed dose-response parameters.

No number recorded in a ledger entry is withdrawn by this defect, because no
prior entry varied α or β at a fixed seed. `NORO-SUSCEPT-03` is the first, and
it reports the confound rather than interpreting the axis.

## Declaration-shaped fix (not implemented here)

Give the dose-response frailty its own spawned stream, the way the sanitary
visit draw already does in the same module:

```python
self._frailty_rng = np.random.default_rng(
    self.rng.bit_generator.seed_seq.spawn(1)[0],
)
```

A child stream spawned from the run's seed sequence is reproducible from the
run seed, and isolates the variable-consumption sampler so that moving α or β
perturbs only the frailty values. That makes a dose-response arm pairable
against its baseline on everything the frailty does not touch.

This is a labelled change, not a silent repair: spawning a child stream moves
the frailty draws themselves on every arm, including arms that change nothing,
so every golden and every recorded voyage reading shifts by one relabelling of
the random stream. It must land as its own paired-seed change with the moved
goldens attributed to it (`ci-test-design`, `stochastic-attribution`), and the
`dose_response_frailty_stream` selection should carry the pre-change shared
stream as the labelled baseline arm so old readings stay reproducible.
