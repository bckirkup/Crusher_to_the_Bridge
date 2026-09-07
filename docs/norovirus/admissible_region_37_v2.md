# #37 re-run on the repaired structure: the region is still empty, and now every anchor scored

Status: measurement, 2026-09-07. Supersedes the design limitation of
[`admissible_region_37.md`](admissible_region_37.md), not its findings. Harness:
`../../telemetry_buffer/observation_model/admissible_region.py`. Raw output:
`../../telemetry_buffer/observation_model/admissible_region_37_v2.json`
(every point's coordinates, cell summary, verdicts and measurements, merged
from the 256 shard streams under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/admissible_region_v2/`
through `admissible_region.py --merge`; AWS Batch job
`245fc5d4-b85e-4a5e-ae69-894bdab97e61`, job definition
`picard-bounded-design:4`, image `bounded-design-v4`).

Nothing here selects a parameter value; there were no admissible points to take
a marginal range over. No interval was widened, no anchor dropped, and no
constant moved after the gate ran.

## 1. What was run

**46,080 simulations**: 256 Sobol' points (scrambled, base-2, design seed 37)
over the **full ten-factor box**, **180 matched seeds (500–679) per point**, so
every point is the same 180 voyages under different parameters. 168 epochs, 450
agents, `mega_cruise_5000`, `norwalk_gi` from `active_profiles` with the other
bundle pathogens withdrawn at the boarding channel, pre-2020 era, no observation
scenario override. 256 AWS Batch array children on EC2 Spot, ~2.5 h wall clock,
256/256 succeeded, 0 failed.

Three things changed since #444, and each of them was a stated defect there:

1. **The box is the repaired one.** Ten factors, not six: the four food/faecal
   axes from FOOD-ARCH-01 and SYMP-EFF-01 are swept alongside the original six
   (`stool_events_baseline_per_day` 0.43–3.0 B, `stool_events_diarrhoeal_per_day`
   3.0–8.5 C, `food_hand_contacts_per_day` 0.3–46 C,
   `food_ingestion_fraction_per_day` 0.05–3.0 C).
2. **A9 is scored, not design-limited.** 180 seeds is the smallest cell in which
   one posting can land inside A9's target of 0.00419–0.00558 postings per
   eligible voyage, so the gate now resolves it: `a9_design_resolution.resolvable
   = true`, `design_limited_anchors = {}`. Every one of the 256 points carries a
   verdict on all six required anchors, and `unscored = 0`.
3. **2⁸ points, not 2⁷**, on the image that carries both the social inputs
   (PKG-02) and the VSP scoring series (PKG-03).

## 2. The result

**Empty. 0 of 256 points admissible, 0 admissible-pending, 256 inadmissible, 0
unscored.** The admissible volume fraction is 0.0. **Every pairwise joint pass
count is zero** — including A5+A4, the one pair #444 found two points for.

| Anchor | Target | Box span over 256 points | PASS | FAIL | misses low / high |
|---|---|---|---:|---:|---|
| A1 ever-ill AR, passengers | 0.10 – 0.22 | 0 – 0.301 | 13 | 243 | 240 / 3 |
| A2 ill / infected | 0.59 – 0.81 | 0 – 0.642 | 1 | 255 | 255 / 0 |
| A5 passenger/crew ratio | 2.5 – 4.5 | 0.427 – 1.805 (211 undefined) | 0 | 256 | 256 / 0 |
| A4 reported AR vs mega pre IQR | 0.0355 – 0.0749 | 0 – 0.301 | 7 | 249 | 228 / 21 |
| A8 incidence /100k travel-days | pax 16.9 – 29.2; crew 5.2 – 16.0 | pax 40.2 – 4,286; crew 37.9 – 3,853 | 0 | 256 | 0 / 512 channels |
| A9 postings / eligible voyage | 0.00419 – 0.00558 | 0.0333 – 1.0 | 0 | 256 | 0 / 256 |

**The take-off fraction is 1.0 at all 256 points.** Not a single one of 46,080
voyages went extinct anywhere in the ten-factor box.

## 3. What the emptiness is about

### 3.1 A9 now scores, and it fails high everywhere — by a factor of at least 6

This is the new result, and it is the sharpest statement the gate has produced.
The quietest point in the entire box posts on **0.0333 of eligible voyages
(6 of 180)**, against A9's ceiling of 0.00558: **6.0× too high**, and that is
the minimum over 256 points. A8 fails the same direction at every point and in
both channels, the quietest passenger cell being 40.2 per 100,000 travel-days
against a ceiling of 29.2.

So the extinction-versus-outbreak mixture VSP measures is **not reachable from
anywhere in this box**. That is the boarding-seed defect recorded in tranche 31
arriving as a measurement: norovirus boards at a carriage prevalence every
voyage, every carrier sheds within a factor of ~3 of a symptomatic case, and
there is no symptom-conditioned spreading-efficiency term — so every voyage
takes off, and the gate's own A9 arithmetic now says no parameter combination in
the sourced intervals can produce quiet voyages at the rate the anchor requires.

### 3.2 A1-against-A2 reproduces on the repaired structure

At the 13 points where A1 is in band, ill/infected spans **0.436–0.562 and never
reaches A2's floor of 0.59** — short by 1.05×, the same tension #444 measured at
a factor of 1.08 with 6 factors and 5 seeds. Widening the box by the four
food/faecal axes and the cell by 36× more seeds did not dissolve it.

Those same 13 points post on **0.994–1.0 of voyages**. Read together with §3.1:
the region where the attack rate is right is the region where every voyage is an
outbreak, which is a joint statement about A1 and A9 that no single anchor makes.

### 3.3 A5 now fails at every point, and its cell is mostly undefined

The passenger/crew ratio spans 0.427–1.805 against a target of 2.5–4.5 — **it
never even reaches the floor**, where #444 found 24 passes over a narrower box.
It is also undefined at 211 of 256 points (no crew case in the median voyage),
so the anchor is being read off 45 points. The ratio collapsing toward 1 as
epidemics grow is the mechanism #444 identified; here the box has no small
epidemics left in which it could be large.

### 3.4 The A4/A8 definitional conflict is unchanged, and now quantified in-run

The gate computes it: at these runs' 7.075-day voyages, A4's band implies
**501–1,059 per 100,000 travel-days against A8's 16.9–29.2** — no overlap, a
separation factor of **17.2**. A4 is conditional on a posted outbreak; A8 is
unconditional over all travel-days on the same numerator. A cell of identically
distributed voyages cannot satisfy both, and this is an anchor-mapping defect
rather than a parameter one.

### 3.5 A3, the construction band, is out of band at 134 of 135 defined points

Reported/symptomatic spans 0–1.0 and lands inside B1/#23's construction band of
0.35–0.45 at exactly one point. The observation model's capture still saturates
at 1.0 rather than sitting in the band, which is where the A1-versus-A4
incompatibility continues to live.

### 3.6 The posted voyages are the right size; there are 20× too many of them, and the quiet ones are not clean

A9's per-point pass/fail hides the shape of the failure, so this section reads
the posting counts directly. **36,087 of 46,080 voyages (78.3%) stayed below the
0.03 reported-attack-rate posting threshold** — quiet voyages are the rule, not
the exception. The anchor still fails because it needs them to be nearly the
*only* case: the median point posts on 20 of 180 voyages (11.1%) against A9's
0.42–0.56%, a factor of ~23; 242 of 256 points produce at least one quiet
voyage, and 14 post on all 180.

Where the quiet voyages live is the finding:

| A1 ever-ill AR at the point | points | voyages below the posting threshold |
|---|---:|---|
| < 0.01 | 217 | 34,829 / 39,060 (89%) |
| 0.01 – 0.05 | 13 | 1,113 / 2,340 (48%) |
| 0.05 – 0.10 | 10 | 143 / 1,800 (8%) |
| **0.10 – 0.22 (A1 in band)** | **13** | **2 / 2,340 (0.09%)** |
| > 0.22 | 3 | 0 / 540 |

There is no region that is simultaneously epidemiologically real and mostly
quiet. The box offers near-nothing or near-certain posting, and A1's band is
entirely inside the second.

**The bimodality is within a point, not only between points.** At the 222 points
that post on under half their voyages, **176 have a median voyage that reports
nothing at all** — reported and ever-ill attack rates of exactly zero — while
that same median voyage's **infection attack rate is 5.1–5.7%** (interquartile):
infection spreads and produces no ill passenger. Meanwhile the same 180 voyages
carry enough reported cases for a cell mean of 0.45–0.79% (interquartile), which
bounds the conditional mean among posting voyages at **≤ 5.5–6.8% reported
attack rate** (median bound 6.0%, 2.0× the threshold; the matching lower bound
is uninformative, so this is a ceiling, not an estimate).
The bound is derived from the cell's own travel-day-weighted A8 mean and its
posting count — the shard streams keep cells, not per-run rows, so the full
within-point distribution is not recoverable from the committed artifact.

That ceiling lands **inside A4's posted-outbreak IQR of 3.55–7.49%**. So
conditional on posting, the model's outbreaks are about the right magnitude;
what is wrong is their frequency, by a factor of ~23, and the fact that the
voyages in between are not small outbreaks but symptomless infection at ~5%
prevalence. A4 nevertheless fails low at 228 points, because it is scored on the
*median* voyage of a cell whose median voyage reports nothing — which is §3.4's
conditioning defect showing up as a level error.

This distinguishes two repairs that A9's tally alone does not. The excess is not
a missing gradation in outbreak size; it is that a symptomless 5%-infection
voyage is one draw away from a 6% reported outbreak under the same parameters.
That points at symptom conversion and the ill-per-infected path, i.e. the
missing symptom-conditioned spreading-efficiency term (§4's first follow-up),
rather than at seeding heterogeneity or a wider dose ladder.

Harness for this section:
`../../telemetry_buffer/observation_model/gate37_quiet_voyages.py`, which reads
the committed merged artifact and prints every number above.

## 4. What this licenses, and what it does not

- **Licensed:** no point of the sampled ten-factor box satisfies the six
  required anchors, or any pair of them, at 180 matched seeds per point; and A9
  in particular is unreachable from the whole box by at least a factor of 6 in
  the direction of too many postings.
- **Licensed, newly:** the emptiness is no longer attributable to anchors that
  never scored. All six scored; `design_limited_anchors` is empty.
- **Not licensed:** "the literature-bounded model is structurally infeasible."
  Two of the six anchors are still mapped onto a cell they do not describe
  (§3.4), one binds inside an assumed observation process (§3.5), and 256 points
  is a quarter of the spec's 2¹⁰ design.
- **Not done, deliberately:** no interval widened, no endpoint selected, no
  anchor dropped, no constant refitted, and no nearest point reported as an
  admissible region.

Follow-ups, in the order they change the verdict:

1. The missing symptom-conditioned spreading-efficiency term (tranche 31) is now
   the binding structural gap: without it, no box point produces quiet voyages,
   so A9 and A8 cannot be approached from any parameter value.
2. Re-map A8/A9 onto a fleet-scale cell, or state their conditioning explicitly,
   so §3.4's factor of 17 stops being carried by the parameters.
3. Fix the observation model's capture against A3's band, then re-read A4.
4. Only then is A1-vs-A2 (§3.2) a statement about transmission structure, and
   the categorical dose-response families are the first thing to vary.
