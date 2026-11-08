# PLATFORM-FIDELITY-02 campaign ledger

Larger-seed Diamond Princess follow-up to the platform-fidelity study.
Pre-registration: `docs/covid/covid_platform_fidelity_02_prereg.md`; design:
`picard_framework/runs/covid_platform_fidelity_02_dp_design.json`; power
calculation: `campaigns/covid/platform_fidelity_02/power_analysis.py` +
`power_analysis.json`. GM untouched.

## 1. Design (frozen)

- Scenario `diamond_princess_2020`, voyage declared; Θ = 7.9e6,
  infection_age_days 6.8, imports 1, sanitary_visit_mode dwell_weighted.
- Seeds 20200205–20200404 (200/arm), contiguous `seed_base + i` extension of
  the frozen 01b series; CRN pairing proxy vs dedicated on the same seeds.
- Protocols `data/config/protocols_covid_pf_dp_01b.json` (SOP-017-MESSBOX,
  union `exempt_work_zones`, frozen — not retuned).
- Both arms rerun over the full 200-seed series (400 cells) so the campaign is
  self-contained; the first 20 dedicated seeds (20200205–20200224) are the
  canary/replication row against PLATFORM-FIDELITY-01b.
- Power basis: smallest grid n with ≥0.90 power on P(takeoff) and
  both-takeoff paired size at the observed 01b plug-in rates, and ≥0.80 on
  both under halved event rates → **200 seeds/arm**.

## 2. Preflight status

- [x] Power calculation committed and reproducible from the synced S3 cells
      (`power_analysis.py`; S3 prefixes are the PF-01 proxy and PF-01b
      dedicated 20-seed cells).
- [ ] Local smoke proving the `platform_id` override + witness contract.
- [x] `scripts/campaign describe covid/platform_fidelity_02` (arrays 20 +
      180 + 200 = 400) and canary `--dry-run` render; count == design file.
- [ ] Image built and pinned by digest.
- [ ] Canary `dp_t7e6_dedicated_canary` (20 cells) submitted and read out —
      STOP per the gate; owner decides the remaining 380 cells.

## 3. Blocks

| block | arm | seeds | cells | status |
|---|---|---:|---:|---|
| `dp_t7e6_dedicated_canary` | `dedicated_diamond_princess` | 20200205–20200224 | 20 | pending |
| `dp_t7e6_dedicated_rest` | `dedicated_diamond_princess` | 20200225–20200404 | 180 | pending owner approval |
| `dp_t7e6_proxy` | `proxy_mega_cruise` | 20200205–20200404 | 200 | pending owner approval |

Total new executions: 400. No GM cells.
