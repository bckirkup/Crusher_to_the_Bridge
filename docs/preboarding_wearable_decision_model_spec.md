# Pre-Boarding Wearable Data Sharing Decision Model — Spec v1

## Purpose

Estimate the return on investment (ROI) of voluntary pre-boarding wearable data
sharing for cruise passengers. The core question is whether wearable-derived
pre-embarkation anomaly detection can prevent costly shipboard outbreaks by
intercepting infectious passengers before they board.

This model is distinct from mid-voyage wearable surveillance. C14 showed that
wearables add little once a pathogen is already circulating onboard because the
VSP threshold response dominates. Pre-boarding is different: detecting an
infectious passenger before embarkation can prevent the entire outbreak.

## Conceptual Framing

Mid-voyage wearable surveillance asks:

```text
Can we detect an outbreak earlier once it is already onboard?
```

Pre-boarding wearable sharing asks:

```text
Can we prevent the infectious index case from boarding at all?
```

The economic value is therefore driven by avoided outbreak costs, avoided VSP
escalations, avoided voyage disruption, and avoided reputational damage.

## Decision Structure

For each voyage, passengers may opt in to share a pre-boarding wearable-derived
health/anomaly signal during the 24--72 hours before embarkation.

A passenger with an anomalous signal can be:

1. allowed to board normally
2. routed to secondary screening
3. delayed and retested
4. denied boarding with guaranteed rebooking/refund
5. allowed to board with monitoring/isolation constraints

The decision model evaluates expected cost under alternative policies.

## State Variables

### Voyage-level inputs

| Symbol | Description |
|--------|-------------|
| `N_pax` | passenger count |
| `platform_class` | expedition, classic, spirit, mega |
| `pathogen` | norovirus, SARS-CoV-2, influenza, measles, etc. |
| `season` | season or prevalence stratum |
| `voyage_length_days` | voyage duration |
| `baseline_response` | onboard response regime (syndromic/VSP/cascade) |

### Prevalence inputs

| Symbol | Description |
|--------|-------------|
| `π_inf` | probability an embarking passenger is infectious |
| `π_sym` | probability an infectious passenger is symptomatic/prodromal before boarding |
| `π_asym` | probability an infectious passenger is asymptomatic but shedding |
| `ρ_cluster` | clustering / travel-party correlation factor |

### Wearable adoption and performance

| Symbol | Description |
|--------|-------------|
| `a` | passenger opt-in/adoption probability |
| `Se_w` | wearable anomaly sensitivity among infectious/prodromal passengers |
| `Sp_w` | wearable anomaly specificity among non-infectious passengers |
| `Se_confirm` | secondary test sensitivity (if used) |
| `Sp_confirm` | secondary test specificity |
| `τ_window` | lookback window (24, 48, 72h before embarkation) |

### Costs

| Symbol | Description |
|--------|-------------|
| `C_screen` | cost per passenger for data handling / screening workflow |
| `C_secondary` | cost of secondary testing / medical evaluation |
| `C_false_positive` | cost of denied boarding or delayed boarding for non-infectious passenger |
| `C_true_positive` | rebooking/refund/isolation cost for intercepted infectious passenger |
| `C_outbreak` | direct cost of onboard outbreak |
| `C_vsp` | cost of VSP/Code Red escalation, missed ports, refunds |
| `C_reputation` | reputational externality / industry-level booking impact |
| `C_missed` | incremental cost of failing to intercept an infectious passenger |

### ABM/Stan posterior inputs

These are supplied by CTB campaign posterior predictions:

| Quantity | Description |
|----------|-------------|
| `P_trigger(k, platform, pathogen, response)` | probability VSP threshold is reached given `k` infectious introductions |
| `E_AR(k, platform, pathogen, response)` | expected final attack rate given `k` introductions |
| `P_accel(k, platform, pathogen, response)` | probability of accelerating outbreak at VSP trigger |
| `E_cost_onboard(k, ...)` | expected onboard cost distribution |
| `E_peak_epoch(k, ...)` | expected peak timing |

