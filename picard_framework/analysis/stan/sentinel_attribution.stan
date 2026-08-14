// Single-ship port introduction hazards with onboard renewal secondaries.
//
// Likelihood is the *onset curve per person group*, not one row per case:
//
//   incidence[g,t] = sum_p lambda_p * ashore_hours[g,t,p]      // imported
//                  + lambda_aboard * aboard_hours[g,t]         // onboard baseline
//                  + R_onboard * share[g] * sum_k w[k] * incidence_total[t-k]
//   mu[g,t]        = ascertainment * sum_k f_inc[k] * incidence[g,t-k]
//   onsets[g,t]    ~ poisson(mu[g,t])
//
// Three properties the sketched model in the spec (1.4-1.6) did not have:
//
//  * lambda_p is a rate per exposed person-hour ashore, because the ashore
//    hours enter as an exposure denominator rather than as a covariate;
//  * R_onboard is sampled with a prior, so port intervals widen by the amount
//    of the onboard/imported split that the data cannot resolve;
//  * censoring needs no separate survival term here — the forward convolution
//    is truncated at T, so infections whose onset falls past the observation
//    window contribute no expected onsets, which is exactly the missing
//    P(onset <= T_end) factor. Do *not* also pass censoring-discounted hours.

data {
  int<lower=1> T;                        // observation epochs
  int<lower=1> P;                        // ports
  int<lower=1> G;                        // person groups (passenger, crew)
  int<lower=1> L_inc;                    // incubation pmf length (lag 0..L_inc-1)
  int<lower=1> L_gen;                    // generation pmf length (lag 1..L_gen)
  array[G, T] int<lower=0> onsets;
  array[G] matrix<lower=0>[T, P] ashore_hours;
  matrix<lower=0>[G, T] aboard_hours;
  vector<lower=0>[L_inc] f_inc_raw;
  vector<lower=0>[L_gen] w_gen_raw;      // strictly lagged: element k = lag k
  vector<lower=0>[G] secondary_share_raw;
  real<lower=0, upper=1> ascertainment;
  real hazard_log_prior_mean;            // log rate per person-hour ashore
  real<lower=0> hazard_log_prior_sd;
  real baseline_log_prior_mean;          // log rate per person-hour aboard
  real<lower=0> baseline_log_prior_sd;
  real<lower=0> r_prior_mean;
  real<lower=0> r_prior_sd;
  real<lower=0> port_sd_prior_scale;
}

transformed data {
  vector[L_inc] f_inc = f_inc_raw / sum(f_inc_raw);
  vector[L_gen] w_gen = w_gen_raw / sum(w_gen_raw);
  vector[G] secondary_share = secondary_share_raw / sum(secondary_share_raw);
  vector[P] port_hours_total;
  real aboard_hours_total = sum(aboard_hours);
  for (p in 1 : P) {
    real h = 0;
    for (g in 1 : G) {
      h += sum(col(ashore_hours[g], p));
    }
    port_hours_total[p] = h;
  }
}

parameters {
  real mu_log_hazard;                    // fleet-free port mean (PR 6 adds the hierarchy)
  real<lower=0> sigma_port;
  vector[P] z_port;
  real log_lambda_aboard;
  real<lower=0> R_onboard;
}

transformed parameters {
  vector[P] log_lambda_port = mu_log_hazard + sigma_port * z_port;
  vector[P] lambda_port = exp(log_lambda_port);
  real lambda_aboard = exp(log_lambda_aboard);
  matrix[G, T] incidence;
  matrix[G, T] mu_onset;
  {
    vector[T] incidence_total = rep_vector(0.0, T);
    for (t in 1 : T) {
      real secondary = 0;
      for (k in 1 : min(t - 1, L_gen)) {
        secondary += w_gen[k] * incidence_total[t - k];
      }
      secondary *= R_onboard;
      for (g in 1 : G) {
        incidence[g, t] = lambda_aboard * aboard_hours[g, t]
                          + row(ashore_hours[g], t) * lambda_port
                          + secondary * secondary_share[g];
      }
      incidence_total[t] = sum(col(incidence, t));
    }
    for (g in 1 : G) {
      for (t in 1 : T) {
        real m = 0;
        for (k in 1 : min(t, L_inc)) {
          m += f_inc[k] * incidence[g, t - k + 1];
        }
        // Floor keeps an all-zero-exposure epoch from making a zero count
        // infinitely likely and a nonzero count impossible.
        mu_onset[g, t] = ascertainment * m + 1e-9;
      }
    }
  }
}

model {
  mu_log_hazard ~ normal(hazard_log_prior_mean, hazard_log_prior_sd);
  sigma_port ~ normal(0, port_sd_prior_scale);
  z_port ~ std_normal();
  log_lambda_aboard ~ normal(baseline_log_prior_mean, baseline_log_prior_sd);
  R_onboard ~ normal(r_prior_mean, r_prior_sd);

  for (g in 1 : G) {
    onsets[g] ~ poisson(to_vector(mu_onset[g]));
  }
}

generated quantities {
  vector[P] imported_cases;
  real aboard_cases = lambda_aboard * aboard_hours_total;
  real secondary_cases;
  real import_share;
  real loglik_clinical = 0;

  for (p in 1 : P) {
    imported_cases[p] = lambda_port[p] * port_hours_total[p];
  }
  secondary_cases = fmax(0.0, sum(incidence) - sum(imported_cases) - aboard_cases);
  import_share = sum(imported_cases) / fmax(sum(incidence), 1e-12);
  for (g in 1 : G) {
    loglik_clinical += poisson_lpmf(onsets[g] | to_vector(mu_onset[g]));
  }
}
