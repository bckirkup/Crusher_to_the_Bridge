# NORO-IMPLICATED-TITRE-01
**Date:** 2026-10-12
**Commit:** 93b7eec6
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 93b7eec6

Literature census of outbreak-implicated food-item norovirus titres + the
shipped-draw reading, answering the titre-tail hypothesis raised by
NORO-DOSE-POS-01. Full document:
`docs/norovirus/noro_implicated_titre_review.md`. No engine change; no
campaign; no anchor fitting.

**Measured.** The outbreak-implicated quantitative titre census spans
~1.5e2–4.6e3 copies/g (Lowther 2012 outbreak-GM 1,048, no implicated sample
<152; Flannery 2013 implicated 2,350/2,040; Polo 2016 implicated 43–1,170
copies/oyster; Rexin 2024 implicated 44–4,630 GC/g). Every figure above 1e4
copies/g found sits in a non-implicated denominator (harvest-area
surveillance to 20,080; retail surveys to 1.45e6). The >1e4 titre-tail
hypothesis fails on titre grounds. Point-source implicated-item attack
rates among exposed: 41–100% (Polo 43–100%; Papafragkou 41%).

**Measured (shipped-draw reading).** On the declared illness Hill
(η = 0.508, γ = 0.095): median shipped serving ~4.7e4 GEC → p ≈ 0.62;
draw ceiling 2.5e6 → p ≈ 0.74; the p = 0.71 challenge reference needs the
joint upper tail. A census-band implicated serving (titre ∈ [1.5e2, 5e3] ×
~150 g) sits at p ≈ 0.5–0.72 — the real implicated band overlaps the
measured AR band without any tail. ~39% of shipped draws fall below the
observed implicated floor; the top ~15% is supported only by non-implicated
surveys — both tails of `COMMON_SOURCE_LOT_TITRE_GEC_PER_G_RANGE` are the
wrong denominator for a fired `provisioned_lot` object.

**Measured (attenuation decomposition).** The ~3-order raw→delivered gap
is compositional in-engine (lot pans credit losslessly; the median
acquisition is a routine-route dose). On the physical item→gut chain the
least-sourced step is the in-item titre → dose-unit conversion: extraction
recovery under-reads true in-item load ~5–50× (ISO 15216-2 oyster recovery
2.1%, Li 2022) and GC:infectivity is refused as non-identifiable. The
handler-arm transfer range `U(0.003, 0.46)` already brackets the literature
(Duret 2017 hand→food median 0.05; Rönnqvist 2014 glove→cucumber 1.5%).

**Proposal recorded and APPLIED** (NORO-TWO-MODE-TITRE, `56762131`) —
option (a), conditioned two-mode draw inside the shipped interval, now
ships default-ON: `transmission.common_source.titre_draw_mode`
`"two_mode"` resolves a fired `provisioned_lot` object — the implicated
denominator — to the implicated band `lot_titre_implicated_gec_per_g`
logU(1.5e2, 5e3) Grade B (shellfish) / C (produce-RTE — no quantitative
implicated titre exists); a background-stock titre site (none modelled)
resolves to `lot_titre_background_gec_per_g` logU(1e1, 1e3) Grade B.
`"background"` is the labelled pre-change baseline restoring the
single-mode `lot_titre_gec_per_g` draw — identical uniform at the same
stream position. Mint-time titre values re-map, so prior campaign cells
are not bit-identical on titre/dose fields (declared, not a defect);
the stream consumes the same one uniform per titre either way. Options
(b) attenuation re-sourcing and (c) units/ledger framing assessed in the
document; (c) remains the residual framing for the challenge-dose gap.
