# Initiation engine: a boarding draw as the baseline, explicit seeds as the override

> **Status:** Implemented as of this PR, in `engines/initiation.py`, and still
> off by default: a run with no `initiation` block is bit-identical to the
> behaviour §1 describes. No constant in this document is adopted; the two
> prevalence intervals it consumes are already recorded in
> [`../literature/consensus_tranche_10.md`](../literature/consensus_tranche_10.md)
> and in the provenance register, and nothing ships a value for
> `never_symptomatic_fraction` — enabling boarding without one is a load
> error. §1 describes what a legacy run still does; §§3–5 describe the
> mechanism that now exists.

## 1. What the model does today

There are **four** seeding paths, and all four are constructions.

| Path | Where | Count | Dose | Infection age |
|---|---|---|---|---|
| Legacy engine seed | `KorkinShipEngine._seed_initial_infection` | `cfg.initial_infected` (1) | `10^(9.0 − 4.0)` = 1e5, from the symptomatic curve's day-1 entry | 1 day |
| Pathogen-aware boarding seed | `orchestrator_init.py` | `profile.initial_infected` (1) | hard-coded `1e4` | `profile.initial_time_infected` (0) |
| Mid-cruise introduction | `step_mid_cruise_introductions` | `profile.initial_infected` (1) | hard-coded `1e4` | `profile.initial_time_infected` (0) |
| Shore introduction at a port call | `step_shore_introductions` | Bernoulli(λ_p) over the agents ashore | hard-coded `1e4` | 0 |

Four properties of that table matter more than any one of its cells.

**The count is deterministic where the measurement is a prevalence.** The
shipped default is one host per pathogen per voyage, chosen uniformly from any
non-immune agent. The measured boarding channel is a per-person probability,
so the number aboard is a Binomial draw, and its mean is one to two orders
above one — see §2.

**Role is not read.** The candidate pool is every eligible agent, so the
passenger and crew channels — which the literature separates by a factor of
about four — cannot be given different rates, and the drawn hosts' role
composition is whatever the agent ordering happens to produce.

**Infection age is zero, and `illness` is set to `NOT_ILL`.** Every voyage
therefore begins with hosts infected exactly at embarkation, i.e. at the head
of the shedding curve and before onset. A real boarder is somewhere inside
their own course, and where they are is what decides whether the ship sees an
onset on day 1 or day 5, or none at all.

**The dose is a construction constant in two different values.** `1e4` and
`1e5` appear with no provenance and no comment, and `acquired_particles` is
the argument of `illness_probability` — so these two numbers set the index
case's probability of ever presenting: at the norovirus profile's η/γ, 0.555
and 0.643 respectively, against 0.577 at its own beta-Poisson N50. They are
in model units and do **not** track `environmental_faecal_release_log10_g_per_epoch`,
so under the campaign's dose sweep every transmission-acquired dose rescales
and the index case's does not. This is recorded in the norovirus open ledger
with this change.

Only the fourth path — the shore hazard — has the right shape: a Bernoulli
over an eligible sub-population, gated so that runs with the gate off stay
bit-identical. It is the template for §3, with one difference. A port hazard
is an *incidence*: it converts a susceptible at a known moment, so age zero is
correct. Boarding is a *prevalence*: the host arrives mid-course, and the age
has to be drawn.

## 2. What the measured prevalence implies

From tranche 10: asymptomatic stool-RNA prevalence `[0.025, 0.040]` for
ordinary adults (Grade B) and `[0.007, 0.030]` for food handlers as the crew
analogue (Grade B). Agent populations are `num_agents` split by
`ship_graph.agent_roles.passenger_fraction`, default 0.70.

| Platform | Passengers | Crew | Infected passengers boarding | Infected crew boarding |
|---|---|---|---|---|
| `expedition_cruise_450` | 315 | 135 | 7.9 – 12.6 | 0.9 – 4.1 |
| `classic_cruise_1900` | 1,330 | 570 | 33.2 – 53.2 | 4.0 – 17.1 |
| `spirit_cruise_3000` | 2,100 | 900 | 52.5 – 84.0 | 6.3 – 27.0 |
| `mega_cruise_5000` | 3,500 | 1,500 | 87.5 – 140.0 | 10.5 – 45.0 |

Two consequences.

The shipped default of **one** imported host is between one and two orders
below the measured channel on every hull, and the campaign's widest swept
`initial_infected` axis — `[1, 2, 5, 10, 20, 50]` — reaches the *low end* of
the classic-hull interval only at its top value. The axis has been exploring a
region the measurement places below the floor.

But the imported hosts are, by the measurement's own inclusion criterion, not
symptomatic when sampled. Most of them will never be observed. §4 makes that
quantitative, and it is the reason the correction is not simply "seed 50
instead of 1".

