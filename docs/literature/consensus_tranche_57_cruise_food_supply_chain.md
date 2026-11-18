# You are helping source evidence for a maritime disease-transmission model. Do NO

**Question:** You are helping source evidence for a maritime disease-transmission model. Do NOT recommend model constants or say which value should be adopted; survey what the peer-reviewed literature actually measures or reports, and flag quantities with no measurement.

Context: we are modeling norovirus supply-chain contamination on cruise ships across hull classes (expedition ~450, classic ~1900, spirit ~3000, mega ~5000 passengers). The model currently has Dining venue service types (buffet/MDR/specialty/crew_mess) and a fixed set of food item lines (shellfish, salad_leaf, fresh_produce, garnish, deli, bakery, dairy), but no per-venue menu incidence, no vendor/source sharing, and no hull-specific supply-class structure. We need to know whether the real food supply chain diversifies by ship class and venue type in ways that affect high-risk food classes.

Please survey peer-reviewed literature (and outbreak records) for:
1. Cruise foodservice structure across ship size/class: number and type of venues, buffet vs main dining vs specialty vs crew mess, menu diversity, and whether food variety or venue specialization scales with ship size.
2. Cruise food procurement/provisioning structure: central kitchens or shipboard galleys, port provisioning vs pre-loaded frozen stores, fresh vs frozen/prepared foods, supplier concentration, whether multiple venues share suppliers or production batches, and any description of supply-chain centralization.
3. Lot/batch/receipt scale in cruise or comparable foodservice supply chains: lot sizes, order/receipt sizes, shelf life, frozen produce/shellfish/RTE batches, and evidence of one lot serving multiple venues or ships.
4. Norovirus/foodborne illness evidence on cruise ships: which food vehicles are implicated (shellfish, produce, RTE foods, buffet items), preparation/cooking survival, implicated-titre or prevalence measurements, and shared/upstream lot events such as the Rispens 2020 frozen raspberry outbreak.
5. For each item, state what was measured vs merely described, the setting (cruise ship, land-based foodservice, retail/dispatch), and the best citation(s). Explicitly list quantities that appear unmeasured in the peer-reviewed literature (for example, per-venue menu incidence by ship class, vendor sharing rates, cruise-specific lot sizes).

Return a structured survey with citations. Preserve DOI/URLs. Distinguish direct measurements from reviews/secondary reports and from industry/gov material if any appears in the literature results. Do not fit anything to VSP or attack-rate targets.

# Evidence Survey on Maritime Foodservice, Supply Logistics, and Norovirus Transmission

