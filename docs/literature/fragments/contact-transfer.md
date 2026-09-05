# Register fragment — `contact_transfer_fraction` (task #22)

> **Superseded on the engine row.** The `contact_transfer_fraction` row below is history: the field was **retired and refused at load** by the C5 change (#22), because it multiplied the direct-contact pathway dose from the same position as `route_efficiency_multipliers["direct_contact"]` and only the product was identifiable. The two fomite rows stand. See [`../consensus_tranche_12_contact_transfer.md`](../consensus_tranche_12_contact_transfer.md) §10 and the register.

> **Merged.** This fragment was merged into [`../../parameter_provenance_register.md`](../../parameter_provenance_register.md) by the sourcing-wave-1 integration pass, with the lead's corrections applied at merge time. It is kept as the audit trail of what the sourcing unit proposed; it is **not** a live proposal, and where it and the register differ the register holds the status.

**Status:** Additive fragment merged into
`docs/parameter_provenance_register.md`. **This file changes nothing** and is
not authoritative; the register is. Sourcing document:
[`consensus_tranche_12_contact_transfer.md`](../consensus_tranche_12_contact_transfer.md).

Nothing in this fragment recommends a value. The engine field and the fomite
constants are deliberately separate rows because §7 of the tranche shows they
are different mechanisms, and one has already been confused for the other once
in this repository.

## Proposed row — replaces the existing `contact_transfer_fraction` row

| Quantity | Shipped | Class | Evidence / interval | Origin | State | Task |
|---|---|---|---|---|---|---|
| `contact_transfer_fraction` (engine) | **1.0, by omission** — neither active profile sets it | **C** | **Blocked by definition.** The field multiplies dose from *contacted partners* (`_direct_contact_dose`, `_per_partner_contact_dose`), and the schema defines it as the fraction of a partner's **emission** reaching the target. No transfer assay in this literature uses emission as its denominator — all use a pipetted donor inoculum recovered at contact time ([T12](../consensus_tranche_12_contact_transfer.md) §6.4). Nearest measured analogue is **hand → hand: 0.7–6.6 %** (rotavirus 6.6 % at 20 min / 2.8 % at 60 min, Ansari 1988 DOI 10.1128/jcm.26.8.1513-1518.1988; rhinovirus 14 0.7–0.9 %, HPIV-3 undetectable, Ansari 1991 DOI 10.1128/jcm.29.10.2115-2119.1991), Grade B, and **no norovirus or norovirus-surrogate measurement of that direction exists** (§6.3). The **~0.25** anchor in `norovirus/norovirus_model_history.md` §10 **does not trace to a primary measurement**: it is numerically indistinguishable from Anderson 2021's direction-free MS2 pooled mean 0.26 (DOI 10.1128/aem.01215-21), Julian 2010's direction-free 0.23 ± 0.22 on glass (DOI 10.1111/j.1365-2672.2010.04814.x) and Grove 2015's single-direction 24 % surface → hand (DOI 10.1016/j.ijfoodmicro.2014.12.023), and the repository does not say which. As a **direction-free** transfer fraction it is **refuted** — the two directions differ by up to two orders of magnitude under drying, so no single number represents both (§1). Arithmetic only, no recommendation: 0.25 is inside the shipped screen interval 0.06–0.50, at the top edge of the surface → hand norovirus-surrogate range 2.0–24 %, **above** the dried hand → surface range 0.1–1.8 % by ~14–250×, and **above** the hand → hand range by ~4–36×. **Measured to clear no noise floor anywhere** in the PR #368 screen — which is not evidence that any value is correct | not recorded — proposed before axis 3 existed; see [tranche 21](../consensus_tranche_21_full_text_reverification.md) §1 | **blocked by field** (definition unmeasurable) + **~0.25 anchor refuted as a direction-free quantity** | #22 |

## Proposed new rows — the two fomite directions, evidence recorded

These are evidence about `SURFACE_TO_HAND_LOGNORMAL` and
`HAND_TO_SURFACE_LOGNORMAL`, **not** about the field above. Whether the
register wants rows for them is the lead's call; the intervals are recorded
here either way so they are not lost with the fragment.

| Quantity | Shipped | Class | Evidence / interval | Origin | State | Task |
|---|---|---|---|---|---|---|
| surface → hand transfer fraction, non-porous (`SURFACE_TO_HAND_LOGNORMAL`) | lognormal `(-2.1, 1.4)` | **B** | **2.0–24 %** for norovirus + norovirus surrogates on non-porous donors by **infectivity**: MNV-1 stainless steel → finger pad **2.0 ± 2.0 %** and Trespa® → finger pad **4.0 ± 5.0 %**, dried 40 min, 0.8–1.9 kg/cm² for ~2 s (Tuladhar 2013, DOI 10.1016/j.ijfoodmicro.2013.09.018); FCV steel disk → finger pad **7 ± 1.9 %**, air-dried, 0.2–0.4 kg/cm² for 10 s (Bidawid 2004, DOI 10.4315/0362-028x-67.1.103); MNV-1 steel spigot → bare hand **24 %** (1.4-log transfer %), ≥ 9 replicates, **moisture state not stated** (Grove 2015, DOI 10.1016/j.ijfoodmicro.2014.12.023). Human NoV GI/GII bound it from above in **genome copies**: **2–11 %** dry, **1–50 %** wet (Sharps 2012, DOI 10.4315/0362-028x.jfp-12-052). Widened to all analogous viruses and tracers on non-porous donors: **~0.5–80 %**, with humidity and time-since-deposition each worth ~1 order of magnitude (Lopez 2013 up to 57 % at RH 15–32 % and 79.5 % at RH 40–65 %, DOI 10.1128/aem.01030-13; Ansari 1988 rotavirus 16.8 % at 20 min → 1.6 % at 60 min; Behzadinasab 2021 SARS-CoV-2 13–16 % wet / 3–9 % dried, DOI 10.1038/s41598-021-00843-0) | not recorded — proposed before axis 3 existed; see [tranche 21](../consensus_tranche_21_full_text_reverification.md) §1 | **evidence recorded** | #22 |
| hand → surface transfer fraction, non-porous (`HAND_TO_SURFACE_LOGNORMAL`) | lognormal `(-2.1, 1.4)` | **B** | **Splits by moisture; do not state as one interval.** **Wet/immediate 9.2–60 %**: MNV-1 hand → stainless steel **9.19 %** (Dallner 2021, DOI 10.3390/v13071352), MNV-1 finger pad → stainless steel **13 ± 16 %** immediate (Tuladhar 2013), human NoV GII fingertip → stainless steel **58–60 %** in genome copies (Sharps 2012). **Dried 0.1–1.8 %**: MNV-1 **0.1 ± 0.2 %** after 10 min drying (Tuladhar 2013), MNV-1 hand → spigot **0.6 %** (Grove 2015), HuNoV GII **< 1 %** dry (Sharps 2012), rotavirus **1.8 %** at 60 min (Ansari 1988). Disagreement retained: FCV finger pad → steel **13 ± 3.6 %** air-dried but transferred immediately after drying (Bidawid 2004) lands with the wet group, so the dried interval is not tight. Direction asymmetry independently confirmed: significant for MS2 (Anderson 2021) and for influenza A RNA (Zhang 2026, DOI 10.1016/j.ijheh.2026.114766); the ~130× drying penalty falls on **this** direction, matching the PR #378 axis | not recorded — proposed before axis 3 existed; see [tranche 21](../consensus_tranche_21_full_text_reverification.md) §1 | **evidence recorded** | #22 |

## Notes for the merge

* **No Grade A is available** for norovirus contact transfer anywhere in this
  literature: no maritime measurement exists (T12 §6.1), and no human-norovirus
  **infectivity** transfer measurement exists in either direction — every HuNoV
  number is RT-qPCR genome copies, every infectious number is a surrogate
  (§6.2). Grade B is the ceiling, not a provisional grade pending more search.
* Genomic and infectious transfer fractions are kept in separate clauses above
  and should not be merged into one range: a genome-copy fraction is an upper
  bound on the infectious one.
* Porous and food-material values (Rönnqvist, Verhaelen, Stals, Wang, Escudero,
  Derrick, and the food legs of Tuladhar/Bidawid/Dallner/Grove) are excluded on
  material, and QMRA/model-derived values (Wilson, Canales, Kraay,
  Pérez-Rodríguez, Iulietto, Jin, Chang, Zhang 2021) are excluded as model
  outputs — adopting one while scoring on attack rates would be circular. Full
  rejection list with reasons: T12 §5.
* Side finding, not this unit's to fix: `consensus_tranche_5.md` §2b records
  Grove 2015 as not reliably retrievable by targeted Consensus search. It was
  the **first result** of query 5 here and its numbers are confirmed, so that
  provenance null is retired.

## Section-of-origin ledger

Not recorded: this fragment predates the register's section-of-origin axis. The
retrieval ledger covering its citations is
[tranche 21](../consensus_tranche_21_full_text_reverification.md) §1.