## 3. The proposed configuration

Two blocks, deliberately not one mechanism.

```jsonc
"initiation": {
  "boarding": {
    "enabled": false,                  // default off: bit-identical to today
    "norwalk_gi": {
      "prevalence": {"passenger": 0.025, "crew": 0.007},
      "age_draw": "duration_equilibrium",
      "state_split": {
        "never_symptomatic_fraction": null,        // swept; no licensed value
        "presymptomatic_share_of_presenting": 0.04 // derived default, §4
      }
    }
  },
  "explicit_seeds": [
    {"pathogen": "norwalk_gi", "count": 1, "role": null,
     "epoch": 0, "infection_age_days": 0, "dose": null, "strain": null}
  ]
}
```

**Precedence is an error, not a default.** If **either** mechanism names a
pathogen whose profile still carries a legacy `initial_infected`, the run fails
to load — boarding, because a voyage must not silently receive both a drawn
cohort and a fiat index case; `explicit_seeds`, because initiation ownership is
per pathogen and an owned pathogen is dropped from legacy seeding, so the
profile field would be **ignored rather than honoured** and the campaign's swept
`initial_infected` axis would silently become the seed's count under an
unchanged `init<N>` run id. Either way the resulting incidence would be
attributable to neither number. So the `explicit_seeds` example above is
writable only once `norwalk_gi`'s profile field is nulled **and** the campaign
axis is re-keyed onto the seed; a scenario that wants a Diamond Princess index
case *on top of* a realistic boarding cohort states both under `initiation`,
which is additive by construction and appears in the run artifact as such
([tranche 24](../literature/consensus_tranche_24_never_symptomatic_adult_null.md)
§3).

**Legacy compatibility is preserved by the default.** With
`boarding.enabled: false`, `profile.initial_infected` and
`profile.initial_time_infected` keep their present meaning and every existing
campaign tier, override, and run-id parser (`resolve_initial_infected`, which
already accepts `initial_infected` / `n_initial_infected` / `n_index`)
continues to work unchanged. The engine-level `cfg.initial_infected` path is
the one to retire, since it seeds a pathogen-unaware infection at a third
dose.

**Prevalence enters as an interval, swept, not as a point.** The two numbers
above are the low ends; the register licenses no point value, so the screen
box gets `passenger ∈ [0.025, 0.040]` and `crew ∈ [0.007, 0.030]` as factors
and the shipped values are declared as the interval's low end rather than as
estimates.

**Dose becomes explicit or absent.** `dose: null` means "do not fabricate an
acquisition dose": the boarded host's presentation is decided by the state
draw of §4, not by `illness_probability` at a construction constant. Where a
scenario needs a stated dose — a controlled dose-response experiment — it
writes one, and the number is then in the config where it can be swept and
audited instead of in the source.

That is not a preference. Neither profile carries a `symptomatic_fraction`:
presentation is decided *only* by `illness_probability(acquired_particles)`,
so a host with no acquisition dose has no way to be assigned a presentation at
all. The state split of §4 is therefore a required input to the boarding
channel rather than an optional refinement of it — which is the substantive
reason it is a swept axis and not a derived diagnostic.

## 4. The state draw and the infection-age draw

A boarded host needs two things the deterministic seed never had: which part
of its course it is in, and how far into that part. The state comes from the
swept axis of §5; the age is then conditional on it, and the age needs no
distribution of its own — tranche 8's `shedding_duration_days` and #45's
per-host chronic stretch already supply one:

1. read the host's own shedding duration `D_i` — its stamped chronic stretch
   if it has one, the profile's `shedding_duration_days` otherwise — and
   select *which* eligible hosts board with probability proportional to that
   duration;
2. draw the boarding state from `state_split` — never-symptomatic,
   pre-symptomatic, or convalescent;
3. draw infection age `a` uniformly over the window that state occupies within
   `D_i` — the renewal-theory equilibrium age of an ongoing episode of that
   length, restricted to the state;
4. run the existing onset and severity clocks forward to age `a`, with the
   host's presentation history set from step 2 rather than from
   `illness_probability`.

Drawing the state first and the age second is deliberate. Drawing the age
first and reading the state off the clocks — the construction the first
version of this document recommended — makes the composition a silent function
of `presymptomatic_shedding_days`, `recovery_day` and
`shedding_duration_days`, none of which was sourced against a *prevalent*
sample. Rejection-sampling on "not symptomatic at boarding" would still be
needed to match the measurement's inclusion criterion, and the two mechanisms
would then be fighting over the same quantity.

