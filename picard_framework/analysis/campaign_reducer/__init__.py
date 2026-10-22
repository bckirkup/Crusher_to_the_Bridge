"""Analysis-only reduction of existing campaign artifacts.

Status: SKELETON — canonical contract files only, no implementation.

The authoritative specification is ``docs/campaign_reduction/SURVEY_AND_DEVIN_SPEC.md``;
the machine contracts under ``contracts/`` are the single schema authority
(34-table field contracts, canonical CLI, request/query/bootstrap schemas,
status namespaces, cold-scope register). Implementation lands in phased tickets
D0–D8 (``docs/campaign_reduction/PHASED_TICKETS.json``) via the public CLI
``python3 scripts/campaign analysis <operation>`` and the internal module worker
``picard_framework.analysis.campaign_reducer.worker`` — never a new
``deploy/aws/`` entrypoint, Dockerfile, jobdef or submit script.
"""
