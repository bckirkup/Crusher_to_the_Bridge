// Fleet port-introduction hazards: port-visit x ship hierarchy, fleet-time
// effect, crew repeat exposure.
//
// Same per-voyage likelihood as sentinel_attribution.stan (Poisson onsets from
// exposure-offset incidence with renewal secondaries and a truncated incubation
// convolution), with the single-voyage hazards replaced by three nested levels:
//
//   log lambda_visit[i] = log lambda_port[visit_port[i]]        // pooled port
//                       + sigma_visit * z_visit[i]              // this visit
//                       + fleet_time[visit_week[i]]             // calendar week
//   log lambda_port[p]  = mu_log_hazard + sigma_port * z_port[p]
//
// and the ashore rate a crew member faces multiplied by
//
//   exp(log_crew_ratio + beta_repeat * crew_repeat[v, p])
//
// where crew_repeat counts that ship's *earlier* calls at the port inside the
// supplied fleet. Crew are the only within-person repeat contrast in the design
// (spec 3), so beta_repeat is where depletion/immunity from prior exposure to
// the same port shows up; a negative value means later calls infect less.
//
// Why the fleet-time effect is not optional: a port called at by every ship in
// the same calendar week is not separable from a fleet-wide time shock (spec
// 3). Without fleet_time in the model that non-identifiability is reported as a
// confident port hazard; with it, the port interval widens instead, which is the
// honest answer. sigma_time is what the two hypotheses trade against.
//
// Ragged voyages: arrays are padded to Tmax and every loop stops at T[v]. Padded
// epochs are never in the likelihood, so a short voyage cannot contribute
// phantom zero-onset epochs that would drag every rate down.
//
// Wastewater (spec 1.3) is a second observation of the *same* latent incidence,
// not a second hazard: a ship's greywater is a closed integrating system, so it
// measures the prevalence of shedders aboard whatever port infected them.
//
//   share[t]        = (w_shed * incidence_total)[t] / persons_aboard[t]
//   logit(p[i])     = ww_logit_base + ww_slope * log(share[t] + floor)
//   ww_reads[i]     ~ beta_binomial(ww_total[i], p[i] * ww_conc, (1-p[i]) * ww_conc)
//
// w_shed is a *survival* kernel (P(still shedding at lag k), offset by the
// holding time), so the signal integrates rather than tracking onsets. Replicate
// collection points are pooled into one trial and the depth is capped before the
// data reaches Stan, and ww_conc adds the overdispersion that keeps a deep
// library from being read as millions of independent trials — three separate
// guards against the channel outvoting the clinical line list it is correlated
// with. NW = 0 turns it off, leaving ww_* prior-only.

functions {
  /* Per-person-hour ashore rate by (group, port) for one voyage.
     Ports this voyage did not call at get 0, so their hours cannot leak in. */
  matrix voyage_rate(array[] int visit_row, array[] int is_crew,
                     array[] real crew_repeat_row, vector lambda_visit,
                     real log_crew_ratio, real beta_repeat) {
    int G = size(is_crew);
    int P = size(visit_row);
    matrix[G, P] rate = rep_matrix(0.0, G, P);
    for (p in 1 : P) {
      if (visit_row[p] == 0) {
        continue;
      }
      for (g in 1 : G) {
        rate[g, p] = lambda_visit[visit_row[p]]
                     * (is_crew[g] == 1
                        ? exp(log_crew_ratio
                              + beta_repeat * crew_repeat_row[p])
                        : 1.0);
      }
    }
    return rate;
  }

  /* (group, Tmax) new infections: exposure-driven imports plus renewal
     secondaries shared out by group. Epochs past Tv stay zero. */
  matrix voyage_incidence(int Tv, vector w_gen, array[] matrix ashore,
                          matrix aboard, matrix rate, vector share,
                          real lambda_aboard, real r_onboard) {
    int G = rows(aboard);
    int L_gen = num_elements(w_gen);
    matrix[G, cols(aboard)] incidence = rep_matrix(0.0, G, cols(aboard));
    vector[Tv] total = rep_vector(0.0, Tv);
    for (t in 1 : Tv) {
      real secondary = 0;
      for (k in 1 : min(t - 1, L_gen)) {
        secondary += w_gen[k] * total[t - k];
      }
      secondary *= r_onboard;
      for (g in 1 : G) {
        incidence[g, t] = lambda_aboard * aboard[g, t]
                          + row(ashore[g], t) * rate[g]'
                          + secondary * share[g];
      }
      total[t] = sum(col(incidence, t));
    }
    return incidence;
  }

  /* Shedder prevalence as a share of the people aboard, per epoch. */
  vector shedder_share(int Tv, vector w_shed, matrix incidence,
                       vector persons) {
    int L = num_elements(w_shed);
    vector[Tv] share;
    for (t in 1 : Tv) {
      real shedders = 0;
      for (k in 1 : min(t, L)) {
        shedders += w_shed[k] * sum(col(incidence, t - k + 1));
      }
      share[t] = shedders / fmax(persons[t], 1.0);
    }
    return share;
  }

  /* Expected onsets: incubation convolution truncated at the horizon, which is
     how right censoring enters. Applying censoring-discounted exposure hours as
     well would discount it twice. */
  matrix voyage_onsets(int Tv, vector f_inc, matrix incidence,
                       real ascertainment) {
    int G = rows(incidence);
    int L_inc = num_elements(f_inc);
    /* Padding is 1.0, not 0: a zero mean makes poisson_lpmf(0 | 0) fine but any
       arithmetic on it fragile, and these epochs are never in the likelihood. */
    matrix[G, cols(incidence)] mu = rep_matrix(1.0, G, cols(incidence));
    for (g in 1 : G) {
      for (t in 1 : Tv) {
        real m = 0;
        for (k in 1 : min(t, L_inc)) {
          m += f_inc[k] * incidence[g, t - k + 1];
        }
        // Floor keeps an all-zero-exposure epoch from making a count impossible.
        mu[g, t] = ascertainment * m + 1e-9;
      }
    }
    return mu;
  }
}

