# PostgreSQL to S3 Backup Flow

Prefect flow that runs pg-s3-backup as a Kubernetes Job.

## Configuration

### Set Variables (non-sensitive)

```bash
just set-var pg_backup_bucket my-backups
just set-var pg_backup_prefix production/
just set-var pg_backup_host db.example.com
just set-var pg_backup_dbname mydb
just set-var pg_backup_user postgres
just set-var pg_backup_aws_region us-east-1
```

### Set Secret Blocks (sensitive)

Set environment variables first, then run:

```bash
export PG_PASSWORD="your-password"
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

just set-secret PG_PASSWORD
just set-secret AWS_ACCESS_KEY_ID
just set-secret AWS_SECRET_ACCESS_KEY
```

## Deploy

```bash
just deploy-scheduled  # Deploy with daily 2am schedule
```

## Just Commands

| Command | Description |
|---------|-------------|
| `just set-var name value` | Set a Prefect variable |
| `just set-secret name` | Set a secret (reads from `$name` env var) |
| `just set-secrets` | Set all required secrets |
| `just list-vars` | List all variables |
| `just deploy-scheduled` | Deploy with schedule |
| `just status` | Show Prefect status |
