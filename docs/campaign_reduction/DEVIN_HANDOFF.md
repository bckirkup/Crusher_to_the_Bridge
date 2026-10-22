# Devin handoff — CREATE **and EXECUTE** the existing-campaign AWS reducer

**NOT YET IMPLEMENTED / NOT AN AWS EXECUTION APPROVAL.** Survey SHA `496a919ca3af4563da34b958db37e737b58bab4b`. I own scientific analysis/interpretation (Kosmos); Devin owns implementation, authorized AWS execution and operational repairs. PI approves scope, budgets and exceptional permissions, not routine file transfers. No new simulation is needed to reduce existing artifacts.

## Copyable instruction

> Implement and execute the single analysis-only interface specified in [SURVEY_AND_DEVIN_SPEC.md](SURVEY_AND_DEVIN_SPEC.md), [CANONICAL_INTERFACE.json](CANONICAL_INTERFACE.json), [FIELD_CONTRACTS.json](FIELD_CONTRACTS.json) and [PHASED_TICKETS.json](PHASED_TICKETS.json). Preserve every available native run scalar and saved timing/mechanism/role joint, not only means/quantiles. Scope is **all 197 dated historical prefixes + 21 current registrations (218 typed records / 198 prefix names), plus fresh root/prefix discoveries**, not only PS01 or norovirus. Build/test offline, prove automatic durable return, execute a bounded existing-data pilot (PS01 all four hulls first), obtain measured quote/admission, then stage AWS-native Parquet/catalog materialization across the entire catalog and return bounded exact joint query pages automatically into durable Edison assets with qualified acknowledgments. Do not stop at a PR. Do not run simulations, Stan fits, raw bulk downloads, or unadmitted paid/cloud actions. Report specific blocks and unavailable fields, never fabricate a complete distribution.

## Required tickets — acceptance order D0 → D8

| Ticket / owner | Implement or execute | Acceptance evidence / next gate |
|---|---|---|
| **D0** Devin; Kosmos schema review | MODIFY `scripts/campaign` with **proposed** `analysis` subcommand; CREATE shared `picard_framework/analysis/campaign_reducer/`; adopt canonical scope, schemas and scientific definitions. Plan/validate strictly offline. | Zero network/model/fit/submit from dry paths; all197/21/198 scopes reconcile; null/unknown budgets and prices block; 26 original scientific tables/382 fields/33 metrics retained + 8 control tables/123 fields. No separate CLI. |
| **D1** Devin | Extend/reuse existing range reader, fused member grouper and saved scans through typed schema adapters. Preserve raw scalar lexical values and parentage. | Source pin on every GET/range; ZIP64/comments/CRC/size limits; no first-member-only or seed-only dedup; old source's 16 probes become explicit regressions; missing/corrupt/lean/unresolved are typed. |
| **D2** Devin; Kosmos metric acceptance | Streaming Parquet, run/member/attempt-aware selection, coverage/capability/errors/lineage, COMMIT catalog, exact joint queries and checkpoints. | Exact scalar rows and independent fixture totals/joints; right/left/interval censoring, role-at-event and denominator guards; kill/resume deterministic; concurrency/retry costs charged; no join explosion or reconstructed marginal joint. |
| **D3** Authorized deployer/Devin; PI budget/access | MODIFY existing `deploy/aws/Dockerfile.analysis`, shared launcher job binding, collector and reviewed role/workflow wiring; verify live queue/image/role/dependencies. | Existing image omits `tools/`; smoke-test actual digest-pinned image/module argv/import. No new legacy entrypoint/Dockerfile/jobdef/submit file. Narrow read-original/write-own-derived roles; no source mutation or simulation authority. |
| **D4** Devin AWS/GitHub + Kosmos Edison | Run admitted synthetic reduce/return success, failure and ≥2 query pages; implement persistent callback **or** durable bounded polling+resume. | GitHub receipt → bounded collector → durable Edison asset/index → attempt/query/page/hash acknowledgment **without human file relay**. Interrupt/expiry/403/hash failure tests recover or explicitly block. Narrow selected-manifest access is not this gate. |
| **D5** Devin execute; Kosmos scope | Fresh admitted metadata inventory across authorized roots including beyond `campaign/`; all197 cold prefixes, registered mega absent Oct19, new/unregistered prefixes; derived excluded. | Frozen exact-key/size/ETag/version/storage-class manifests and listing window; explicit continuation/access gaps/deltas. Physical object/member/design-cell/run units distinct. No 2026-10-19 count presented as current. |
| **D6** Devin execute; Kosmos selects scientific coverage; budget owner admits | Bounded existing-object pilot, adaptive by schema/risk/size/observability. Prioritize PS01 **all four hulls** and include regular summary, lean/full census, embedded TS, nested/fused legacy, clinical non-AGE and unsupported/missing witness, expanding as needed. Reuse scan rows when equivalent. | Per-class measured compressed/decoded/API/memory/time/output costs; actual role, clock, event observability; independent small archived golden comparison; exact PS01 D1–D4 reconciliation and analysis-image unknowns retained. Fresh quote with real prices, explicit finite limits, deadline and approval. No arbitrary 'six archives' rule. |
| **D7** Devin execute; Kosmos coverage review | Execute admitted phased materialization across all discovered supported families, resume from immutable checkpoints, publish catalog only after reconciliation. | All physical inputs and logical runs accounted, unsupported/unavailable metrics explicit; all available scalar rows queryable, selected saved detailed tables retained S3-side. No unqualified all-metrics/all-family success on partial scope. |
| **D8** Kosmos analysis; Devin repairs/execution | Return exact scalar, joint role/mechanism/timing, censored risk and hierarchical/paired uncertainty analysis pages; validate source→member→adapter→metric→query/figure lineage. | Durable qualified acknowledgments and reproducible catalog/query IDs; ≥2 pages equal exhaustive independent fixture; across-campaign access, not just PS01. Four separate validity axes/claim quarantine remain; no three-hull first paper. |

