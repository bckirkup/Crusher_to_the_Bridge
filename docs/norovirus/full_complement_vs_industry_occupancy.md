# What "full complement" is, against what real ships sail at

**Status: sourced measurement, no parameter moved.** Every run in the posting,
realism-ladder and hull-compounding campaigns boards each hull's declared
`nominal_complement`. This note asks what that declaration is a capacity *of*,
and where a real sailing sits against it. Nothing here is fitted, and no
complement is changed by it: the question is whether the campaigns' headcount
is a normal sailing, an upper bound, or neither.

## The capacity definition is the whole question

Cruise capacity is published in two incompatible units, and a comparison that
mixes them is meaningless:

- **Lower berths** (equivalently "double occupancy", or Royal Caribbean's
  *APCD*): exactly two per cabin, by definition, whatever the cabin can
  actually sleep. Both operators state the convention in their own filings —
  Carnival: "passenger capacity is calculated based on the assumption of two
  passengers per cabin even though some cabins can accommodate three or more"
  (2019 10-K, Item 1); Royal Caribbean: "APCD … represents double occupancy per
  cabin", and occupancy "in excess of 100% indicates that three or more
  passengers occupied some cabins" (4Q19 earnings release, definitions).
- **Maximum berths** ("full occupancy"): every upper berth and sofa bed sold.
  Runs 20–26% above lower berths on the hulls below.

**Published industry occupancy is per lower berth**, so it routinely exceeds
100% and cannot be read as "the ship was 106% full".

## The declared complements are lower-berth figures

Each hull's `nominal_complement` was declared from the archetype named in its
own `spatial_layout.json` description (B3/#29). Sourcing those archetypes shows
what unit was picked up:

| hull | declared pax + crew | archetype | archetype lower berths | archetype maximum | archetype crew |
|---|---|---|---|---|---|
| `expedition_cruise_450` | 300 + 150 | Silver Cloud / Le Boréal / Viking Star | 254 / 264 / 930 | — | 212 / ~140 / ~465 |
| `classic_cruise_1900` | 1,350 + 560 | HAL Veendam | **1,350** (675 cabins × 2) | 1,620–1,627 | 580–588 |
| `spirit_cruise_3000` | 2,100 + 900 | Carnival Spirit | **2,124** (1,062 cabins × 2) | 2,680 | 930 |

The two large hulls land on their archetype's lower-berth count to within 1%
(classic is exactly 2 × Veendam's cabin count), and their crew is 3–5% below
the archetype's. So **full complement = 100% of lower berths**, not maximum
capacity. Grade **M** (operator fact sheets and deck-plan cabin counts), and
the identity `lower berths = 2 × cabins` is checked in tree for both hulls
rather than assumed.

The expedition hull is the one loose end: its 2:1 passenger/crew ratio matches
Le Boréal and Viking Star but not Silversea, where crew nearly equals guests
(Silver Cloud 254 guests / 212–223 crew, and *more crew than passengers* on
polar itineraries). A 450-person expedition hull is therefore a defensible
Le Boréal-class complement and a wrong Silver Cloud one; it is not repaired
here, because the expedition posting cells are scored on the declared figure.

## Where real sailings sit

Occupancy = passenger cruise days ÷ available passenger cruise days, from
audited operator statistical information:

| operator | year | occupancy (% of lower berths) | source |
|---|---|---|---|
| Carnival Corp | FY2018 | 106.9% | 4Q2019 8-K, statistical information |
| Carnival Corp | FY2019 | **106.8%** | 4Q2019 8-K, statistical information |
| Carnival Corp | FY2023 | 100% | 4Q2024 8-K |
| Carnival Corp | FY2024 | 105% | 4Q2024 8-K |
| Royal Caribbean | FY2018 | 108.9% | 4Q2019 earnings release |
| Royal Caribbean | FY2019 | **108.1%** | 4Q2019 earnings release |
| Royal Caribbean | FY2023 | 105.6% | 8-K 2025-01-28 |
| Royal Caribbean | FY2024 | 108.5% | 8-K 2025-01-28 |

These are fleet-year averages over every itinerary length, not per-voyage
distributions; a single voyage's occupancy is not published anywhere, so the
spread around these means is unmeasured here.

## What that makes of the campaigns

1. **Full complement is a slightly *light* sailing, not a heavy one.** At 100%
   of lower berths the model boards **6–8% fewer passengers** than the
   pre-2020 fleet average and 0–8% fewer than the post-restart years. It is
   **78–84% of maximum berth capacity** — a holiday sailing with every upper
   berth sold carries ~20% more people than any run in the archive.
2. **Crew is 3–5% low** on classic and spirit against their archetypes
   (560 vs 580–588; 900 vs 930), in the same direction.
3. **Arm B's occupancy probe brackets reality from below.** Its cells are
   0.25 / 0.5 / **1.0** of declared complement; real sailings sit at
   1.00–1.09, i.e. at and just *above* the top cell — the end of the probe
   where per-import secondary yield is steepest (classic 0.37 → 2.42 → 6.60
   secondaries per import across the three cells). So the occupancy error runs
   toward *under*-boarding, and correcting it would raise per-import yield, not
   lower it. That is a direction, not a magnitude: 1.07 is outside the probe's
   support and the response there is not measured.
4. **It does not rescue the posting overshoot.** The gap is that 7-day
   postings are 6–20× A9, and a 6–8% headcount correction moves in the wrong
   direction for that. The finding is that the headcount is *not* where the
   error lives — which is worth knowing precisely because it removes a
   candidate.

Nothing in the model is altered by this note. If the complements are ever
re-declared on it, the declaration is a capacity-definition repair (lower
berths → a sourced occupancy multiplier), and it must be measured as its own
matched arm like every other rung, not folded into a default.