data {
  int<lower=1> V;                          // voyages
  int<lower=1> S;                          // ships
  int<lower=1> P;                          // distinct ports in the fleet
  int<lower=1> G;                          // person groups (passenger, crew)
  int<lower=1> NV;                         // port visits (port x calendar week)
  int<lower=1> W;                          // calendar weeks spanned
  int<lower=1> Tmax;
  array[V] int<lower=1> T;                 // observation epochs per voyage
  array[V] int<lower=1, upper=S> ship;
  array[G] int<lower=0, upper=1> is_crew;  // which group carries the crew terms
  array[V, P] int<lower=0, upper=NV> visit_idx;  // 0 = port not called at
  array[NV] int<lower=1, upper=P> visit_port;
  array[NV] int<lower=1, upper=W> visit_week;
  array[V, P] real<lower=0> crew_repeat;   // earlier calls by this ship
  int<lower=1> L_inc;                      // incubation pmf length (lag 0..L_inc-1)
  int<lower=1> L_gen;                      // generation pmf length (lag 1..L_gen)
  vector<lower=0>[L_inc] f_inc_raw;
  vector<lower=0>[L_gen] w_gen_raw;
  array[V, G, Tmax] int<lower=0> onsets;   // zero-padded past T[v]
  array[V, G] matrix<lower=0>[Tmax, P] ashore_hours;
  array[V] matrix<lower=0>[G, Tmax] aboard_hours;
  array[V] vector<lower=0>[G] secondary_share_raw;
  array[V] real<lower=0, upper=1> ascertainment;
  real hazard_log_prior_mean;              // log rate per person-hour ashore
  real<lower=0> hazard_log_prior_sd;
  real baseline_log_prior_mean;            // log rate per person-hour aboard
  real<lower=0> baseline_log_prior_sd;
  real r_log_prior_mean;                   // log R_onboard, fleet mean
  real<lower=0> r_log_prior_sd;
  real<lower=0> port_sd_prior_scale;
  real<lower=0> visit_sd_prior_scale;
  real<lower=0> time_sd_prior_scale;
  real<lower=0> ship_sd_prior_scale;
  real<lower=0> r_sd_prior_scale;
  real<lower=0> crew_ratio_prior_sd;
  real<lower=0> repeat_prior_sd;
  // Wastewater channel. NW = 0 is a valid, fully clinical fit.
  int<lower=0> NW;                         // pooled samples (one per voyage-epoch)
  array[NW] int<lower=1, upper=V> ww_voyage;
  array[NW] int<lower=1> ww_epoch;
  array[NW] int<lower=0> ww_reads;         // depth-capped pathogen reads
  array[NW] int<lower=1> ww_total;         // depth-capped library size
  int<lower=1> L_shed;
  vector<lower=0>[L_shed] w_shed;           // shedding survival, lag 0 first
  array[V] vector<lower=0>[Tmax] ww_persons;  // headcount aboard per epoch
  real<lower=0> ww_share_floor;
  real ww_base_prior_mean;
  real<lower=0> ww_base_prior_sd;
  real ww_slope_prior_mean;
  real<lower=0> ww_slope_prior_sd;
  real ww_conc_prior_log_mean;
  real<lower=0> ww_conc_prior_log_sd;
}

