# DP-REPLAY-DOSE-DIAG-01
**Date:** 2026-11-22
**Commit:** 519c3e97
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 41097e74
**Scope note:** index-only exposure diagnostic — no infection converts, no theta

## Scope

Checkpoint B of the post-behavior theta protocol (THETA_AFTER_BEHAVIOR):
the four prespecified, non-outcome-selected movement seeds of
`covid_dp_replay_01` arm `replay_niid` (20200205–20200208), the first
120 hours on the dedicated `diamond_princess` hull, one imported source,
current normalized shedding and transport, susceptibility-weighted
recipient doses, and **secondary transmission disabled** — realized by
pinning `pathogen_overrides.sars_cov2_resp.dose_response
.susceptibility_scale` to 1e-30 so infection hazards are ~0 while the
engine's dose accounting still records every challenge. Tool:
`tools/dp_dose_diagnostic.py`; committed readout:
`docs/covid/dp_dose_diag_01_readout.json`.

The optional `Θ_new = Θ_old · Q_old/Q_new` mapping is **not applicable**:
no old-movement-kernel arm runs the dedicated diamond hull
(`replay_baseline` rides `mega_cruise_5000` under the journal clock), so
the protocol's own fallback applies — Q_new is reported per seed and
Checkpoint C brackets directly off a labelled historical reference.

## Readout (measured, 4 seeds × 120 epochs, 3710 eligible recipients)

| seed | source | shed epochs | recipients | zero frac | dose total | dose p50/p99 | U·D mean | U·D p50/p99 |
|------|--------|------------:|-----------:|----------:|-----------:|--------------|---------:|--------------|
| 20200205 | pax 1826 (PC_D6_P_M) | 48 | 1805 | 0.51 | 2.1e-7 | 2.9e-13 / 8.8e-11 | 3.4e-14 | 7.6e-18 / 6.3e-14 |
| 20200206 | pax 1581 (PC_D12_P_F) | 48 | 3331 | 0.10 | 4.1e-8 | 6.6e-19 / 5.0e-14 | 1.9e-13 | 1.6e-22 / 8.8e-17 |
| 20200207 | staff 391 (PC_D8_S_M) | 48 | 2932 | 0.21 | 3.9e-8 | 1.2e-18 / 6.5e-15 | 2.6e-13 | 2.4e-22 / 4.3e-17 |
| 20200208 | pax 1259 (PC_D6_P_A) | 48 | 1643 | 0.56 | 1.1e-8 | 1.1e-13 / 1.8e-11 | 9.1e-15 | 1.0e-17 / 3.4e-14 |

- Source echoes: each seed's index sheds in 48 of 120 epochs (infection
  age 2.8 d at import, onset day 3); locations tracked per epoch —
  overwhelmingly the cabin corridor once quarantine binds, with venue
  visits only pre-confinement.
- Route mix: `caregiver` + `droplet` carry >99% of delivered dose;
  `direct_contact` and `fomite` ~1e-15; `hvac_airborne` nonzero at
  1e-12–1e-13 — present but orders below the contact routes, consistent
  with the "outside isn't venting much virion" picture.
- Setting mix: `cabin` takes 60.8–99.5% of dose by seed (82.9% / 99.5%
  / 99.1% / 60.8% on 05/06/07/08); on 20200208 the index's pool and
  grill visits leave 14% outdoor and ~12% each in dining and
  indoor-free, while outdoor is e-14–e-20 elsewhere.
- Reach vs intensity are anti-correlated across seeds: the two
  passenger-corridor sources dose ~half the ship with a heavy tail
  (p99 ~1e-11–1e-10), while the PC_D12/PC_D8_S sources reach ~80–90%
  thinly (p50 ~1e-18, p99 ~1e-14–1e-15). The crew share of recipients
  swings 149–776 — the staff-cabin source (20200207) doses crew
  preferentially; passenger share of delivered dose is 72–99.5% by
  seed (84.0% / 99.5% / 99.0% / 72.0%).
- U·D (normalized host-susceptibility-weighted dose, i.e. the exponent
  factor a Θ multiplies): seed means 9e-15–2.6e-13; p99 across seeds
  4e-17–6e-14. For P_i = 1−exp(−Θ·U_i·D_i) to matter on the heavy tail
  (U·D ~1e-13–1e-11), Θ needs ~1e10–1e12 on this 120h window — three
  decades above the cell's historical 7.9e6 on the old kernel, which is
  exactly why the reference is labelled, not mapped.

## Judgment calls

- Susceptibility weight uses the host factor alone:
  `dose_response_susceptibility / susceptibility_scale` recovers
  draw·age_band with the pinned scale divided out, matching the
  normalized Θ convention `1−exp(−Θ·U·D)`.
- "Contact-duration proxy" is reported as per-recipient
  `dose_epochs` quantiles (epochs with positive dose delta): p50 12–14,
  p90 33–38, p99 48–52 across seeds; direct index attribution proxy is
  the `direct_contact` route total.
- The diagnostic writes no θ leg and scores nothing against an
  epidemiological anchor.

## Next

Checkpoint C: 12 integrated cells (3 log-spaced Θ × the same 4 matched
seeds) centered on a labelled historical normalized reference ±1
decade, declared before submission — the readout above is what the
bracket anchors to.
