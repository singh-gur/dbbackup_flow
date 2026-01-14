"""pg-s3-backup flow for PostgreSQL backup to S3 using Kubernetes Job."""

from typing import Any

from prefect import flow, get_run_logger
from prefect.runtime import flow_run
from prefect.variables import Variable
from prefect_kubernetes.credentials import KubernetesCredentials
from prefect_kubernetes.jobs import KubernetesJob

# Constants
JOB_NAME_PREFIX = "pg-s3-backup"
APP_LABEL = "pg-s3-backup"
FLOW_LABEL = "pg-s3-backup"
CONTAINER_NAME = "pg-s3-backup"
BACKUP_COMMAND = "/app/pg_s3_backup"

# Variable names
VAR_BUCKET = "pg_backup_bucket"
VAR_PREFIX = "pg_backup_prefix"
VAR_HOST = "pg_backup_host"
VAR_DBNAME = "pg_backup_dbname"
VAR_USER = "pg_backup_user"
VAR_AWS_REGION = "pg_backup_aws_region"
VAR_AWS_ENDPOINT_URL = "pg_backup_aws_endpoint_url"


def load_config_value(var_name: str, default: Any) -> Any:
    """Load configuration from Prefect Variable with fallback to default.

    Args:
        var_name: Name of the Prefect Variable
        default: Default value if variable not found

    Returns:
        Variable value or default
    """
    return Variable.get(name=var_name, default=default)


def build_command_string(
    host: str,
    port: int,
    dbname: str,
    user: str,
    bucket: str,
    aws_profile: str,
    aws_region: str,
    backup_all: bool,
    prefix: str,
    aws_endpoint_url: str | None,
    compress: bool,
    keep_local: bool,
) -> str:
    """Build command string for pg-s3-backup container with env var references.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        dbname: Database name
        user: Database user
        bucket: S3 bucket name
        aws_profile: AWS profile
        aws_region: AWS region
        backup_all: Backup all databases flag
        prefix: S3 prefix
        aws_endpoint_url: Custom AWS endpoint URL
        compress: Enable compression flag
        keep_local: Keep local backup flag

    Returns:
        Command string with environment variable references
    """
    # Build command with environment variable references for secrets
    # Use quoted strings to handle spaces/special chars
    cmd_parts = [
        "/app/pg_s3_backup",
        "--host",
        f'"{host}"',
        "--port",
        str(port),
        "--dbname",
        f'"{dbname}"',
        "--user",
        f'"{user}"',
        "--password",
        '"$PGPASSWORD"',
        "--bucket",
        f'"{bucket}"',
        "--aws-access-key-id",
        '"$AWS_ACCESS_KEY_ID"',
        "--aws-secret-key",
        '"$AWS_SECRET_ACCESS_KEY"',
        "--aws-region",
        f'"{aws_region}"',
    ]

    # Optional flags and arguments
    if backup_all:
        cmd_parts.append("--all")

    if prefix:
        cmd_parts.extend(["--prefix", f'"{prefix}"'])

    if aws_endpoint_url:
        cmd_parts.extend(["--aws-endpoint-url", f'"{aws_endpoint_url}"'])

    if compress:
        cmd_parts.append("--compress")

    if keep_local:
        cmd_parts.append("--keep-local")

    return " ".join(cmd_parts)


def build_env_vars(
    k8s_secret_name: str,
) -> list[dict[str, Any]]:
    """Build environment variables for the container using Kubernetes Secret references.

    Args:
        k8s_secret_name: Name of the Kubernetes Secret containing credentials

    Returns:
        List of environment variable dicts with secret references
    """
    return [
        {
            "name": "PGPASSWORD",
            "valueFrom": {
                "secretKeyRef": {
                    "name": k8s_secret_name,
                    "key": "pg-password",
                }
            },
        },
        {
            "name": "AWS_ACCESS_KEY_ID",
            "valueFrom": {
                "secretKeyRef": {
                    "name": k8s_secret_name,
                    "key": "aws-access-key",
                }
            },
        },
        {
            "name": "AWS_SECRET_ACCESS_KEY",
            "valueFrom": {
                "secretKeyRef": {
                    "name": k8s_secret_name,
                    "key": "aws-secret-key",
                }
            },
        },
    ]


