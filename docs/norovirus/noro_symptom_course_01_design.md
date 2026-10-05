# NORO-SYMPTOM-COURSE-01 design — the infected → symptomatic-course draw

Status: declared, pre-run. Criteria in this file are frozen before any
cell runs; nothing below is altered after the surface is seen.

## Question

NORO-CHANNEL-03 (measured `d6c51c14`) and NORO-MEGA-IMPACT-01 (measured
`7e1b54bc`, 7,000-agent hull) both find the infected → symptomatic-course
link at 0.12–0.19 against the declared 0.6, hull-invariant. The
decomposition readout (`docs/norovirus/noro_symptom_course_01_decomposition.md`,
measured `50bc52ab`) splits the ~0.82 loss on the a1 fleet:

- **(a) the onboard presentation draw carries ~66% of the loss**
  (bounded [0.48, 0.74] by the dose-conditioned incubation window): on
  54,674 clip-free acquisitions — window longer than the 6 d incubation
  maximum, so the draw is guaranteed to fire — the realized
  never-presented share is **0.764** (pooled; per-voyage median present
  rate 0.234). The shipped dose-conditional Hill realizes a presentation
  rate *below the floor of either sourced `never_symptomatic_fraction`
  regime*.
- **(b) import side ~22% of the loss** (30,496 imports never ill aboard;
  funnel leg: `symptomatic_course − symptomatic_onboard` = 18.0% of
  infected pooled — presented courses whose window sits entirely off the
  voyage, essentially all imports);
- **(c) ramp-clipping ~13%** (inferred via the declared incubation
  survival function; [4%, 30%] across the dose-conditioning clamps — the
  voyage-window term is real but minor).

So the first-link gap is a **course-draw phenomenon, not a window
defect**: a sweep that can move ill/inf must move the presentation draw
itself, and the measured realization (0.234) sits below both declared
regimes of the register's `never_symptomatic_fraction` axis.

## Sweep axis — `symptomatic_fraction` on `norwalk_gi` (declared intervals only)

The register (`docs/parameter_provenance_register.md`, the
`never_symptomatic_fraction` row) declares the fraction **swept, never a
point**, as two unpooled regimes: `adult_challenge` {0.22, 0.29, 0.36}
and `community_cohort` {0.59, 0.635, 0.68}. Armed on the *onboard*
presentation draw as `symptomatic_fraction` = 1 − regime point:

- **challenge regime arms:** `symptomatic_fraction` ∈ **{0.64, 0.71, 0.78}**
- **community regime arms:** `symptomatic_fraction` ∈ **{0.32, 0.365, 0.41}**
- **baseline arm:** the shipped `illness_probability` Hill
  (η 0.508, γ 0.095), unmodified — the existing CHANNEL-04 dumps are the
  seed-paired baseline (see Pairing); no baseline re-run.

Mechanism: `presentation_probability` already honours a profile-level
`symptomatic_fraction` field (measured-proportion presentation,
dose-independent — the same form influenza_a and sars_cov2 carry); the
patch rides the manifest's `pathogen_overrides` vocabulary
(`{"norwalk_gi": {"symptomatic_fraction": <arm>}}`), exactly as the
boarding rungs' `illness_duration` patch does. Imports are untouched by
construction — `will_present` replaces the dose draw at boarding, so the
import side stays governed by `never_symptomatic_fraction` (0.29, the
cell's shipped coordinate — the boarding axis itself is already swept by
existing campaign machinery and is not re-declared here).

What the regime transfer means: the sourced intervals measure a
*boarding* population; applying them to onboard acquisitions is the
hypothesis under test, not an adoption claim. The campaign reads the
funnel's response curve across the union of declared points — no value
outside the two regimes is run, and the regimes are never pooled.

## Cells

Same spec source as CHANNEL-03/04 (`generate_tier_runs` over
`noro_outbreak_01_manifest.json`), 12 d voyages, 20 seeds per cell, and
the same hull × matchtag grid restricted to the two hulls with the
infection volume to resolve the split — expedition is dropped (131–591
infections/cell at 20 seeds cannot resolve a 0.05-step move):

| hull | tier | matchtags (cells) |
|---|---|---|
| classic_cruise_1900 | `fl_cls_12d_scr`, `fl_cls_12d_ren` | `rung-shipped,bp32p5c18p5` · `rung-shipped,bp40c30` · `rung-reportable` |
| spirit_cruise_3000 | `fl_spr_12d_scr`, `fl_spr_12d_ren` | same three |

The scr/ren rung contrast also spans `illness_duration_draw`
(shipped→point, renewal→empirical_survival) — the course-window term is
carried by the cell grid, not a separate axis.

Arms × cells: 6 sf arms × 6 cells × 20 seeds = **720 funnel runs**.
Fresh prefix `campaign/noro_symptom_course_01/` under the identical
`<tier>/<matchtag>/observation_channel_funnel_<arm>_seed<S>.json.gz`
scheme, with the arm label embedded in the run id.

**Mega witness (declared, canary-gated):** the a1 spec verbatim
(`fl_mega_impact_a1`, 7,000 agents, 288 epochs, nsf29 bp25c7) ×
sf ∈ {0.365, 0.71} (regime midpoints) × 20 seeds = **40 mega runs**,
zips written so the census leg of `symptom_course_decomposition.py`
reads the full (a)/(b)/(c) split at scale. The mega witness runs only
after the small-cell canary reports — its purpose is to confirm the
hull-invariance already measured on the baseline holds on the arms.

