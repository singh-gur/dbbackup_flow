# PostgreSQL to S3 Backup Flow

Prefect flow that runs pg-s3-backup as a Kubernetes Job.

## Configuration

### Quick Setup

Use the provided setup script to interactively configure all variables and secrets:

```bash
./setup_secrets.sh
```

The script will prompt you for:
- PostgreSQL host, database, user
- S3 bucket name and prefix
- AWS region
- PostgreSQL password (hidden input)
- AWS credentials (hidden input)

### Manual Setup

#### Set Variables (non-sensitive)

```bash
just set-var pg_backup_bucket my-backups
just set-var pg_backup_prefix production/
just set-var pg_backup_host db.example.com
just set-var pg_backup_dbname mydb
just set-var pg_backup_user postgres
just set-var pg_backup_aws_region us-east-1
```

#### Set Secret Blocks (sensitive)

```bash
just set-secret pg-password "your-password"
just set-secret aws-access-key "your-access-key-id"
just set-secret aws-secret-key "your-secret-access-key"
```

## Deploy

```bash
just deploy-scheduled  # Deploy with daily 2am schedule
```

## Just Commands

| Command | Description |
|---------|-------------|
| `just set-var name value` | Set a Prefect variable |
| `just set-secret name value` | Set a Prefect Secret block |
| `just list-vars` | List all variables |
| `just deploy-scheduled` | Deploy with schedule |
| `just status` | Show Prefect status |