Empirical literature directly measures upstream viral distribution networks and general provisioning pathways, whereas specific venue allocations across hull sizes remain largely descriptive [[1.1]](https://consensus.app/papers/rispens-freeland-notes-from-the-field-multiple-cruise-ship/w:58fa135e-ef45-45cf-a2d6-8e3addb620be/) [[2.1]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/). Cruise supply architectures operate under strict storage classifications and centralized purchasing pipelines, though per-venue menu incidence across ship classes lacks measured documentation [[3.1]](https://consensus.app/papers/sun-yang-a-twostage-stochastic-optimization-model-for/w:420f752c-8604-494e-82da-ec4185927bb8/) [[2.2]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/).

## Shipboard Foodservice and Provisioning Architecture

Modern cruise ships function as large hospitality complexes requiring synchronized food supply systems [[3.2]](https://consensus.app/papers/sun-yang-a-twostage-stochastic-optimization-model-for/w:420f752c-8604-494e-82da-ec4185927bb8/) [[2.3]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/). Unlike cargo or merchant vessels carrying limited crews requiring smaller item assortments, passenger ships support large crews and thousands of travelers, driving massive procurement volumes [[4.1]](https://consensus.app/papers/stefanova-sustainable-logistics-services-of-food-provisions/w:0ce8d8e3-5325-458a-b623-d803a16caf39/) [[4.2]](https://consensus.app/papers/stefanova-sustainable-logistics-services-of-food-provisions/w:0ce8d8e3-5325-458a-b623-d803a16caf39/) [[4.3]](https://consensus.app/papers/stefanova-sustainable-logistics-services-of-food-provisions/w:0ce8d8e3-5325-458a-b623-d803a16caf39/). Initial order quantities are dictated by onboard consumption patterns and replenishment windows during short port turnarounds [[5.1]](https://consensus.app/papers/qu-wang-modelling-the-procurement-process-and-production/w:b693e9f4-797a-4a1f-b5ac-60ddfb4ff82a/) [[5.2]](https://consensus.app/papers/qu-wang-modelling-the-procurement-process-and-production/w:b693e9f4-797a-4a1f-b5ac-60ddfb4ff82a/) [[6.1]](https://consensus.app/papers/rodrigue-wang-cruise-shipping-supply-chains-and-the-impacts-of/w:c641621e-6edd-4857-89fb-4047d1fc210c/). 

Food and beverage provisioning flows through centralized global distribution hubs, regional chandlers, local port markets, or inter-vessel transfers [[2.4]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/) [[2.5]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/) [[2.6]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/) [[2.7]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/). Central global facilities primarily handle non-perishable and frozen provisions, while local chandlers manage perishable and fresh produce replenishments [[2.8]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/) [[2.2]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/) [[2.9]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/). Requisitions originating from distinct onboard galley sections are consolidated into a single corporate procurement requisition before routing to assigned suppliers [[2.1]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/) [[2.2]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/). 

**Figure 2.** Model quality by number of components. Source: Figure by author. [[4]](https://consensus.app/papers/stefanova-sustainable-logistics-services-of-food-provisions/w:0ce8d8e3-5325-458a-b623-d803a16caf39/)

*How to read: The plot displays model quality metrics across increasing numbers of components for maritime provision evaluation. The horizontal axis represents the number of components, while the vertical axis tracks relative explanatory performance.*

## Lot Sizing and Inventory Dynamics

Cold chains for perishable commodities integrate strict time-temperature preservation constraints with warehouse storage limits [[7.1]](https://consensus.app/papers/zanoni-cardini-lot-sizing-problem-for-cold-supply-chain-with/w:7fe091c1-2194-44c3-a598-7ec09355edd5/) [[7.2]](https://consensus.app/papers/zanoni-cardini-lot-sizing-problem-for-cold-supply-chain-with/w:7fe091c1-2194-44c3-a598-7ec09355edd5/). Mathematical modeling demonstrates that food provisioning requires two-stage decision structures where inventory quantities are set before sailing under fixed volumetric storage caps, followed by post-demand substitution [[3.3]](https://consensus.app/papers/sun-yang-a-twostage-stochastic-optimization-model-for/w:420f752c-8604-494e-82da-ec4185927bb8/) [[3.1]](https://consensus.app/papers/sun-yang-a-twostage-stochastic-optimization-model-for/w:420f752c-8604-494e-82da-ec4185927bb8/) [[3.4]](https://consensus.app/papers/sun-yang-a-twostage-stochastic-optimization-model-for/w:420f752c-8604-494e-82da-ec4185927bb8/). Neglecting temperature degradation and inventory holding costs produces severe suboptimal supply policies in multi-echelon systems [[7.3]](https://consensus.app/papers/zanoni-cardini-lot-sizing-problem-for-cold-supply-chain-with/w:7fe091c1-2194-44c3-a598-7ec09355edd5/) [[8.1]](https://consensus.app/papers/sebatjane-adetunji-optimal-inventory-replenishment-and-shipment/w:db8fd2e3-35c5-42ce-a860-0dc08c7e9160/) [[8.2]](https://consensus.app/papers/sebatjane-adetunji-optimal-inventory-replenishment-and-shipment/w:db8fd2e3-35c5-42ce-a860-0dc08c7e9160/). 

Lot sizing across multi-unit hospitality networks directly affects setup costs, distribution schedules, and perishable lifespan limits [[9.1]](https://consensus.app/papers/cai-zhang-cruise-ship-optimal-catering-supply-plan/w:49f8b0ce-eb90-4882-9135-633a7d0fde94/) [[10.1]](https://consensus.app/papers/alipour-jolai-general-lotsizing-and-scheduling-for-perishable/w:5c6738ea-59eb-42f0-a8ee-64aaf799948e/) [[10.2]](https://consensus.app/papers/alipour-jolai-general-lotsizing-and-scheduling-for-perishable/w:5c6738ea-59eb-42f0-a8ee-64aaf799948e/) [[11.1]](https://consensus.app/papers/patel-venkatadri-an-adaptive-sequential-decisionmaking-approach-for/w:4014cc75-6849-4f73-a402-b9be92dc8dd1/). Integrated planning combining batching with vehicle routing optimizes delivery intervals while respecting fixed product expiration thresholds [[12.1]](https://consensus.app/papers/amorim-belofilho-lot-sizing-versus-batching-in-the-production-and/w:2142e3b4-f75f-490a-b5d8-b3312aa7bd3c/) [[11.2]](https://consensus.app/papers/patel-venkatadri-an-adaptive-sequential-decisionmaking-approach-for/w:4014cc75-6849-4f73-a402-b9be92dc8dd1/) [[11.3]](https://consensus.app/papers/patel-venkatadri-an-adaptive-sequential-decisionmaking-approach-for/w:4014cc75-6849-4f73-a402-b9be92dc8dd1/). Two-stage replenishment networks that permit secondary intermediate deliveries substantially improve system profit under fluctuating operational demand [[13.1]](https://consensus.app/papers/vorkut-volynets-the-model-to-optimize-deliveries-of-perishable/w:b49437ab-162b-407a-a4dc-755a94404e38/) [[13.2]](https://consensus.app/papers/vorkut-volynets-the-model-to-optimize-deliveries-of-perishable/w:b49437ab-162b-407a-a4dc-755a94404e38/) [[13.3]](https://consensus.app/papers/vorkut-volynets-the-model-to-optimize-deliveries-of-perishable/w:b49437ab-162b-407a-a4dc-755a94404e38/).

**Figure 3.** I-BS-VRPTW and I-LS-VRPTW solutions to instance PP=1, SL=3, #=4, C-S-NTS (Seq). [[12]](https://consensus.app/papers/amorim-belofilho-lot-sizing-versus-batching-in-the-production-and/w:2142e3b4-f75f-490a-b5d8-b3312aa7bd3c/)

*How to read: The schematic illustrates routing and scheduling sequences for perishable distribution under time-window constraints. Individual nodes indicate customer drops, and connected paths illustrate vehicle routes between production facilities and delivery destinations.*

## Norovirus Vehicles and Outbreak Evidence

Norovirus is predominantly transmitted via person-to-person spread aboard passenger vessels, but common-source foodborne introductions initiate substantial outbreak events [[14.1]](https://consensus.app/papers/hardstaff-clough-foodborne-and-foodhandler-norovirus-outbreaks-a/w:ff970517-61fa-4aa9-975c-6a899c9c749f/) [[15.1]](https://consensus.app/papers/mouchtouri-simou-systematic-literature-review-and-metaanalysis-on/w:e1a33479-6974-48ca-afdf-1371d4699f78/) [[16.1]](https://consensus.app/papers/deo-thakur-norovirus-on-cruise-ships-a-recurring-sentinel/w:4385e925-0f95-445b-9cce-e4f330aaeb5b/). A systematic review spanning 1990 to 2020 identified that five of 41 investigated cruise outbreaks were confirmed foodborne incidents, while poor food handling and contaminated water historically served as primary environmental vectors [[15.2]](https://consensus.app/papers/mouchtouri-simou-systematic-literature-review-and-metaanalysis-on/w:e1a33479-6974-48ca-afdf-1371d4699f78/) [[15.3]](https://consensus.app/papers/mouchtouri-simou-systematic-literature-review-and-metaanalysis-on/w:e1a33479-6974-48ca-afdf-1371d4699f78/) [[15.4]](https://consensus.app/papers/mouchtouri-simou-systematic-literature-review-and-metaanalysis-on/w:e1a33479-6974-48ca-afdf-1371d4699f78/).

Epidemiological investigations confirm that frozen produce and bivalve mollusks serve as primary vehicles for commercial upstream contamination [[14.2]](https://consensus.app/papers/hardstaff-clough-foodborne-and-foodhandler-norovirus-outbreaks-a/w:ff970517-61fa-4aa9-975c-6a899c9c749f/) [[14.3]](https://consensus.app/papers/hardstaff-clough-foodborne-and-foodhandler-norovirus-outbreaks-a/w:ff970517-61fa-4aa9-975c-6a899c9c749f/) [[17.1]](https://consensus.app/papers/saupe-rounds-outbreak-of-norovirus-gastroenteritis-associated/w:d9f42611-30e0-4b13-8d15-764e6fbaec3c/):
* **Frozen berry lots** contaminated at origin were distributed to an entire cruise line fleet, causing synchronous outbreaks across separate vessels (85 cases on Ship B, 83 on Ship A) linked to a single 22,000-pound commercial consignment [[1.1]](https://consensus.app/papers/rispens-freeland-notes-from-the-field-multiple-cruise-ship/w:58fa135e-ef45-45cf-a2d6-8e3addb620be/) [[1.2]](https://consensus.app/papers/rispens-freeland-notes-from-the-field-multiple-cruise-ship/w:58fa135e-ef45-45cf-a2d6-8e3addb620be/) [[1.3]](https://consensus.app/papers/rispens-freeland-notes-from-the-field-multiple-cruise-ship/w:58fa135e-ef45-45cf-a2d6-8e3addb620be/) [[1.4]](https://consensus.app/papers/rispens-freeland-notes-from-the-field-multiple-cruise-ship/w:58fa135e-ef45-45cf-a2d6-8e3addb620be/).
* **Infected food handlers** represent the predominant vector in non-shellfish food outbreaks, contributing to over 75% of investigated berry-associated contamination events in commercial catering settings [[14.4]](https://consensus.app/papers/hardstaff-clough-foodborne-and-foodhandler-norovirus-outbreaks-a/w:ff970517-61fa-4aa9-975c-6a899c9c749f/) [[18.1]](https://consensus.app/papers/bozkurt-phanthien-outbreaks-occurrence-and-control-of-norovirus-and/w:7855269b-21c9-4a60-ad0f-db8caf0f502f/) [[18.2]](https://consensus.app/papers/bozkurt-phanthien-outbreaks-occurrence-and-control-of-norovirus-and/w:7855269b-21c9-4a60-ad0f-db8caf0f502f/).
* **Commercial distribution vehicles** often evade standard venue inspections because frozen produce ingredients are blended across complex dessert or beverage recipes before service [[17.2]](https://consensus.app/papers/saupe-rounds-outbreak-of-norovirus-gastroenteritis-associated/w:d9f42611-30e0-4b13-8d15-764e6fbaec3c/) [[17.3]](https://consensus.app/papers/saupe-rounds-outbreak-of-norovirus-gastroenteritis-associated/w:d9f42611-30e0-4b13-8d15-764e6fbaec3c/) [[17.4]](https://consensus.app/papers/saupe-rounds-outbreak-of-norovirus-gastroenteritis-associated/w:d9f42611-30e0-4b13-8d15-764e6fbaec3c/).

## Evidence Matrix and Empirical Data Gaps

| Supply Chain and Transmission Dimension | Empirical Status in Literature | Setting Evaluated | Key Citations and DOIs |
| :--- | :--- | :--- | :--- |
| **Fleetwide Receipt & Upstream Batches** | Measured single 22,000-lb frozen lot distributed across entire cruise line fleet [[1.3]](https://consensus.app/papers/rispens-freeland-notes-from-the-field-multiple-cruise-ship/w:58fa135e-ef45-45cf-a2d6-8e3addb620be/) [[1.4]](https://consensus.app/papers/rispens-freeland-notes-from-the-field-multiple-cruise-ship/w:58fa135e-ef45-45cf-a2d6-8e3addb620be/) | Cruise line fleetwide distribution | Rispens et al. (2020), DOI: 10.15585/mmwr.mm6916a3 |
| **Supply Routing Pathways** | Described 4-tier routing: global hubs, regional chandlers, local ports, vessel transfers [[2.4]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/) [[2.5]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/) | Mediterranean cruise port hub | Ghiara et al. (2026), DOI: 10.1186/s12544-026-00813-5 |
| **Consolidated Vessel Ordering** | Described consolidation of individual galley orders into unified corporate purchasing [[2.1]](https://consensus.app/papers/ghiara-messinese-supply-chain-in-the-cruise-industry-suppliers/w:72a0e5b7-ceab-49cb-806b-12d47a5d682f/) | Cruise corporate purchasing | Ghiara et al. (2026), DOI: 10.1186/s12544-026-00813-5 |
| **Foodborne vs Contact Transmission** | Measured 5 foodborne outbreaks out of 41 total cruise ship events (1990–2020) [[15.3]](https://consensus.app/papers/mouchtouri-simou-systematic-literature-review-and-metaanalysis-on/w:e1a33479-6974-48ca-afdf-1371d4699f78/) | International cruise ships | Mouchtouri et al. (2024), DOI: 10.2807/1560-7917.es.2024.29.10.2300345 |
| **Cold Storage Optimization** | Modeled volumetric constraints, product degradation, and two-stage substitution [[3.1]](https://consensus.app/papers/sun-yang-a-twostage-stochastic-optimization-model-for/w:420f752c-8604-494e-82da-ec4185927bb8/) [[3.4]](https://consensus.app/papers/sun-yang-a-twostage-stochastic-optimization-model-for/w:420f752c-8604-494e-82da-ec4185927bb8/) [[7.3]](https://consensus.app/papers/zanoni-cardini-lot-sizing-problem-for-cold-supply-chain-with/w:7fe091c1-2194-44c3-a598-7ec09355edd5/) | Theoretical optimization / simulated supply | Sun et al. (2025), DOI: 10.3390/math13233806; Zanoni et al. (2026), DOI: 10.3390/en19051360 |

Several model parameters remain completely unmeasured in peer-reviewed maritime literature:
* **Per-venue menu incidence across ship classes**: Quantitative allocation of specific high-risk ingredient lines (e.g., shellfish, leafy greens, berries) disaggregated by venue type (buffet vs. main dining vs. specialty vs. crew mess) across defined hull classes (expedition, classic, spirit, mega) does not appear in peer-reviewed studies.
* **Galley cross-sourcing and batch sharing**: Empirical sharing matrices detailing whether specialty dining galleys draw from isolated supplier consignments or share prepared prep batches with main galleys are unmeasured.
* **In-transit pathogen load**: Viral load distribution, degradation kinetics across frozen maritime transit, and initial plating titres aboard passenger vessels remain undocumented in maritime field samples [[16.2]](https://consensus.app/papers/deo-thakur-norovirus-on-cruise-ships-a-recurring-sentinel/w:4385e925-0f95-445b-9cce-e4f330aaeb5b/) [[16.3]](https://consensus.app/papers/deo-thakur-norovirus-on-cruise-ships-a-recurring-sentinel/w:4385e925-0f95-445b-9cce-e4f330aaeb5b/).
 
_These search results were found and analyzed using Consensus, an AI-powered search engine for research. Try it at https://consensus.app. © 2026 Consensus NLP, Inc. Personal, non-commercial use only; redistribution requires copyright holders’ consent._
 
## References
 
`1.` Rispens JR, Freeland AL, Wittry BC, et al. Notes from the Field: Multiple Cruise Ship Outbreaks of Norovirus Associated with Frozen Fruits and Berries — United States, 2019. *MMWR Morbidity and Mortality Weekly Report.* 2020;69:501-502. doi:10.15585/mmwr.mm6916a3
 
> [1.1] The first outbreak occurred on another ship (ship B) of cruise line X sailing to and from New York City along the eastern seaboard and affected 85 (3.9%) of 2,166 passengers and 10 (1.6%) of 612 crew members; the second outbreak occurred on ship A sailing from Montreal to New York City and affected 83 (3.7%) of 2,251 passengers and 10 (1.6%) of 610 crew members. (Body)
 
> [1.2] Food item lot numbers from ship B matched those from the same frozen fruit and berry items on ship A. (Body)
 
> [1.3] After removal of the fruit items, no further outbreaks were reported on cruise line X. Upon further review of food provisioning, cruise line X determined that its food vendor had purchased several containers (nearly 22,000 pounds) of frozen raspberries of the same lot from a supplier in China beginning the end of June 2019. (Body)
 
> [1.4] These raspberries had been supplied to the entire fleet of cruise line X. Both the epidemiologic and laboratory data implicated the raspberries as the cause of the outbreaks. (Body)
 
`2.` Ghiara H, Messinese S, Musso E. Supply chain in the cruise industry: Suppliers' localization, territorial organization, and local impacts—Insights from the Genoa case study. *European Transport Research Review.* 2026;18. doi:10.1186/s12544-026-00813-5
 
> [2.1] At the outset, the manager of the "food and beverage" unit green-lights requisitions from various onboard teams, consolidating them into a singular request for the corporate buying department. (Body)
 
> [2.2] Upon receipt, this department categorizes the order into three segments, based on factors like product availability, procurement costs, current warehouse stock levels, item type, and spoilage risks: assignments are then made to the global distribution center, regional, or local ship suppliers accordingly. (Body)
 
> [2.3] Furthermore, the operational nature of cruise ships-mobile hospitality platforms serving thousands of passengers and crew-intensifies coordination challenges, requiring reliable and timely supply deliveries at each port of call [25]. (Body)
 
> [2.4] In the realm of cruise ship provisioning, especially within the Food and Beverage category, the journey of supplies to their final port of call involves navigating through one of four distinct supply chain pathways. (Body)
 
> [2.5] These are: (Body)
 
> [2.6] 1. A centralized global hub; (Body)
 
> [2.7] 4. Alternative sourcing from other cruise vessels. (Body)
 
> [2.8] Predominantly, the Global Distribution Center serves as the primary repository for storing durable goods (such as dry and frozen items), with the choice of facility location typically influenced by the cruise company's main office. (Body)
 
> [2.9] An interesting example provided by the in-depth analysis is that of a company where the Fresh and Food supply has been the origin of an important evolution towards specialized Fresh and Food export activity. (Body)
 
`3.` Sun W, Yang Y, Wang S. A Two-Stage Stochastic Optimization Model for Cruise Ship Food Provisioning with Substitution. *Mathematics.* 2025;13:3806-3806. doi:10.3390/math13233806
 
> [3.1] The first-stage decisions involve procurement quantities made before the voyage under demand uncertainty, subject to the volumetric constraints of different storage types. (Abstract)
 
> [3.2] The global cruise industry has demonstrated remarkable growth, with modern ships functioning as large-scale floating resorts. (Abstract)
 
> [3.3] To address these challenges, this paper develops a two-stage stochastic optimization model for cruise ship food provisioning. (Abstract)
 
> [3.4] The second-stage decisions determine the optimal substitution plan after the actual demand is realized, mitigating shortages by utilizing alternative available items. (Abstract)
 
`4.` Stefanova M. Sustainable Logistics Services of Food Provisions on Merchant Ships. *MDPI eBooks.* 2025. doi:10.3390/books978-3-7258-3269-9
 
> [4.1] The food supply chain for merchant ships typically requires a wide variety of products in small quantities due to low crew numbers, which should be stored on board in limited space, from fresh fruits and vegetables to frozen foods and spices (Lau and Yip 2017; Mercier et al. 2019; Lao et al. 2012). (Body)
 
> [4.2] The difference in crew size between merchant ships and cruise ships is also one important factor affecting the food supply chain (Di Vaio et al. 2021). (Body)
 
> [4.3] Merchant ships typically have a much smaller crew compared to cruise ships, which have a significant number of passengers in addition to a large number of employees (Hein et al. 2024). (Body)
 
`5.` Qu C, Wang GW, Zeng Q. Modelling the procurement process and production disruption of a multilayer cruise supply chain. *Maritime Policy & Management.* 2019;47:435-455. doi:10.1080/03088839.2019.1691277
 
> [5.1] Due to the short resupply window for the cruise ship and possible conflicts of self-interests with suppliers, it is crucial for cruise lines to establish the long-term reliable relationships with service providers. (Abstract)
 
> [5.2] Results show that initial order quantity of onboard supplies only depends on the reliability of high-flexible suppliers and onboard consumption patterns. (Abstract)
 
`6.` Rodrigue J, Wang GW. Cruise shipping supply chains and the impacts of disruptions: The case of the Caribbean. *Research in Transportation Business & Management.* 2020;45:100551-100551. doi:10.1016/j.rtbm.2020.100551
 
> [6.1] Since cruise ships are floating resorts that must be resupplied during their short port rotations, they require customized procurement practices. (Abstract)
 
`7.` Zanoni S, Cardini S, Marchi B, Zavanella LE. Lot Sizing Problem for Cold Supply Chain with Energy and Quality Considerations. *Energies.* 2026;19:1360-1360. doi:10.3390/en19051360
 
> [7.1] This paper develops a joint economic lot-sizing model for a two-echelon cold supply chain that explicitly integrates time–temperature-dependent quality degradation with energy consumption in refrigerated warehouses. (Abstract)
 
> [7.2] Unlike traditional approaches, energy is modeled as an endogenous function of warehouse filling level and warehouse temperature, allowing the interaction between inventory volume, energy efficiency, and quality preservation to be captured. (Abstract)
 
> [7.3] Numerical results for chilled and frozen products show that neglecting energy and quality costs can lead to sub-optimal policies with total cost penalties exceeding 300% compared to the proposed integrated optimization. (Abstract)
 
`8.` Sebatjane M, Adetunji O. Optimal inventory replenishment and shipment policies in a three-echelon supply chain for growing items with expiration dates. *OPSEARCH.* 2022;59:809-838. doi:10.1007/s12597-022-00572-6
 
> [8.1] Consequently, this study develops a model for managing inventory in a three-echelon supply chain for growing items with distinct farming, processing and retail operations. (Abstract)
 
> [8.2] The proposed supply chain system is modelled as a cost minimisation problem. (Abstract)
 
`9.` Cai C, Zhang L, Gan L, Shu Y, Zhang D. Cruise ship optimal catering supply plan. *International Conference on Algorithms, Microchips, and Network Applications (AMNA).* 2022;12176:75-75. doi:10.1117/12.2636513
 
> [9.1] The key to cruise catering supply lies in the balance between catering procurement and sales, and the difficulty lies in scientifically grasping many productions, procurement, and sales. (Abstract)
 
`10.` Alipour Z, Jolai F, Monabbati SE, Zaerpour N. General lot-sizing and scheduling for perishable food products. *RAIRO - Operations Research.* 2019;54:913-931. doi:10.1051/ro/2019021
 
> [10.1] The lifespan and shelf life are two important key features of perishable products that are considered in the problem. (Abstract)
 
> [10.2] The objective function is sum of production costs, inventory holding costs, waste costs, and lifespan related cost function. (Abstract)
 
`11.` Patel M, Venkatadri U, Diallo C, Habib A, Malekahmadi A. An Adaptive Sequential Decision-Making Approach for Perishable Food Procurement, Storage and Distribution Using Hyperconnected Logistics. *Sustainability.* 2023;16:98-98. doi:10.3390/su16010098
 
> [11.1] We present an adaptive sequential optimization decision-making approach for procurement, storage, and distribution of perishable food products to multi-unit restaurants at the regional level. (Abstract)
 
> [11.2] The research aims to enhance costvefficiency across the network by devising optimal routes, managing loads, and planning distribution schedules for perishable item deliveries. (Abstract)
 
> [11.3] Finally, an integrated model is developed to optimally combine procurement and distribution options generated by the first two models to minimize costs while respecting total shelf-life constraints. (Abstract)
 
`12.` Amorim P, Belo-Filho M, Toledo FMB, Almeder C, Almada‐Lobo B. Lot sizing versus batching in the production and distribution planning of perishable goods. *International Journal of Production Economics.* 2013;146:208-218. doi:10.1016/j.ijpe.2013.07.001
 
> [12.1] The main contribution of this paper is to extend this approach and prove the importance of lot sizing for make-to-order systems when perishability is explicitly considered. (Abstract)
 
`13.` Vorkut T, Volynets L, Bilonog OY, Sopotsko YO, Левченко Я. The model to optimize deliveries of perishable food products in supply chains. *Eastern-European Journal of Enterprise Technologies.* 2019;5:43-50. doi:10.15587/1729-4061.2019.177903
 
> [13.1] The demand for PFPs is effectively satisfied by introducing into supply chain systems a possibility for additional delivery of PFPs in case of their deficit in the period between planned deliveries. (Abstract)
 
> [13.2] It has been proven that the optimum size of basic delivery that corresponds to the maximum profit of a PFP supply chain system is affected by the following:– the magnitude of profit from the sale of a single PFP unit earned from basic and additional delivery;– the magnitude of loss incurred due to excess PFP units; – the parameters of demand distribution between the periods of planned deliveries; – technical-operational and economic indicators that characterize the operation of automobiles along multi-drop routes.We have performed a comparative analysis of conditions for ensuring PFP deliveries in supply chain systems using the known and proposed improved variant of the probabilistic-statistical analytical model of PFP deliveries optimization. (Abstract)
 
> [13.3] This analysis has revealed that the two-stage supply system, that is the one that implies additional delivery, is more economical-reasonable in terms of conditions for the operation of PFP supply chains. (Abstract)
 
`14.` Hardstaff JL, Clough HE, Lutje V, et al. Foodborne and Food-Handler Norovirus Outbreaks: A Systematic Review. *Foodborne Pathogens and Disease.* 2018;15:589-597. doi:10.1089/fpd.2018.2452
 
> [14.1] Transmission is most often mediated from person to person. (Abstract)
 
> [14.2] Of all food types, shellfish were implicated in the greatest number of definite foodborne outbreaks. (Abstract)
 
> [14.3] Second, seafood may additionally dominate food sources in our review because of the availability of oysters for testing from batches implicated in outbreaks. (Body)
 
> [14.4] Food handlers contributed to definite foodhandler outbreaks involving a diverse range of foodstuffs and in a wide variety of settings, including weddings and military establishments. (Abstract)
 
`15.` Mouchtouri VΑ, Simou E, Soteriades S, et al. Systematic literature review and meta-analysis on preventing and controlling norovirus outbreaks on cruise ships, 1990 to 2020: calling for behaviour change strategies of travellers. *Eurosurveillance.* 2024;29. doi:10.2807/1560-7917.es.2024.29.10.2300345
 
> [15.1] Our systematic literature review demonstrated that in the vast majority of included norovirus outbreaks, the mode of transmission was person-to-person, either as a single mode or in combination with other transmission modes including food-borne, waterborne and/or environment. (Body)
 
> [15.2] These include common exposure at a certain location onboard the ship, consumption of food, consumption of food and common exposure at a ship place, consumption of water, having an ill cabinmate, ill traveller before embarkation, poor hygiene (such as inappropriate food handling, hygiene and storage, no detectable free chlorine in potable water) and travelling with a group before embarkation. (Body)
 
> [15.3] Similarly, only a small proportion of the outbreaks reviewed were food-borne outbreaks (five of 41). (Body)
 
> [15.4] Waterborne or food-borne norovirus outbreaks as a result of poor hygiene practices on board have not been published since 2002 (with the exception of two food-borne outbreaks in 2014 and 2017 on river cruises in China); this is probably due to high food and water hygiene standards maintained on cruise ships. (Body)
 
`16.` Deo AP, Thakur N, Mohi GK. Norovirus on Cruise Ships: A Recurring Sentinel Event. *Cureus.* 2026;18:e114832-e114832. doi:10.7759/cureus.114832
 
> [16.1] Norovirus remains the leading cause of acute gastroenteritis outbreaks worldwide and is particularly well adapted for transmission aboard cruise ships due to its low infectious dose, prolonged environmental persistence, and rapid person-to-person spread. (Abstract)
 
> [16.2] Current surveillance relies predominantly on symptomatic case reporting, limiting the ability to distinguish between single-source introduction, environmental persistence, foodborne transmission, and emergence of novel recombinant strains. (Abstract)
 
> [16.3] Recent modelling studies have shown that early diagnosis and isolation of symptomatic individuals substantially reduce secondary transmission, yet routine genomic surveillance is rarely implemented onboard. (Abstract)
 
`17.` Saupe AA, Rounds JM, Sorenson A, et al. Outbreak of Norovirus Gastroenteritis Associated With Ice Cream Contaminated by Frozen Raspberries From China—Minnesota, United States, 2016. *Clinical Infectious Diseases.* 2020;73:e3701-e3707. doi:10.1093/cid/ciaa821
 
> [17.1] DOI: 10.1093/cid/ciaa821 Commercially distributed food vehicles (ie, those that are contaminated before reaching the point of service), are rarely reported for norovirus outbreaks, and most are due to oysters [6-9]. (Body)
 
> [17.2] In addition, produce (including frozen berries) may often be used as an ingredient in other dishes, which makes them difficult to identify as the vehicle in an outbreak. (Body)
 
> [17.3] Raspberry chocolate chip ice cream was statistically associated with illness in 2 analytic studies (6 of 7 cases vs 0 of 7 controls; odds ratio, undefined; P = .005). (Body)
 
> [17.4] Kawasaki) strains from case stool specimens matched norovirus found in frozen raspberries imported from China that were used to make the implicated ice cream. (Body)
 
`18.` Bozkurt H, Phan-Thien K, Van Ogtrop F, Bell TL, McConchie R. Outbreaks, occurrence, and control of norovirus and hepatitis a virus contamination in berries: A review. *Critical Reviews in Food Science and Nutrition.* 2020;61:116-138. doi:10.1080/10408398.2020.1719383
 
> [18.1] Food handlers were implicated as the source in the majority of outbreaks (Tables 1 and 2). (Body)
 
> [18.2] Food handlers (75%) continued to be the primary source of contamination, followed by contaminated water (12.5%), and fruit pickers (12.5%). (Body)
