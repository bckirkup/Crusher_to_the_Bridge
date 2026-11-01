# FLU-CONTAMX-01 — ContamX engine probe of the settled flu confined cell

> **Status:** Findings (2026-11-01). One settled flu cell re-run under
> `hvac.transport_engine: contamx` with identical seeds, plus a native parity
> lane at the same HEAD, local only. Question posed: does a settled flu
> verdict route through environmental/airborne (transported-pool) dose, and
> does it move under ContamX? Answer: **the settled confined-SAR cell does
> not load on the transported pool at HEAD — the `hvac` channel delivers
> ~0.008 copies across 34 confined slots under either engine — so the solver
> swap cannot move the verdict, and it does not.** Environmental dose on
> this cell arrives through the near-field plume and the local droplet pool,
> which no transport solver writes.

## Cell declaration

- Cell: the conditioned `influenza_a` confined-cabinmate cell on
  `classic_cruise_1900` — `ACTIVE` bundle, 2 explicit seeds at epoch 0,
  `confinement: declared` (SOP-017 day 1 → voyage end), `k = 6e-4`,
  288 epochs — seeds 8105, 8106, 8112, 8184.
- Criteria (from the session prompt): (a) **settled** — this is the
  CABIN-FLOOR-03 scored anchor, measured of record at FLU-SOCIAL-01
  (`8c03e9d7`: on-arm 56/856 = 6.5% [5.1–8.4], inside the declared band);
  (b) `classic_cruise_1900` ships the committed ContamX `platform.prj`
  (`data/platforms/classic_cruise_1900/contam/platform.prj`); (c) the cell
  is the one settled flu verdict whose delivered dose *could* route through
  the environmental pool — the withdrawn FLU-DOSE-01 measured `hvac` at
  ~33% of confined-slot copies pre-`1b9d37ca`, before the far-field rework.
  The probe measures what the channel composition is at HEAD.
- Runner: `tools/flu_confined_contamx_probe.py` — the same conditioned-cell +
  cabin-pair-ledger machinery the settled cells use
  (`tools/diag/conditioned_cell.py`, `tools/noro_diag/cabin_pair_challenge_probe.py`,
  `tools/covid_route_attribution.py`), with the only delta
  `config_overrides.hvac.transport_engine`. `tools/flu_confined_contamx_compare.py`
  joins the lanes and writes the surface.

## Engine identity

Each payload records a `transport_engine` block written at build time:
`requested`, `config_transport_engine`, `engine_class`, `n_airflow_paths`,
`total_flow_m3h`, `max_path_flow_m3h`. This is required because an
unresolvable ContamX request falls back to native silently. On this box
every contamx-lane cell built `ContamXTransportEngine` (666 airflow paths,
~410,834 m³/h total) and every native-lane cell built
`ContamTransportEngine` (705 paths, ~391,683 m³/h). The config echo alone
would not prove the swap — the engine class and path counts do.

## Headline

Two findings, one per prompt question:

1. **The settled confined-SAR cell does not route through the transported
   pool.** Summed over all 34 confined slots at HEAD, `hvac` channel dose
   totals 0.0076 copies native / 0.0077 contamx — ~0.0002% of confined dose.
   The cell loads on `plume` (near-field droplet: 6,124 / 6,243 copies) and
   `pool` (local aerosol pool: 3,137 / 3,222 copies); `contact`, `emesis`,
   `flush`, `fomite` are residual. Only `hvac` reads the solver-written
   `zone_pathogen_mass` reservoir (`_pathway_hvac_airborne`); `pool` is
   `aerosol_pools_by_pathogen` local accumulation and `plume` is the
   same-epoch near-field plume — neither is a solver output.
2. **The verdict does not move under ContamX.** Paired on all four seeds:
   identical `confined_slots`, `confined_secondaries`, and
   `observed_mate_case_attack_confined` per seed; pooled attack 2/34 =
   5.88% [Wilson-95 1.6–19.1] in *both* lanes — identical numbers, inside
   the CABIN-FLOOR-03 on-arm band [4.5%, 14.7%] and consistent with the
   settled 6.5% point estimate (n=856) within the spec's small-n scatter
   rule. `non_load_bearing_shift`.

