# CTB paper-program dependency view

This is a readiness dependency view, **not** a recommendation to force a single publication order.

## Shared platform gate (all papers)

Before any quotable campaign: immutable attempts; source/config/input/environment/seed fingerprint; stale-cache rejection; campaign identity and intent; parent-child revision lineage; figure/table input hashes. This is the dominant common dependency and should be implemented once rather than separately in eight paper branches.

## Scientific foundation gate

The validation/calibration line (M01) should establish which core mechanisms and outputs are claim-grade. It need not be published before every methods paper, but downstream confirmatory claims must cite a frozen, validated core version. Time/units defects and parameter provenance are upstream of calibration.

## Parallelizable domain lanes after the shared gate

- **M02 diagnostics** and **M05 medical response** share runtime-schema/effective-config defects; fix them together at the observation/decision boundary, then separate estimands.
- **M04 wastewater** and **M07 fleet-to-port inference** share Sentinel Stan contracts, diagnostic gating, and analysis-artifact schema needs; validate these as one inference substrate before diverging into surveillance versus public-health claims.
- **M03 wearables** can progress independently after a complete wearable parameter/provenance inventory and the shared campaign gate.
- **M06 HVAC** can progress with native-engine development, but any ContamX equivalence claim remains a separate licensed human-operated gate.
- **M08 variant early warning** remains downstream of the phylodynamics/c1 chain and cannot inherit validity merely from surveillance detection performance.

## Iteration model

Each lane should be a directed acyclic graph of campaign records, not “one campaign per paper”:

`exploratory → frozen estimand/design → confirmatory → manuscript_vN → review_response → revision campaign(s)`

Every child records its parent, reason for change, analysis-plan version, and which prior claims/figures it supersedes. Negative and abandoned campaigns remain immutable nodes rather than being overwritten.
