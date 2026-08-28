# Per-Platform Medical Response Parameters

Adds a `medical_response` block to each cruise platform's `voyage_config.json`
that configures how aggressively the shipboard medical team detects and
responds to infectious disease cases. These parameters seed the syndromic
surveillance and FRED quarantine-compliance systems already in the model.

## Rationale

Cruise ship medical care varies structurally by ship class (expedition through
mega). VSP outbreak data (~5–6% AR flat across ship sizes) already includes
real-world medical responses. Calibrating `none_true` against VSP was incorrect —
calibrate `syndromic` + medical response against observed AR.

This repo ships **stock-equivalent** platform values (identical to today's
global defaults) so enabling the block is a no-op until knobs are turned via
platform edits or campaign `config_overrides`. A class gradient is documented
below as a calibration suggestion only.

## Data Model

Added to each platform's `voyage_config.json`:

```json
{
  "medical_response": {
    "sick_call_probability_per_day": 0.70,
    "isolation_compliance": 0.85,
    "detection_delay_hours": 0,
    "crew_screening_interval_hours": null,
    "notes": "Stock defaults (= current global behavior)."
  }
}
```

### Parameters

| Parameter | Type | Seeds | Stock default |
|-----------|------|-------|---------------|
| `sick_call_probability_per_day` | float [0,1] | `syndromic.sick_call_probability_per_day` | `0.70` |
| `isolation_compliance` | float [0,1] | `fred_behavior.quarantine_compliance` | `0.85` |
| `detection_delay_hours` | int >= 0 | `syndromic.detection_delay_hours` | `0` |
| `crew_screening_interval_hours` | int >= 1 or null | `syndromic.crew_screening_interval_hours` | `null` |

**Compliance stays in FRED.** `isolation_compliance` is a voyage-facing alias that
seeds `fred_behavior.quarantine_compliance`. The bimodal Compliant / Reluctant /
Defiant draw is unchanged — there is no second compliance system.

**Detection delay:** minimum hours after first observed symptom onset before the
sick-call Bernoulli is allowed. `0` = today's IID-per-epoch behavior.
`report_sick_call` overrides and background noise are not delayed.

**Crew screening:** when set to `N >= 1`, non-isolated crew are added to the
sick-call roster every `N` hours (including hour 0). Independent of
`sick_call_probability_per_day`.

## Precedence

`apply_voyage_medical_response` runs after Picard `config_overrides` and only
seeds a key when it is still at stock default. Campaign presets such as
`none_true` (`sick_call_probability_per_day: 0`) therefore still win.

```
config.yaml stock → Picard config_overrides → apply_voyage_medical_response → build_modalities
```

When no `medical_response` block is present (naval / fiction / legacy platforms),
global YAML defaults apply unchanged.

## Suggested class gradient (calibration only)

Not applied as shipping platform defaults (would change AR). Use via platform
edits or campaign overrides when calibrating:

| Parameter | Expedition | Classic | Spirit | Mega |
|-----------|-----------|---------|--------|------|
| `sick_call_probability_per_day` | 0.9 | 0.7 | 0.5 | 0.4 |
| `isolation_compliance` | 0.95 | 0.90 | 0.85 | 0.80 |
| `detection_delay_hours` | 1 | 2 | 2 | 3 |
| `crew_screening_interval_hours` | null | null | null | null |

## Campaign override

Sweep without editing voyage files:

```json
{
  "config_overrides": {
    "syndromic": {
      "sick_call_probability_per_day": 0.7,
      "detection_delay_hours": 2
    },
    "fred_behavior": {
      "quarantine_compliance": 0.90
    }
  }
}
```

T12 already sweeps `syndromic.sick_call_probability_per_day`.

## Interaction with surveillance strategies

- `none` / `none_true`: campaign overrides zero sick-call; voyage medical_response
  does not re-raise stock keys.
- `syndromic`: sick-call + detection delay / crew screening feed clinical assays
  and escalation; cascade off.
- `cascade` / `cascade_mpx`: same sick-call roster enters cascade Tier 1.

## Code hooks

| Piece | Location |
|-------|----------|
| Schema | `schemas/voyage_config.schema.json` |
| Apply | `orchestrator_init.apply_voyage_medical_response` |
| Extractor | `engines.voyage_itinerary.medical_response_from_config` |
| Wiring | `ShipSimulation.initialize` (after dining meal weights) |
| Runtime | `SyndromicSurveillance` (`detection_delay_hours`, crew screening) |