For Phase 0, approximate `k` introductions using binomial or beta-binomial
prevalence and use lookup/interpolation from CTB posterior results.

## Generative Model

### Step 1: Introductions before screening

For passenger `i`:

\[
Z_i \sim \mathrm{Bernoulli}(\pi_{inf})
\]

where `Z_i = 1` means infectious at embarkation.

If travel-party clustering is modeled:

\[
\pi_{voyage} \sim \mathrm{Beta}(\alpha_\pi, \beta_\pi)
\]

\[
K \sim \mathrm{BetaBinomial}(N_{pax}, \alpha_\pi, \beta_\pi)
\]

where `K` is the number of infectious introductions before screening.

### Step 2: Wearable adoption

\[
A_i \sim \mathrm{Bernoulli}(a)
\]

Only passengers with `A_i=1` produce wearable signals.

### Step 3: Wearable signal

For adopted passengers:

\[
W_i \mid Z_i=1 \sim \mathrm{Bernoulli}(Se_w)
\]

\[
W_i \mid Z_i=0 \sim \mathrm{Bernoulli}(1-Sp_w)
\]

`W_i=1` means an anomaly is flagged.

### Step 4: Secondary confirmation (optional)

For flagged passengers routed to confirmatory testing:

\[
T_i \mid Z_i=1 \sim \mathrm{Bernoulli}(Se_{confirm})
\]

\[
T_i \mid Z_i=0 \sim \mathrm{Bernoulli}(1-Sp_{confirm})
\]

Policy determines whether boarding is denied based on `W_i` alone or `W_i + T_i`.

### Step 5: Post-screening introductions

\[
K_{board} = \sum_i Z_i \cdot I(\text{not denied})
\]

### Step 6: Outbreak outcome

Use CTB/Stan posterior lookup:

\[
P(VSP \mid K_{board}, platform, pathogen, response)
\]

\[
E(AR \mid K_{board}, platform, pathogen, response)
\]

\[
P(accelerating \mid K_{board}, platform, pathogen, response)
\]

### Step 7: Total expected cost

\[
E[C] = C_{screening} + C_{false+} + C_{true+} + E[C_{onboard}]
\]

where:

\[
C_{screening} = N_{pax} \cdot a \cdot C_{screen}
\]

\[
C_{false+} = N_{FP} \cdot C_{false\_positive}
\]

\[
C_{true+} = N_{TP} \cdot C_{true\_positive}
\]

\[
E[C_{onboard}] = P(VSP) (C_{outbreak} + C_{vsp} + C_{reputation})
+ E[AR] \cdot N_{pax} \cdot C_{case}
\]

## Policies to Compare

### P0: No pre-boarding wearable sharing
Baseline.

### P1: Passive wearable advisory
Passenger receives self-directed recommendation to delay travel, but cruise line
uses no signal operationally.

### P2: Voluntary wearable sharing + secondary screening
Flagged passengers receive rapid confirmatory testing at terminal.
Denied boarding only if confirmatory test positive.

### P3: Voluntary wearable sharing + conservative delay
Flagged passengers with high anomaly score are delayed/rebooked without boarding,
with guaranteed compensation.

### P4: Insurance-incentivized wearable sharing
Same as P2 or P3, but adoption `a` increases due to reduced travel insurance
premium or onboard credit.

### P5: Mandatory crew wearable pre-boarding
Crew required to share pre-boarding data. Passenger participation optional.

## Main Outcomes

Per voyage:

- expected number of infectious passengers intercepted
- expected infectious passengers boarding
- probability of VSP trigger
- probability of accelerating outbreak
- expected attack rate
- expected total cost
- expected reputational cost
- false positives per true positive
- false positives per VSP event avoided
- cost per VSP event avoided
- break-even prevalence
- value of information per passenger

## Key Plots

1. Expected total cost vs embarkation prevalence
2. Probability of VSP trigger vs embarkation prevalence
3. Break-even prevalence by platform
4. False positives per outbreak avoided
5. Adoption threshold needed for positive ROI
6. Heatmap: wearable sensitivity × specificity → expected net benefit
7. Platform comparison: expedition vs mega at same prevalence
8. Policy frontier: cost vs VSP events avoided

