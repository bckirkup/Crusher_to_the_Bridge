# Morris screen #36 on the rebuilt model: one factor resolves, five do not

Status: measurement, 2026-09-05. Supersedes
[`bounded_screen_results.md`](bounded_screen_results.md), which measured a box
that no longer exists. Design:
`../proposals/bounded_sensitivity_and_admissible_region_spec.md` §2. Harness:
`../../telemetry_buffer/observation_model/bounded_screen.py`. Raw output:
`../../telemetry_buffer/observation_model/bounded_screen_isolated_36.json` and
`bounded_screen_isolated_36_floor.json`.

Nothing here selects a parameter value, and this is not the feasibility test.
The screen ranks factors; §6 of the design forbids writing an admissible range
back into a profile, and #37 is a separate measurement that this one does not
anticipate.

## 1. What was run

350 simulations: 10 Morris trajectories over the current six-factor box, 7
design points per trajectory, 5 seeds per point — **the same five seeds
(500–504) at every point**, so each elementary effect differences two
matched-seed means. Grid of 4 levels, δ = 2/3. 168 epochs, 450 agents,
`mega_cruise_5000`, `norwalk_gi` from `active_profiles`, `co_seeded =
"isolated"`. 3 h 33 min wall clock. The floor is 20 further runs at the box
centre, same seeding mode.

| Factor | Interval | Transform | Grade |
|---|---|---|---|
| `secretor_negative_relative_susceptibility` | 0.04 – 0.83 | linear | B |
| `emesis_total_shed_gec` | 3.6 × 10⁷ – 3.1 × 10⁸ | log10 | B |
| `hand_to_surface_drying_multiplier` | 0.008 – 1.0 | log10 | B |
| `surface_decay_log10_per_day` | 0.067 – 0.79 | linear | B |
| `shedding_variance_log10` | 0.5 – 1.5 | linear | C |
| `environmental_faecal_release_log10_g_per_epoch` | 4.0 – 24.0 | linear | D |

**Isolated, not composite.** `active_profiles` seeds norovirus, influenza A and
SARS-CoV-2 with one index case each, and every scored output is a host-level
quantity that unions a host's lineages, so a bundle run's attack rate belongs to
no single pathogen (0.4348 co-seeded against 0.0052 norovirus-alone at the box
centre). This screen suppresses the other two pathogens' seeds. Seeding itself
is *not* a factor: one norovirus index case at every design point, so it shifts
every point equally and no elementary effect can absorb it. At 450 agents that
is an index-case density about 11× the 5,000-agent campaign's.

## 2. The floor, and the threshold derived from it

An elementary effect is a difference of two 5-seed means divided by δ, so the
noise scale of an effect is `SD·√(2/5)/δ`, **not** the single-run SD and not
`SD/√5` — the previous document's threshold omitted both the difference and the
division and was about 2.1× too permissive as a result. Under pure noise, μ\*
averages 10 half-normal draws, so its null expectation is `0.798·s` with
standard error `0.185·s/√10`; the critical value below is that null plus two
standard errors of it.

| Output | Single-run SD, 20 seeds | Effect noise `s` | μ\* under noise | Critical μ\* |
|---|---|---|---|---|
| `attack_rate` | 0.01072 | 0.01017 | 0.00812 | 0.01188 |
| `ever_ill_attack_rate_passenger` | 0.00502 | 0.00476 | 0.00380 | 0.00556 |
| `reported_case_attack_rate_passenger` | 0.00473 | 0.00448 | 0.00358 | 0.00524 |
| `reported_case_attack_rate_crew` | 0.00855 | 0.00811 | 0.00647 | 0.00947 |
| `peak_epoch` | 64.11 | 60.82 | 48.53 | 71.01 |
| `vsp_posted` | 0.0 | 0.0 | — | — see §5 |

`s` is an **upper bound**: common random numbers correlate the two means and
subtract a non-negative amount of shared variance, unmeasured here. A factor
above the critical value is therefore above it conservatively; a factor below it
is *indistinguishable from stochastic noise at this design size*, which is not
the same claim as insensitive and does not license freezing it.

## 3. The ranking

One factor clears the critical value, and it clears it on the whole-ship and
both passenger channels:

