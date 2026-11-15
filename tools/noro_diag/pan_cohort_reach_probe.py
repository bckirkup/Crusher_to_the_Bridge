#!/usr/bin/env python3
"""Read-only probe: do secondary hand transfers reach non-taker pan cohort members?"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.noro_diag import growth_chain_census as gcc  # noqa: E402
from tools.noro_diag import hand_cascade_witness as witness  # noqa: E402

ARM = "carriers_ordered"
PATHOGEN = "norwalk_gi"
MANIFEST = REPO / "picard_framework/runs/mega_cruise_campaign/noro_provisioned_sensitivity_01_manifest.json"
TIER = "fl_exp_12d_sens_p06_paxv"
SEEDS = [8073, 8038, 8046, 8047, 8077]
CS_PATHWAY = "common_source_food"


def _f(value):
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _pathway(row):
    return str(row.get("dominant_pathway") or row.get("pathway") or "").split(":", 1)[0]


def _first_epochs(voyage):
    series = (voyage or {}).get("timeseries") or []
    first_sym = next((int(r.get("epoch")) for r in series if _f(r.get("symptomatic")) > 0.0), None)
    first_q = next((int(r.get("epoch")) for r in series if _f(r.get("quarantined")) > 0.0), None)
    return first_sym, first_q


def _bucket(epoch, cs_start, cs_end, first_q):
    if epoch is None or cs_start is None or cs_end is None:
        return "unknown"
    if epoch < cs_start:
        return "before_cs"
    if epoch > cs_end:
        return "after_cs"
    q = first_q if first_q is not None else cs_end + 1
    return "cs_span_pre_q" if epoch < q else "cs_span_post_q"


def run_seed_pan_cohort(pathogen_id, spec_dict, natural_history_clock):
    rec = gcc.CensusRecorder(pathogen_id=pathogen_id, payload_profile="full")
    rec.occupancy = gcc.hand_occupancy.OccupancyRecorder(pathogen_id)
    pan_rows = []
    call_id = 0
    orig = None

    def wrapper(self, state, obj, epoch, zone_name, token, cohort, servings_served, pan_servings, pathogen_id_, cs_block, matrix):
        nonlocal call_id, orig
        before = len(getattr(self, "_cs_event_log", []) or [])
        orig(
            self, state, obj, epoch, zone_name, token, cohort,
            servings_served, pan_servings, pathogen_id_, cs_block, matrix,
        )
        events = (getattr(self, "_cs_event_log", []) or [])[before:]
        if not events:
            return
        call_id += 1
        cohort_ids = sorted(int(a.agent_id) for a in cohort)
        window_takers = sorted({
            int(t) for event in events for t in (event.get("taker_ids") or [])
        })
        for event in events:
            pan_rows.append({
                "call_id": call_id,
                "event_id": event.get("event_id"),
                "epoch": int(epoch),
                "end_epoch": event.get("end_epoch"),
                "zone": zone_name,
                "meal": token,
                "object_id": obj.get("object_id"),
                "pan_serial": event.get("pan_serial"),
                "servings_taken": int(event.get("servings_taken") or 0),
                "per_serving_dose": _f(event.get("per_serving_dose")),
                "pan_mass": _f(event.get("pan_mass")),
                "cohort_size": int(event.get("cohort_size") or len(cohort_ids)),
                "cohort_ids": cohort_ids,
                "taker_ids": [int(x) for x in (event.get("taker_ids") or [])],
                "window_taker_ids": window_takers,
            })

    num_agents = int((spec_dict.get("config_overrides") or {}).get("ship_graph", {}).get("num_agents", 0))
    with gcc.materialized_picard_spec(spec_dict, gcc.REPO_ROOT) as picard_spec:
        rec.profile = dict(picard_spec.pathogen_profiles.get(pathogen_id) or {})
        with gcc.instrumented(rec):
            orig = gcc.tc.TransmissionCore._cs_object_emit_pans
            with mock.patch.object(gcc.tc.TransmissionCore, "_cs_object_emit_pans", wrapper):
                sim = gcc.ShipSimulation(picard_spec, display=False)
                sim.initialize()
                for agent in sim.engine.agents:
                    inf = (getattr(agent, "infections", {}) or {}).get(pathogen_id)
                    if inf is None:
                        continue
                    aid = int(agent.agent_id)
                    rec.host_gen.setdefault(aid, 0)
                    rec.import_ids.add(aid)
                    strain = inf.get("strain_id")
                    if strain:
                        rec.strain_home.setdefault(str(strain), aid)
                    rec.host_row(agent)
                sim.epoch_observer = gcc._census_observer(rec, pathogen_id)
                started = time.perf_counter()
                result = sim.run()
                wall_clock_s = time.perf_counter() - started
                try:
                    rec.voyage_rss_mb = gcc._proc_rss_mb()[1]
                except Exception:  # RSS probe is best-effort; diagnostics can run without it.
                    pass
        rec.seed_ids = set(getattr(sim.engine, "explicit_seed_agent_ids", None) or ())
        core = sim.tx_core
        initiation = gcc._initiation_witness(sim, pathogen_id, rec.profile)
    voyage = gcc._voyage_blocks(spec_dict, result, num_agents, natural_history_clock)
    payload = gcc._summarise_run(rec, spec_dict, wall_clock_s, core)
    payload["pan_cohort_rows"] = pan_rows
    return payload, voyage, initiation


def summarise_reach(payload, voyage):
    pan_rows = payload.get("pan_cohort_rows") or []
    prov_events = [
        e for e in ((payload.get("common_source") or {}).get("events") or [])
        if e.get("source_kind") == "provisioned_lot"
    ]
    cs_start = min((int(e.get("start_epoch") or 0) for e in prov_events), default=None)
    cs_end = max((int(e.get("end_epoch") or 0) for e in prov_events), default=None)
    _first_sym, first_q = _first_epochs(voyage)

    def bucket_of(epoch):
        return _bucket(epoch, cs_start, cs_end, first_q)

    ever_cohort = set()
    ever_takers = set()
    first_cohort_epoch = {}
    first_taker_epoch = {}
    service_windows = defaultdict(lambda: {
        "cohort": set(), "takers": set(), "events": 0, "servings": 0,
        "pan_mass": 0.0, "max_per_serving": 0.0, "end_epoch": None,
    })
    for row in pan_rows:
        cohort = {int(x) for x in row.get("cohort_ids") or []}
        takers = {int(x) for x in row.get("taker_ids") or []}
        epoch = int(row.get("epoch") or 0)
        ever_cohort |= cohort
        ever_takers |= takers
        for aid in cohort:
            first_cohort_epoch[aid] = min(first_cohort_epoch.get(aid, 10**9), epoch)
        for aid in takers:
            first_taker_epoch[aid] = min(first_taker_epoch.get(aid, 10**9), epoch)
        key = (row.get("zone"), row.get("meal"), epoch)
        window = service_windows[key]
        window["cohort"] |= cohort
        window["takers"] |= takers
        window["events"] += 1
        window["servings"] += int(row.get("servings_taken") or 0)
        window["pan_mass"] += _f(row.get("pan_mass"))
        window["max_per_serving"] = max(window["max_per_serving"], _f(row.get("per_serving_dose")))
        end_epoch = row.get("end_epoch")
        if end_epoch is not None:
            end_i = int(end_epoch)
            window["end_epoch"] = end_i if window["end_epoch"] is None else max(window["end_epoch"], end_i)

    never_takers = sorted(ever_cohort - ever_takers)

    first_cs_epoch = {}
    acq_by_agent = defaultdict(list)
    secondary_acq_by_agent = defaultdict(list)
    for row in payload.get("acquisitions") or []:
        epoch = row.get("epoch")
        agent_id = row.get("agent_id")
        if epoch is None or agent_id is None:
            continue
        epoch_i = int(epoch)
        aid = int(agent_id)
        pathway = _pathway(row)
        acq_by_agent[aid].append((epoch_i, pathway))
        if pathway == CS_PATHWAY:
            first_cs_epoch[aid] = min(first_cs_epoch.get(aid, 10**9), epoch_i)
        elif pathway:
            secondary_acq_by_agent[aid].append((epoch_i, pathway))

    pk_by_target = defaultdict(list)
    for row in payload.get("pickups") or []:
        if not row.get("challengeable") or _f(row.get("source_acquired_share")) <= 0.0:
            continue
        target = row.get("target", row.get("agent_id"))
        epoch = row.get("epoch")
        if target is None or epoch is None:
            continue
        pk_by_target[int(target)].append((int(epoch), _f(row.get("dose")), _f(row.get("delivered")), row.get("unit"), row.get("channel")))

    ct_by_target = defaultdict(list)
    for row in payload.get("hand_contacts") or []:
        target = row.get("target", row.get("agent_id"))
        donor = row.get("donor")
        epoch = row.get("epoch")
        if target is None or donor is None or epoch is None:
            continue
        ct_by_target[int(target)].append((int(epoch), _f(row.get("dose")), int(donor)))

    exposed_agents = set()
    infected_agents = set()
    exposed_by_bucket = Counter()
    infected_by_bucket = Counter()
    secondary_by_bucket_pathway = Counter()
    pickup_dose_by_bucket = Counter()
    contact_dose_by_bucket = Counter()
    earliest = {}

    for aid in never_takers:
        start = first_cohort_epoch.get(aid)
        if start is None:
            continue
        candidates = []
        for epoch, dose, _delivered, _unit, _channel in pk_by_target.get(aid, []):
            if epoch >= start:
                candidates.append((epoch, "pickup", dose))
                pickup_dose_by_bucket[bucket_of(epoch)] += dose
        seen_contact_epochs = set()
        for epoch, dose, donor in ct_by_target.get(aid, []):
            donor_first = first_cs_epoch.get(donor)
            if epoch >= start and donor_first is not None and donor_first < epoch and epoch not in seen_contact_epochs:
                candidates.append((epoch, "contact", dose))
                contact_dose_by_bucket[bucket_of(epoch)] += dose
                seen_contact_epochs.add(epoch)
        for epoch, pathway in secondary_acq_by_agent.get(aid, []):
            if epoch >= start:
                candidates.append((epoch, f"acq:{pathway}", 0.0))
                secondary_by_bucket_pathway[f"{bucket_of(epoch)}|{pathway}"] += 1
        if candidates:
            exposed_agents.add(aid)
            first = min(candidates, key=lambda item: item[0])
            earliest[aid] = {"epoch": first[0], "kind": first[1], "bucket": bucket_of(first[0])}
            exposed_by_bucket[bucket_of(first[0])] += 1
        if any(epoch >= start for epoch, _pathway in secondary_acq_by_agent.get(aid, [])):
            infected_agents.add(aid)
            for epoch, pathway in secondary_acq_by_agent.get(aid, []):
                if epoch >= start:
                    infected_by_bucket[bucket_of(epoch)] += 1

    window_summaries = []
    for (zone, meal, epoch), window in sorted(service_windows.items(), key=lambda item: (item[0][2], str(item[0][0]), str(item[0][1]))):
        cohort = window["cohort"]
        takers = window["takers"]
        nontakers = cohort - takers
        window_summaries.append({
            "zone": zone,
            "meal": meal,
            "start_epoch": epoch,
            "end_epoch": window["end_epoch"],
            "events": window["events"],
            "cohort_size": len(cohort),
            "takers": len(takers),
            "nontakers": len(nontakers),
            "servings_taken": window["servings"],
            "pan_mass": window["pan_mass"],
            "max_per_serving_dose": window["max_per_serving"],
            "pre_q": first_q is None or epoch < first_q,
        })

    return {
        "cs_start": cs_start,
        "cs_end": cs_end,
        "first_sym": _first_epochs(voyage)[0],
        "first_q": first_q,
        "n_pan_events": len(pan_rows),
        "n_service_windows": len(service_windows),
        "cohort_agents": len(ever_cohort),
        "taker_agents": len(ever_takers),
        "never_taker_agents": len(never_takers),
        "service_window_person_events": {
            "cohort": sum(len(w["cohort"]) for w in service_windows.values()),
            "takers": sum(len(w["takers"]) for w in service_windows.values()),
            "nontakers": sum(len(w["cohort"] - w["takers"]) for w in service_windows.values()),
        },
        "never_taker_exposed_any": len(exposed_agents),
        "never_taker_infected_secondary": len(infected_agents),
        "never_taker_exposed_by_bucket": dict(exposed_by_bucket),
        "never_taker_infected_by_bucket": dict(infected_by_bucket),
        "never_taker_secondary_by_bucket_pathway": dict(secondary_by_bucket_pathway),
        "never_taker_pickup_acquired_dose_by_bucket": {k: pickup_dose_by_bucket[k] for k in sorted(pickup_dose_by_bucket)},
        "never_taker_contact_dose_by_bucket": {k: contact_dose_by_bucket[k] for k in sorted(contact_dose_by_bucket)},
        "never_taker_earliest": {str(k): v for k, v in sorted(earliest.items())},
        "top_service_windows": sorted(window_summaries, key=lambda w: (w["servings_taken"], w["pan_mass"]), reverse=True)[:10],
        "early_service_windows": [w for w in window_summaries if w["start_epoch"] <= 24][:20],
    }


def main():
    manifest = gcc._load_manifest(MANIFEST)
    clock = manifest.get("natural_history_clock")
    nhc = str(clock) if clock is not None else None
    specs = witness.tier_specs(MANIFEST, TIER, SEEDS)
    rows = []
    for seed in SEEDS:
        spec = witness._arm_spec(specs[int(seed)], ARM)
        payload, voyage, _initiation = run_seed_pan_cohort(PATHOGEN, spec, nhc)
        row = summarise_reach(payload, voyage)
        row["seed"] = int(seed)
        rows.append(row)
        print(
            f"seed {seed}: windows {row['n_service_windows']} cohort {row['cohort_agents']} "
            f"takers {row['taker_agents']} never-takers {row['never_taker_agents']} "
            f"exposed {row['never_taker_exposed_any']} infected {row['never_taker_infected_secondary']}",
            flush=True,
        )
    out = {"tier": TIER, "arm": ARM, "pathogen_id": PATHOGEN, "rows": rows}
    path = REPO / "results" / "noro_pan_cohort_reach" / "hash1" / "pan_cohort_reach.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=str))
    print(f"written: {path}")


if __name__ == "__main__":
    main()
