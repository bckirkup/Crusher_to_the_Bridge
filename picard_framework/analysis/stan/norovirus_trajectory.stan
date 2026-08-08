// Phase-1b norovirus trajectory (Stage B): size | outbreak.
// NegBin2 on per-epoch new_infections with reduce_sum; no N×T transformed params.
// Intended for outbreak-conditioned run sets (hurdle Stage B).

functions {
  real trajectory_lpmf(
      array[] int run_idx,
      int start,
      int end,
      int T,
      array[,] int new_infections,
      array[,] int infected,
      array[,] int trigger_state,
      array[] int platform,
      array[] int surveillance,
      vector dose_adj,
      vector vsp_threshold,
      vector alpha_platform,
      real beta_d,
      vector f,
      vector gamma_platform,
      vector delta_surveillance,
      real eta_vsp,
      real phi,
      real d0,
      real vsp_ref
  ) {
    real lp = 0;
    for (i in start:end) {
      int r = run_idx[i];
      int trig_on = 0;
      for (t in 1:T) {
        if (trigger_state[r, t] >= 1) {
          trig_on = 1;
        }
        real I_prev = (t == 1) ? 0 : infected[r, t - 1];
        real vsp_on = (vsp_threshold[r] < 1.0 && trigger_state[r, t] >= 2) ? 1 : 0;
        real vsp_strength = (vsp_threshold[r] <= 0)
          ? 0
          : fmax(0.0, (vsp_ref - vsp_threshold[r]) / vsp_ref);
        real log_lambda =
          alpha_platform[platform[r]]
          + beta_d * (d0 - dose_adj[r])
          + f[t]
          + gamma_platform[platform[r]] * (t * 1.0 / T)
          - delta_surveillance[surveillance[r]] * trig_on
          - eta_vsp * vsp_on * (1 + vsp_strength)
          + log(I_prev + 1);
        lp += neg_binomial_2_log_lpmf(new_infections[r, t] | log_lambda, phi);
      }
    }
    return lp;
  }
}

data {
  int<lower=1> N_runs;
  int<lower=1> T;
  int<lower=1> P;
  int<lower=1> S;
  int<lower=1> grainsize;
  array[N_runs] int<lower=1> N_agents;
  array[N_runs] int<lower=1, upper=P> platform;
  array[N_runs] int<lower=1, upper=S> surveillance;
  vector[N_runs] dose_adj;
  vector[N_runs] vsp_threshold;
  array[N_runs] int seed;
  array[N_runs, T] int<lower=0> infected;
  array[N_runs, T] int<lower=0> symptomatic;
  array[N_runs, T] int<lower=0> recovered;
  array[N_runs, T] int<lower=0> new_infections;
  array[N_runs, T] int<lower=0> quarantined;
  array[N_runs, T] int<lower=0, upper=2> trigger_state;
  real d0;
  real vsp_ref;
}

transformed data {
  array[N_runs] int run_idx;
  for (r in 1:N_runs) {
    run_idx[r] = r;
  }
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

  target += reduce_sum(
    trajectory_lpmf, run_idx, grainsize,
    T, new_infections, infected, trigger_state,
    platform, surveillance, dose_adj, vsp_threshold,
    alpha_platform, beta_d, f, gamma_platform, delta_surveillance,
    eta_vsp, phi, d0, vsp_ref
  );
}

generated quantities {
  // Compact summaries only — no y_rep[N,T] (memory bomb at full N).
  vector[N_runs] pred_attack_rate;
  vector[P] platform_risk;
  real vsp_compression;
  vector[T] ppc_new_inf_mean;

  for (p in 1:P) {
    platform_risk[p] = exp(alpha_platform[p]);
  }
  vsp_compression = exp(eta_vsp);

  for (t in 1:T) {
    ppc_new_inf_mean[t] = 0;
  }

  for (r in 1:N_runs) {
    int ever = 0;
    int trig_on = 0;
    for (t in 1:T) {
      if (trigger_state[r, t] >= 1) {
        trig_on = 1;
      }
      real I_prev = (t == 1) ? 0 : infected[r, t - 1];
      real vsp_on = (vsp_threshold[r] < 1.0 && trigger_state[r, t] >= 2) ? 1 : 0;
      real vsp_strength = (vsp_threshold[r] <= 0)
        ? 0
        : fmax(0.0, (vsp_ref - vsp_threshold[r]) / vsp_ref);
      real log_lambda =
        alpha_platform[platform[r]]
        + beta_d * (d0 - dose_adj[r])
        + f[t]
        + gamma_platform[platform[r]] * (t * 1.0 / T)
        - delta_surveillance[surveillance[r]] * trig_on
        - eta_vsp * vsp_on * (1 + vsp_strength)
        + log(I_prev + 1);
      int y = neg_binomial_2_log_rng(log_lambda, phi);
      ever += y;
      ppc_new_inf_mean[t] += y;
    }
    if (ever > N_agents[r]) {
      ever = N_agents[r];
    }
    pred_attack_rate[r] = ever * 1.0 / N_agents[r];
  }
  for (t in 1:T) {
    ppc_new_inf_mean[t] /= N_runs;
  }
}
