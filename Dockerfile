# Mega cruise campaign runner — AWS Batch / Fargate Spot worker image.
#
# Build:
#   docker build -t picard-campaign .
# Smoke test:
#   docker run --rm picard-campaign --smoke
#
# See deploy/aws/README.md for the full ECR + AWS Batch array-job workflow.
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONUTF8=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/app/.venv/bin:$PATH

COPY --from=ghcr.io/astral-sh/uv:0.7.9 /uv /bin/uv

# Install dependencies first for better layer caching.
# Locked resolution from uv.lock (hash-verified) + wheels-only (Sonar docker:S8541 / S8544).
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --all-extras --no-install-project --no-build

# Copy only the code and data the headless campaign runner needs (explicit
# paths rather than `COPY . .` so nothing outside these is ever added).
COPY picard_framework/ ./picard_framework/
COPY crusher_labs/ ./crusher_labs/
COPY engines/ ./engines/
COPY decision_engine/ ./decision_engine/
COPY simulation_utils/ ./simulation_utils/
COPY telemetry_buffer/ ./telemetry_buffer/
COPY data/ ./data/
COPY schemas/ ./schemas/
COPY orchestrator.py ./
COPY orchestrator_chronic.py orchestrator_display.py orchestrator_epoch.py ./
COPY orchestrator_init.py orchestrator_record.py orchestrator_types.py ./

# Run as a non-root user; it owns /app so the runner can write telemetry.
RUN useradd --create-home --uid 10001 campaign && chown -R campaign:campaign /app
USER campaign

ENTRYPOINT ["python3", "picard_framework/runs/mega_cruise_campaign/campaign_runner.py"]
