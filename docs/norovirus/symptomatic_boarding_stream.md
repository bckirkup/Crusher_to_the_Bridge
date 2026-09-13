# The symptomatic boarding stream: partitioning the renewal-derived import rate

Status: derivation of record for the `boarding.symptomatic_stream` arm. Default
off; the arm is inert until a run selects it. No constant here is chosen against
A4, A8, A9, VSP, MIDRS or Park — the two inputs were sourced for other purposes
and the stream's rate is an identity over them.

## The gap this closes

The boarding cohort had no state in which a host is *ill at embarkation*. Every
state the draw could produce is either pre-onset (`presymptomatic`,
`incubating`), never-presenting (`never_symptomatic`), past its illness
(`convalescent`, whose window starts at `recovery_day`), or outside the
representable shedding window (`cleared`). That is not an accident of the age
draw: the prevalence the cohort is drawn from is *asymptomatic carriage*, so a
still-ill boarder is excluded from its denominator before any screening question
is asked.

Two consequences followed, and both are the reason this arm exists:

1. VSP §4.1.1.2 (2018 Operations Manual, p. 31) requires reportable AGE cases to
   include crew whose symptom onset was up to three days before boarding. The
   engine could not generate that host at all, so the observed crew numerator
   contains a class of case the model structurally cannot produce.
2. A gangplank screen had nobody to turn away: post-onset age at boarding was
   3–15 days by construction (`recovery_day` = 3 was the convalescent window's
   lower edge), so "onset within the last three days" had probability zero.

## The partition

Write \(I\) for community case incidence per person-year, \(f\) for the
never-symptomatic fraction of infections, \(D\) for mean detectable duration in
days, and \(E[T]\) for mean illness duration in days. The renewal identity
already in use for the import rate (`rate_mode: "renewal"`) gives the
RNA-positive prevalence per role

\[
p_{\text{total}} = \frac{I}{1-f}\cdot\frac{D}{365.25},
\]

because \(I/(1-f)\) converts case incidence to infection incidence. Of the \(D\)
detectable days an infection contributes, the ones on which the host is *ill*
number \(T\) for a presenting host and zero otherwise, so the expected
symptomatic-day contribution per infection is \((1-f)E[T]\) and

\[
p_{\text{sym}} = \frac{I}{1-f}\cdot\frac{(1-f)E[T]}{365.25}
             = I\cdot\frac{E[T]}{365.25},
\qquad
p_{\text{asym}} = p_{\text{total}} - p_{\text{sym}}.
\]

The never-symptomatic correction cancels: a symptomatic prevalence is case
incidence times illness duration, full stop. The two streams therefore **sum to
the same total the renewal arm already draws** — this is a partition, not an
addition, and that is what keeps it from double-counting the symptomatic days
already inside \(p_{\text{total}}\).

The partition exists only under `rate_mode: "renewal"`. The shipped
`screening_prevalence` series (passenger 3.25%, crew 1.85%) is a measured
asymptomatic-carriage rate with no illness-day decomposition, so no partition of
it can be formed; the arm refuses that combination rather than adding a second
stream on top of a rate whose composition is unknown.

## Inputs, and where each comes from

| Symbol | Value | Source | Grade / origin |
|---|---|---|---|
| \(I\) | 39.0 cases per 1,000 person-years, ages 15–64 | O'Brien et al. 2016, *J Infect Dis*, DOI 10.1093/infdis/jiv411, Table 1 | B, `T1` |
| \(f\) | 0.29 | register row `never_symptomatic_fraction` (adult challenge) | as registered |
| \(D\) | 28 days | Atmar et al. 2008, DOI 10.3201/eid1410.080117 (median RT-PCR detectability) | B, `R` |
| \(E[T]\) | 2.5715 days | Harris et al. 2019 IID2, DOI 10.1186/s12879-019-3706-z, Fig 4C digitized survival table — the profile's own `illness_duration` model | B, `F4·dig` |

\(E[T]\) is read from the profile rather than restated: under
`illness_duration.draw = "empirical_survival"` it is the exact mean of the
authored survival table, and under `draw = "point"` it is `recovery_day`. The
stream is therefore coherent in both duration modes, and selecting the dispersed
duration arm moves this rate through the same table that governs clearance. The
mean is a population quantity, so the per-host chronic recovery adjustment does
not enter it.

