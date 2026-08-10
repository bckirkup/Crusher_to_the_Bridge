// Boundary pipeline Stage B: attack rate | outbreak ~ Beta regression.
// Mean on logit scale with platform / surveillance / log(k) / dose effects.
// Not the NegBin epidemic-trajectory monograph model.

data {
  int<lower=1> N_runs;
  int<lower=1> P;
  int<lower=1> S;
  vector<lower=0, upper=1>[N_runs] ar;   // attack rate in (0,1) after clip
  array[N_runs] int<lower=1, upper=P> platform;
  array[N_runs] int<lower=1, upper=S> surveillance;
  vector[N_runs] log_k;
  vector[N_runs] dose_adj;
  real d0;
}

parameters {
  vector[P] alpha_platform;
  real beta_k;
  real beta_d;
  vector[S] delta_surveillance;
  real<lower=0> phi;   // Beta precision
}

transformed parameters {
  vector[N_runs] mu;
  for (r in 1:N_runs) {
    real logit_mu =
      alpha_platform[platform[r]]
      + beta_k * log_k[r]
      + beta_d * (d0 - dose_adj[r])
      - delta_surveillance[surveillance[r]];
    mu[r] = inv_logit(logit_mu);
  }
}

model {
  alpha_platform ~ normal(0, 2);
  beta_k ~ normal(0, 1);
  beta_d ~ normal(0, 1);
  delta_surveillance ~ normal(0, 1);
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
