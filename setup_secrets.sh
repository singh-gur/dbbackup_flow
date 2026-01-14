#!/usr/bin/env bash
# Setup script for PostgreSQL to S3 backup flow configuration
# This script sets all required Prefect variables and secrets

set -euo pipefail

echo "=== PostgreSQL to S3 Backup Flow - Configuration Setup ==="
echo ""

# Check if just is available
if ! command -v just &> /dev/null; then
    echo "Error: 'just' command not found. Please install just first."
    exit 1
fi

# ============================================================================
# Non-sensitive Variables (Prefect Variables)
# ============================================================================

echo "Setting Prefect Variables (non-sensitive)..."
echo ""

# PostgreSQL Configuration
read -p "PostgreSQL Host [localhost]: " PG_HOST
PG_HOST=${PG_HOST:-localhost}

read -p "PostgreSQL Database [postgres]: " PG_DBNAME
PG_DBNAME=${PG_DBNAME:-postgres}

read -p "PostgreSQL User [postgres]: " PG_USER
PG_USER=${PG_USER:-postgres}

# S3 Configuration
read -p "S3 Bucket Name [my-backups]: " S3_BUCKET
S3_BUCKET=${S3_BUCKET:-my-backups}

read -p "S3 Prefix (optional) []: " S3_PREFIX
S3_PREFIX=${S3_PREFIX:-}

# AWS Configuration
read -p "AWS Region [us-east-1]: " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

echo ""
echo "Setting variables..."

just set-var pg_backup_host "$PG_HOST"
just set-var pg_backup_dbname "$PG_DBNAME"
just set-var pg_backup_user "$PG_USER"
just set-var pg_backup_bucket "$S3_BUCKET"
just set-var pg_backup_prefix "$S3_PREFIX"
just set-var pg_backup_aws_region "$AWS_REGION"

echo ""
echo "✅ Variables set successfully"
echo ""

# ============================================================================
# Sensitive Secrets (Prefect Secret Blocks)
# ============================================================================

echo "Setting Prefect Secrets (sensitive)..."
echo ""

# PostgreSQL Password
read -sp "PostgreSQL Password: " PG_PASSWORD
echo ""

# AWS Credentials
read -sp "AWS Access Key ID: " AWS_ACCESS_KEY
echo ""

read -sp "AWS Secret Access Key: " AWS_SECRET_KEY
echo ""

echo ""
echo "Setting secrets..."

just set-secret pg-password "$PG_PASSWORD"
just set-secret aws-access-key "$AWS_ACCESS_KEY"
just set-secret aws-secret-key "$AWS_SECRET_KEY"

echo ""
echo "✅ Secrets set successfully"
echo ""

# ============================================================================
# Verification
# ============================================================================

echo "=== Configuration Summary ==="
echo ""
echo "Variables:"
just list-vars
echo ""
echo "Secrets created: pg-password, aws-access-key, aws-secret-key"
echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Deploy the flow: just deploy-scheduled"
echo "  2. Trigger a test run: just trigger pg-s3-backup"
