# AGENTS.md - Database Backup Flow

This document provides guidelines for AI agents working on this PostgreSQL to S3 backup flow.

## Project Overview

A Prefect flow that runs `pg-s3-backup` Docker container as a Kubernetes Job to backup PostgreSQL databases to S3.

**Key Technologies:**
- Prefect 3.x for workflow orchestration
- `prefect-kubernetes` for Kubernetes Job management
- `uv` for package management

## Build Commands

```bash
# Install dependencies
uv sync

# Add new dependency
uv add package-name

# Remove dependency
uv remove package-name

# Deploy to Prefect server
just deploy
just deploy-scheduled  # With daily 2am cron schedule

# Set configuration
just set-var pg_backup_bucket my-bucket
just set-secret PG_PASSWORD secret-value
just set-secret AWS_ACCESS_KEY_ID key
just set-secret AWS_SECRET_ACCESS_KEY secret

# List Prefect variables
just list-vars
```

## Linting & Formatting

```bash
# Check syntax
python -m py_compile main.py

# Verify imports work
.venv/bin/python -c "from module import name"

# Justfile syntax check
just --list
```

## Testing

```bash
# Run a test flow locally (requires Prefect server access)
just run-local run_pg_backup

# Deploy and trigger manually
just deploy-scheduled
just trigger pg-s3-backup
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

### Secrets Management
- Store sensitive data in **Prefect Secret Blocks** (`Secret.load("name").get()`)
- Use `Secret.save(value, overwrite=True)` to create/update
- Never commit secrets to version control
- Use `.env` files locally (gitignored)

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
├── main.py           # Flow definition
├── pyproject.toml    # Project metadata & deps
├── prefect.yaml      # Prefect deployment config
├── justfile          # Automation commands
├── .gitignore
├── AGENTS.md         # This file
└── README.md         # User documentation
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
