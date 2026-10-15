# Sentinel Source + Market Revision — provisioning, embarkation-market, and voyage covariates

> **Status:** frozen design, landed with its implementation in the same change.
> Ledger entry `docs/ledger/SENTINEL-SOURCE-MARKET-01.md`.

Revision of `sentinel_surveillance_spec.md` (v2). The forward model now ties
provisioning, crew, and passengers to ports and to cruise/market structure:
PROVISIONED-SOURCE-01 derives lot minting from a per-source `q_source` registry
(`docs/provisioned_source_01_design.md`), `crew_shore_leave_fraction` is wired
(`rhythm_layer.py`), boarding prevalence is role-stratified
(`engines/initiation.py`), and demographic mix varies by market segment
(`presidio/data/social/ship_population_*.json`). The fleet incidence model in
`sentinel_fleet.stan` had exactly one port-to-ship channel — person-hours
ashore at port calls — plus a flat `lambda_aboard` baseline. Provisioned-source
cases carried no ashore hours and would have been absorbed into the baseline or
smeared into the home-port visit hazard; embarkation prevalence had no channel
of its own; market structure had no covariate surface. This revision adds the
three terms the new couplings need and the confound flags they imply.

## 1. The incidence model, revised

Per (voyage, group, epoch) inside `voyage_incidence`:

```text
incidence[g,t] = lambda_aboard[ship] * aboard[g,t]
              + susc[v] * Σ_p λ_visit[g,p] * ashore[g,t,p]        (existing)
              + susc[v] * Σ_s κ_s        * prov[g,t,s]            (NEW)
              + susc[v] * ε_m[g] · persons_boarded[v,g]           (NEW, t = embark_epoch)
              + R_onboard[ship] * Σ_k w_gen[k] * total[t-k] * share[g]
```

`susc[v] = exp(X[v] · beta_x)` is the voyage-level susceptibility multiplier
(§4). The renewal term and the wastewater observation of the same latent curve
are unchanged. `lambda_aboard` keeps its meaning: the residual onboard
background the named channels do not explain.

## 2. The provisioning-source channel (κ_s)

**Exposure.** `prov[v,g,t,s]` = servings of lots provisioned from `source_id`
`s`, consumed by group `g` at epoch `t`. The schema
(`ObservationBundle.provisioning`, §5) carries per-epoch serving counts per
group; totals with a `service_window_epochs` pair are spread uniformly over the
window, the same no-invented-profile rule as ashore hours over call epochs
(`_sentinel_data.ashore_hours_by_epoch`).

**Hazard.** `log κ_s = mu_log_prov + sigma_source * z_source[s]`, partially
pooled per `source_id` across the fleet — two voyages provisioning from the
same source share its prevalence, exactly the visit-level logic pooled per
port×week. κ_s is a per-serving hazard. There is deliberately no per-receiving
(week) level inside κ: supply-side shocks are source-level and are absorbed by
`sigma_source`; adding a shared week column would put every provisioning event
in the same calendar cell as the fleet-time effect and re-create the
port×week degeneracy on a weaker exposure column.

**Priors (declared, Grade C modelling choices — nothing fit to an anchor).**
`mu_log_prov ~ normal(log 1e-4, 2.0)` — the same prior as the port hazard:
a voyage serves O(1e3-1e4) provisioned servings, so the median puts a handful
of food-channel cases on it; wide enough to leave orders of magnitude open.
`sigma_source ~ normal(0, 0.75)`.

**Separability flag.** `source_home_confounded`: a source whose every
consuming voyage embarked from one shared home port *and* whose first service
epoch falls inside that port's embarkation ashore window. κ_s, the home port's
embark-day λ, and ε_m then share the embarkation timing; only the exposure
columns (servings vs pier-hours vs persons) separate them. Reported from the
design like `fleet_time_confounded_ports`, never inferred from interval width.

## 3. The embarkation-market channel (ε_m)

Boarding prevalence is a per-capita import against the **source market** —
passengers drawn from a consumer market, crew from a labour market — not a
per-person-hour exposure on the embarkation pier, which the home-port call
already measures. These are different quantities with different offsets
(`log persons`, not `log person-hours`) and different timing (carriage at
boarding, before the voyage).

