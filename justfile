# Prefect Deployment Commands
# Use: just <task>

# Deploy all deployments to prod profile
deploy:
    prefect deploy --all --prod

# Deploy with specific entrypoint
deploy-flow:
    prefect deploy main.py:run_pg_backup --name pg-s3-backup --prod

# Deploy with schedule (daily at 2am)
deploy-scheduled:
    prefect deploy main.py:run_pg_backup --name pg-s3-backup --prod --cron "0 2 * * *"

# Run a deployment immediately (ad-hoc run)
run DEPLOYMENT_NAME:
    prefect deployment run {{ DEPLOYMENT_NAME }} --prod

# View deployed deployments
list-deployments:
    prefect deployment ls --prod

# View deployment details
info DEPLOYMENT_NAME:
    prefect deployment info {{ DEPLOYMENT_NAME }} --prod

# Trigger a deployment
trigger DEPLOYMENT_NAME:
    prefect deployment run '{{ DEPLOYMENT_NAME }}' --prod

# Install project dependencies
install:
    uv sync

# Register prefect-kubernetes blocks
register-blocks:
    prefect block register -m prefect_kubernetes

# Set a Prefect Variable (non-sensitive)

# Usage: just set-var pg_backup_bucket my-bucket
set-var name value:
    prefect variable set "{{ name }}" "{{ value }}" --prod

# Set a Secret block (sensitive)

# Usage: just set-secret PG_PASSWORD my-secret-value
set-secret name value:
    #!/usr/bin/env bash
    set -euo pipefail
    .venv/bin/python -c 'import os; from prefect.blocks.system import Secret; Secret(value="{{ value }}").save("{{ name }}", overwrite=True)'

# List Prefect variables
list-vars:
    prefect variable ls --prod

# Show Prefect version and status
status:
    prefect version && prefect profile ls
