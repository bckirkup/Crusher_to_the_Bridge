# Post-merge anchor pilot: what the five-state observation layer did and did not fix

Runs: 120 (expedition_cruise_450, classic_cruise_1900 x dose 2.0/2.5/3.0 x
none_response/syndromic_comp85 x 10 seeds), 0 failures, executed at
`7a9b439` — i.e. with #340 (symmetric confinement), #341 (own-severity sick
call), #342 (matched denominators) and #343 (five-state severity) all in.
Take-off conditioned (peak prevalence >= 10). Table:
`anchor_report_hull_resolved.md`.

## Two measurement defects found in my own scorer, before any result stands

1. **The scorer pooled the two hulls.** It read `parameters.platform` /
   `parameters.hull`; the artifacts carry `parameters.platform_id`. Every hull
   came back `unknown`, so expedition and classic were averaged into single
   20-seed cells — with 450-berth and 1900-berth complements in the same
   denominator. The first run of this pilot was scored that way. It now reads
   `platform_id` and **raises** rather than defaulting to `"unknown"`, because
   a silent default here averages different ships.
2. **A3's target was the pre-correction one.** The scorer compared measured
   reported/ever-ill against 0.55-0.65, which is Edison's reported/**AGE-
   eligible** figure. For the same five-state parameter set the implied
   reported/**symptomatic** is 0.403. Scoring against 0.60 would have demanded
   1.5x the reporting the literature chain allows — the exact error the
   five-state layer was built to remove. The anchor is now
   `A3_reported_per_symptomatic` at 0.35-0.45; reported/eligible is *not*
   scored because the runs emit no AGE-eligible count. That count is the
   natural next telemetry addition.

Both are measurement-layer defects, not model defects, and both are of the
class this project keeps finding: a name that looked right.

## Results, as measured

| Anchor | Target | Measured (no response, dose 2.0) | Verdict |
|---|---|---|---|
| A1 ever-ill (pax) | 0.10-0.22 | expedition 0.215, classic 0.178 | PASS at dose 2.0 only |
| A2 ill/infected | 0.59-0.81 | 0.264 / 0.224 | **FAIL, ~2.5-3x low, every cell** |
| A3 reported/symptomatic | 0.35-0.45 | 0.280 / 0.199 | FAIL low pre-recognition; 0.54-1.00 under response |
| A4 reported AR vs VSP IQR | exp 4.51-13.60%, classic 4.46-7.76% | exp 6.02% PASS, classic 3.88% FAIL (just below) | mixed |
| A5 reported pax:crew | 2.5-4.5 | 1.11-1.69, and <1 in four cells | **FAIL, structural** |

## What this says

**The observation-layer replacement did not repair the chain, and it was never
going to.** A2 is set by the dose-conditioned Teunis draw, which #343 did not
touch; it is unchanged and still ~3x low. So the earlier diagnosis stands
after correction rather than being an artifact of it: the engine produces a
*diffuse low-dose* epidemic (infection AR 0.79 at dose 2.0, most infections
subclinical) where the literature describes a *concentrated high-dose* one
(infection AR ~0.22, most of those ill). That is a statement about dose
**variance**, not dose mean, and no rung of the dose ladder fixes it — raising
the mean raises infection AR faster than it raises ill/infected.

**A4 passing on expedition is still a cancellation, now measurable as one.**
Expedition at dose 2.0 lands inside the VSP IQR while its two intervening
links are wrong in opposite directions (infection AR 3.6x high, ill/infected
3x low). The corrected observation layer moved reported/symptomatic from
~0.15 to 0.20-0.31 pre-recognition — the right direction, roughly half the
deficit — but the agreement at the endpoint is not evidence the mechanism is
right, and should not be quoted as a fit.

**A5 is a new failure and a genuinely informative one.** Reported
passenger:crew comes out 0.4-1.7 against a literature ~3.5 (7% vs 2%): our
crew report about as often as passengers, and sometimes more. Nothing in dose
or in the severity vectors can produce a 3x split — it needs a real asymmetry
(crew reporting suppression, different contact structure, or crew screening
handled separately from passenger sick call). This anchor was never scored
before #342 gave us crew rates, and it fails independently of everything
above.

## Consequence for the next step

Not a dose ladder, and not a Spot campaign. The next experiment is the dose
*variance* test (exposure concentration): whether making exposures rarer and
larger at fixed mean can satisfy A1, A2 and A4 together. A2 is the anchor with
the discriminating power here, since it is a within-host consequence of the
inoculum distribution and cannot be moved by reporting assumptions.

A5 needs its own investigation and is not blocked behind that.
