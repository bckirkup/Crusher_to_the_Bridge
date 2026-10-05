# NORO-SYMPTOM-COURSE-01 decomposition — the infected -> onboard-ill loss

Status: measured readout (design input for `noro_symptom_course_01_design.md`).
No voyage was rerun; every number below is read off committed artifacts.

Measured at `50bc52ab` — census leg over the 288 MEGA-IMPACT-01 a1 zips
(`campaign/noro_mega_impact_01/fl_mega_impact_a1/`, engine `7e1b54bc`,
`--payload lean`, `--payload lean` zips still carry `summary.json` +
`growth_census.json.gz`) and the funnel leg over the 180 CHANNEL-03 dumps
(`campaign/noro_channel_03/`, engine `d6c51c14`, pre-caregiver stack).
Tool: `tools/noro_diag/symptom_course_decomposition.py` (regenerates
`results/noro_symptom_course_01_decomposition.{md,json}`).

## The question

MEGA-IMPACT-01 measured pooled ill/inf ≈ 0.18 on every arm against
(1 − `never_symptomatic_fraction`) = 0.71 — the course-window/draw loss is
the dominant term in the funnel, not reporting. This readout splits that
~0.82 loss:

- **(a) never-symptomatic draw** — the host's presentation draw fails, or
  it never fires because incubation never elapsed aboard;
- **(b) presented course never visible aboard** — convalescent or
  still-incubating imports whose symptomatic window falls entirely off the
  voyage (on the census this is the non-ill import bound; on the funnel
  dumps it is exact: `symptomatic_course − symptomatic_onboard`);
- **(c) infected too late for an onboard-visible course** — remaining
  voyage window shorter than the incubation draw.

### What the census can and cannot measure

`growth_census` `hosts[]` carries `agent_id`, `gen` (0 = import),
`infected_epochs`, `symptomatic_epochs`, `confined_epochs`,
`epoch_acquired` (onboard infections only) and the emesis markers — but no
`presented` flag, no onset epoch, no dose. So on the mega leg:

- (a) is measured directly on **clip-free** acquisitions — a host with
  `num_epochs − epoch_acquired > 144` (the 6.0 d incubation maximum at
  1 h epochs) is guaranteed its presentation draw aboard; a non-ill such
  host is a realized never-present draw, no model needed;
- (c) is measured exactly only for **certain-clip** hosts (window ≤
  incubation min 0.1 d ⇒ can never present aboard); the clip band is
  split *inferred* via the declared truncated-lognormal incubation
  survival function (median 1.2 d, GSD 1.56, truncated [0.1, 6.0] d),
  evaluated at dose factors 0.3 / 1.0 / 2.5 — the engine's own clamps;
- (b) is the non-ill import bound — `vomiting_axis`/`emesis_scheduled`
  persist as a partial presented marker (0 observed), so the bound is the
  whole non-ill import count; `gen: 0` rows with `infected_epochs: 0`
  additionally identify imports resolved pre-boarding.

Cross-checks (per voyage, census vs `summary.json`/`census` header):
`ever_infected`, `ever_ill`, `n_imports`, `n_acquired` — **0 mismatches
on 288/288 zips.**

## Mega a1 census leg — 288 voyages, pooled

| term | count | share of infected | label |
|---|---|---|---|
| infected | 172,689 | 1.000 | measured |
| onboard ill (`symptomatic_epochs` > 0) | 32,267 | **0.187** | measured |
| imports, never ill aboard | 30,496 | 0.177 | measured bound on (b) ∪ import-(a) |
| — of which resolved pre-boarding (0 infected epochs) | 97 | 0.001 | measured, pure out-of-window |
| acq non-ill, clip-free (window > 6 d) | 41,755 | 0.242 | **(a) measured** |
| acq non-ill, clip band (0.1 d < window ≤ 6 d) | 67,339 | 0.390 | measured, split inferred below |
| acq non-ill, certain clip (window ≤ 0.1 d) | 832 | 0.005 | **(c) measured** |

Expected ramp-clip over all 141,294 acquisitions under the declared
incubation SF — inferred, not measured — by dose-conditioned median
(dose factor 0.3 / 1.0 / 2.5 → medians 0.36 / 1.2 / 3.0 d):
**5,369 / 17,927 / 42,684 hosts**.

Allocating the inferred clip to the band: at the reference median the
non-ill loss of 140,422 splits as —

| term | hosts | share of infected | share of the loss |
|---|---|---|---|
| (a) never-symptomatic draw, acquisitions | ~92,000 (67,242 – 104,557) | 0.53 (0.39 – 0.61) | ~0.66 (0.48 – 0.74) |
| (b)-side: imports never ill aboard | 30,496 | 0.177 | 0.22 |
| (c) infected too late (inferred) | ~17,900 (5,369 – 42,684) | 0.10 (0.03 – 0.25) | ~0.13 (0.04 – 0.30) |

The (a) band follows the dose-conditioning uncertainty end to end; even
at the longest-median bound the draw, not the window, carries the loss.