Step 1 does something the deterministic count cannot, and it does it by
weighting *selection* rather than by drawing a duration. A host's shedding
duration is already a host property, assigned at initialization, so there is
nothing to re-draw; what prevalence does is over-represent long episodes in
proportion to their length, because a host with a 218-day duration sits in the
boarding population for about 14.5× as much calendar time as a 15-day one and
is that much likelier to be caught mid-episode. The count still comes from the
Binomial on the measured prevalence; only the identity of the boarders is
weighted. The chronic share **among boarders** is therefore higher than the
chronic share of the population, and it stays a *derived, checkable*
quantity: with `immunocompromised_fraction` 0.05 and `chronic_shedder_fraction`
0.228 the population's chronic share is about 1.1%, and weighting a 218-day
episode against a 15-day one lifts the share among boarders to roughly **14%**
— the correct consequence of tranche 10's finding that the chronic shedder's
distinguishing feature is duration and not prevalence. Note which fraction is
which: `chronic_shedder_fraction` is a share of immunocompromised hosts, and
applying it to every boarding host would silently promote it to a share of all
infections.

**A correction to the first version of this document.** It put the
pre-symptomatic share of imported hosts at 1.2 / (15 − 3) ≈ 10%, using the GII
incubation median as the pre-symptomatic window. That is the wrong window. An
imported host is in the sample because it is *shedding*, and the profile's own
pre-symptomatic **shedding** window is `presymptomatic_shedding_days` = 0.5
days (Atmar 2008: stool virus first detected at a median ~36 h, essentially
concurrent with onset). The admissible non-symptomatic shedding course is
therefore 0.5 + (15 − 3) = 12.5 days, of which the pre-symptomatic part is
0.5 / 12.5 ≈ **4%**, not 10%. So on a classic hull the realistic baseline
delivers roughly **1–2 hosts who will present in the first days, alongside
30–50 who will not** — where today's default delivers one presenting host and
no silent shedders.

The correction sharpens the finding rather than weakening it. The count of
*observable* index cases at embarkation was approximately right all along; what
is missing from the model is the entire silent shedding pool that accompanies
them. Those silent shedders are the mechanism by which a voyage can exceed the
3% posting threshold without an identifiable index case — the pattern VSP
records and the model currently cannot produce.

## 5. The imported-host state: an explicit swept axis

No source in tranche 10 resolves this: the 2.5% measurement pools genuinely
never-symptomatic infection with convalescent shedding after resolved
symptoms, a distinction this model has only been able to represent since
tranche 8. **Decided: the split is an explicit swept axis, not a derived
output** — the composition is declared in the config, appears in the run
artifact, and is screened, so a result that depends on it says so.

It enters as two independent coordinates rather than as a three-part
composition, because a simplex cannot be swept one factor at a time and
because each coordinate then has its own meaning and its own provenance:

| Coordinate | Meaning | Status |
|---|---|---|
| `never_symptomatic_fraction` | Share of imported infections that will never present. A property of infection, not of importation — the classical asymptomatic fraction | **Unsourced.** No value shipped; a sourcing tranche is opened for it |
| `presymptomatic_share_of_presenting` | Of the imported hosts that do present at some point, the share that has not presented yet at boarding | Derived default **0.04** from §4, swept |

The three states follow: `never = f_never`,
`pre = (1 − f_never) · s_pre`, `convalescent = (1 − f_never) · (1 − s_pre)`.
The engine validates that both coordinates lie in [0, 1] and reports the
resulting three-way composition in the artifact; nothing in the config states
the composition directly, so it cannot be set to something that does not sum
to one.

`never_symptomatic_fraction` ships **without a value and with the boarding
gate off**, rather than with a plausible one. It is a measurable quantity —
challenge studies and community cohorts report it — and it has not been
searched yet, so filling it in here would be exactly the kind of
citation-shaped assumption the register exists to prevent. Enabling boarding
requires setting it explicitly, which makes every run that uses the channel
carry the choice on the record.

What this costs is one knob, and the accounting is honest about it: the
initiation engine removes two construction constants (the 1e4 and 1e5 doses)
and a deterministic count, and adds two swept coordinates of which one is
sourceable and unsourced. The reason it is worth it is in §3 — with no
`symptomatic_fraction` in either profile, a dose-free imported host has no
presentation mechanism at all, so this is not a refinement of the channel but
a part of it.

## 6. Prerequisites and verification

Done, in `engines/initiation.py` and its callers:

- The boarding gate leaves every existing run bit-identical when off, in the
  manner of `shore_exposure.enabled`: a run with no `initiation` key resolves
  to `InitiationPlan((), (), legacy=True)` and consumes no new draw, which
  `tests/test_initiation_engine.py` asserts against the parent stream and the
  24-epoch orchestrator smoke confirms end to end.
