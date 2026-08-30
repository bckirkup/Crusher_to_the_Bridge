# Park re-measurement after emesis deposition

Re-run of `park_surface_check.py` with the emesis term of
`emesis_deposition_spec.md` added and nothing else changed. Full output in
`park_surface_check_out.txt`. The prediction was written down in §6 of the spec
before the term was implemented; this records what came out.

## 1. The level is a hit, and a sharper one than expected

One vomiting episode in a cabin deposits, from the measured constants alone:

```text
mean episode load                        1.055e7 copies
pool gain, cabin high-touch surface      2.029e6 copies
immediately after the episode            8.72e4 copies per 645 cm2 swab
```

Park reports 1.2-36% recovery on macrofoam swabs. Applying Park's own stated
recovery to the prediction:

| | copies per swab |
|---|---|
| Predicted, one episode, at Park's recovery | 1,047 - 31,400 |
| Park observed, cabins of sick passengers | 80 - 31,217 |

The predicted upper bound and Park's observed maximum agree to within 0.6%.

This is worth stating carefully, because it is easy to overclaim. Nothing was
fitted to Park; the inputs are Kirby's measured GII vomitus titre, an emesis
volume range that is an *estimate* rather than a measurement, Tung-Thompson's
measured aerosol fraction, and Booth's measured deposition footprint, none of
them ours. But agreement between the top of one range and the top of another is
one point of contact, the volume term is the weakest input, and the geometric
`touchable_fraction` is a declared Grade C assumption that happens to sit in
the middle of its plausible span. The correct reading is that a single
vomiting episode is the right order of magnitude to produce Park's dirtiest
cabins, and the hand-transfer chain alone (1,434 copies/swab) is not. That was
the hypothesis in `park_surface_findings.md` and it survives.

## 2. The gradient is still a miss, and emesis contributes none of it intrinsically

The per-swab gain from one episode is **identical** in a cabin and a public
lounge:

```text
cabin:  2.029e6 copies / 1.5 m^2  =  1.35e6 copies/m^2
public: 8.115e6 copies / 6.0 m^2  =  1.35e6 copies/m^2
```

That is not a coincidence and it is not a bug. Under uniform spread the pool
gain is `load x (area / 7.8)` and the concentration divides by `area`, so the
area cancels exactly wherever the high-touch area is smaller than the
deposition footprint. **Emesis carries no intrinsic cabin/public gradient.**
Every bit of the gradient it produces comes from *where the episodes happen*.

So the gradient is a measurement of localisation, and it is knife-edged:

| f (episodes in own cabin) | cabin copies/swab | public copies/swab | gradient |
|---:|---:|---:|---:|
| 0.50 | 9.87e4 | 2.99e4 | 3.3x |
| 0.80 | 1.57e5 | 1.22e4 | 12.9x |
| 0.95 | 1.86e5 | 3,314 | 56x |
| 0.99 | 1.94e5 | 948 | 205x |
| 1.00 | 1.96e5 | 357 | 549x |

Park's 100-300x corresponds to f between roughly 0.985 and 0.997. The band is
narrow enough that the gradient is a poor test of the emesis model and a
sensitive test of a behavioural quantity nobody has measured.

`f` is deliberately **not** a model parameter. The implementation deposits
emesis wherever the host is standing when a scheduled episode comes due, so the
effective `f` is whatever the schedule and confinement logic produce. Reading
`f` off Park's gradient and writing it into the model would be fitting, and is
refused.

## 3. What the model's own schedules can produce

Episodes are drawn uniformly over the three-day emetic window and deposit at
the host's location. A symptomatic passenger is in its cabin corridor for
roughly 8-10 hours a day before detection and roughly 22 hours a day after
confinement, so the schedule-implied `f` is bounded above by about 0.9 and is
realistically lower. **Inference, not measurement:** the simulated gradient
should therefore land nearer the 13x row than the 205x row — better than the
4.0x the hand chain alone gave, and still around an order of magnitude short of
Park.

This must be measured directly from emesis deposition records in a voyage
rather than inferred from the table, and that measurement is outstanding.

## 4. What the residual gradient says is missing

If the schedule-implied `f` is around 0.8 and Park implies around 0.99, the
missing element is a behaviour rather than a parameter: **a person who feels
sick goes to a toilet.** The model has no toilet, no bathroom, and no
sick-host movement rule; a passenger with sudden-onset nausea in a lounge
deposits into the lounge. This is the same well-mixed-versus-concentrated
defect found in the direct-contact route (PR #329), in the fomite chain
(PR #351), and in cabin occupancy, where the finest mixing compartment is a
37-person corridor rather than a two-berth stateroom.

## 5. Non-claims

- The single-episode level agreeing with Park's maximum is not validation of
  the model, and not validation of the emesis term's frequency or geometry.
  It constrains the product `volume x titre x touchable_fraction` at one point.
- The gradient is not reproduced. It is improved and remains a miss.
- Nothing here licenses adjusting `EMESIS_VOLUME_ML_RANGE`,
  `EMESIS_EPISODES_RANGE`, `EMESIS_DEPOSITION_AREA_M2`, or
  `HIGH_TOUCH_AREA_M2` toward Park's gradient.
- No claim is made that emesis affects A5. Route composition and the
  passenger/crew ratio have not been re-measured since PR #351.