Per-voyage: median ill/inf 0.186 (range 0.143–0.253); **realized
presentation rate on clip-free acquisitions 0.236 pooled**
(41,755 never-presented of 54,674; per-voyage median 0.234 presenting);
median non-ill share of imports 0.973 (899 of 31,395 imports presented
aboard). Presented-marker among non-ill imports: 0 — the census carries
no reliable (b) split inside imports. Confined share of symptomatic
epochs: **0.709** — once ill, hosts spend ~71% of the course confined,
which is why a presentation-level sweep also moves transmission.

## CHANNEL-03 funnel leg — 180 dumps, pooled per cell

The funnel dumps carry aggregates, so (b) is exact here and (a)+(c) pool
into `infected − symptomatic_course`:

| cell | dumps (tk) | infected | imported | acquired | presented S | onboard O | (b) S−O | (a)+(c) N−S | ill/inf |
|---|---|---|---|---|---|---|---|---|---|
| fl_cls_12d_ren · rung-reportable | 20 (13) | 794 | 95 | 699 | 192 | 133 | 59 | 602 | 0.168 |
| fl_cls_12d_scr · bp32p5c18p5 | 20 (20) | 3,062 | 889 | 2,173 | 1,110 | 511 | 599 | 1,952 | 0.167 |
| fl_cls_12d_scr · bp40c30 | 20 (20) | 3,600 | 1,130 | 2,470 | 1,336 | 569 | 767 | 2,264 | 0.158 |
| fl_exp_12d_ren · rung-reportable | 20 (2) | 38 | 16 | 22 | 20 | 7 | 13 | 18 | 0.184 |
| fl_exp_12d_scr · bp32p5c18p5 | 20 (18) | 512 | 205 | 307 | 213 | 65 | 148 | 299 | 0.127 |
| fl_exp_12d_scr · bp40c30 | 20 (19) | 591 | 244 | 347 | 232 | 71 | 161 | 359 | 0.120 |
| fl_spr_12d_ren · rung-reportable | 20 (19) | 2,016 | 148 | 1,868 | 347 | 274 | 73 | 1,669 | 0.136 |
| fl_spr_12d_scr · bp32p5c18p5 | 20 (20) | 5,306 | 1,379 | 3,927 | 1,765 | 844 | 921 | 3,541 | 0.159 |
| fl_spr_12d_scr · bp40c30 | 20 (20) | 5,902 | 1,807 | 4,095 | 2,169 | 987 | 1,182 | 3,733 | 0.167 |
| **pooled** | 180 (131) | 21,821 | 5,913 | 15,908 | 7,384 | 3,461 | 3,923 | 14,437 | 0.159 |

Reading: (b) = 3,923 = **18.0% of infected** on small hulls, almost
coincident with the pooled import count (5,913 imported, of which the
presented-and-missed set is the bulk — scr boarding pumps imports and
nearly all presented imports miss the window). On mega the census's
import bound is 17.7% — consistent across the hull scale gap.

## Conclusions the design inherits

1. **The loss is the draw, not the window.** On the hull with the
   cleanest measurement, ~66% of the infected→not-ill loss is the
   onboard presentation draw (a), ~13% is ramp-clipping (c) at the
   reference incubation median (bounded [4%, 30%] by dose conditioning),
   and ~22% is the import side (b). A sweep that can move this gap must
   act on the presentation draw level/form — voyage-length and
   incubation-window terms touch at most ~13% of the loss.
2. **The realized draw is far below either sourced regime.** The shipped
   dose-conditional Hill (`illness_probability` η 0.508, γ 0.095)
   realizes 23–24% presentation on clip-free acquisitions — below even
   the community-cohort regime floor of the register's
   `never_symptomatic_fraction` axis (1 − 0.68 = 0.32). The register
   declares `never_symptomatic_fraction` swept-never-a-point over
   `adult_challenge` {0.22, 0.29, 0.36} and `community_cohort`
   {0.59, 0.635, 0.68}; the corresponding `symptomatic_fraction` sweep
   points are {0.64, 0.71, 0.78} and {0.32, 0.365, 0.41}, and the engine
   already honours a profile `symptomatic_fraction` field as the
   measured-proportion presentation form. Note the register caveat: the
   boarding interval is measured in a boarding population, not onboard
   acquisitions — the sweep reads whether the funnel's first link can be
   moved by the draw at all, not a claim that either regime is the truth
   for aboard infections.
3. **Presentation is transmission-coupled.** Presented courses spend
   ~71% of symptomatic epochs confined — lifting the draw lifts
   confinement and plausibly cuts acquisitions. The sweep must read the
   acquisition side too, not only the funnel rungs.
4. **What the census cannot split.** The import-side (b) vs (a) split is
   only exact on the funnel dumps; if a campaign cell needs it at mega
   scale, the fleet zips would have to carry the funnel dump too — out
   of scope for this stage (the funnel harness produces no census; the
   mega witness reads the pooled bound, not the split).