- The boarding draw has its own derived stream, `_boarding_rng`, spawned
  **third** — after host genetics (#377) and the chronic-shedder stream, and
  only when boarding is enabled, so neither sibling is rebased.
- Sensitivity, not goldens, per `ci-test-design`: each prevalence moves its own
  role's count and leaves the other role's alone, every drawn age lies inside
  the window its state defines, no host is symptomatic at epoch 0, each
  `state_split` coordinate moves the realised composition in the one direction
  it owns, and the chronic share among boarders exceeds the profile's chronic
  share of infections — the length-bias claim of §4, asserted directly.
- The run artifact records the initiation mode, the drawn counts by role and
  pathogen, both `state_split` coordinates as configured, and the realised
  three-way composition. It is `engine.initiation_manifest`, written under the
  `"initiation"` key of `resolved_pathogen_profiles.json`, and defaults to
  `{"mode": "legacy"}` so the key always exists.
- Enabling boarding with `never_symptomatic_fraction` unset is a load error,
  not a defaulted run, and so is naming a pathogen whose profile still carries
  `initial_infected` — from **either** mechanism, boarding or `explicit_seeds`.
- The legacy engine-level seed at `10^(9.0 − 4.0)` is retired for any run that
  declares an `initiation` block; `profile.initial_infected` and
  `profile.initial_time_infected` still run exactly as before for every run
  that does not.

Landed with #54 (Track C, C1):

- `crusher_labs/config.yaml` ships an `initiation.boarding.norwalk_gi` block
  with all four coordinates, and the shipped `norwalk_gi` profile carries
  `initial_infected: null`, so the load-time refusal passes and
  `initiation_owned_pathogens` drops it from legacy seeding.
- `never_symptomatic_fraction` is **supplied by sweep, never licensed**
  ([tranche 24](../literature/consensus_tranche_24_never_symptomatic_adult_null.md)
  §3): the shipped block carries the adult-challenge midpoint 0.29 as the
  coordinate an unswept run uses, and the campaign sweeps the two register
  intervals as separate regimes (`adult_challenge` default, `community_cohort`
  by name) through `picard_framework/runs/mega_cruise_campaign/boarding_axis.py`.
- The campaign's index-case axis is re-keyed: sites that wrote
  `path_over["norwalk_gi"]["initial_infected"]` now write
  `config_overrides["initiation"]["boarding"]`, run ids carry the swept
  coordinate (`nsf<…>`, `bp<…>c<…>`, `psp<…>`) instead of `init<N>`, and a
  count axis listed for an owned pathogen is a generation error unless the tier
  declares `fiat_index_case: true`. Analysis reads the effective introduction
  count from the manifest's `drawn_by_role` when a run boarded.

Extended with #54's follow-on, to every shipped profile:

- **Coordinates live on the profile, not in `config.yaml`.** Each profile
  carries its own `boarding` block, so a scenario that loads a narrowed bundle
  neither inherits another pathogen's coordinates nor names an absent pathogen
  — which was a load error while the shipped block was global. `config.yaml`
  keeps only `initiation.boarding.enabled: true`; a config block still merges
  over the profile's, coordinate by coordinate.
- **Ownership is derived, not enumerated.** `initiation_owned_pathogens`
  reports whatever the resolved plan holds, and the campaign's
  `boarding_axis.shipped_boarding_blocks()` reads the bundles, so adding a
  pathogen with a block is sufficient and no list needs editing.
- **A second mode, `party`, for imports that arrive as a group.** One
  per-voyage Bernoulli at `party.probability`; on success one party of
  `party.size` boards, every member infected, selected cabin-mates-first and
  then same-zone, in the stated `role`. It is a distinct mechanism from
  `prevalence` and may not carry prevalence coordinates at the same time; the
  manifest records probability, size, role, whether the party boarded, and the
  realised composition, and run ids tag it `pty<permille>n<size>`. It exists
  because independent per-person draws over 7,000 heads are the wrong shape
  for Andes hantavirus, Ebola, measles or cholera: the realistic import is one
  small travelling party in which everyone is infected.
- **Per-pathogen `enabled: false`** withdraws one pathogen from the channel
  without disabling boarding for the rest, and a profile that keeps a fiat
  count (`legionella_pneumophila`, whose reservoir is the ship's water plant)
  simply carries no block.
- **Staged introductions stay staged.** A block's `epoch` draws that pathogen
  at that port call rather than at embarkation, and the boarding cohort size is
  independent of the introduction epoch.

Still outstanding:

- Task #51 (the COVID arm's missing `shedding_duration_days`) is a hard
  prerequisite for enabling boarding on `sars_cov2_resp`: step 1 has nothing
  to draw from until that field exists, and step 2 would silently collapse to
  the illness clock. The profile now carries a boarding block, so a run that
  boards COVID takes the illness clock until #51 lands — the shedding draw
  is the open half, not the introduction.
