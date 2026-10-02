# Hazard source model: emitters, fields, and the penetration adapter seam

> **Status:** Implemented, off by default — `ENV-SOURCE-01` (companion to
> `proposals/ship_function_capacity_spec.md` §8). Declaration parsing lives in
> `engines/hazard_sources.py`; deposition into `env_contamination` zone pools
> in `engines/transmission_core.py` (`_deposit_hazard_sources`); transport in
> `picard_framework/simulation/ship_simulation.py`
> (`_transport_hazard_source_pools`). Worked example:
> `data/platforms/spirit_cruise_3000/voyage_config.json` (`hazard_sources`
> block, `enabled: false`).

This layer declares where non-pathogen (or pathogen) hazard mass enters the
ship: an **emitter** is a scheduled mass source writing into
`env_contamination[substance_id][zone]` each epoch — the same pools the scalar
`environmental_contamination` arm reads. Absent or `enabled: false`, nothing
registers and every seeded run is bit-identical.

## Where declarations live

Three layers merge into one block, later winning on same-id entries:

1. The pathogen-profiles file's top-level `hazard_sources` key (shared,
   platform-agnostic declarations; read only when profiles come from
   `multi_pathogen.profiles_path`, not `resolved_profiles`).
2. A platform `voyage_config.json` `hazard_sources` block (the worked
   example's home; platform-scoped zone ids validate here).
3. `hazard_sources` in run config / `config_overrides` (the campaign arm;
   `config_overrides.voyage.hazard_sources` also reaches the voyage layer).

`emitters`, `substances`, and `penetrations` lists merge by their id key —
a later layer overrides a same-id entry key-by-key. `enabled` resolves to the
last layer that declares it (default `false`), so a run can arm a platform's
disabled block with `hazard_sources.enabled: true` alone, and a layer can
disarm one entry with `{..., "enabled": false}`.

## Substances

```json
{
  "substance_id": "voc_spill",
  "transport": "armed",
  "environmental_contamination": {
    "source_zones": ["Engine_Room"],
    "baseline_environmental_load": 0.0,
    "base_emission_rate_per_day": 1.0,
    "exposure_probability_per_day": 0.5,
    "spore_decay_rate_per_day": 2.0,
    "colonization_rate_per_day": 0.0
  },
  "parameters_provenance": "NULL-SOURCE: ..."
}
```

A substance registers as a profile fragment marked `hazard_substance: true`
with `person_to_person: false` (the machinery owns that key and refuses
overrides) and `dose_response: {model: exponential, k: 0.0}` — dose is
recorded on the strain dose ledger but never converts to infection; the
effect arm is ENV-HAZARD-01's. `initial_infected` is `null`: no fiat index
case. Substances never shore-seed (`_shore_pathogen_id` skips them) and a
mid-cruise `introduction_epoch` does not apply — scheduling lives on the
emitter, not the profile.

`transport`: `"armed"` (default) steps the pool through whichever transport
engine is armed — the native HVAC airflow network or ContamX, identical to
pathogen airborne mass; `"none"` keeps a standing field that never leaves its
zones. `environmental_contamination` accepts exactly the reservoir scalars
listed in the schema; `enabled`/`person_to_person` are rejected.

## Emitters

```json
{
  "emitter_id": "engine_room_voc_release",
  "substance_id": "voc_spill",
  "kind": {"placement": "point", "field": "dynamic"},
  "zones": ["Engine_Room"],
  "schedule": {"start_epoch": 6, "duration_hours": 6},
  "rate": {
    "kind": "functional",
    "functional_form": "exponential_decay",
    "mass_per_hour": 2500.0,
    "decay_rate_per_hour": 0.7,
    "source": "NULL-SOURCE: ...", "grade": "C"
  }
}
```

* `kind.placement`: `point` (exactly one zone) or `multipoint` (the **full**
  declared rate replicated into every zone — replicated point emitters, the
  same semantics the scalar arm gives each `source_zones` entry).
* `kind.field`: `standing` requires `rate.kind: constant`; `dynamic` requires
  `series` or `functional`.
* `schedule`: `start_epoch` (the `introduction_epoch`-style onset) plus
  optional `duration_hours`; the last covered epoch may be partial and its
  deposit scales to covered hours. A `series` beyond its declared length
  emits zero — the window ends where the table ends.
* `rate.kind`:
  * `constant`: `mass_per_hour`.
  * `series`: `series_per_hour`, one rate per epoch from onset.
  * `functional`: `functional_form` ∈ `exponential_decay`
    (`mass_per_hour`, `decay_rate_per_hour`) or `linear_ramp`
    (`mass_per_hour` plateau, `ramp_up_hours`). Epoch mass integrates the
    closed form analytically — nothing compounds by hand.
* `substance_id` may also name an existing pathogen profile: the emitter then
  tops up that pathogen's zone reservoirs (the scalar arm as a `standing,
  multipoint` shorthand), with no other behavior change.

Every rate carries `source` + `grade`; `source: "NULL-SOURCE"` is the
declared-arm spelling. All rates are `*_per_hour`, durations `*_hours` —
never `*_epochs`.

## Penetration adapters

```json
{
  "penetration_id": "harbor_plume_promenade",
  "substance_id": "harbor_plume",
  "adapter": "uniform_outdoor",
  "zones": ["Promenade", "LidoBuffet"],
  "penetration_factor": 0.3,
  "outdoor_field": {"kind": "uniform", "concentration_per_hour": 40.0},
  "schedule": {"start_epoch": 0, "duration_hours": 12},
  "source": "...", "grade": "C"
}
```

A penetration couples an off-ship field to the ship at declared zone points.
At model build the named **adapter** resolves the spec into an `EmitterSpec`
(`origin: "penetration:<id>"`); everything downstream is ordinary emitter
machinery. The contract is one function signature:

```python
PENETRATION_ADAPTERS: dict[str, Callable[[PenetrationSpec], EmitterSpec]]
```

`uniform_outdoor` is the shipped analytic adapter: rate = outdoor
concentration rate × `penetration_factor`; a `uniform` outdoor field yields a
`standing` emitter, a `series` field a `dynamic` one.

**Where QUIC output drops in:** a plume solver's per-penetration-point
concentration time series becomes the `series_per_hour` on a
`solver`-flavoured adapter entry in `PENETRATION_ADAPTERS`, returning the same
`dynamic`/`series` emitter shape — one emitter per penetration zone, mass =
concentration × factor. The adapter never sees the epoch loop and the epoch
loop never sees the solver.

## Pool semantics

Deposits run at the top of `execute_transmission`, after zone occupancy is
built and before the per-pathogen pathway loop, as plain dict writes with
zero RNG draws. Emitter mass in a pool decays under the substance's
`spore_decay_rate_per_day` like any other reservoir level, and zone coverage
is the union of the substance's declared `source_zones`, every zone an
emitter covers, and — for armed substances — every zone already holding pool
mass (a transported field exposes and decays in zones no emitter named).
