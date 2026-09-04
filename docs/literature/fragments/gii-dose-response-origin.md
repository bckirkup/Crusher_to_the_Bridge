# Register fragment — the GII α interval's origins: one endpoint body-verified, the other abstract-only, and the shipped pair's own source unreached (tranche 20)

> **Not merged.** Proposed amendment to `docs/parameter_provenance_register.md`
> §3.1, rows `dose_response.alpha` / `beta` and
> `illness_probability.eta` / `gamma`. Not authoritative until the lead merges
> it. Evidence:
> [`../consensus_tranche_20_full_text_reverification.md`](../consensus_tranche_20_full_text_reverification.md)
> §1, §3 and findings **F9** and **F10**.

**Status:** Additive fragment, not authoritative until the lead merges it. Evidence: tranche 20.

**No dose figure changes and none is proposed.** Every dose figure in this
repository is void pending refit
([`../../norovirus/norovirus_open_ledger.md`](../../norovirus/norovirus_open_ledger.md)
§1); the ID50s below are the **sources' own published figures**, quoted as
evidence about those sources. The α interval [0.072, 0.161] and β = 32.81 are
unchanged here.

| Quantity | Shipped | Class | Evidence / interval | Origin | State | Task |
|---|---|---|---|---|---|---|
| `dose_response.alpha` / `beta` | unchanged | unchanged | *Amendment only:* the two endpoints of the GII interval do not have the same evidentiary standing. **Guix 2020 is body-verified**: its own text gives "2,934 (95% CI 1,683–5,044) genome copies/day for norovirus GII" and "556 (95% CI 319–957) … for norovirus GI", and the same body restates the volunteer-challenge range it relies on — "range from 18 (95% CI 1–4,350) … to 2,800 (95% CI, 290–25,000) genome equivalents" — which is a **secondary** route to the Teunis figure, not a primary one. **Rouphael 2022 is abstract-only** after two attempts, so the lower endpoint 0.072 derives from an abstract-only ID50, and the register's attribution of infection/illness rates to Rouphael **Table 1** was not reached by this route. **Teunis 2008, the source of the shipped pair itself, returned zero chunks in three attempts**, including a query naming its table; its aggregation parameter therefore remains unverified by retrieval and the register's open categorical question is unchanged. Ramesh 2020 is body-verified (Grade C, gnotobiotic pig) | Teunis 2008: **?nr** (3 attempts), Rouphael 2022: **Ab** (2 attempts; the Table 1 attribution **?nr**), Guix 2020: **R** (+ **Sec** for the volunteer range it cites), Ramesh 2020: **R** + Ab | unchanged | — |
| `illness_probability.eta` / `gamma` | unchanged | unchanged | *Amendment only:* neither citation was reached. Teunis 2008 **?nr** (3 attempts); Teunis 2020 returned chunks that were **only its electronic appendix and R code**, so the withdrawn ≈3.7× genogroup ratio could not be re-examined from the paper body. The register's account — that the per-copy genogroup contrast cannot be quantified — is unchanged and untouched by this pass | Teunis 2008: **?nr**, Teunis 2020: **?nr** | unchanged | — |

## Section-of-origin ledger

| Citation | Quantity + unit, as queried | Query string | Retrieval | Section of origin | Verbatim locator |
|---|---|---|---|---|---|
| Teunis 2008 | ID50, genome equivalents; particles per aggregate | "Norwalk virus: how infectious is it beta-Poisson dose response aggregated virus particles ID50 genome equivalents human challenge" and 2 further phrasings incl. the table by number | not retrieved (3 attempts) | **?nr** | — |
| Teunis 2020 | per-genogroup infectivity, per aggregate | "norovirus genogroup GI GII infectivity per aggregate dose response host susceptibility variation pathogenicity ratio" (2 phrasings) | chunks (appendix and R code only) | **?nr** | — |
| Guix 2020 | illness ID50, genome copies/day | "norovirus waterborne outbreak dose reconstruction from drinking water ID50 genome copies per day illness" | chunks | **R** + **Sec** | "we estimated 50% illness doses … 556 (95% CI 319–957) genome copies/day for norovirus GI and 2,934 (95% CI 1,683–5,044) genome copies/day for norovirus GII"; "Reported doses causing infection in 50% of exposed persons (ID50) … range from 18 (95% CI 1–4,350) … to 2,800 (95% CI, 290–25,000) genome equivalents" |
| Rouphael 2022 | GII.2 ID50, GEC; Table 1 infection and illness rates, % | "norovirus GII.2 Snow Mountain controlled human challenge ID50 genome equivalent copies infection illness rate" (2 phrasings) | abstract only | **Ab** | abstract: "median infectious dose (ID50) … 5.1×10⁵ GEC" |
| Ramesh 2020 | ID50, genome equivalents (pig) | "gnotobiotic pig norovirus GII.4 50 percent infectious dose ID50 genome equivalents" | chunks | **R** + Ab | body chunk carries the ID50 |
