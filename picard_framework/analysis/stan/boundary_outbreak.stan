// Boundary pipeline Stage A: P(outbreak | k, platform, surveillance, dose).
// Bernoulli-logit; k enters as log(k) (introductions). Distinct from the
// norovirus monograph outbreak.stan (dose/VSP-focused, no k index).

data {
  int<lower=1> N_runs;
  int<lower=1> P;
  int<lower=1> S;
  array[N_runs] int<lower=0, upper=1> outbreak;
  array[N_runs] int<lower=1, upper=P> platform;
  array[N_runs] int<lower=1, upper=S> surveillance;
  vector[N_runs] log_k;           // log(introductions)
  vector[N_runs] dose_adj;
  real d0;
}

parameters {
  vector[P] alpha_platform;
  real beta_k;
  real beta_d;
  vector[S] delta_surveillance;
}

model {
  alpha_platform ~ normal(0, 2);
  beta_k ~ normal(0, 1);
  beta_d ~ normal(0, 1);
  delta_surveillance ~ normal(0, 1);

  for (r in 1:N_runs) {
    real logit_p =
      alpha_platform[platform[r]]
      + beta_k * log_k[r]
      + beta_d * (d0 - dose_adj[r])
      - delta_surveillance[surveillance[r]];
    outbreak[r] ~ bernoulli_logit(logit_p);
  }
}

generated quantities {
  vector[N_runs] pred_outbreak_prob;
  for (r in 1:N_runs) {
    real logit_p =
      alpha_platform[platform[r]]
      + beta_k * log_k[r]
      + beta_d * (d0 - dose_adj[r])
      - delta_surveillance[surveillance[r]];
    pred_outbreak_prob[r] = inv_logit(logit_p);
  }
}