## Parameter Priors

### Wearable sensitivity/specificity
Use broad priors from infectious-disease wearable reviews:

```text
Se_w ~ Beta(mean 0.65, broad)
Sp_w ~ Beta(mean 0.85, broad)
```

Need separate values for:
- fever-dominant respiratory pathogens
- GI pathogens such as norovirus where wearables may detect sleep/HRV anomaly but not diarrhea directly

### Adoption
Use existing CTB wearable deployment profiles:

```text
BYOD baseline:      a = 0.43
Incentivized:       a = 0.70
Crew mandatory:     a = 1.00 for crew
```

### Embarkation prevalence
Default decision matrix uses a **25-point log-spaced** sweep
`π_inf ∈ [0.0001, 0.02]` (not four coarse strata) so VoI peaks, break-even
crossings, and cost rollover are resolvable. Smoke/CI keeps a 2-point grid.

Named strata for narrative scenarios:

```text
low:       0.05% infectious
moderate: 0.20%
high:     0.50%
severe:   1.00%
```

For norovirus, include asymptomatic shedding prevalence separately from
transmission-competent high-shedding prevalence.

### Costs
Initial scenario ranges:

```text
C_screen:           $0.10-$2 per passenger (data handling)
C_secondary:        $25-$150 per test/evaluation
C_false_positive:   $500-$5,000 per denied boarding/rebooking
C_true_positive:    $500-$5,000 per intercepted infectious passenger
C_case:             $100-$1,000 direct medical/compensation
C_vsp:              $0.5M-$5M per Code Red / missed ports / refunds
C_reputation:       $0.5M-$20M equivalent expected loss
```

The reputational externality should be scenario-modeled, not point-estimated.

## Phase 0 Edison Prototype

Build in a notebook first.

Inputs:

- posterior summaries from Stan Step 2
- C14/C14b observed response surfaces if Stan posterior unavailable
- simple prevalence/adoption/cost priors

Outputs:

- CSV of policy comparison by platform/pathogen/prevalence
- plots listed above
- short narrative report

## Phase 1 Package (implemented)

Package lives under `picard_framework/analysis/boundary/` (ancillary to the
ship ABM; does not call `ShipSimulation`):

```text
picard_framework/analysis/boundary/
  prevalence.py
  screening.py
  decision_model.py
  posterior_lookup.py
  costs.py
  figures.py
  report.py
  campaign.py
  run_decision_model.py
  fixtures/outbreak_surface.json
  data/scenario_matrix.json
```

CLI:

```bash
# Smoke / CI (fixture surface)
python3 -m picard_framework.analysis.boundary.run_decision_model --smoke

# Full matrix with Stan surface when exported beside a fit
python3 -m picard_framework.analysis.boundary.run_decision_model \
  --stan-fit analysis/analysis_stan_norovirus/hurdle_fit \
  --lookup auto \
  --n-mc 2000 \
  --out boundary_analysis/
```

Stan fit directories should provide `outbreak_surface.json` or
`outbreak_surface.csv` (also accepted under `posterior/` or `boundary/`).
Export empirically from campaign zips:

```bash
python3 -m picard_framework.analysis.boundary.export_outbreak_surface \
  results/c12c_fine_calibration results/results_c14 \
  --pathogen norovirus \
  --out path/to/stan_fit/outbreak_surface.csv
```

Without that export, `--lookup auto` falls back to the packaged fixture.

Ship-sim handoff (`K_board` → embarkation seeding) is deferred to a later PR.

## Interpretation for Monograph

This model supports the thesis:

- mid-voyage wearables/wastewater add little to final AR once VSP response exists
- pre-boarding wearable data can have high value by preventing the index case from boarding
- the right evaluation metric is expected cost and decision quality, not attack-rate reduction alone

Advanced surveillance should be framed as **decision support for avoiding unnecessary VSP escalation and preventing boundary introductions**, not as a simple mid-outbreak attack-rate reducer.
