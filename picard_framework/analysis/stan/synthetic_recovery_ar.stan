// Synthetic-recovery Stage B: attack rate ~ Beta regression.
// dose_adj and density exponent enter as known covariates (pooled ridge test).

data {
  int<lower=1> N_runs;
  int<lower=1> P;
  vector<lower=0, upper=1>[N_runs] ar;
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
  real<lower=0> phi;
}

transformed parameters {
  vector[N_runs] mu;
  for (r in 1:N_runs) {
    real logit_mu =
      alpha_platform[platform[r]]
      + beta_d * (d0 - dose_adj[r])
      + beta_alpha * (alpha_c[r] - a0);
    // Keep Beta shapes away from 0 during warmup.
    mu[r] = fmin(1 - 1e-6, fmax(1e-6, inv_logit(logit_mu)));
  }
}

model {
  alpha_platform ~ normal(0, 2);
  beta_d ~ normal(0, 1);
  beta_alpha ~ normal(0, 1);
  phi ~ exponential(1);

  for (r in 1:N_runs) {
    ar[r] ~ beta(mu[r] * phi, (1 - mu[r]) * phi);
  }
}

generated quantities {
  vector[N_runs] pred_ar;
  for (r in 1:N_runs) {
    pred_ar[r] = mu[r];
  }
}
