# Sentinel Attribution Stan Model Fix Spec
# Addresses: 18.5% coverage in synthetic recovery (target ≥85%)

> **Status:** Three of four fixes, and the target model

## Diagnosis

The current `sentinel_attribution.stan` systematically underestimates port 
hazards (~100× too low) and overestimates onboard transmission. R_onboard 
recovers at 0.05-0.18 regardless of the true value (0 to 1.5).

Root cause: `lambda_aboard * aboard_hours[g,t]` provides a constant per-hour 
aboard infection rate across ALL epochs. Since passengers spend ~90% of the 
voyage aboard, this term dominates the likelihood and absorbs signal that 
should be attributed to ports. The model prefers explaining onset clusters 
via a smooth aboard baseline + R_onboard renewal rather than via sharp 
port-specific importation pulses.

## Required changes to `sentinel_attribution.stan`

### Fix 1: Informative R_onboard prior from CTB hurdle posterior

Current: `R_onboard ~ normal(r_prior_mean, r_prior_sd)` with broad SD.

Change: Pass the CTB norovirus hurdle model posterior as a tight prior.
From the existing boundary campaign Stage B fit:
- Platform-specific R estimates are available in the hurdle posterior
- Use posterior mean ± posterior SD as the prior
- For norovirus on mega: R_onboard prior ~ normal(0.06, 0.02) approximately
  (from the Stage B per-epoch infection rates)

This prevents R from absorbing port signal. The CTB model has already 
estimated onboard transmission from 10,000+ dedicated runs — use that 
information.

### Fix 2: Structured aboard baseline — separate sea-day vs port-day rates

Current: Single `lambda_aboard` applied uniformly to all aboard hours.

Change: Two aboard rates:
```stan
parameters {
  real log_lambda_sea;    // aboard rate during sea days
  real log_lambda_port;   // aboard rate during port days (lower — fewer people aboard)
}
```

Pass a binary indicator `is_port_day[T]` in data. During port days, the 
aboard population is reduced (passengers are ashore), so the aboard infection 
rate should be lower. This prevents the aboard term from explaining 
post-port onset clusters.

Alternatively (simpler): the `aboard_hours[g,t]` matrix should already 
reflect reduced aboard time during port days. Verify that the data assembly 
in `exposure.py` correctly reduces aboard hours when passengers are ashore.
If it does, the model is correct but the prior on `lambda_aboard` is too 
broad — tighten it.

### Fix 3: Onset-timing contrast as explicit diagnostic

Add to generated quantities:
```stan
generated quantities {
  // Per-port: ratio of onsets in the 12-48h window after the port call
  // vs the same window around sea days
  // This is the key temporal signal the model should capture
  vector[P] port_onset_ratio;  // onsets after port / expected under null
}
```

This provides a direct check on whether the model is using the temporal 
clustering signal.

### Fix 4: Wastewater channel (new likelihood term)

Wire `wastewater_signal.py` into the model. The wastewater observation 
enters as a beta-binomial observation of the latent incidence curve 
(spec §1.3). It is NOT an independent hazard channel — it's a second 
observation of the same latent incidence.

```stan
data {
  int<lower=0> N_ww;                     // number of wastewater samples
  array[N_ww] int<lower=0> ww_reads;     // pathogen reads
  array[N_ww] int<lower=0> ww_total;     // total reads
  array[N_ww] int<lower=1> ww_epoch;     // sample epoch
  real<lower=0> ww_phi_prior_mean;       // overdispersion
}

parameters {
  real<lower=0> phi_ww;                   // beta-binomial precision
  real<lower=0> ww_sensitivity;           // reads per unit incidence
}

model {
  // Wastewater likelihood: pathogen reads ~ BetaBinomial
  // Expected proportion = ww_sensitivity * sum of recent incidence
  // (convolved with shedding kernel, not incubation kernel)
  for (i in 1:N_ww) {
    real expected_prop = ww_sensitivity * incidence_total[ww_epoch[i]];
    // ... beta-binomial parameterization
  }
}
```

The wastewater signal provides independent temporal evidence: if reads 
spike 24h after Cozumel and are flat after sea days, that's port signal 
that clinical onset timing alone can't resolve (because clinical cases 
have stochastic care-seeking delays).

## Validation

Re-run on the existing 3,360 synthetic voyages. The wastewater samples 
are already in the line lists. No new sim runs needed.

Pass criteria (unchanged):
- 90% CI coverage ≥ 85% across non-null cells
- Null profile: no false port attributions
- One-hot: hot port posterior > 3× cold ports
- Last-port-hot: George Town not systematically underestimated
- Fleet crossover narrows CIs by ≥ 30%

## Priority order
1. Fix 1 (tight R prior) — highest impact, smallest change
2. Fix 2 (structured aboard rate) — moderate impact
3. Fix 4 (wastewater channel) — adds independent information
4. Fix 3 (diagnostic) — for interpretation, not inference
