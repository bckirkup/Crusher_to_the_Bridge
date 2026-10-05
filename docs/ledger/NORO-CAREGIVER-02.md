# NORO-CAREGIVER-02
**Date:** 2026-10-03
**Commit:** #856
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** a78c942e

## Defect

The discovery half of NORO-CAREGIVER-01 was dead on arrival at
`a78c942e` — found by CHANNEL-04's pre-campaign smoke, one expedition
scr-mid voyage at seed 8000, before any cell ran.

`_caregiver_response` stamps `caregiver_report_due_epoch` on the live
engine agent and `to_schema_dict()` emits it, but
`engine_payload_to_schema` rebuilds every agent dict through
`_copy_optional_agent_fields`'s fixed key list — which omitted the
field — so `work.agents` never carried a stamp and the syndromic
caregiver branch (`agent.get("caregiver_report_due_epoch") is not
None`) was unreachable. `caregiver_report_ids` was always empty; no
run could report via the attendant channel. The unit tests passed
because they covered the stamp on the live object and the roster
reading a synthetic dict — never the serialization hop between them.

## Measured (seed 8000, `fl_exp_12d_scr` × `rung-shipped,bp32p5c18p5`)

Broken at `a78c942e`: `caregiver_reports` telemetry 4, stamps persisting
55+ epochs on hosts {28, 78, 313} in the live population — zero stamps
in any serialized `work.agents` dict, `caregiver_report_ids` empty.

Fixed (this PR): `stamped_hosts` 2, `reports_via_caregiver` 2
(passenger channel), `reports_on_nonemetic_course` [] and
`reports_without_infection_record` [] — integrity clean. rep/elig
moved 0.231 -> 0.533 and conf/rep 0.000 -> 0.375 on the single seed
(reports shift downstream draws; a single seed is a witness, not a
pooled verdict).

## Fix

`caregiver_report_due_epoch` added to the fixed key list in
`_copy_optional_agent_fields` (`orchestrator_init.py`); seam regression
test `test_caregiver_report_stamp_survives_boundary` in
`tests/test_telemetry_seams.py`.

## Also dropped at the same hop (no consumer today)

`party_id`, `dining_party_ids`, `dining_table_index` are emitted by
`_export_optional_state` and stripped by the same list. Add them when a
downstream consumer needs them; the caregiver pipeline itself is
unaffected (responder selection reads live objects).
