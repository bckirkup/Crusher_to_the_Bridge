// Phase-1b norovirus takeoff probability (Stage A / hurdle).
// Bernoulli-logit on run-level takeoff vs fizzle
// (outbreak_occurred := VSP onset while Δ²incidence >= 0; see epidemic_labels).

data {
  int<lower=1> N_runs;
  int<lower=1> P;
  int<lower=1> S;
  array[N_runs] int<lower=0, upper=1> outbreak;
  array[N_runs] int<lower=1, upper=P> platform;
  array[N_runs] int<lower=1, upper=S> surveillance;
  vector[N_runs] dose_adj;
  vector[N_runs] vsp_threshold;   // < 1 => VSP enabled
  real d0;
  real vsp_ref;
}

parameters {
  vector[P] alpha_platform;
  real beta_d;                      // higher dose_adj => lower risk if beta_d > 0
  vector[S] delta_surveillance;     // higher => lower outbreak prob
  real<lower=0> eta_vsp;            // VSP-on compression of outbreak logit
}

model {
  alpha_platform ~ normal(0, 2);
  beta_d ~ normal(0, 1);
  delta_surveillance ~ normal(0, 1);
  eta_vsp ~ normal(0, 1);

  for (r in 1:N_runs) {
    real vsp_on = (vsp_threshold[r] < 1.0) ? 1 : 0;
    real vsp_strength = (vsp_threshold[r] <= 0)
      ? 0
      : fmax(0.0, (vsp_ref - vsp_threshold[r]) / vsp_ref);
    real logit_p =
      alpha_platform[platform[r]]
      + beta_d * (d0 - dose_adj[r])
      - delta_surveillance[surveillance[r]]
      - eta_vsp * vsp_on * (1 + vsp_strength);
    outbreak[r] ~ bernoulli_logit(logit_p);
  }
}

generated quantities {
  vector[P] platform_risk;          // inv_logit(alpha)
  vector[N_runs] pred_outbreak_prob;
  real vsp_compression;

  vsp_compression = exp(eta_vsp);
  for (p in 1:P) {
    platform_risk[p] = inv_logit(alpha_platform[p]);
  }
  for (r in 1:N_runs) {
    real vsp_on = (vsp_threshold[r] < 1.0) ? 1 : 0;
    real vsp_strength = (vsp_threshold[r] <= 0)
      ? 0
      : fmax(0.0, (vsp_ref - vsp_threshold[r]) / vsp_ref);
    real logit_p =
      alpha_platform[platform[r]]
      + beta_d * (d0 - dose_adj[r])
      - delta_surveillance[surveillance[r]]
      - eta_vsp * vsp_on * (1 + vsp_strength);
    pred_outbreak_prob[r] = inv_logit(logit_p);
  }
}
