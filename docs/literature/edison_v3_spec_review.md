# Review: Edison's `formal_spec_v3.md` and `pre_establishment_clearance_params_v3.json`

**Status:** Review of two received artifacts. Nothing adopted; no constant, schema
or profile changed by this document. §4 records what A5 (#25) later settled about
the shape of any adoption of the clearance layer — no value, grade or interval
moved with it.

Both files were supplied on 2026-08-30. They are relevant to the provenance work
in [`parameter_sourcing_bundle.md`](parameter_sourcing_bundle.md) and to the
question list in [`edison_provenance_request.md`](edison_provenance_request.md),
and two of the questions there are already partly answered by them.

---

## 1. What the two artifacts are

- **`formal_spec_v3.md`** — a within-host specification audited against SHA
  `d557f39` (the PR #346 merge). Its title line still reads "v2.0", so the
  filename and the document disagree about version; we treat the content as
  authoritative over both.
- **`pre_establishment_clearance_params_v3.json`** — a parameter file for the
  new §3 mechanism, keyed by pathogen, in **exactly the shape our interval
  ledger needs**: every entry carries `value`, `range`, `grade` and a `note`,
  and some carry `citations`. Eleven pathogens plus `_defaults`.

The proposal in §3 is a **pre-establishment inoculum clearance** layer with two
mechanisms: a one-shot relative gastric survival multiplier on enteric routes,
and a continuous per-route exponential clearance of retained inoculum between
epochs. Both default to no-op (multiplier 1.0, rate 0.0), so legacy behaviour is
preserved when unconfigured.

## 2. Where it is stale against this tree

`d557f39` is **83 commits behind `main`**. The spec therefore predates the
SARS-CoV-2 provenance audit (#366), the interval/sensitivity work (#367, #368),
the A4 withdrawal (#360) and the `dose_adjustment` →
`environmental_faecal_release_log10_g_per_epoch` rename. Its Appendix A source
columns are the pre-audit ones: it still shows `surface_decay_per_day = 0.95`
for SARS-CoV-2 with a blank source, where #366 sourced it. Read the appendix as
a snapshot of the tree at the end of August, not as a current provenance
statement.

## 3. What it answers for us

**The dose-response form is not what our documents say it is.** §4.3.1, and the
code at `transmission_core.py:1594-1602`, implement a persistent **beta-frailty**
model: a per-host $r \sim \mathrm{Beta}(\alpha,\beta)$ drawn once, then
$P(\text{establish in epoch}) = 1 - \exp(-r\,D_{\text{epoch}})$, using *this*
epoch's dose. Several of our documents — including `ai_handshake.md` and the
COVID audit — quote the classic approximation $1 - (1 + D/\beta)^{-\alpha}$,
which corresponds to a Gamma frailty and is only used by an unrelated
population-level helper. Numerically the two agree to <0.001 at shipped
norovirus parameters, so no result moves; but the **identifiability argument
gets sharper, not weaker**. Under the frailty form, $r$ and $D$ enter strictly
as a product, so a rescaling of the emission side is absorbed *exactly* by a
rescaling of the Beta mean. What #366 argued as an approximate degeneracy is an
exact one. Our documents should be corrected to the frailty form.

**`shedding_curve_log10` is declared as $\log_{10}$(copies/g)** (§6.2), and
`dose_adjustment` as a log10 offset applied to it (§6.3). That is the first
explicit statement of the unit, and it converts our COVID Q8 from "what is this
number" to "grams of *what*, on a respiratory profile" — a sharper question,
and the audit's 2–4 order emission discrepancy should be re-checked under this
reading before it is quoted again.

**§3.7 is the NPI dose-reduction interface** that our open task #9 refers to. It
is an interface only: route-specific per-agent dose multipliers, with policies
and compliance explicitly out of scope.

## 4. The concern this raises

The clearance layer adds, per pathogen, one gastric multiplier and up to five
route-specific clearance rates. In the shipped parameter file the norovirus rates
are **Grade C** with ranges spanning a factor of two to seven (`fomite` 0.07–0.5),
and they multiply retained inoculum by $\exp(-\lambda\,dt)$ *on the same dose
axis whose scale is already unidentifiable* (§3 above). A constant per-epoch
clearance is, to leading order, a rescaling of that axis. Adopting it with
non-zero defaults would therefore hand back several of the degrees of freedom
the interval discipline was introduced to remove — the fitted-knob problem in a
new place, and harder to see because it is spelled as biology.

That is an argument about *how* to adopt it, not against the mechanism, which is
real: mucociliary clearance and gastric inactivation exist and their absence is a
genuine model gap. Three conditions would make adoption safe:

1. Ship with `rate_per_hour = 0.0` (the spec's own default) so legacy behaviour
   is exactly preserved and the mechanism is opt-in.
2. Enter the rates into the interval ledger as **intervals with their supplied
   grades**, and screen them alongside the existing box — a Grade C parameter the
   outputs are insensitive to across 0.07–0.5 costs us nothing, and one they are
   sensitive to must be resolved before it is used.
3. Never fit a clearance rate and a dose scale against the same observation.

**A5 (#25) has since settled the *shape* of any adoption, and it is not a
second layer.** Route efficiency has one owning field,
`route_efficiency_multipliers`; a per-route clearance rate parameterises the
same quantity, so a clearance layer standing beside the multipliers leaves
neither identifiable — condition 3 in the form the tree can enforce. Measured
rates now enter *through* the multipliers, by
`engines.transmission_core.route_efficiency_from_clearance_rates`, which returns
`lambda_reference / lambda_j` against a **declared** reference portal: the
portal the dose-response was fitted to, whose upstream losses its constants
already contain. Only the ratios survive that conversion, which is exactly why
it is safe — the absolute rate scale, the part that would have rescaled the dose
axis, cannot enter. A profile declaring `pre_establishment_clearance`,
`route_clearance_rate_per_hour` or `gastric_survival_fraction` is refused by the
schema and by the loader, inert defaults included, since shipping the layer at
no-op is how it becomes live later. Condition 1 is therefore met by there being
no layer to ship, and condition 2 still stands unmet: the rates are Grade C, the
reference portal is the §3.3.2 substantive claim below and is unsourced, and
nothing here adopts a value.

The one piece of the proposal that is a *substantive claim* rather than a knob is
the portal-assignment note in §3.3.2: for norovirus, virus inhaled via droplet or
HVAC is cleared by the mucociliary escalator **to** the pharynx and swallowed, so
respiratory acquisition is a delivery route to an enteric establishment site and
should take the enteric clearance rate. That collapses an efficiency penalty
between inhalation and ingestion which our route weights currently impose
implicitly, and it bears directly on the route-weight semantics question (Q15).
It deserves its own sourcing pass rather than being adopted with the parameter
file.

## 5. Not done here

No profile, schema or engine change. The clearance parameters are recorded as
*received*, not as sourced: the grades and ranges are Edison's, and this
repository's rule is that a value carries a source and an evidence grade **we**
can check at its point of definition.
