// Synthetic-recovery Stage A: P(outbreak | platform, dose_adj, alpha_c).
// dose_adj and density exponent enter as known covariates (pooled ridge test).

data {
  int<lower=1> N_runs;
  int<lower=1> P;
  array[N_runs] int<lower=0, upper=1> outbreak;
  array[N_runs] int<lower=1, upper=P> platform;
  vector[N_runs] dose_adj;
  vector[N_runs] alpha_c;
  real d0;
  real a0;
}

parameters {
  vector[P] alpha_platform;
  real beta_d;
  real beta_alpha;
}

model {
  alpha_platform ~ normal(0, 2);
  beta_d ~ normal(0, 1);
  beta_alpha ~ normal(0, 1);

  for (r in 1:N_runs) {
    real logit_p =
      alpha_platform[platform[r]]
      + beta_d * (d0 - dose_adj[r])
      + beta_alpha * (alpha_c[r] - a0);
    outbreak[r] ~ bernoulli_logit(logit_p);
  }
}

generated quantities {
  vector[N_runs] pred_outbreak_prob;
  for (r in 1:N_runs) {
    real logit_p =
      alpha_platform[platform[r]]
      + beta_d * (d0 - dose_adj[r])
      + beta_alpha * (alpha_c[r] - a0);
    pred_outbreak_prob[r] = inv_logit(logit_p);
  }
}
