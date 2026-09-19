# NORO-EMESIS-SIZE session prompt

## Settled inputs (do not re-derive)

- `NORO-SUSCEPT-02`, measured at `9f4cd79`: credited dose, challenge dose, and
  evaluated hazard reconcile exactly on `classic_cruise_1900` at seeds 8105/8106,
  288 epochs, shipped profile.
- `NORO-SUSCEPT-03`, measured at `f5f9ff3`: the sourced alpha interval
  [0.072, 0.161] is excluded as the explanation for absent secondaries. Zero
  secondaries in 14 voyages, max summed hazard 1.186e-2, alpha moves mean
  susceptibility only 2.2-fold against orders-of-magnitude shortfall. alpha is
  closed.
- `NORO-DOSE-01`, measured at `f55e93f`: the dose shortfall on
  `classic_cruise_1900` is geometrical attenuation in a one-hop fomite chain
  (4.1 log10 loss across surface-to-hand and hand-to-mouth), not a blocked
  mechanism. Fomite is 93.5% of dose. The carrier-dead-end archetype is
  confirmed. No host blocker. Σ hazard 3.81e-4 gives P(0) = 0.9996. The
  recommendation is replicated-seed emesis sizing as the next declared study.
- `RNG-FRAILTY-STREAM-01`: any arm that moves `dose_response.alpha` or `.beta`
  is unpairable at fixed seed. Do not touch them.

## Deliverable (exactly one)

A single merged PR containing:

1. **Ledger entry `docs/ledger/NORO-EMESIS-SIZE-01.md`** with the frozen design
   and admissibility criteria (before any cell runs), then the measured results.
2. **Open-ledger paragraph** in `docs/norovirus/norovirus_open_ledger.md` recording
   what the finding restores or withdraws (or that it does neither).
3. The instrument dumps themselves go to `docs/norovirus/noro_emesis_size_01/`.

The readout must report, per hull:

- Emesis event rate: fraction of seeds with >= 1 emesis event, and the
  conditional episode count distribution.
- Per-event dose delivered to hands (from `patch_pickup_dose_gec`) and per-event
  patch mass filed (from `patch_mass_gec`).
- Emesis share of total credited dose (fomite route only) at seeds where
  emesis fires.
- Whether the emesis event rate or per-event dose differs structurally between
  hulls, or whether the difference is solely headcount-driven.

## Non-goals

- Do not reopen alpha, beta, or any dose-response parameter.
- Do not change any constant, profile value, or engine path.
- Do not run a campaign on AWS Batch; this is a local diagnostic, not a sweep.
- Do not measure or attribute the carrier-dead-end truncated mass (that is a
  separate study, `NORO-CARRIER-REDEPOSIT-01`, not scoped here).
- Do not attempt to size the fomite transfer-efficiency product (study 3 in
  `NORO-DOSE-01`).

## Hulls

| Hull | Complement | Epochs | Description |
| --- | --- | --- | --- |
| `classic_cruise_1900` | 1,910 | 288 | The settled reference hull from -02/-03/-DOSE-01 |
| `expedition_cruise_450` | 450 | 168 | The expedition archetype; shorter voyage, fewer agents |

Both at their `declared_total` complement and their platform `voyage_config`
default epoch count.

## Design

### Seed count

>= 20 seeds per hull, paired. Use a contiguous block starting at seed 8000
(i.e. 8000..8019 for 20 seeds). 8105 and 8106 are included as a consistency
check against the `NORO-SUSCEPT-02` reference dumps but are not in the block —
run them as two extra seeds (22 total per hull).

### Instrument

`tools/noro_diag/per_host_dose_challenge.py` with `--platform <hull>
--epochs <epochs> --seeds <list> --out docs/norovirus/noro_emesis_size_01/`.
No `--alpha` override. The instrument already records the full emesis witness
chain (`emesis_events`, `emitting_hosts`, `patch_mass_gec`,
`patch_pickup_dose_gec`, `patch_pickups`, `scheduled_episodes`,
`hosts_with_schedule`, `phase_blocked`, `phase_eligible`) and the fomite
witness chain. No instrument modification is needed unless a witness counter is
missing; if one is, add it as its own commit before any data commit.

### Runtime estimate

~25 min per seed on `classic_cruise_1900` (1,910 agents x 288 epochs).
`expedition_cruise_450` (450 agents x 168 epochs) should be roughly
(450/1910) * (168/288) ~ 0.14x, so ~3.5 min per seed.
22 seeds x classic: ~550 min = ~9.2 h. 22 seeds x expedition: ~77 min.
Total: ~10.3 h on one core. Two cores available; run both hulls in parallel:
~9.2 h wall clock.

### Forbidden arms

Any arm changing `dose_response.alpha` or `.beta`; any constant or shipped
configuration change.

## Validation gate before PR

1. The 8105 and 8106 seeds on `classic_cruise_1900` must reproduce the
   `NORO-SUSCEPT-02` reference values exactly (same `emesis_events`,
   `patch_mass_gec`, `patch_pickup_dose_gec`, `Σ hazard`, `credited_scaled`).
   If they do not match, stop and report — the instrument or engine has drifted.
2. Every seed must have a non-degenerate fomite witness (non-zero
   `surface_mass_deposited_gec`). A seed with zero surface deposit means no
   import was assigned or the import never shed; report it as a void seed, do
   not include it in the emesis statistics.
3. Ledger header format passes `tests/test_ledger_entries.py`.

## Report immediately if

- The emesis event rate across 20 seeds is 100% (every seed fires) or 0% (no
  seed fires) on either hull — the first invalidates the "most stochastic" claim
  from NORO-DOSE-01, the second makes the study void.
- The 8105/8106 consistency check fails.
- The instrument errors or the engine panics on any seed.
- Wall clock exceeds 14 h (something is wrong with the runtime estimate).

## Stop when

The PR containing `NORO-EMESIS-SIZE-01.md` (with frozen design, measured
results, and open-ledger paragraph) is merged, and the dumps are committed
under `docs/norovirus/noro_emesis_size_01/`.

## Follow-on studies (do not execute, declare only)

After the emesis sizing readout, the next two candidates from `NORO-DOSE-01`
are, in order:

1. **`NORO-CARRIER-REDEPOSIT-01`**: Instrument one arm that labels non-shedding
   carriers' hand-to-surface deposits (a shadow deposit that does not enter the
   pool but is counted) and measure the mass the carrier-dead-end archetype
   truncates. One local voyage per seed, same seed block, both hulls.
2. **`NORO-TRANSFER-PRODUCT-01`**: Compare the product of
   `SURFACE_TO_HAND_LOGNORMAL`, `HAND_TO_MOUTH_NORMAL`, and the contact counts
   against the few whole-voyage environmental assay studies that measure both
   surface contamination and hand contamination in the same setting. Literature
   review, not a simulation run.

These are declared here so the successor session's prompt can reference them
by ID. Neither runs in this session.