## The numbers this yields

With \(I = 39.0\), \(f = 0.29\), \(D = 28\), \(E[T] = 2.5715\):

| Quantity | Value |
|---|---|
| \(p_{\text{total}}\) | 0.4211% |
| \(p_{\text{sym}}\) | 0.02746% |
| \(p_{\text{asym}}\) | 0.3936% |
| symptomatic share of the RNA-positive cohort | 6.52% |

Expected symptomatic passengers embarking per voyage: 0.12 (expedition, 450),
0.52 (classic, 1,910), 0.82 (spirit, 3,000). The stream is small in count and
its interest is entirely in *where on the shedding curve* it lands: a
symptomatic boarder embarks at or near the symptomatic peak, whereas a
convalescent import boards past it.

Under `draw = "point"` (\(E[T] = 3\)) the same identity gives
\(p_{\text{sym}}\) = 0.03203%, and every host draws the same three-day illness,
so the arm exists but carries no dispersion.

## Where a symptomatic boarder sits in its own illness

For a stationary population of ongoing illnesses, the elapsed time since onset
(the backward recurrence time) has density \(S(a)/E[T]\). That is sampled
exactly, without integrating the curve, by the standard renewal construction:

1. draw the illness length length-biased, \(P(T = d) \propto d\,\Pr[T = d]\);
2. draw elapsed time \(a \sim U(0, T)\).

The host then boards with \(a\) days of illness behind it and \(T - a\) ahead,
which is stamped as `recovery_day = T` on the infection record so the existing
clearance seam ends the illness at the right time. Selection of *which* host
boards is uniform over the eligible pool: the length bias of a prevalent sample
is already carried by step 1, and reusing the shedding-duration weight
`_select_prevalent` applies to the asymptomatic stream would apply it twice.

Consequences worth stating, because they are what the campaign measures:

- \(\Pr[a \le 3] = 0.772\) — so VSP's three-day crew window covers about
  three-quarters of the symptomatic boarders, and has something to catch for the
  first time.
- \(E[a] = E[T^2]/(2E[T])\) exceeds \(E[T]/2\): the length bias puts elapsed
  time preferentially inside the long illnesses.
- A host whose elapsed time exceeds the authored shedding window boards
  `cleared`, on the same representability-boundary semantics the stationary age
  draw already uses.

## Emesis already ashore is not deposited onboard

The emesis schedule is drawn as onset-relative event times, and the emitter
fires every event whose time has passed the first time it looks. A host boarding
at \(a = 2\) days post-onset would therefore deposit its day-0.4 and day-1.1
episodes on the ship, where in fact they happened ashore. Events at or before
\(a\) are dropped at boarding; the per-episode load is *not* rescaled, because
the total is a per-subject cumulative shed partitioned over the illness's
episodes and the ashore share of it was not deposited onboard.

## Open items this arm does not settle

- **Pre-boarding treatment.** `apply_treatment_at_onset` is not applied to a
  symptomatic boarder: whatever care it sought ashore is unmodelled, so its
  drawn duration is untreated. Reported cases onboard are unaffected; the
  duration is, in the direction of being slightly long.
- **The resolving-phase bound.** Norovirus's `resolving` clinical phase carries
  `dpi_max: null`, which resolves to the *profile* recovery day rather than the
  host's, so a host drawn a long illness loses its diarrhoea feature at day 3.
  Recorded in the ledger; unchanged here.
- **Reportability.** A symptomatic boarder becomes a reported case through the
  ordinary surveillance path once onboard. VSP's §4.1.1.2 clause — a crew
  onset up to three days *before* boarding counted in the reportable numerator —
  and the three-day crew assessment with its declaration compliance are the
  following change, and both are measured against this stream rather than
  assumed by it. Onset back-dating has landed alongside this stream: the
  syndromic modality now reads `epochs_since_symptom_onset` from the infection
  record instead of stamping onset at first observation, so a host ill at
  embarkation carries its true (possibly negative-epoch) onset into the
  detection-delay gate and the onset-observation record.