Full actions, dependencies and production fixture IDs are in [PHASED_TICKETS.json](PHASED_TICKETS.json). **FUTURE-T1** is a separate *future producer-telemetry* ticket only; it is **not** a prerequisite to reducing old rows, and authorizes neither reruns nor new campaigns.

## Canonical proposed commands — **ALL NOT YET IMPLEMENTED**

```text
# Offline design only; invalid placeholders never authorize a launch.
python3 scripts/campaign analysis plan --request BLOCKED_REQUEST.template.json --out PLAN_DIR
python3 scripts/campaign analysis validate --request FILLED_REQUEST.json --request-kind execution --out CHECK_DIR
# Metadata/return and paid Batch reservations are separate machine gates under the approved envelope; not fresh PI approvals.
python3 scripts/campaign analysis preflight --request APPROVED_BOOTSTRAP.json --out PRECHECK_DIR
python3 scripts/campaign analysis inventory --request APPROVED_BOOTSTRAP.json --out INVENTORY_DIR
# The following require a real image/job/resource binding, quote and finite phase admission.
python3 scripts/campaign analysis submit --phase pilot --request APPROVED_PILOT.json --out PILOT_RECEIPT_DIR
python3 scripts/campaign analysis quote --request NEXT_PHASE_REQUEST.json --evidence PILOT_EVIDENCE.json --out QUOTE_DIR
python3 scripts/campaign analysis submit --phase materialize --request APPROVED_MATERIALIZE.json --out RUN_RECEIPT_DIR
python3 scripts/campaign analysis status --request APPROVED_CONTROL.json --attempt-id REDUCTION_ID --out STATUS_DIR
python3 scripts/campaign analysis resume --request APPROVED_RESUME.json --checkpoint CHECKPOINT_URI --out RESUME_RECEIPT_DIR
python3 scripts/campaign analysis submit --phase finalize --request APPROVED_FINALIZE.json --out CATALOG_DIR
python3 scripts/campaign analysis query --request APPROVED_QUERY.json --query JOINT_QUERY.json --out QUERY_RECEIPT_DIR
python3 scripts/campaign analysis collect --request APPROVED_RETURN.json --receipt RECEIPT_URI --out VERIFIED_PAGES_DIR
python3 scripts/campaign analysis acknowledge --request APPROVED_RETURN.json --ack DURABLE_INGEST_ACK.json --out ACK_DIR
```