| Output | μ\* | Ratio to critical | μ | σ |
|---|---|---|---|---|
| `attack_rate` | 0.02341 | 1.97 | −0.02341 | 0.02568 |
| `ever_ill_attack_rate_passenger` | 0.00989 | 1.78 | −0.00989 | 0.01098 |
| `reported_case_attack_rate_passenger` | 0.00826 | 1.58 | −0.00826 | 0.00932 |
| `reported_case_attack_rate_crew` | 0.00448 | 0.47 | −0.00224 | 0.00700 |

That factor is `environmental_faecal_release_log10_g_per_epoch`, and μ\* = |μ|
exactly on the three channels it clears: every one of its ten elementary effects
had the same sign, monotone across the box. The sign is negative because the
factor is −log10 grams — more release, higher attack rate.

Below the critical value on **every** continuous output:

| Factor | Best ratio | Where |
|---|---|---|
| `emesis_total_shed_gec` | 0.74 | `reported_case_attack_rate_passenger` |
| `surface_decay_log10_per_day` | 0.58 | `reported_case_attack_rate_passenger` |
| `secretor_negative_relative_susceptibility` | 0.51 | `reported_case_attack_rate_passenger` |
| `shedding_variance_log10` | 0.40 | `reported_case_attack_rate_passenger` |
| `hand_to_surface_drying_multiplier` | 0.34 | `ever_ill_attack_rate_passenger` |

Four consequences.

**The screen resolves the weakest-sourced factor and nothing else.** The one
factor above the floor is the grade-D one — the only factor in the box whose
interval is an assumption rather than a measurement — and it is also the one the
freedom audit records as unusable as a calibration axis. So the ranking's
practical content is that the model's scored outputs are, over this box,
dominated by the quantity we have the least right to place. That is a statement
about the box, not a licence to fit it.

**This is not the old ranking with new labels.** The 2026-09-01 pass put
`innate_nonsusceptible_fraction` first and faecal release third. That factor no
longer exists (partial susceptibility replaced the removed-fraction mechanism),
`contact_transfer_fraction` is retired as unidentifiable, the emesis pair became
a single total-shed factor, three intervals were recut, and the seeding is now
isolated. The two rankings share no comparable row and the old order must not be
carried forward.

**Five factors below the floor is a statement about the design, not about the
biology.** At 450 agents with one index case the isolated norovirus epidemic at
the box centre reaches an attack rate of ≈0.005 — a handful of cases, mostly at
the edge of extinction — so nearly all of the between-point variation the design
sees is takeoff-versus-fadeout. Raising the resolution needs more seeds per
point (the floor SD is the binding term, and it falls as 1/√seeds), not more
trajectories.

**Both `reported_case` channels rank the same factor first as the
infection-level ones, and the crew channel resolves nothing.** No factor clears
the critical value on `reported_case_attack_rate_crew`, so this screen says
nothing about which parameters drive the passenger/crew asymmetry A5 is scored
on.

## 4. Where the channels disagree

`emesis_total_shed_gec` is the top-ranked factor on the crew reported-case
channel (μ\* 0.00537, ratio 0.57) while faecal release leads everywhere else —
below threshold, so it is a difference in an unresolved ordering rather than a
measured disagreement, but it is the same crew/passenger split the previous pass
found and it is the one to watch when the design is refined.

`peak_epoch` is noise-dominated: the critical value is 71 epochs on a 168-epoch
horizon and no factor exceeds 60, so the timing channel carries no ranking at
all. σ ≥ μ\* on every row of every output except the three faecal-release rows
that clear, i.e. the resolved factor is also the only monotone one.

## 5. Posting fires in a thin part of the box, and this design cannot say how
thin

`vsp_posted` never fired at the box centre — 0 of 20 floor runs — so its floor
SD is structurally 0 and the threshold machinery above cannot discriminate. It
does fire inside the box: μ\* 0.15 for faecal release (μ −0.15, i.e. every step
that reduced release turned a posting off), 0.06 for
`secretor_negative_relative_susceptibility` and `emesis_total_shed_gec`, 0.03
for the remaining three. With 5 seeds the smallest resolvable seed-mean
difference is 0.2, so a μ\* of 0.03 is one trajectory step out of ten flipping a
single seed. **A binary output needs its own treatment — more seeds per point,
or a sign test over the steps — and no ranking for it is claimed here.**

## 6. What this does and does not unblock

It ranks. It does not bound, and it is not #37: no admissible region, empty or
non-empty, follows from a screen, and no interval in any profile changes on
account of it. The one usable input to the feasibility test is the resolution
finding in §3 — a design that resolves one of six factors at 5 seeds per point
tells the region search what its own seed budget has to be.
