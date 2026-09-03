# Register fragment — cabin-localization fraction `f`

**Status:** additive fragment, tranche 17 / unit `cabin-localization` / task
**#12**. Not authoritative. This is a *proposal* for one row of
[`../../parameter_provenance_register.md`](../../parameter_provenance_register.md),
written here because that register is shared and merged by the lead in one pass.
Evidence and derivation: [`../consensus_tranche_17_cabin_localization.md`](../consensus_tranche_17_cabin_localization.md).
**No profile, config or code value changes with this fragment.**

## Proposed row

Replacing the existing §3 row for `Cabin-localization fraction f`, in the
register's `| Quantity | Shipped | Class | Evidence / interval | State | Task |`
format:

| Quantity | Shipped | Class | Evidence / interval | State | Task |
|---|---|---|---|---|---|
| Cabin-localization fraction `f` | swept | **C, bounded above** | **Still no measurement of `f`** — no study on any ship reports the share of norovirus transmission occurring between cabinmates, and none reports the cabin-level case distribution that would give it without a model (tranche 17 §3, §6). What exists is an **upper bound**: structurally `f ≤ 0.5` at double occupancy, since one occupant of every affected cabin was infected elsewhere; and `f ≤ 0.18` (Wikswo 2011, RR 3.0, AR 15.4%, `10.1093/cid/cir144`), `≤ 0.26` (Chimonas 2008, OR 3.40, 95% CI 1.80–6.44, AR 24.1%, `10.1111/j.1708-8305.2008.00200.x`), `≤ 0.37`, CI 0.25–0.45 (Mouchtouri 2024 pooled, OR 38.70, 95% CI 13.51–110.86, `10.2807/1560-7917.ES.2024.29.10.2300345`) — all Grade B/C for `f`, all over-attributing to the cabin because cabinmates share dining, excursions and travelling party. Household SAR is the Grade B analogue at **14–23%** per contact in households of ≥3 (Quee 2020 15%, `10.1016/S1473-3099(20)30058-X`; Matsuyama 2018 13.8%, `10.1177/0300060518776451`), and is a per-contact probability, not a fraction of transmission. **No lower bound is supported: `f = 0` is not excluded.** Fitted route splits (Towers 2017, Tsang 2018, De Bellis 2025, Lei 2018) are excluded as circular against the attack-rate anchors | **evidence recorded — upper bound only, `f ≤ 0.5` structural, `f ≤ 0.18–0.45` empirical; ∅ null on any central value** | #12 |

## Notes for the merge

* The change from the current row is **not** the arrival of a value. It is that
  the null is now a *bounded* null: the previous row said no measurement exists,
  which remains true; this adds a ceiling that any swept range must respect.
* The bound is arithmetic derived by this unit from published associations and
  attack rates (tranche 17 §5.2), not a value read from a paper. It is Grade C
  as a derivation over Grade A/B inputs and should never be cited as measured.
* It should not be read as a recommendation about the sweep range. Whether and
  how the screen's swept axis changes is a separate decision for #12, and this
  unit did not compute what any of these values would do to any anchor.
* Two dependencies worth queueing: (a) the Wikswo and Chimonas Results tables are
  paywalled and would replace the derivation with counts; (b) De Bellis 2025
  (`10.1093/jtm/taaf059`) fits an explicit cabin-sharing route to a 121-case
  cruise line-list — if its Appendix reports the cabin share it is the most
  relevant number in the literature, and it is still a fitted one.
