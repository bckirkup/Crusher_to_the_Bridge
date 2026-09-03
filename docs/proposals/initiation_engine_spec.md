# Initiation engine: a boarding draw as the baseline, explicit seeds as the override

> **Status:** Proposed. Nothing here describes current behaviour. No constant
> in this document is adopted; the two prevalence intervals it consumes are
> already recorded in
> [`../literature/consensus_tranche_10.md`](../literature/consensus_tranche_10.md)
> and in the provenance register, and this document adds the mechanism that
> would let them enter the model at all.

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
      "age_draw": "duration_equilibrium"
    }
  },
  "explicit_seeds": [
    {"pathogen": "norwalk_gi", "count": 1, "role": null,
     "epoch": 0, "infection_age_days": 0, "dose": null, "strain": null}
  ]
}
```

**Precedence is an error, not a default.** If `boarding.enabled` is true for a
pathogen and that pathogen also carries a legacy `initial_infected`, the run
fails to load. A voyage must not silently receive both a drawn cohort and a
fiat index case, because the resulting incidence would be attributable to
neither. Scenario runs that want both — a Diamond Princess index case *on top
of* a realistic boarding cohort — say so by writing the seed into
`explicit_seeds`, which is additive by construction and appears in the run
artifact as such.

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
acquisition dose": the boarded host's presentation is decided by the natural
history in §4, not by `illness_probability` at a construction constant. Where
a scenario needs a stated dose — a controlled dose-response experiment — it
writes one, and the number is then in the config where it can be swept and
audited instead of in the source.

## 4. The infection-age draw, and why it is not a new parameter

Tranche 8 gave the infection axis its own clock (`shedding_duration_days`),
and #45 gave it a per-host stretch (the chronic median of 218 days). Those two
fields are sufficient to derive the boarding age distribution, so the
initiation engine adds no distribution of its own:

1. draw the host's own shedding duration `D_i` from the profile exactly as an
   infection acquired aboard would;
2. draw infection age `a ~ Uniform[0, D_i)` — the renewal-theory equilibrium
   age of an ongoing episode of length `D_i`;
3. run the existing onset and severity clocks forward to age `a`;
4. **reject and redraw if the host is symptomatic at boarding**, because the
   measurement that supplies the prevalence sampled people without
   diarrhoeal symptoms.

Step 4 is the part that makes the sample consistent with its own source, and
step 1 does something the deterministic count cannot: because prevalence is
length-biased, a host with a 218-day duration occupies about 14.5× more of the
prevalence pool than a 15-day one. The chronic share **among boarders** is
therefore much higher than the chronic share among infections, and it is a
*derived, checkable* quantity rather than a knob — which is the correct
consequence of tranche 10's finding that the chronic shedder's distinguishing
feature is duration and not prevalence.

The prediction to test, at the norovirus profile's GII incubation median of
1.2 days, `recovery_day` 3 and `shedding_duration_days` 15: of the ages
admissible under step 4, the pre-symptomatic window is about
1.2 / (15 − 3) ≈ **10%**. So on a classic hull the realistic baseline delivers
roughly **3–5 onsets in the first two days plus 30–50 silent shedders**, where
today's default delivers exactly one onset and no silent shedders. Those
silent shedders are the mechanism by which a voyage can exceed the 3% posting
threshold without an identifiable index case — the observable pattern VSP
records and the model currently cannot produce.

## 5. The open decision

Step 4 resolves the imported-host state *given* that the natural-history
clocks are the right generator for it. It does not resolve one thing, and no
source in tranche 10 does either: the 2.5% measurement pools genuinely
never-symptomatic infection with convalescent shedding after resolved
symptoms, a distinction this model has only been able to represent since
tranche 8. Under the §4 construction the split is implied by the profile's own
`symptomatic_fraction` and clocks rather than chosen — which is the
defensible option — but it is implied by parameters that were never sourced
against a *prevalent* sample, so the implied split is a model output that
nothing yet validates.

The alternative is to make the three-way split (pre-symptomatic /
never-symptomatic / convalescent) an explicit swept axis. That is one more
knob, against a derived quantity that may be wrong.

Recommendation: take the derived split, and record the implied composition in
the run artifact so it is falsifiable when a prevalent-sample measurement
appears. Do not add the axis until the derived value is shown to disagree with
something.

## 6. Prerequisites and verification

- The boarding gate must leave every existing run bit-identical when off, in
  the manner of `shore_exposure.enabled`: no RNG draws consumed on the off
  path. This is the property to test first, because tranche 6 showed that a
  new draw against the shared stream rebases every downstream decision.
- Host genetics already has a derived stream (#377); the boarding draw needs
  its own for the same reason.
- Sensitivity, not goldens, per `ci-test-design`: prevalence up must move
  boarding count up, the crew and passenger rates must move their own
  populations only, and the drawn ages must lie in `[0, D_i)` with no
  symptomatic host at epoch 0.
- The run artifact records the initiation mode, the drawn counts by role, and
  the implied state composition of §5, so downstream analysis can tell a
  prevalence-based run from an explicitly seeded one without re-deriving it.
- Task #51 (the COVID arm's missing `shedding_duration_days`) is a hard
  prerequisite for enabling boarding on `sars_cov2_resp`: step 1 has nothing
  to draw from until that field exists, and step 2 would silently collapse to
  the illness clock.