transformed data {
  vector[L_inc] f_inc = f_inc_raw / sum(f_inc_raw);
  vector[L_gen] w_gen = w_gen_raw / sum(w_gen_raw);
  array[V] vector[G] secondary_share;
  for (v in 1 : V) {
    // Normalized here so the model block never divides by a group total of zero
    // for a voyage whose crew never went ashore.
    secondary_share[v] = secondary_share_raw[v] / sum(secondary_share_raw[v]);
  }
}

parameters {
  real mu_log_hazard;                      // fleet mean log port hazard
  real<lower=0> sigma_port;                // between-port spread
  vector[P] z_port;
  real<lower=0> sigma_visit;               // between-visit spread within a port
  vector[NV] z_visit;
  real<lower=0> sigma_time;                // fleet-wide calendar-week shock
  vector[W] z_time;
  real mu_log_aboard;                      // fleet mean log onboard baseline
  real<lower=0> sigma_ship;
  vector[S] z_ship;
  real mu_log_r;                           // fleet mean log R_onboard
  real<lower=0> sigma_r;
  vector[S] z_r;
  real log_crew_ratio;                     // crew:passenger ashore hazard ratio
  real beta_repeat;                        // per earlier call at the same port
  real ww_logit_base;                      // background read fraction, logit scale
  real<lower=0> ww_slope;                  // elasticity in shedder prevalence
  real<lower=0> ww_conc;                   // beta-binomial concentration
}

transformed parameters {
  // Only the reportable levels live here; the (voyage, group, epoch) incidence
  // and onset matrices are recomputed where needed rather than written to every
  // draw, which would make the output CSV mostly padding.
  vector[P] log_lambda_port = mu_log_hazard + sigma_port * z_port;
  vector[W] fleet_time = sigma_time * z_time;
  vector[NV] log_lambda_visit;
  vector[S] lambda_aboard = exp(mu_log_aboard + sigma_ship * z_ship);
  vector[S] R_onboard = exp(mu_log_r + sigma_r * z_r);

  for (i in 1 : NV) {
    log_lambda_visit[i] = log_lambda_port[visit_port[i]]
                          + sigma_visit * z_visit[i]
                          + fleet_time[visit_week[i]];
  }
}

model {
  mu_log_hazard ~ normal(hazard_log_prior_mean, hazard_log_prior_sd);
  sigma_port ~ normal(0, port_sd_prior_scale);
  z_port ~ std_normal();
  sigma_visit ~ normal(0, visit_sd_prior_scale);
  z_visit ~ std_normal();
  sigma_time ~ normal(0, time_sd_prior_scale);
  z_time ~ std_normal();
  mu_log_aboard ~ normal(baseline_log_prior_mean, baseline_log_prior_sd);
  sigma_ship ~ normal(0, ship_sd_prior_scale);
  z_ship ~ std_normal();
  mu_log_r ~ normal(r_log_prior_mean, r_log_prior_sd);
  sigma_r ~ normal(0, r_sd_prior_scale);
  z_r ~ std_normal();
  log_crew_ratio ~ normal(0, crew_ratio_prior_sd);
  beta_repeat ~ normal(0, repeat_prior_sd);
  ww_logit_base ~ normal(ww_base_prior_mean, ww_base_prior_sd);
  ww_slope ~ normal(ww_slope_prior_mean, ww_slope_prior_sd);
  ww_conc ~ lognormal(ww_conc_prior_log_mean, ww_conc_prior_log_sd);

  {
    vector[NV] lambda_visit = exp(log_lambda_visit);
    /* Per-voyage share, kept so the wastewater terms can be evaluated without
       recomputing the incidence recursion a second time. */
    array[V] vector[Tmax] share;
    for (v in 1 : V) {
      matrix[G, Tmax] incidence = voyage_incidence(
        T[v], w_gen, ashore_hours[v], aboard_hours[v],
        voyage_rate(visit_idx[v], is_crew, crew_repeat[v], lambda_visit,
                    log_crew_ratio, beta_repeat),
        secondary_share[v], lambda_aboard[ship[v]], R_onboard[ship[v]]);
      matrix[G, Tmax] mu_onset = voyage_onsets(T[v], f_inc, incidence,
                                               ascertainment[v]);
      for (g in 1 : G) {
        onsets[v, g, 1 : T[v]] ~ poisson(to_vector(mu_onset[g, 1 : T[v]]));
      }
      share[v] = rep_vector(0.0, Tmax);
      if (NW > 0) {
        share[v][1 : T[v]] = shedder_share(T[v], w_shed, incidence,
                                           ww_persons[v]);
      }
    }
    for (i in 1 : NW) {
      real p = inv_logit(ww_logit_base
                         + ww_slope * log(share[ww_voyage[i]][ww_epoch[i]]
                                          + ww_share_floor));
      ww_reads[i] ~ beta_binomial(ww_total[i], p * ww_conc,
                                  (1 - p) * ww_conc);
    }
  }
}

