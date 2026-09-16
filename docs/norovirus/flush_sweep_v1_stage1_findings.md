# Stage 1 of the flush sweep: the emission arithmetic holds, the saturation inference does not

Status: measured. Companion to the generated tables in
[`flush_sweep_v1_stage1_readout.md`](flush_sweep_v1_stage1_readout.md);
design and declared uncertainty in
[`flush_aerosolisation_v1.md`](flush_aerosolisation_v1.md). Every dose
figure in this repository remains void pending refit
([ledger](norovirus_open_ledger.md)).

Stage 1 ran four arms — `off` (the item-42 `dwell_weighted`
configuration, shared heads executing with the flush route off) and
`flush_aerosol_fraction` at 1e-9, 1e-7 and 1e-5 — on one seed prefix
(8000–8099) across six hull/length cells, 2,400 runs. Imports were
identical in 1.000 of pairs in all 18 contrasts, so every difference
below is the route and nothing else.

## 1. The emission arithmetic is confirmed, and is exactly linear

Pooled inhaled particles per exposure event, against \(N_{50} = 16{,}871\):

| arm | classic 7 d | spirit 7 d | expedition 7 d |
|---|---|---|---|
| 1e-9 | 1.59 | 0.81 | 15.8 |
| 1e-7 | 138 | 84.3 | 1.48e3 |
| 1e-5 | 1.36e4 | 2.22e4 | 7.70e4 |

Each decade pair is a clean ×100, as a linear emission term must be, and
the level agrees with the closed-form prediction (0.77 particles per
visit at 1e-9 for a peak shedder in a median 18.6 m³ head) to within a
factor of ~2 — the residual being the mixture over titre, head volume
and multi-flush accumulation rather than a single peak shedder. The
expedition's per-exposure dose is an order of magnitude higher than the
big hulls' at every fraction: fewer, smaller heads concentrate the same
bolus. So the mechanism behaves as derived, and the small hull is the
one where a flush is worth the most per exposure.

## 2. My saturation prediction was falsified at the outcome level

I predicted that 1e-5 and above would saturate and therefore carry no
information. That prediction was correct about the **per-exposure
infection probability** and wrong about the **voyage**. Secondaries per
import, pooled:

| cell | off | 1e-9 | 1e-7 | 1e-5 |
|---|---|---|---|---|
| classic 7 d | 0.002 | 0.004 | 0.584 | 3.737 |
| classic 12 d | 0.002 | 0.002 | 0.481 | 13.214 |
| expedition 7 d | 0.167 | 0.176 | 0.569 | 1.892 |
| expedition 12 d | 0.235 | 0.186 | 0.480 | 3.461 |
| spirit 7 d | 0.242 | 0.135 | 1.271 | 11.385 |
| spirit 12 d | 0.105 | 0.108 | 2.585 | 29.462 |

From 1e-7 to 1e-5 — two decades of fraction, across which one
exposure's probability is flat — the outcome still rises 3–11×. The
reason is that a voyage is not one exposure: saturating each exposure
still multiplies the number of exposures (flush recipients per voyage
rise 142→217 on classic 7 d, 524→1,730 on spirit 12 d) and each new
infection is itself a shedder who flushes. The dose-response knee bounds
the per-event term; it does not bound the epidemic. **Placing stage 2 on
"where the per-visit probability saturates" would therefore have been
the wrong rule, and the falsifier arm is what caught it.** The staging
was still right for a different reason: the arms it declined to run
(1e-4, 1e-3) sit above a fraction that already produces 470 postings per
1,000 voyages, which is an outcome regime, not a measurement.

## 3. Where the route first becomes resolvable

The paired Δ secondaries interval is the sharpest readout, because
posting is a tail statistic and 100 seeds resolve little of it:

- **1e-9 — null in all six cells.** Every Δ secondaries CI straddles
  zero (e.g. classic 7 d +0.010 [−0.020, 0.050]); two cells are
  nominally negative. The route runs (94–99 of 100 voyages emit on the
  big hulls) and moves nothing: at ~1 particle per exposure it is the
  same kind of result as the structure-only sanitary arm.
- **1e-7 — resolvable in all six cells.** Every Δ secondaries CI
  excludes zero (+0.25 to +16.5 secondaries per voyage), flush takes
  30–63% of dominant attributions, and posting has only just begun to
  appear (0/1,000 in five cells, 30/1,000 on spirit 12 d).
- **1e-5 — large everywhere.** +1.8 to +195 secondaries per voyage, 19
  of 100 seeds gaining a posting on two cells and 47 on spirit 12 d.

So the resolvability crossing lies strictly inside the open interval
(1e-9, 1e-7) — one decade wide, bracketed on both sides by measurement
rather than by argument. That, and not any anchor, is what stage 2
samples.

## 4. What this does and does not say about the observed series

Reported beside the measurement, used to select nothing: A9's
fleet-pooled posting probability is 4.19–5.58 per 1,000 voyages, and
18.3 for the 11–14 day band. Stage 1's posting column brackets that
range — 0/1,000 at and below 1e-7 in five of six cells, 30–470/1,000 at
1e-5 — which means the campaign has the observed series *inside* its
span rather than at one end of it. It does **not** mean the fraction
that reproduces A9 is the true fraction: no decade acquires standing
from its distance to an anchor, and the vacuum-versus-gravity gap
(no virus measurement exists for a vacuum marine system) remains the
reason the sourced interval [1e-9, 1e-3] stays frozen and unnarrowed.

What can be said without fitting anything: a flush term anywhere at or
above the resolvability crossing supplies the amplification the droplet
deletion removed, and supplies it through a venue the ship actually has
(shared heads), on an event the host actually performs (diarrhoeal
defecation), with an emitted quantity whose two factors — bowl titre and
107 g stool mass — are sourced independently of any cruise outcome. The
one unsourced factor is the aerosolised share, and it is still a span.

## 5. Stage 2, declared before it runs

Arms: **3e-9, 1e-8, 3e-8** at 200 paired seeds (the same block, extended
prefix), on the same six cells — half-decade resolution inside the
measured crossing interval, chosen because that is where Δ secondaries
goes from straddling zero to excluding it in every cell. 3 arms × 6
cells × 200 seeds = 3,600 runs; the `off` and 1e-7 arms are re-read from
stage 1 on the shared 100-seed prefix rather than re-run.

The stage-2 readout answers one question — at which half-decade does the
paired contrast first exclude zero, and in which cells — and is
forbidden from answering "which arm best matches A9/A4/MIDRS". If the
crossing turns out to sit below 3e-9, the finding is that the route is
resolvable at Johnson's own measured bottom decade, which is a statement
about the evidence and not about the ships.
