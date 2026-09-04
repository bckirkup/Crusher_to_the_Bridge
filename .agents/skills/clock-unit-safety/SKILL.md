---
name: clock-unit-safety
description: Keep time-dependent configuration unit-declared and converted through SimClock.
---

# Clock Unit Safety

Use this skill when adding or changing a time-dependent configuration value,
natural-history rate, probability, decay, growth factor, or delay.

## Core convention

Every time-dependent parameter declares its physical unit in its key:

- `*_per_day` for daily rates, amounts, probabilities, and fractional losses
- `*_hours` for wall-clock durations and half-lives
- `*_per_hour` for hourly rates

Do not add a naked `*_per_epoch` or `*_epochs` parameter for a physical
quantity. Those spellings remain only where the compatibility guard or schema
explicitly allows a retired alias, run-length bookkeeping, or another
epoch-native contract.

Convert a declared value once through a `SimClock` helper at the boundary where
the simulation consumes it. Do not apply `/ 24`, `* 24`, or another clock
conversion inline at individual call sites.

## Conversion rules

For an hourly natural-history clock, let
`f = hours_per_epoch / 24`:

- Amounts: `amount_per_epoch(x_per_day) = x_per_day * f`.
- Independent probabilities: `probability_per_epoch(p_per_day) =
  1 - (1 - p_per_day)^f`.
- Fractional decay: `decay_per_epoch(d_per_day) = 1 - (1 - d_per_day)^f`.
- Multiplicative growth: `growth_factor_per_epoch(g_per_day) =
  g_per_day^f`.
- Half-life survival: `survival_from_half_life(t_half_hours) =
  0.5^(hours_per_epoch / t_half_hours)`.

These helpers are implemented by `engines.sim_clock.SimClock`; the legacy
day-per-epoch mode preserves its historical one-epoch behavior.

## Guard test and allowlist

Run:

```bash
python3 -m pytest tests/test_unit_safety_guard.py -q
```

`tests/test_unit_safety_guard.py` scans repository configuration keys ending in
`_per_epoch` or `_epochs` and rejects them unless the path/key pair appears in
`ALLOWED_EPOCH_KEYS`. It also scans epoch-step methods for mutation by
per-epoch module constants; deliberate exceptions belong in
`ALLOWED_PER_EPOCH_CONSTANTS` with a narrow justification. The allowlist is
not a general escape hatch: add an entry only for bookkeeping, an active
epoch-native contract, or a retired compatibility alias that cannot yet be
removed.

## Adding a parameter safely

1. Name the parameter with its physical unit, such as
   `surface_decay_log10_per_day`, `detection_delay_hours`, or
   `contact_rate_per_hour`.
2. Add the canonical key to the applicable schema and configuration.
3. Read it through the appropriate `SimClock` helper at the consumer boundary.
4. Keep any retired alias as an explicit fallback with a warning or schema
   compatibility entry, rather than making it the documented canonical name.
5. Add a focused clock-unit test covering legacy and hourly behavior and run
   the guard test.

## Failure mode to reproduce

A daily rate applied once per hourly epoch is 24 times too fast: the code
advances a full day's loss or growth during each of the day's 24 epochs.
Complement exponentiation and growth-factor exponentiation prevent that
mistake. The historical food-pool failure is a concrete diagnostic: food
contamination reached **99.95% of delivered norovirus dose** when the
per-day kinetics were effectively applied hourly. A regression test should
compare the accumulated hourly result with the one-day result, not merely
assert that a run completes.
