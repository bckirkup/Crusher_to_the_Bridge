# How flexible are the 20 severity/observation numbers?

Produced by `severity_prior_sensitivity.py` (Dirichlet concentration 80 on the
severity simplex, Edison's named coherent scenarios for eligibility/reporting,
40k draws, simplex-respecting elasticities). Central case reproduces the spec:
eligible/infected 0.499, reported/infected 0.302, reported/eligible 0.606.

## 1. Only four of the twenty numbers do any work

| component | d ln(rep/elig) | d ln(rep/inf) |
|---|---:|---:|
| `r_post[subclinical]` | 0.500 | 0.500 |
| `q[subclinical]` | -0.106 | 0.500 |
| `r_post[mild]` | 0.468 | 0.468 |
| `q[mild]` | 0.094 | 0.468 |
| `pi[mild]` | 0.094 | 0.277 |
| `pi[asymptomatic]` | 0.000 | -0.249 |
| `r_post[moderate]`, `pi[moderate]` | <= 0.03 | <= 0.03 |
| `pi[severe_critical]`, `q[moderate]`, `q[severe_critical]`, `r_post[severe_critical]` | ~0 | ~0 | 

The subclinical and mild reporting elasticities sum to ~0.97: reported/infected
is effectively a **two-parameter** function of this layer. The moderate and
severe entries are inert — `q` and `r` are pinned at 1.0 there by construction
and carry 0.1-1.3% of the mass — so they are **not identifiable from any cruise
observation we have** and should be declared as such rather than defended as
estimates. Their only real use is the fatality layer, which is not implemented.

## 2. The 0.60 anchor is weak, and that is the load-bearing finding

Under the Dirichlet prior, reported/eligible has a 95% interval of
**0.570-0.645** (12% of the median) and **98.6%** of draws fall inside the
0.60 +/- 0.05 anchor. Nearly any coherent severity vector satisfies it. The
anchor therefore does **not** identify the decomposition — it only rules out
gross mis-specification, exactly as the source review says.

## 3. The flexible quantity is the one the fit runs through

`reported/infected` is what converts modelled infections into VSP cases:

| source of flexibility | reported/infected |
|---|---|
| central (post-recognition) | 0.302 |
| Dirichlet 95% interval | 0.250-0.361 (+/-19%) |
| asymptomatic 0.19-0.35 | 0.327-0.262 |
| pre-recognition reporting | 0.276 |
| isolation-avoidance post-recognition | **0.188** |

So the prior alone gives +/-19%, and the coherent scenario span reaches
**1.6x** (0.188 to 0.302). The dose that reproduces a given VSP reported rate
inherits that band. Two consequences for the fit:

1. A single fitted dose quoted without this band is false precision. The dose
   must be reported with the reporting-layer band attached, or as a small set of
   named scenarios (central / pre-recognition / isolation-avoidance).
2. Isolation-avoidance is not a fringe scenario — under an active outbreak
   response with confinement, hosts have a motive to under-report, and it is the
   single largest lever in the layer. It belongs in the campaign as an arm, not
   as a footnote.

`reported/eligible` and `reported/symptomatic` are invariant to the asymptomatic
fraction by construction (it renormalises out), so the asymptomatic anchor
constrains only `reported/infected` — it is an independent constraint, not a
duplicate of the 0.60.