Internal Batch transport uses the same package's `-m picard_framework.analysis.campaign_reducer.worker` as literal argv under **EXISTING** `ENTRYPOINT ["python3"]`; not a new public campaign interface. Original proposals and their replacement names are in [ALIAS_AND_AUTHORITY_MAP.json](ALIAS_AND_AUTHORITY_MAP.json). Do not create `scripts/campaign-reduce`, a new bespoke `deploy/aws/*_entrypoint.py`, Dockerfile, jobdef JSON or submit script. Preserve active legacy argv files.

## Scientific stop rules and returned completion package

- Preserve exact metric numerator/denominator, unit/window/clock, population/role and actual source/engine/image; native AR is never automatically multiplied by PR1081 external AGE etiologic fractions. Voyage means ≠ pooled-person risks. Dominant route/channel attribution ≠ causal intervention effect.
- Frozen PS01 D2 relative and operational absolute are separate; frozen D3 is **BLOCKED_DEFINITION** until PI freezes numerator/denominator. Recover mega D4 only from saved telemetry/original scan; do not manufacture onset from acquisition or symptom-duration counts. Document 46,000 main ledger cells at original production image, keep canaries separate and unknown historic scanner image/SHA unknown.
- Missing exact onsets, complete rosters or event IDs cannot be repaired by combining marginals. Record specific `not_saved/counted_not_retained/unsupported/corrupt/blocked` states while reducing all recoverable existing rows. No automatic rerun.
- Unavailable live role/queue/price/credentials/integration, unknown or expired admission, any budget limit or mutable source stops nonzero with receipt/checkpoint/owner. `None` is never unlimited. No routine human ZIP/CSV relay.
- Return implementation/image/adapter hashes, actual AWS binding, approved quote, frozen inventory and delta, measured pilot, per-attempt/job/checkpoint/budget/coverage receipts, COMMIT catalog+Parquet partition hash manifest, full per-run scalar access, query/figure input lineage and **durable Edison project asset acknowledgments**. A source PR or transient GitHub artifact alone is not completion.

[ACCEPTANCE_MATRIX.json](ACCEPTANCE_MATRIX.json) lists **26 scientific + 10 operational proposed production tests**, all unrun; 41 reference arithmetic tests,135 contract checks and16 source-edge probes are prior offline evidence only. [VALIDATION.json](VALIDATION.json) validates this specification package, not production readiness.

### Discretionary decisions
- I use one shared launcher and canonical table dictionary to resolve the competing lane proposals and comply with source policy.
- I require complete exact run rows but conditional saved-detail tables, so future Kosmos questions remain possible without routine raw transfers.
- I separate bounded bootstrap and paid admissions, and require automatic durable readback before catalog-scale work, to prevent an unquoted launch or unusable output.

## Final QA clarifications

- Retain existing `scripts/campaign run/submit` campaign semantics and `readout` analysis/reuse semantics; reuse readout functions, but the new analysis namespace must not call a simulation launcher.
- [Status namespaces](STATUS_NAMESPACES.json) are table/field-specific. Read failure reasons are not metric-value, asset-read or capability literals; preserve precise failures in `data_gaps.detail`. Historical stopped states do not mean lost data; unknown does not mean completed.
- Automatically reserve admissions within the approved scope/budget envelope for routine queries, pages, resumes, phases and campaigns. Escalate only new scope, budget-envelope exceptions or credentials/permissions. No new manual PI token per in-envelope operation.
- This completed survey/specification is not implementation or production acceptance. Devin implements and subsequently executes approved AWS reductions; no AWS execution occurs in this QA.
