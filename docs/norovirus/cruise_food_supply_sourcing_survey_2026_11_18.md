# Cruise food-supply sourcing survey — 2026-11-18

Status: evidence survey; **adopts nothing** and changes no engine constant. This note asks whether the real cruise food supply chain diversifies by hull class and venue type in ways that bear on high-risk norovirus food classes. It separates measured outbreak/supply-chain facts from descriptive industry reporting and from unmeasured gaps.

Raw peer-reviewed survey: [literature/consensus_tranche_57_cruise_food_supply_chain.md](../literature/consensus_tranche_57_cruise_food_supply_chain.md) ([Consensus thread](https://consensus.app/search/you-are-helping-source-evidence-for-a-maritime-dis/CChFjh6GRo299Hmj2e61wg/)).

## Question

The current model mints supply lots from served Dining venues × a fixed seven-item line set (`shellfish`, `salad_leaf`, `fresh_produce`, `garnish`, `deli`, `bakery`, `dairy`) under one `generic_cruise_port` source with independent contamination draws. The open hypothesis is whether real provisioning instead (a) scales lot size with hull class, (b) bridges lots through a common upstream source/vendor, or (c) assigns high-risk foods unevenly across buffet/MDR/specialty/crew venues so that venue class changes exposure. This survey does not choose among those; it records what is measured.

## What is measured vs described

### Venue/menu incidence and food diversity

- **Measured in this survey:** no peer-reviewed per-venue menu incidence by hull class. The Consensus evidence matrix lists this as unmeasured.
- **Described, industry/press:** large ships carry many more dining options and higher daily meal throughput. Hospitality Upgrade (2025) reports Icon of the Seas at up to 7,600 passengers, ~2,350 staff, >40 dining options, and provisioning for nearly 10,000 people/day over 14 days while 100 nautical miles from land; turnaround day covers the entire cruise, with up to 50 tons of delivered food for Icon-class vessels. BBC Storyworks describes Cunard Queen Elizabeth (~2,000 guests + 1,000 crew) with six restaurants, seven galleys, 234 kitchen staff, >12,000 meals/day, a 24-hour Lido buffet plus main/specialty/crew galleys, and main-restaurant menus repeating on a 24-day cycle. SeaTrade's cruise F&B procurement guide classifies mega-ships (5,000+ passengers/crew) as requiring industrial-scale food production, luxury vessels as premium/personalized, and expedition ships as specialized remote provisioning.
- **Inference only:** consumption-side venue diversity rises with hull size, and specialty/buffet share rises on larger hulls in the repo platform data. Item-line incidence by venue (which venues actually serve shellfish/leafy greens/berries) is **not measured** and should not be inferred from venue counts or service-type names.

### Procurement/provisioning structure

- **Measured/traceable in industry reporting:** ships are self-sufficient for 7–14 days; provisioning is concentrated on turnaround day in short port windows. SeaTrade reports a six-hour port-call window to load ~15,000 items; Hospitality Upgrade reports entire-cruise F&B provisioning on turnaround, with at-sea restocking by fast supply ship or helicopter. Shoreside procurement teams use systems such as Datex/AMOS Procurement with SPMS/POS integration; onboard galleys monitor stock and report real-time data.
- **Academic/descriptive:** Ghiara et al. (2026, via Consensus tranche 57; DOI 10.1186/s12544-026-00813-5) describes cruise F&B supply routing through global distribution hubs, regional chandlers, local port markets, and inter-vessel transfers; central global facilities handle non-perishable/frozen provisions while local chandlers handle perishable/fresh replenishment; requisitions from distinct onboard galley sections are consolidated into a single corporate procurement requisition before routing to assigned suppliers.
- **Inference only:** this supports a centralized procurement layer above individual venues, but it does **not** measure which venues share suppliers, prep batches, or item lines.

### Lot scale and shared lots

- **Measured outbreak event:** Rispens et al. 2020 (MMWR; DOI 10.15585/mmwr.mm6916a3) is the key shared-upstream-lot bridge. Cruise line X had >3% AGE outbreaks on 10 ships July–September 2019. Ship A: 117/2,046 passengers (5.7%) and 8/610 crew; ship B: 85/2,166 passengers (3.9%) and 10/612 crew; ship A second voyage: 83/2,251 passengers (3.7%) and 10/610 crew. Nearly 80% of completed food questionnaires on ship B implicated a smoothie made from frozen fruits/berries; FDA found norovirus in raspberries, tropical fruit cocktail, and berry mix, with sequences ~97.5% similar to stool; food-item lot numbers matched across ships. The line's food vendor had bought several containers — nearly 22,000 pounds — of frozen raspberries of the same lot from a China supplier beginning late June 2019, supplied to the entire fleet; after removal of the fruit items, no further outbreaks were reported, and WHO issued a recall notice.
- **What this establishes:** a single upstream frozen-fruit lot can bridge a cruise-line fleet, multiple ships, multiple voyages, and multiple service venues. It is one measured event, not a lot-size distribution or sharing probability.
- **Unmeasured:** cruise-specific lot/receipt size distributions, shelf-life by item line, fresh-vs-frozen proportions by venue, galley cross-sourcing/batch-sharing matrices, and in-transit viral load/degradation are not measured in peer-reviewed maritime literature (Consensus tranche 57 evidence matrix). Land-based lot-sizing literature is optimization/theory, not cruise field measurement.

### High-risk food classes

- **CDC Yellow Book:** contaminated ready-to-eat cold foods (salads, sandwiches) are a particular norovirus risk; raw shellfish, especially oysters, are a frequent source because filter feeders concentrate viral particles; contaminated ice has been implicated.
- **UK HPA cruise-ship norovirus guidance (2007):** person-to-person spread predominates, but food is occasionally implicated; bivalve molluscs such as mussels/oysters from sewage-polluted water are named; infected food handlers can contaminate food and surroundings.
- **Via Consensus tranche 57:** Mouchtouri et al. (2024; DOI 10.2807/1560-7917.es.2024.29.10.2300345) identified 5 foodborne outbreaks among 41 investigated cruise-ship outbreaks (1990–2020); Hardstaff/Clough review evidence summarized in the tranche names frozen produce and bivalve mollusks as primary commercial upstream vehicles and infected food handlers as the predominant vector in non-shellfish food outbreaks; Saupe et al. is cited for frozen produce ingredients being blended across dessert/beverage recipes before service, complicating venue-level attribution.
- **Inference only:** the high-risk classes remain shellfish, leafy/fresh produce, and RTE/prepared items; preparation and blending determine which venue or recipe becomes the exposure point. Venue-class menu incidence is still unmeasured.

## Model implications

- The current flat supply census is a reasonable **mean-introduction null**: it preserves the expected number of contaminated lots while ignoring correlation and venue-class incidence. It cannot represent centralized galley consolidation, shared upstream lots across venues/ships, or hull-size venue specialization.
- Rispens 2020 is direct evidence that a shared upstream lot can synchronize outbreaks across ships; a shared-lot/source-cluster mechanism is therefore plausible, but its frequency and extent beyond that event are unmeasured.
- The mega solver-screen rarity is not evidence against supply contamination generally; it says the burden-quantile seeds from the current census rarely cross the 7000-agent posting threshold. This survey does not by itself choose between lot-size scaling and upstream-source sharing.
- If a supply-structure mechanism is built, unmeasured quantities should be declared Grade C assumptions with provenance, paired-seed witnesses, and no fitting to VSP/attack-rate anchors.

## Gaps to close before mechanism constants

- Per-venue menu incidence by hull class and venue type for `shellfish`, `salad_leaf`, `fresh_produce`, and RTE lines.
- Vendor/source sharing or galley consolidation rules: which venues share suppliers, prep batches, or item lines.
- Cruise-specific lot/receipt size distributions and shelf-life by item line.
- Fresh vs frozen proportions and preparation-survival by venue/meal.
- In-transit norovirus load and degradation for frozen produce/shellfish.

## Sources

- Consensus literature survey (peer-reviewed evidence assembled): [tranche 57](../literature/consensus_tranche_57_cruise_food_supply_chain.md), [Consensus thread](https://consensus.app/search/you-are-helping-source-evidence-for-a-maritime-dis/CChFjh6GRo299Hmj2e61wg/).
- Rispens et al. 2020, MMWR: https://www.cdc.gov/mmwr/volumes/69/wr/mm6916a3.htm
- Hospitality Upgrade, “Sustaining the Voyage: Exploring the Complex World of F&B Supply Chains for Cruise Ships” (2025): https://www.hospitalityupgrade.com/magazine/spring-2025/sustaining-the-voyage-exploring-the-complex-world-of-f-b-supply-chains-for-cruise-ships
- SeaTrade Cruise Events, “Supply Chain Readiness for Cruise F&B Vendors” PDF: https://www.seatradecruiseevents.com/media/5876edd7/-e406a5da-3bfc-49f6-bed5-11eaa57d45e2-FBS26-5291-Cruise-Procurement-Guide-proof1-2f18495b1d09ab5d17feeea5306431c7.pdf
- BBC Storyworks, “Gastronomy at Sea”: https://www.bbc.com/storyworks/travel/sea-to-believe/dining-on-board-a-cruise
- UK Health Protection Agency, “Guidance for the Management of Norovirus Infection in Cruise Ships” (2007): https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/362998/2007_guideline_norovirus_cruiseships.pdf
- CDC Yellow Book, Norovirus: https://www.cdc.gov/yellow-book/hcp/travel-associated-infections-diseases/norovirus.html
- Repo context: [food_supply_01_design.md](../food_supply_01_design.md), [provisioned_source_01_design.md](../provisioned_source_01_design.md), [consensus_tranche_55_provisioned_lot_prevalence.md](../literature/consensus_tranche_55_provisioned_lot_prevalence.md)
