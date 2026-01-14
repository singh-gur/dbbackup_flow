# AGENTS.md - Database Backup Flow

This document provides guidelines for AI agents working on this PostgreSQL to S3 backup flow.

## Project Overview

A Prefect flow that runs `pg-s3-backup` Docker container as a Kubernetes Job to backup PostgreSQL databases to S3.

**Key Technologies:**
- Prefect 3.x for workflow orchestration
- `prefect-kubernetes` for Kubernetes Job management
- `uv` for package management
- Python 3.12+

## Build Commands

```bash
# Install dependencies
uv sync

# Add new dependency
uv add package-name

# Remove dependency
uv remove package-name

# Generate requirements.txt (for Prefect deployments)
just reqs

# Deploy to Prefect server
just deploy
just deploy-scheduled  # With daily 2am cron schedule

# Set configuration
just set-var pg_backup_bucket my-bucket
just set-secret pg-password secret-value
just set-secret aws-access-key key-id
just set-secret aws-secret-key secret-key

# List Prefect variables and blocks
just list-vars
just list-secrets
```

## Linting & Formatting

```bash
# Run Ruff linter (check only)
.venv/bin/ruff check .

# Run Ruff formatter (check only)
.venv/bin/ruff format --check .

# Auto-fix linting issues
.venv/bin/ruff check --fix .

# Auto-format code
.venv/bin/ruff format .

# Run type checker (basedpyright)
.venv/bin/basedpyright

# Check syntax of a single file
python -m py_compile dbbackup_flow/flows/pg_s3_backup.py

# Verify imports work
.venv/bin/python -c "from dbbackup_flow import run_pg_backup"

# Justfile syntax check
just --list
```

## Testing

```bash
# No unit tests currently - this is an integration-focused project

# Run flow locally (requires Prefect server access)
just run-local run_pg_backup

# Deploy and trigger manually
just deploy-scheduled
just trigger pg-s3-backup

# View deployment info
just list-deployments
just info pg-s3-backup

# Check Prefect status
just status
```

## Code Style Guidelines

### Imports
- Use absolute imports: `from prefect import flow`
- Group imports: stdlib → third-party → local
- Sort imports alphabetically within groups

### Types
- Use type hints on all function parameters and returns
- Use `| None` instead of `Optional[]` for Python 3.10+
- Define complex types with `TypedDict` or `NamedTuple` if needed

### Naming Conventions
- **Functions**: `snake_case` (e.g., `run_pg_backup`)
- **Variables**: `snake_case` (e.g., `bucket_name`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`)
- **Classes**: `PascalCase` (e.g., `KubernetesJob`)
- **Private methods/variables**: `_leading_underscore`

### Error Handling
- Use specific exceptions from `prefect.exceptions`
- Wrap external API calls in try/except with logging
- Include context in error messages: `"Failed to create job: {error}`

### Async/Await
- Use `async def` for Prefect flows that need async operations
- Never block on async code in async contexts
- Use `await` for I/O operations (Secret.load, API calls)

### Kubernetes Integration
- Use `KubernetesCredentials` block for cluster access (falls back to in-cluster config)
- Build job manifests as dicts, pass to `KubernetesJob`
- Always set `delete_after_completion=True` for cleanup
- Use `job_run.wait_for_completion()` before fetching results
- **IMPORTANT**: For Kubernetes work pools, specify dependencies in `job_variables.packages` (prefect.yaml), NOT `pip_install_requirements`
  - Example: `job_variables: {packages: ["prefect-kubernetes==0.7.2"]}`
  - The `pip_install_requirements` step does NOT work with Kubernetes work pools

### Secrets Management
- **IMPORTANT**: Store sensitive credentials in **Kubernetes Secrets**, not Prefect Secret Blocks
- Reference secrets in pod specs using `secretKeyRef` (never as plain environment variables)
- Secrets are injected at runtime by Kubernetes, keeping them secure
- Never commit secrets to version control
- Use `./scripts/create-k8s-secret.sh` to create secrets securely

### Configuration
- Store non-sensitive config in **Prefect Variables**: `Variable.get(name="key", default=fallback)`
- Use meaningful variable names: `pg_backup_bucket`, `pg_backup_host`
- Provide sensible defaults in function signatures

### Documentation
- Write docstrings for all public functions
- Include Args and Returns sections
- Document secret/variable names needed for the flow

### File Structure
```
.
├── main.py                       # Entry point (imports from dbbackup_flow)
├── pyproject.toml                # Project metadata & deps
├── prefect.yaml                  # Prefect deployment config
├── justfile                      # Automation commands
├── .gitignore
├── AGENTS.md                     # This file
├── README.md                     # User documentation
└── dbbackup_flow/                # Root package
    ├── __init__.py
    └── flows/
        ├── __init__.py
        └── pg_s3_backup.py       # Main backup flow
```

## Quick Reference

| Task | Command |
|------|---------|
| Sync deps | `uv sync` |
| Deploy | `just deploy-scheduled` |
| Set variable | `just set-var name value` |
| Set secret | `just set-secret name value` |
| List vars | `just list-vars` |
| Trigger run | `just trigger pg-s3-backup` |
| Check syntax | `python -m py_compile main.py` |
