"""FastAPI surface for remote Crusher simulation orchestration.

Exposes ``PicardRunSpec``/``ShipSimulation`` as an HTTP job API so remote
orchestrators and fleet integrations can submit voyages, poll progress,
and collect results without a local checkout.

Run with ``python -m api`` or the ``crusher-api`` script entry point.
Requires the ``api`` install extra (``pip install .[api]``).
"""

from __future__ import annotations

import argparse
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.jobs import JobManager, JobStateError
from picard_framework.catalog.registry import CatalogRegistry
from simulation_utils.paths import REPO_ROOT

AUTH_TOKEN_ENV = "CRUSHER_API_TOKEN"
WORKERS_ENV = "CRUSHER_API_WORKERS"
DEFAULT_MAX_WORKERS = 2

_API_VERSION = "v1"


class JobAccepted(BaseModel):
    job_id: str
    status: str


class JobStatusView(BaseModel):
    job_id: str
    status: str
    created_at: str
    started_at: str | None
    finished_at: str | None
    num_epochs: int
    epochs_completed: int
    cancel_requested: bool
    error: str | None
    telemetry: dict[str, str]


class JobDetail(JobStatusView):
    result: dict[str, Any] | None


def _manager(request: Request) -> JobManager:
    return request.app.state.jobs


def _require_bearer(request: Request) -> None:
    token = request.app.state.auth_token
    if not token:
        return
    if request.headers.get("authorization", "") != f"Bearer {token}":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "missing or invalid bearer token",
        )


def _worker_count(value: int | None) -> int:
    if value is not None:
        return value
    try:
        return int(os.environ.get(WORKERS_ENV, DEFAULT_MAX_WORKERS))
    except ValueError:
        return DEFAULT_MAX_WORKERS


def create_app(
    repo_root: str | None = None,
    *,
    max_workers: int | None = None,
    auth_token: str | None = None,
) -> FastAPI:
    """Build the FastAPI application.

    ``auth_token`` defaults to ``$CRUSHER_API_TOKEN``; when set, every
    endpoint except ``/health`` requires ``Authorization: Bearer <token>``.
    """
    root = repo_root or REPO_ROOT
    token = auth_token if auth_token is not None else os.environ.get(AUTH_TOKEN_ENV)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        app.state.jobs.shutdown()

    app = FastAPI(
        title="Crusher to the Bridge API",
        version="1.0.0",
        description=(
            "REST job API over PicardRunSpec/ShipSimulation. Submit a Picard "
            "run spec JSON, poll for completion, collect the voyage history."
        ),
        lifespan=lifespan,
    )
    app.state.jobs = JobManager(root, max_workers=_worker_count(max_workers))
    app.state.auth_token = token

    @app.exception_handler(JobStateError)
    async def _state_conflict(_request: Request, exc: JobStateError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_409_CONFLICT)

    @app.exception_handler(KeyError)
    async def _not_found(_request: Request, exc: KeyError) -> JSONResponse:
        missing = exc.args[0] if exc.args else ""
        return JSONResponse(
            {"detail": f"job not found: {missing}"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(f"/{_API_VERSION}/catalog", dependencies=[Depends(_require_bearer)])
    def catalog() -> dict[str, Any]:
        """List the platform and pathogen bundle IDs valid in run specs."""
        return CatalogRegistry.from_repo(root).to_dict()

    @app.post(
        f"/{_API_VERSION}/runs",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=JobAccepted,
        dependencies=[Depends(_require_bearer)],
    )
    def submit_run(
        spec: dict[str, Any],
        jobs: JobManager = Depends(_manager),
    ) -> JobAccepted:
        """Submit a Picard run spec (``schemas/picard_run_spec.schema.json``)."""
        try:
            record = jobs.submit(spec)
        except (ValueError, KeyError, FileNotFoundError) as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc),
            ) from exc
        return JobAccepted(job_id=record.job_id, status=record.status)

    @app.get(
        f"/{_API_VERSION}/runs",
        response_model=list[JobStatusView],
        dependencies=[Depends(_require_bearer)],
    )
    def list_runs(jobs: JobManager = Depends(_manager)) -> list[dict[str, Any]]:
        return [record.to_status_dict() for record in jobs.list()]

    @app.get(
        f"/{_API_VERSION}/runs/{{job_id}}",
        response_model=JobDetail,
        dependencies=[Depends(_require_bearer)],
    )
    def get_run(job_id: str, jobs: JobManager = Depends(_manager)) -> dict[str, Any]:
        return jobs.get(job_id).to_detail_dict()

    @app.post(
        f"/{_API_VERSION}/runs/{{job_id}}/cancel",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=JobStatusView,
        dependencies=[Depends(_require_bearer)],
    )
    def cancel_run(
        job_id: str,
        jobs: JobManager = Depends(_manager),
    ) -> dict[str, Any]:
        """Request cancellation; takes effect on the next epoch boundary."""
        return jobs.cancel(job_id).to_status_dict()

    @app.delete(
        f"/{_API_VERSION}/runs/{{job_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(_require_bearer)],
    )
    def delete_run(job_id: str, jobs: JobManager = Depends(_manager)) -> None:
        jobs.remove(job_id)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crusher to the Bridge simulation REST service",
    )
    parser.add_argument(
        "--host", default=os.environ.get("CRUSHER_API_HOST", "127.0.0.1"),
    )
    parser.add_argument(
        "--port", type=int,
        default=int(os.environ.get("CRUSHER_API_PORT", "8000")),
    )
    parser.add_argument(
        "--workers", type=int, default=None,
        help=f"concurrent simulations (default ${WORKERS_ENV} or {DEFAULT_MAX_WORKERS})",
    )
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(create_app(max_workers=args.workers), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