generated quantities {
  vector[P] lambda_port = exp(log_lambda_port);
  vector[NV] lambda_visit = exp(log_lambda_visit);
  vector[NV] imported_cases_visit;
  vector[P] imported_cases;
  vector[P] attribution_share;
  real aboard_cases = 0;
  real secondary_cases;
  real total_incidence = 0;
  real import_share;
  real crew_hazard_ratio = exp(log_crew_ratio);
  real repeat_hazard_ratio = exp(beta_repeat);
  real loglik_clinical = 0;
  real loglik_wastewater = 0;
  vector[NW] ww_expected_fraction = rep_vector(0.0, NW);

  imported_cases_visit = rep_vector(0.0, NV);
  imported_cases = rep_vector(0.0, P);
  for (v in 1 : V) {
    matrix[G, P] rate = voyage_rate(visit_idx[v], is_crew, crew_repeat[v],
                                    lambda_visit, log_crew_ratio, beta_repeat);
    matrix[G, Tmax] incidence = voyage_incidence(
      T[v], w_gen, ashore_hours[v], aboard_hours[v], rate,
      secondary_share[v], lambda_aboard[ship[v]], R_onboard[ship[v]]);
    matrix[G, Tmax] mu_onset = voyage_onsets(T[v], f_inc, incidence,
                                             ascertainment[v]);
    total_incidence += sum(block(incidence, 1, 1, G, T[v]));
    aboard_cases += lambda_aboard[ship[v]]
                    * sum(block(aboard_hours[v], 1, 1, G, T[v]));
    for (p in 1 : P) {
      if (visit_idx[v, p] == 0) {
        continue;
      }
      real cases = 0;
      // Hours x the rate that group actually faced, so the crew ratio and the
      // repeat slope are inside the attributed count rather than averaged away.
      for (g in 1 : G) {
        cases += rate[g, p] * sum(sub_col(ashore_hours[v, g], 1, p, T[v]));
      }
      imported_cases_visit[visit_idx[v, p]] += cases;
      imported_cases[p] += cases;
    }
    for (g in 1 : G) {
      loglik_clinical += poisson_lpmf(onsets[v, g, 1 : T[v]]
                                      | to_vector(mu_onset[g, 1 : T[v]]));
    }
    if (NW > 0) {
      vector[T[v]] share = shedder_share(T[v], w_shed, incidence,
                                         ww_persons[v]);
      for (i in 1 : NW) {
        if (ww_voyage[i] != v) {
          continue;
        }
        real p = inv_logit(ww_logit_base
                           + ww_slope * log(share[ww_epoch[i]]
                                            + ww_share_floor));
        ww_expected_fraction[i] = p;
        loglik_wastewater += beta_binomial_lpmf(ww_reads[i] | ww_total[i],
                                                p * ww_conc,
                                                (1 - p) * ww_conc);
      }
    }
  }
  secondary_cases = fmax(0.0, total_incidence - sum(imported_cases) - aboard_cases);
  import_share = sum(imported_cases) / fmax(total_incidence, 1e-12);
  // Share of *all* fleet incidence attributed to each port: the fleet quantity
  // the single-ship model could not report (spec 2, PortHazardEstimate).
  attribution_share = imported_cases / fmax(total_incidence, 1e-12);
}
