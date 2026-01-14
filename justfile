# Prefect Deployment Commands
# Use: just <task>

# Deploy all deployments
deploy:
    just reqs && .venv/bin/prefect deploy --all

# Deploy with specific entrypoint
deploy-flow:
    just reqs && .venv/bin/prefect deploy dbbackup_flow/flows/pg_s3_backup.py:run_pg_backup --name pg-s3-backup -p kubernetes

# Deploy with schedule (daily at 2am)
deploy-scheduled:
    just reqs && .venv/bin/prefect deploy dbbackup_flow/flows/pg_s3_backup.py:run_pg_backup --name pg-s3-backup --cron "0 2 * * *" -p kubernetes

# Run a deployment immediately (ad-hoc run)
run DEPLOYMENT_NAME:
    .venv/bin/prefect deployment run '{{ DEPLOYMENT_NAME }}'

# View deployed deployments
list-deployments:
    .venv/bin/prefect deployment ls

# View deployment details
info DEPLOYMENT_NAME:
    .venv/bin/prefect deployment info '{{ DEPLOYMENT_NAME }}'

# Trigger a deployment
trigger DEPLOYMENT_NAME:
    .venv/bin/prefect deployment run '{{ DEPLOYMENT_NAME }}'

# Install project dependencies
install:
    uv sync

# Generate requirements.txt (top-level deps only, no transitive deps, no annotations)
reqs:
    uv pip compile pyproject.toml --no-deps --no-annotate --no-header > requirements.txt

# Run flow locally for testing
run-local FLOW_NAME:
    .venv/bin/python -c "from dbbackup_flow import {{ FLOW_NAME }}; {{ FLOW_NAME }}()"

# Register prefect-kubernetes blocks
register-blocks:
    .venv/bin/prefect block register -m prefect_kubernetes

# Set a Prefect Variable (non-sensitive)

# Usage: just set-var pg_backup_bucket my-bucket
set-var name value:
    .venv/bin/prefect variable set "{{ name }}" "{{ value }}"

# Usage: just set-var pg_backup_bucket my-bucket
set-var-overwrite name value:
    .venv/bin/prefect variable set --overwrite "{{ name }}" "{{ value }}"

# Set a Secret block (sensitive)

# Usage: just set-secret PG_PASSWORD my-secret-value
set-secret name value:
    #!/usr/bin/env bash
    set -euo pipefail
    .venv/bin/python -c 'import os; from prefect.blocks.system import Secret; Secret(value="{{ value }}").save("{{ name }}", overwrite=True)'

# List Prefect variables
list-vars:
    .venv/bin/prefect variable ls

# List Prefect secrets
list-secrets:
    .venv/bin/prefect block ls

# Show Prefect version and status
status:
    .venv/bin/prefect version && .venv/bin/prefect profile ls