## Paired lanes

| seed | lane | infections | acquired | slots | secondaries | confined SAR | plume | pool | hvac | engine |
|---|---|---|---|---|---|---|---|---|---|---|
| 8105 | native | 19 | 0 | 11 | 0 | 0.0 | 3729.5 | 1526.7 | 0.000 | ContamTransportEngine |
| 8105 | contamx | 19 | 0 | 11 | 0 | 0.0 | 3752.6 | 1540.9 | 0.000 | ContamXTransportEngine |
| 8106 | native | 11 | 1 | 5 | 1 | 0.20 | 1547.2 | 1215.0 | 0.0072 | ContamTransportEngine |
| 8106 | contamx | 11 | 1 | 5 | 1 | 0.20 | 1649.6 | 1288.3 | 0.0073 | ContamXTransportEngine |
| 8112 | native | 22 | 0 | 14 | 0 | 0.0 | 596.2 | 236.0 | 0.000 | ContamTransportEngine |
| 8112 | contamx | 22 | 0 | 14 | 0 | 0.0 | 589.6 | 233.1 | 0.000 | ContamXTransportEngine |
| 8184 | native | 7 | 1 | 4 | 1 | 0.25 | 251.5 | 159.5 | 0.000 | ContamTransportEngine |
| 8184 | contamx | 7 | 1 | 4 | 1 | 0.25 | 251.5 | 159.5 | 0.000 | ContamXTransportEngine |

Pooled channel totals: plume 6,124.4 → 6,243.4 (+1.9%), pool 3,137.2 →
3,221.8 (+2.7%), hvac 0.0076 → 0.0077 (~equal). The sub-3% jitter on the
solver-independent channels is RNG-stream reorder from the engine build,
not a dose-delivery change: the verdict-bearing fields are bit-identical
and `implied_sar_confined_median` is identical on 8105/8184 and within
~1% on 8106/8112.

## What flu's settled verdicts actually load on

The prompt's fallback asks, if no settled flu verdict routes through the
transported pool, which channels they do load on. Measured at HEAD:

- **This cell (confined cabinmate SAR):** near-field droplet plume ~66% and
  local droplet pool ~34% of confined-slot dose; the transported `hvac`
  channel is ~0.0002%. The withdrawn FLU-DOSE-01 (pre-`1b9d37ca`) had
  `hvac` at ~33% of confined copies — the far-field rework did not break
  flu's confined verdict; it *removed* the transported channel from it.
- **Open-voyage onboard-acquired attribution (FLU-OPEN-01, `7f4702ef`):**
  caregiver ~49–68% and droplet ~44–50% of acquisitions; `hvac_airborne`
  ≤1% in every measured class.
- **Visibility sweep (FLU-VIS-01, `ca775a0b`):** `hvac_airborne` ≤~1%.

So no settled flu verdict loads on the transported pool — flu's airborne
dose is droplet (plume + local pool) and caregiver, both solver-independent.

## Caveats

- Four seeds × ~34 confined slots is sparse by design (local-only,
  ~7 min/cell on a 2-CPU box); the verdict rests on per-seed bit-identical
  verdict fields plus the channel composition being ~0 on the solver's own
  channel, not on aggregate inference.
- `pairs_observed` jitters by ±1–2 across lanes (23↔24, 25↔23, 7↔8) —
  pair-formation draws reorder under the different engine build; the
  confined-slot cohorts are identical.
- A conditioned confined cell suppresses cross-zone delivery by
  construction (the cohort is quarantined to staterooms); the ≤1%
  open-voyage `hvac_airborne` attribution generalizes the answer to the
  un-confined cells.
- `results/` payloads are local-only (gitignored). The committed surface
  CSV carries every verdict and channel column plus the engine-identity
  fields.

## Surface

Per-seed probe rows: `docs/flu/flu_confined_contamx_probe_surface.csv`.
Machine summary: `results/flu_confined_contamx_probe/summary.json` (not
committed — `results/` is gitignored; the committed surface carries the
same rows).