## Instrument

No engine change and no new dump field: the CHANNEL-03 funnel harness
(`deploy/aws/noro_channel_03_entrypoint.py`,
`tools/noro_diag/observation_channel_funnel.py`) already emits every
rung this readout consumes. New work is confined to:

- a campaign manifest (`noro_symptom_course_01_manifest.json`) arming the
  sf patch per arm;
- a `symptom_course_01` entrypoint/submit pair (clone of the
  channel_03/04 pattern);
- `tools/noro_diag/symptom_course_decomposition.py` (this stage's tool,
  already landed) run with `--funnel-root campaign/noro_symptom_course_01/`
  for the funnel-leg readout, and against the mega-witness zip prefix
  for the census leg.

## Pairing

Each sf-arm dump pairs against the **CHANNEL-04** dump at the same
spec+seed (`campaign/noro_channel_04/`, `1e158d47`, caregiver stack) —
the current-stack baseline. The CHANNEL-03 dumps
(`campaign/noro_channel_03/`, `d6c51c14`, pre-caregiver) remain the
deeper-history reference; they are the decomposition leg's data, not the
attribution baseline. CHANNEL-04's caveat carries: the sf patch changes
presentation *outcomes*, so an arm voyage is the same spec, not the same
voyage — divergence from the baseline twin is a treatment effect, not a
join violation.

## Readout list (frozen)

Per cell × arm, pooled over seeds and takeoff-conditional:

1. the CHANNEL-03 rung table — infected / symptomatic_course /
   symptomatic_onboard / syndrome_eligible / eligible_onboard /
   reported / lab_sampled / lab_confirmed / onset_dated, plus rep/elig
   and the caregiver columns the current harness emits;
2. the decomposition columns — `(b) = S−O`, `(a)+(c) = N−S`,
   `ill/inf = O/N`, the import/acquired split of `infected`, and
   `non_report_decomposition` per dump;
3. seed-paired deltas vs the CHANNEL-04 baseline on every rung;
4. the incidence side-effects — acquired_onboard share of infected per
   arm (the confinement feedback), and import share flatness (the sf
   patch must not touch the boarding draw);
5. mega witness only: the census-leg decomposition (clip-free present
   rate, clip-band split, resolved imports) from the run zips.

## Admissibility / report-immediately triggers (frozen)

- Any dump failing the identity `infected = onboard + (S−O) + (N−S)` —
  instrument defect; report, do not patch the readout.
- `presented/infected` ordering across the six sf arms not monotone in
  declared `symptomatic_fraction` on any cell (beyond seed-pairing
  tolerance) — the patch is not reaching the draw; report.
- On any sf arm, pooled `presented/acquired_onboard` farther than ±0.10
  from the declared sf once clip-adjusted by the decomposition's
  measured clip share (~0.10, inferred) — the patch leaks or the arm
  mislabels; report.
- Import-side movement on sf arms — imported share of infected, or the
  `(b)` term, moving materially (outside the CHANNEL-04 seed-paired
  envelope) on an arm that by construction cannot touch imports —
  report; the boarding draw is not isolated.
- Acquired volume moving >30% either direction on sf arms vs baseline —
  the confinement feedback over-delivers; report with the route split.
- `onboard_ill` < 0.5 × `presented_course` on any cell — the
  aboard-visibility path broke; report.
- A `symptomatic_fraction` arm's ill/inf exceeding its declared sf on
  clip-free-equivalent terms — over-presentation; report.

Success looks like: presented/infected ≈ declared sf × (1 − clip share)
on the small cells, ill/inf moving with it, the funnel's downstream
rungs responding in proportion, and the import side flat. Failure looks
like a flat first link (the draw is not the gap's carrier after all) or
an import-side move (the patch is not isolated).

## Gates

1. This file + the ledger declaration committed before any cell runs.
2. Local smoke: `generate_tier_runs` resolves each declared
   (tier, arm, seed) to exactly one spec, the sf patch lands in the
   bundled profile, and one funnel voyage writes a dump.
3. Canary ≥20 seeds on `fl_cls_12d_scr` × `rung-shipped,bp32p5c18p5` at
   sf = 0.71 (challenge midpoint) on the merge-SHA image, read out and
   reported before the remaining arrays submit.
4. Mega witness only after the small-cell readout reports; jobdef
   digest-pinned at the merge SHA.

## Artifacts

- decomposition tool + readout:
  `tools/noro_diag/symptom_course_decomposition.py`,
  `docs/norovirus/noro_symptom_course_01_decomposition.md`
- instrument: `tools/noro_diag/observation_channel_funnel.py` (unchanged)
- entrypoint: `deploy/aws/noro_channel_03_entrypoint.py` pattern
- S3 prefix: `s3://<bucket>/campaign/noro_symptom_course_01/`
- ledger: `docs/ledger/NORO-SYMPTOM-COURSE-01.md`

## Non-goals

- No engine, profile or constant changes — the sf field and the
  pathogen-override path already exist; nothing is fitted.
- No anchor re-score (the OUTBREAK-01-scale decision belongs to a later
  stage).
- No voyage-length or incubation-axis arms — (c) is measured minor.
- No fleet submission from this stage — the design freezes criteria;
  whether the campaign runs is the user's decision.
- The import-side (b)/(a) split at mega scale needs an instrument the
  census does not carry — declared out of scope, not silently worked
  around.
