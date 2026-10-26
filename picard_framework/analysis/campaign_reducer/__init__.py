"""Analysis-only reduction of existing campaign artifacts.

Status: D0 landed — the canonical contract files are adopted and the
strictly-offline ``plan`` and ``validate`` operations are implemented; the
other nine registered operations return NOT_YET_IMPLEMENTED until their
phased tickets land. D1 adds the library layer: pinned bounded object
readers (``pinned_reader``), ranged ZIP/ZIP64 member access
(``zip_members``), attempt/run identity (``identity``), pre-materialization
row payloads (``payloads``), NA-semantic readout helpers
(``readout_helpers``) and the family adapter registry (``adapters``).

D2 adds the materialization layer: the shared reservation/budget ledger
(``ledger``), create-only derived outputs (``derived_store``), contract
row emitters (``rows``, ``long_tables``), streaming shard materialization
with checkpoints and the COMMIT catalog (``materialize``, ``catalog``),
the bounded query engine (``query_engine``) and the offline worker
transport shim (``worker``).

The authoritative specification is ``docs/campaign_reduction/SURVEY_AND_DEVIN_SPEC.md``;
the machine contracts under ``contracts/`` are the single schema authority
(34-table field contracts, canonical CLI, request/query/bootstrap schemas,
status namespaces, cold-scope register). Implementation lands in phased tickets
D0–D8 (``docs/campaign_reduction/PHASED_TICKETS.json``) via the public CLI
``python3 scripts/campaign analysis <operation>`` and the internal module worker
``picard_framework.analysis.campaign_reducer.worker`` — never a new
``deploy/aws/`` entrypoint, Dockerfile, jobdef or submit script.
"""
