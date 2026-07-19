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
    PIP_NO_CACHE_DIR=1

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt boto3

# Copy the rest of the repo (see .dockerignore for exclusions).
COPY . .

# Run as a non-root user; it owns /app so the runner can write telemetry.
RUN useradd --create-home --uid 10001 campaign && chown -R campaign:campaign /app
USER campaign

ENTRYPOINT ["python3", "picard_framework/runs/mega_cruise_campaign/campaign_runner.py"]
