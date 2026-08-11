// Per-vector latent recovery of (dose_adj, alpha_c).
// No free platform FE (would absorb the dose shift). Size-centered log_n
// identifies alpha_c via the interaction; dose shifts the shared intercept.

data {
  int<lower=1> N_runs;
  array[N_runs] int<lower=0, upper=1> outbreak;
  vector[N_runs] log_n_c;   // log(num_agents) - mean
  real d0;
  real a0;
  real beta_d_fixed;
  real beta_alpha_size_fixed;
}

parameters {
  real dose_adj;
  real<lower=0.2, upper=1.5> alpha_c;
  real intercept;
}

model {
  dose_adj ~ normal(d0, 1.5);
  alpha_c ~ normal(a0, 0.35);
  intercept ~ normal(0, 1);

  for (r in 1:N_runs) {
    real logit_p =
      intercept
      + beta_d_fixed * (d0 - dose_adj)
      + beta_alpha_size_fixed * (alpha_c - a0) * log_n_c[r];
    outbreak[r] ~ bernoulli_logit(logit_p);
  }
}
