# PROPENSITY-V1 — persistent contact-propensity heterogeneity

Status: implemented — the rhythm-layer deal, payload echo, and witnesses ship
with the declaration; measurement (clause canary, band array) is a later stage.

## 1. The defect this addresses

The rhythm layer deals each agent a fresh Bernoulli draw on an event's
`participation_fraction` per event per day. Every passenger is therefore
the same sociable person in expectation: there is no persistent
activity-level trait anywhere in the tree. Over the 17-day pre-quarantine
window that is the DP replay's exposure window, i.i.d. dealing exposes the
whole complement nearly equally — one contributor to the 96%-burn shape the
record (712 confirmed, 197 dated onsets) does not show.

The 2020-era literature's answer to "why were the early models
apocalyptic" is heterogeneity: contact propensity is a *person trait*.
Britton, Ball & Trapman (Science 2020, eabc6810) showed a gamma-distributed
contact-rate heterogeneity lowers the effective herd threshold by
concentrating infection in the high-propensity tail, then stalling in the
low-propensity tail. That is precisely the axis we have never declared —
emission dispersion (`shedding_variance_log10`), hazard frailty
(FRAILTY-V1), and partner sampling all exist; *exposure-frequency*
dispersion does not.

## 2. Mechanism

Each propensity unit carries a persistent multiplier on the participation
probability of discretionary events:

- **Unit.** `mode: party` (shipped default): one draw shared by every member
  of a `party_id` group — a travelling family shares its activity level.
  Agents with `party_id < 0` (solo passengers, all crew) draw individually.
  `mode: agent` is the labelled per-agent variant; `mode: off` is the
  labelled baseline (no draws on the propensity stream — bit-identical).
- **Draw.** `distribution: lognormal`, `cv` declared; mean pinned at 1.0 so
  the multiplier shifts *which* people accumulate venue hours, never the
  venue's mean. Same discipline as FRAILTY-V1. Drawn once per unit at the
  layer's first deal on a dedicated spawn-keyed stream — off-arm runs
  consume nothing extra.
- **Age tilt.** `age_band_mean` maps the agent's own `age_band` label to a
  deliberate tilt applied per-agent at consumption: elderly attend less,
  mid-adults most. Not mean-pinned — the tilt is the covariate, the draw is
  the residual dispersion. Unlisted bands read 1.0.
- **Scope.** Multiplies `p` in the participation Bernoulli only for events
  whose class is in `applies_to_event_classes` (discretionary classes:
  `open_venue`, `show_performance`, `scheduled_activity`, `port_call`,
  `meal_seating`). Duty and flow classes (`watch_turnover`,
  `cleaning_rotation`, `embarkation_flow`, `disembarkation_flow`,
  `queue_event`) are never thinned — sociability does not excuse a watch.
  Effective probability is `min(1, p × propensity)`; capacity and SOP
  shaping run downstream unchanged.

## 3. Grammar

```yaml
rhythm:
  participation_propensity:
    mode: party | agent | off        # default party (shipped ON)
    distribution: lognormal          # lognormal | gamma
    cv: 0.8
    applies_to_event_classes: [open_venue, show_performance, scheduled_activity, meal_seating, port_call]
    age_band_mean:                   # optional, per age_band label; 1.0 default
      "0-4": 0.5
      "5-17": 0.9
      "18-34": 1.05
      "35-49": 1.1
      "50-64": 1.05
      "65-74": 0.95
      "75+": 0.8
```

## 4. Factor table

| parameter | declaration | grade | provenance |
|---|---|---|---|
| `cv` | 0.8 (lognormal σ² = ln(1+cv²) ≈ 0.50; 5th–95th pct ≈ 0.32–3.1) | C | No cruise-activity attendance variance in the literature; cv chosen so a cabin-stayer tail exists without emptying venues. Standing liability — the widest unmeasured cell in this spec. |
| `distribution` | lognormal | C | Matches the repo's shedding/frailty idiom; `gamma` is the declared alternative. |
| `mode` | party | C | Families cruise together — party-shared sociability is the cheaper hypothesis than independent members; `agent` arm kept for attribution. |
| `age_band_mean` | table in §3 | C | Directional: older guests attend fewer public venues; mid-adults peak. Elderly hull (DP band weights 969/734.5 on 65-74/75+) nets ~0.9 weighted attendance — the tilt working, not a bug. |
| `applies_to_event_classes` | discretionary set in §3 | C | Duty classes carry crew obligations; flows are compulsory. |

Nothing in the table is fitted to an anchor. The mechanism's prediction is
*shape*: divergent ignition tails, cluster concentration in high-propensity
parties, and a surviving low-propensity susceptible pool — not a uniform
count shift.

## 5. Conformance

- `mode: off` reproduces the pre-change behaviour **bit-identically** — no
  draws on any stream, `_propensity` never consulted.
- The resolved block echoes into the run payload (`rhythm.participation_propensity`
  under the config echo) so conditioned arrays audit which arm ran.
- Telemetry: `rhythm.propensity_draws` (units dealt), the drawn multiplier
  histogram's q05/median/q95 in `rhythm.propensity_multiplier_q` for the
  readout's pairing audit.

## 6. Measurement hooks

- Readout witnesses: attack-rate by propensity decile (declared
  instrument), cabin/party clustering of secondaries vs baseline arm.
- The DP question is whether the low-propensity tail survives the
  17-day window — instrument as `susceptible_at_end` × propensity decile.

## 7. Non-goals

- No dynamic propensity (a person who skips three venues doesn't get
  lonelier); no SOP-conditioned propensity (behaviour change under
  information is INFO-SUPPRESS-V1's channel).
- No propensity effect on mandatory flows (embark, muster, disembark).
- No refit of `cv` or `age_band_mean` against the DP anchor — Grade C
  declarations stand until a literature source lands.