def build_job_manifest(
    job_name: str,
    image: str,
    image_pull_policy: str,
    command_string: str,
    env_vars: list[dict[str, Any]],
    backoff_limit: int,
    ttl_seconds_after_finished: int,
    namespace: str,
    image_pull_secret: str | None = None,
) -> dict[str, Any]:
    """Build Kubernetes Job manifest.

    Args:
        job_name: Name for the Kubernetes Job
        image: Docker image to use
        image_pull_policy: Image pull policy
        command_string: Command string with env var references
        env_vars: Environment variables for the container
        backoff_limit: Job backoff limit
        ttl_seconds_after_finished: Job TTL after completion
        namespace: Kubernetes namespace for the job
        image_pull_secret: Name of image pull secret (optional)

    Returns:
        Kubernetes Job manifest dict
    """
    pod_spec = {
        "restartPolicy": "Never",
        "containers": [
            {
                "name": CONTAINER_NAME,
                "image": image,
                "imagePullPolicy": image_pull_policy,
                "command": ["/bin/sh", "-c"],
                "args": [command_string],
                "env": env_vars,
            }
        ],
    }

    if image_pull_secret:
        pod_spec["imagePullSecrets"] = [{"name": image_pull_secret}]

    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "namespace": namespace,
            "labels": {
                "app": APP_LABEL,
                "prefect-flow": FLOW_LABEL,
            },
        },
        "spec": {
            "backoffLimit": backoff_limit,
            "ttlSecondsAfterFinished": ttl_seconds_after_finished,
            "template": {
                "spec": pod_spec,
            },
        },
    }


