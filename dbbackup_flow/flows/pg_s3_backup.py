"""pg-s3-backup flow for PostgreSQL backup to S3 using Kubernetes Job."""

from typing import Any

from prefect import flow, get_run_logger
from prefect.blocks.system import Secret
from prefect.exceptions import ObjectNotFound
from prefect.runtime import flow_run
from prefect.variables import Variable
from prefect_kubernetes.credentials import KubernetesCredentials
from prefect_kubernetes.jobs import KubernetesJob


def load_secret_value(name: str) -> str:
    """Load a Prefect Secret block value."""
    try:
        secret_block = Secret.load(name)
    except ObjectNotFound as exc:
        raise ObjectNotFound(
            Exception(
                f"Prefect Secret block '{name}' not found. Create it before running the flow."
            )
        ) from exc

    return secret_block.get()


@flow(
    name="pg-s3-backup",
    description="Run pg-s3-backup Docker container as Kubernetes Job to backup PostgreSQL to S3",
)
def run_pg_backup(
    # Kubernetes options
    namespace: str = "default",
    kubernetes_credentials: KubernetesCredentials | None = None,
    # Docker image
    image: str = "regv2.gsingh.io/personal/pg-s3-backup:latest",
    image_pull_policy: str = "Always",
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

        # Sensitive Secrets (create via Prefect UI or CLI):
        from prefect.blocks.system import Secret
        Secret(value="your-password").save("pg-password", overwrite=True)
        Secret(value="your-access-key").save("aws-access-key", overwrite=True)
        Secret(value="your-secret-key").save("aws-secret-key", overwrite=True)

    Args:
        namespace: Kubernetes namespace to run the job in (default: default)
        kubernetes_credentials: KubernetesCredentials block to use. If None,
            uses in-cluster config.
        image: Docker image to run for backup
        image_pull_policy: Docker image pull policy
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

    # Get values from Prefect Variables (with fallback to parameters)
    bucket = Variable.get(name="pg_backup_bucket", default=bucket)
    prefix = Variable.get(name="pg_backup_prefix", default=prefix)
    host = Variable.get(name="pg_backup_host", default=host)
    dbname = Variable.get(name="pg_backup_dbname", default=dbname)
    user = Variable.get(name="pg_backup_user", default=user)
    aws_region = Variable.get(name="pg_backup_aws_region", default=aws_region)

    # Get secrets from Prefect Secret blocks
    password = load_secret_value("pg-password")
    aws_access_key = load_secret_value("aws-access-key")
    aws_secret = load_secret_value("aws-secret-key")

    # Build command arguments
    cmd = [
        "--host",
        host,
        "--port",
        str(port),
        "--dbname",
        dbname,
        "--user",
        user,
        "--bucket",
        bucket,
        "--aws-profile",
        aws_profile,
        "--aws-region",
        aws_region,
    ]

    if backup_all:
        cmd.append("--all")

    if prefix:
        cmd.extend(["--prefix", prefix])

    if aws_endpoint_url:
        cmd.extend(["--aws-endpoint-url", aws_endpoint_url])

    if compress:
        cmd.append("--compress")

    if keep_local:
        cmd.append("--keep-local")

    # Build environment variables with secrets
    env: list[dict[str, Any]] = [
        {"name": "PGPASSWORD", "value": password},
        {"name": "AWS_ACCESS_KEY_ID", "value": aws_access_key},
        {"name": "AWS_SECRET_ACCESS_KEY", "value": aws_secret},
    ]

    flow_run_id = flow_run.id
    job_suffix = flow_run_id[:8] if flow_run_id else "manual"
    job_name = f"pg-s3-backup-{job_suffix}"

    # Build Kubernetes Job manifest
    job_manifest = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "labels": {
                "app": "pg-s3-backup",
                "prefect-flow": "pg-s3-backup",
            },
        },
        "spec": {
            "backoffLimit": backoff_limit,
            "ttlSecondsAfterFinished": ttl_seconds_after_finished,
            "template": {
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [
                        {
                            "name": "pg-s3-backup",
                            "image": image,
                            "imagePullPolicy": image_pull_policy,
                            "command": ["/app/pg_s3_backup"],
                            "args": cmd,
                            "env": env,
                        }
                    ],
                }
            },
        },
    }

    logger.info(f"Starting PostgreSQL backup to S3: {bucket}/{prefix}")

    # Create and run the job
    job = KubernetesJob(
        v1_job=job_manifest,
        namespace=namespace,
        kubernetes_credentials=kubernetes_credentials,
        delete_after_completion=True,
        timeout_seconds=600,
    )

    job_run = job.trigger()
    result = job_run.wait_for_completion()
    logs = job_run.fetch_result() if include_logs else None

    logger.info("Backup completed successfully")
    response = {
        "success": result,
        "bucket": bucket,
        "prefix": prefix,
    }
    if include_logs:
        response["logs"] = logs

    return response