**Exposure.** `persons_boarded[v,g]` = headcount boarding at embarkation
(defaults to `n_passengers`/`n_crew`; an explicit `n_boarded` overrides for
partial-complement scenarios). All of it lands at `embark_epoch` — the
embarkation day's first epoch. Imported carriage at boarding is treated as
infection at `embark_epoch` with the voyage's full incubation pmf: the delay
distribution is then onset-delay-from-boarding, an approximation declared here
because the alternative (pre-elapsed incubation at boarding) requires a
boarding-time infection-age distribution no dataset carries.

**Hazard.** `ε_m = inv_logit(mu_logit_market + sigma_market * z_market[m])`,
pooled per `market_id` across the fleet. Logit scale because ε_m is a
probability: `exp()` on a log scale admits prevalence > 1, which is
constructionally impossible. Priors (declared): `mu_logit_market ~
normal(logit 2e-3, 1.5)` — 0.2% central boarding prevalence with ~20x odds
either way; `sigma_market ~ normal(0, 0.75)`.

Markets are declared per group: `embarkation.markets = {"passenger": ...,
"crew": ...}` — a cruise line's consumer market and its crew labour market are
different pools.

**Separability flag.** `market_home_confounded`: every voyage boarding from
market m embarked at one shared home port with an ashore windowed embarkation
day — ε_m and that port's embark-day λ then compete on the same epochs.

## 4. Voyage covariates (market structure)

`X[v]` is a caller-supplied covariate row per voyage (e.g. child fraction of
the demographic mix, segment indicator); `beta_x` is one shared coefficient
vector applied multiplicatively to the three import channels. It answers
"does a voyage's market composition change per-exposure risk" without
inventing named effects inside the fit. `beta_x ~ normal(0, 0.5)`. K = 0 keeps
the old model exactly. Covariates are *not* applied to `lambda_aboard` or
`R_onboard`: those are ship-level poolings, and a voyage covariate on them
would silently re-enter the market structure the ship level already absorbs.

## 5. Observation schema additions (`ObservationBundle`)

```json
"provisioning": {
  "<source_id>": {
    "servings_per_epoch": {"passenger": [...], "crew": [...]},
    // or
    "servings_total": {"passenger": N, "crew": M},
    "service_window_epochs": [a, b]
  }
},
"embarkation": {
  "markets": {"passenger": "<market_id>", "crew": "<market_id>"},
  "n_boarded": {"passenger": 0, "crew": 0},     // optional override
  "embark_epoch": 1                              // optional; defaults to the
                                                  // embarkation day's first epoch
},
"covariates": {"child_fraction": 0.08, ...}
```

Validated like `exposure_totals`: non-negative numbers, known keys. A
provisioning `source_id` never enters the port list — it is a supply-chain
entity, not a call; the itinerary does not need it (PROVISIONED-SOURCE-01's
own non-goal: `source_id` is a scenario label, not a routed leg). A field
export from the sim's mint ledger (`provisioned_source_id` on object rows,
the `{source_id, n_stations, n_contaminated}` mint summary) is the producer
seam; this schema is what it writes to.

## 6. Posterior quantities and confounds

Generated quantities add: `kappa[NS]`, `epsilon[NM]`,
`imported_cases_source[NS]`, `imported_cases_market[NM]`,
`attribution_share_source[NS]`, `attribution_share_market[NM]`.
`import_share` is upgraded: share of fleet incidence imported through *any*
channel (ports + sources + markets), previously ports-only — provisioned and
boarded cases are imports. `secondary_cases` nets all import channels out.

Fleet summaries add `source_hazards.csv` / `market_hazards.csv` next to
`port_hazards.csv` / `visit_hazards.csv`, each row carrying the confound flags
of §2–3.

## 7. Scope and non-goals

- Single-ship `sentinel_attribution` is untouched: one voyage cannot pool
  sources or markets, and its port-visit attribution is unchanged.
- The port-ledger validation trick (port signal generated from the same λ_p
  the ship used) gains a provisioning-source counterpart in a later leg: a
  supplier-surveillance signal generator (inspection/RASFF analogue of
  `port_surveillance_<region>.json`) is its own mechanism, named here so the
  seam is on record. Until then `corr(inferred κ_s, source truth)` is checked
  only in synthetic recovery, where the truth is the declared κ.
- The reference walker (`_sentinel_fleet_reference.py`) walks the same
  density; CmdStan and numpy stay parity-tested on one model.
- `example_*` fixture data carries a small provisioning + market block so the
  whole path — manifest → data builder → forward → fit → report — is
  exercised without new fixture files.
