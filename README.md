# PostgreSQL to S3 Backup Flow

Prefect flow that runs pg-s3-backup as a Kubernetes Job.

## Prerequisites

### Kubernetes RBAC Setup

**If you're running Prefect in a dedicated namespace (e.g., `prefect`):**

See [QUICKSTART-PREFECT-NAMESPACE.md](QUICKSTART-PREFECT-NAMESPACE.md) for the fastest setup.

```bash
# Quick fix for permission errors
kubectl apply -f k8s/rbac-prefect-namespace.yaml
just deploy-scheduled
```

**If you're running Prefect in the `default` namespace:**

```bash
kubectl apply -f k8s/rbac.yaml
```

This creates:
- ServiceAccount: `prefect-worker`
- Role: `prefect-worker-job-manager` (permissions to manage Jobs and Pods)
- RoleBinding: `prefect-worker-job-manager-binding`

See [k8s/README.md](k8s/README.md) for detailed documentation.

## Configuration

### Quick Setup

#### 1. Create Kubernetes Secret

Use the provided script to securely create a Kubernetes Secret for credentials:

```bash
./scripts/create-k8s-secret.sh
```

The script will prompt you for:
- PostgreSQL password (hidden input)
- AWS access key (hidden input)
- AWS secret key (hidden input)

This creates a secret named `pg-backup-secrets` in the `prefect` namespace.

#### 2. Set Prefect Variables (non-sensitive configuration)

```bash
just set-var pg_backup_bucket my-backups
just set-var pg_backup_prefix production/
just set-var pg_backup_host db.example.com
just set-var pg_backup_dbname mydb
just set-var pg_backup_user postgres
just set-var pg_backup_aws_region us-east-1
just set-var pg_backup_aws_endpoint_url https://s3.custom.com  # Optional: for S3-compatible services
```

### Manual Setup

#### Create Kubernetes Secret

```bash
kubectl create secret generic pg-backup-secrets \
  --from-literal=pg-password='your-db-password' \
  --from-literal=aws-access-key='your-access-key' \
  --from-literal=aws-secret-key='your-secret-key' \
  --namespace=prefect
```

**Security Note:** Secrets are securely referenced in the Kubernetes Job manifest using `secretKeyRef` and passed to the container as environment variables. The CLI arguments reference these environment variables (e.g., `--password "$PGPASSWORD"`), ensuring secrets are never exposed in the manifest YAML or command arguments.

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
