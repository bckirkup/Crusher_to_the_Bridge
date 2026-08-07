// Phase-1 norovirus trajectory model for campaign ABM outputs.
// Observes per-epoch new_infections with a NegBin2 likelihood.
// Trigger epochs are treated as observed (no latent hazard in v1).

data {
  int<lower=1> N_runs;
  int<lower=1> T;
  int<lower=1> P;                 // platforms
  int<lower=1> S;                 // surveillance strategies
  array[N_runs] int<lower=1> N_agents;
  array[N_runs] int<lower=1, upper=P> platform;
  array[N_runs] int<lower=1, upper=S> surveillance;
  vector[N_runs] dose_adj;
  vector[N_runs] vsp_threshold;   // lockdown AR threshold; large value = off
  array[N_runs] int seed;
  array[N_runs, T] int<lower=0> infected;
  array[N_runs, T] int<lower=0> symptomatic;
  array[N_runs, T] int<lower=0> recovered;
  array[N_runs, T] int<lower=0> new_infections;
  array[N_runs, T] int<lower=0> quarantined;
  array[N_runs, T] int<lower=0, upper=2> trigger_state;
  real d0;                        // reference dose_adj (e.g. 10.6)
  real vsp_ref;                   // reference VSP threshold for compression term
}

parameters {
  vector[P] alpha_platform;
  real<lower=0> beta_d;
  vector[T] f_raw;
  real<lower=0> sigma_f;
  vector[P] gamma_platform;
  vector<lower=0>[S] delta_surveillance;
  real<lower=0> eta_vsp;
  real<lower=0> phi;
}

transformed parameters {
  vector[T] f = sigma_f * f_raw;
  array[N_runs, T] real log_lambda;

  for (r in 1:N_runs) {
    int trig_on = 0;
    for (t in 1:T) {
      if (trigger_state[r, t] >= 1) {
        trig_on = 1;
      }
      real I_prev = (t == 1) ? 0 : infected[r, t - 1];
      real vsp_on = (vsp_threshold[r] < 1.0 && trigger_state[r, t] >= 2) ? 1 : 0;
      // Stronger VSP response when threshold is tighter than reference.
      real vsp_strength = (vsp_threshold[r] <= 0)
        ? 0
        : fmax(0.0, (vsp_ref - vsp_threshold[r]) / vsp_ref);

      log_lambda[r, t] =
        alpha_platform[platform[r]]
        + beta_d * (d0 - dose_adj[r])
        + f[t]
        + gamma_platform[platform[r]] * (t * 1.0 / T)
        - delta_surveillance[surveillance[r]] * trig_on
        - eta_vsp * vsp_on * (1 + vsp_strength)
        + log(I_prev + 1);
    }
  }
}

model {
  alpha_platform ~ normal(0, 2);
  beta_d ~ normal(0, 1);
  f_raw ~ normal(0, 1);
  sigma_f ~ exponential(1);
  gamma_platform ~ normal(0, 1);
  delta_surveillance ~ normal(0, 1);
  eta_vsp ~ normal(0, 1);
  phi ~ exponential(1);

  for (r in 1:N_runs) {
    for (t in 1:T) {
      new_infections[r, t] ~ neg_binomial_2_log(log_lambda[r, t], phi);
    }
  }
}

generated quantities {
  array[N_runs, T] int y_rep;
  vector[N_runs] pred_attack_rate;
  vector[P] platform_risk;        // exp(alpha) relative risk scale
  real vsp_compression;           // exp(eta_vsp)

  for (p in 1:P) {
    platform_risk[p] = exp(alpha_platform[p]);
  }
  vsp_compression = exp(eta_vsp);

  for (r in 1:N_runs) {
    int ever = 0;
    for (t in 1:T) {
      real lam = exp(log_lambda[r, t]);
      y_rep[r, t] = neg_binomial_2_rng(lam, phi);
      ever += y_rep[r, t];
    }
    // Cap at N_agents for a crude posterior predictive attack rate.
    if (ever > N_agents[r]) {
      ever = N_agents[r];
    }
    pred_attack_rate[r] = ever * 1.0 / N_agents[r];
  }
}
