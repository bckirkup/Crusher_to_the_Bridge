# ANCHOR-MIXTURE-01
**Date:** 2026-10-02
**Commit:** def39066
**Pathogens:** norwalk_gi
**Status:** closed

## Declaration

A8 (unconditional AGE incidence per 100,000 travel-days) and A9 (posting
probability) are **fleet-mixture anchors**: they score the frequency of
reported cases and posted outbreaks over a heterogeneous voyage population —
the real fleet's mix of quiet and loud voyages. A4 is the complementary
conditional quantity: the attack rate VSP publishes, conditional on posting.

A cell of i.i.d. voyages at one parameter point cannot hold A4 and A8/A9 at
their targets simultaneously. Conditioning removes every voyage below the
posting rule, so at 7.075-day voyages A4's band implies 501–1,059 per
100,000 travel-days against A8's 16.9–29.2 — separation factor 17.2, no
overlap (measured on the 37-gate map,
`docs/norovirus/norovirus_open_ledger.md`). Scoring A8/A9 against a
homogeneous ensemble therefore measures the parameter point, not the
mixture; the miss can only close when the ensemble itself contains the
observed quiet/outbreak composition — the per-host heterogeneity gap the
noro open ledger names as binding.

Consequences, recorded once:

- A cell whose take-off fraction is 1.0 carries a posting floor, not a
  verdict: its A8/A9 miss is under-determined evidence about the point and
  says nothing about the mixture.
- Per-point cells are *inputs* to a mixture estimate, never the mixture;
  the MMWR ship-size-band targets score against a voyage ensemble spanning
  the loud/quiet composition, not against any single design cell.
- A8 and A4 are reported side by side precisely because they are different
  populations; "fixing" the separation by moving a constant fits the
  anchor, and is barred by the provenance rule regardless.
