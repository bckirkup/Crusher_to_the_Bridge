# Simulation REST API

> **Status:** Implemented in `api/` (issue #101)

`api/` exposes `PicardRunSpec`/`ShipSimulation` over HTTP so remote
orchestrators and fleet integrations can submit voyages without a local
checkout (issue #101).

## Install and run

```bash
pip install .[api]          # or: uv sync --all-extras
python -m api               # serves http://127.0.0.1:8000
python -m api --host 0.0.0.0 --port 8000 --workers 4
crusher-api --port 8000     # equivalent console script
```

Interactive OpenAPI docs live at `/docs`.

Authentication: set `CRUSHER_API_TOKEN` to require
`Authorization: Bearer <token>` on every endpoint except `/health`.
Unbound by default (loopback-only `--host 127.0.0.1`), which is the
supported posture for trusted-network use; put the service behind a real
gateway for anything else.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness (unauthenticated). |
| `GET` | `/v1/catalog` | Valid `platform_id` / `pathogen_bundle_id` values. |
| `POST` | `/v1/runs` | Submit a run spec → `202 {job_id, status}`. |
| `GET` | `/v1/runs` | Job list (newest first), without result payloads. |
| `GET` | `/v1/runs/{id}` | Status, epoch progress, and `result` when terminal. |
| `POST` | `/v1/runs/{id}/cancel` | Cancel; lands on the next epoch boundary. |
| `DELETE` | `/v1/runs/{id}` | Remove a terminal job's record (`409` while active). |

## Run submission

`POST /v1/runs` takes a Picard run spec — the same JSON document that
`schemas/picard_run_spec.schema.json` validates and
`PicardRunSpec.from_picard_json` accepts. Invalid specs are rejected
synchronously with `422`, including unknown catalog references.

```bash
curl -X POST http://127.0.0.1:8000/v1/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "catalog": {"platform_id": "destroyer_baseline",
                "pathogen_bundle_id": "active_profiles"},
    "run": {"random_seed": 42, "num_epochs": 168,
            "write_ground_truth": false},
    "legacy_yaml": "crusher_labs/config.yaml",
    "actors": [], "incentives": {}
  }'
# → {"job_id": "9f3c…", "status": "queued"}

curl http://127.0.0.1:8000/v1/runs/9f3c…
# → {"status": "succeeded", "epochs_completed": 168,
#    "result": {"num_epochs": 168, "final_trigger_status": "…",
#               "history": [ …per-epoch records… ]},
#    "telemetry": {"simulation_history": "telemetry_buffer/api_jobs/9f3c…/…", …}}
```

Job lifecycle: `queued → running → succeeded | failed | cancelled`.
`result.history` is the same per-epoch record list `ShipSimulation.run()`
returns. Telemetry files land under `telemetry_buffer/api_jobs/<job_id>/`
unless the spec's `run` block names its own `simulation_history` /
`ground_truth` / `lab_notebook` paths (all confined to the repo tree by the
usual path validators).

## Testing

`tests/test_api_service.py` exercises the full lifecycle but is opt-in —
each test spins real voyages, so it does not run in CI or routine pytest
invocations. Run it explicitly:

```bash
CTTB_API_TESTS=1 python3 -m pytest tests/test_api_service.py -v
```

## Limits (v1)

- Jobs run in-process on a thread pool (`--workers`, default 2 or
  `CRUSHER_API_WORKERS`). CPU-bound voyages serialize against each other
  and the service; large batches belong on AWS Batch via `deploy/aws/`.
- The job table is in-memory: a restart drops job records (telemetry files
  on disk are unaffected).
- Cancellation is cooperative — checked between epochs, so a job finishes
  its in-flight epoch before reporting `cancelled`.