@flow(
    name=JOB_NAME_PREFIX,
    description="Run pg-s3-backup Docker container as Kubernetes Job to backup PostgreSQL to S3",
)
def run_pg_backup(
    # Kubernetes options
    namespace: str = "prefect",
    kubernetes_credentials: KubernetesCredentials | None = None,
    k8s_secret_name: str = "pg-backup-secrets",
    # Docker image
    image: str = "regv2.gsingh.io/personal/pg-s3-backup:latest",
    image_pull_policy: str = "Always",
    image_pull_secret: str | None = None,
    # PostgreSQL connection options
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "postgres",
    user: str = "postgres",
    backup_all: bool = False,
    # S3 options
    bucket: str = "my-backups",
    prefix: str = "",
    # AWS options
    aws_profile: str = "default",
    aws_region: str = "us-east-1",
    aws_endpoint_url: str | None = None,
    # Other options
    compress: bool = False,
    keep_local: bool = False,
    include_logs: bool = True,
    # Job options
    backoff_limit: int = 4,
    ttl_seconds_after_finished: int = 300,
) -> dict[str, Any]:
    """
    Run the pg-s3-backup Docker container as a Kubernetes Job to backup PostgreSQL to S3.

    Configuration:
        # Non-sensitive Variables:
        prefect variable set pg_backup_bucket "my-backups" --prod
        prefect variable set pg_backup_prefix "production/" --prod
        prefect variable set pg_backup_host "db.example.com" --prod
        prefect variable set pg_backup_dbname "mydb" --prod
        prefect variable set pg_backup_user "postgres" --prod
        prefect variable set pg_backup_aws_region "us-east-1" --prod
        prefect variable set pg_backup_aws_endpoint_url "https://s3.custom.com" --prod

        # Kubernetes Secret (create in the namespace):
        kubectl create secret generic pg-backup-secrets \
          --from-literal=pg-password='your-db-password' \
          --from-literal=aws-access-key='your-access-key' \
          --from-literal=aws-secret-key='your-secret-key' \
          --namespace=prefect

    Args:
        namespace: Kubernetes namespace to run the job in (default: prefect)
        kubernetes_credentials: KubernetesCredentials block to use. If None,
            uses in-cluster config.
        k8s_secret_name: Name of Kubernetes Secret containing credentials
        image: Docker image to run for backup
        image_pull_policy: Docker image pull policy
        image_pull_secret: Name of Kubernetes secret for pulling private images
        host: Hostname of the postgres server (default: localhost)
        port: Port of the postgres server (default: 5432)
        dbname: Name of the database to backup (default: postgres)
        user: Username to connect to the database (default: postgres)
        backup_all: Backup all databases (default: False)
        bucket: S3 Bucket to upload the backup
        prefix: S3 Prefix to upload the backup (default: "")
        aws_profile: AWS Profile to use for the upload (default: default)
        aws_region: AWS Region (default: us-east-1)
        aws_endpoint_url: Custom AWS endpoint URL (for S3-compatible services)
        compress: Enable gzip compression (default: False)
        keep_local: Keep local backup file after upload (default: False)
        include_logs: Include job logs in response (default: True)
        backoff_limit: Job backoff limit (default: 4)
        ttl_seconds_after_finished: Job TTL seconds after finished (default: 300)

    Returns:
        Dict with backup status and job info
    """
    logger = get_run_logger()

    # Load configuration from Prefect Variables (with fallback to parameters)
    bucket = load_config_value(VAR_BUCKET, bucket)
    prefix = load_config_value(VAR_PREFIX, prefix)
    host = load_config_value(VAR_HOST, host)
    dbname = load_config_value(VAR_DBNAME, dbname)
    user = load_config_value(VAR_USER, user)
    aws_region = load_config_value(VAR_AWS_REGION, aws_region)
    aws_endpoint_url = load_config_value(VAR_AWS_ENDPOINT_URL, aws_endpoint_url)

    # Build command string with env var references
    command_string = build_command_string(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        bucket=bucket,
        aws_profile=aws_profile,
        aws_region=aws_region,
        backup_all=backup_all,
        prefix=prefix,
        aws_endpoint_url=aws_endpoint_url,
        compress=compress,
        keep_local=keep_local,
    )

    # Build environment variables with Kubernetes Secret references
    env_vars = build_env_vars(
        k8s_secret_name=k8s_secret_name,
    )

    # Generate unique job name
    flow_run_id = flow_run.id
    job_suffix = flow_run_id[:8] if flow_run_id else "manual"
    job_name = f"{JOB_NAME_PREFIX}-{job_suffix}"

    # Build Kubernetes Job manifest
    job_manifest = build_job_manifest(
        job_name=job_name,
        image=image,
        image_pull_policy=image_pull_policy,
        command_string=command_string,
        env_vars=env_vars,
        backoff_limit=backoff_limit,
        ttl_seconds_after_finished=ttl_seconds_after_finished,
        namespace=namespace,
        image_pull_secret=image_pull_secret,
    )

    logger.info(f"Starting PostgreSQL backup to S3: {bucket}/{prefix}")

    # Setup Kubernetes credentials (use in-cluster config if not provided)
    if kubernetes_credentials is None:
        logger.info("No credentials provided, using in-cluster Kubernetes config")
        kubernetes_credentials = KubernetesCredentials()

    # Create and run the Kubernetes job
    job = KubernetesJob(
        v1_job=job_manifest,
        namespace=namespace,
        credentials=kubernetes_credentials,
        delete_after_completion=True,
        timeout_seconds=600,
    )

    job_run = job.trigger()
    result = job_run.wait_for_completion()
    logs = job_run.fetch_result() if include_logs else None

    logger.info("Backup completed successfully")

    # Build response
    response = {
        "success": result,
        "bucket": bucket,
        "prefix": prefix,
    }
    if include_logs:
        response["logs"] = logs

    return response
