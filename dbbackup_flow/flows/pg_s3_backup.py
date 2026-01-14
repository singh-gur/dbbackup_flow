"""pg-s3-backup flow for PostgreSQL backup to S3 using Kubernetes Job."""

from typing import Any

from prefect import flow, get_run_logger
from prefect.blocks.system import Secret
from prefect.exceptions import ObjectNotFound
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

# Secret names
SECRET_PG_PASSWORD = "pg-password"
SECRET_AWS_ACCESS_KEY = "aws-access-key"
SECRET_AWS_SECRET_KEY = "aws-secret-key"

# Variable names
VAR_BUCKET = "pg_backup_bucket"
VAR_PREFIX = "pg_backup_prefix"
VAR_HOST = "pg_backup_host"
VAR_DBNAME = "pg_backup_dbname"
VAR_USER = "pg_backup_user"
VAR_AWS_REGION = "pg_backup_aws_region"
VAR_AWS_ENDPOINT_URL = "pg_backup_aws_endpoint_url"


def load_secret_value(name: str) -> str:
    """Load a Prefect Secret block value.

    Args:
        name: Name of the Prefect Secret block

    Returns:
        Secret value as string

    Raises:
        ObjectNotFound: If secret block doesn't exist
    """
    try:
        secret_block = Secret.load(name)
    except ObjectNotFound as exc:
        raise ObjectNotFound(
            Exception(
                f"Prefect Secret block '{name}' not found. Create it before running the flow."
            )
        ) from exc

    return secret_block.get()


def load_config_value(var_name: str, default: Any) -> Any:
    """Load configuration from Prefect Variable with fallback to default.

    Args:
        var_name: Name of the Prefect Variable
        default: Default value if variable not found

    Returns:
        Variable value or default
    """
    return Variable.get(name=var_name, default=default)


def build_command_args(
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
) -> list[str]:
    """Build command arguments for pg-s3-backup container.

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
        List of command arguments
    """
    # Required arguments
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

    # Optional flags and arguments
    optional_args = [
        (backup_all, ["--all"]),
        (prefix, ["--prefix", prefix]),
        (aws_endpoint_url, ["--aws-endpoint-url", aws_endpoint_url]),
        (compress, ["--compress"]),
        (keep_local, ["--keep-local"]),
    ]

    for condition, args in optional_args:
        if condition:
            cmd.extend(args)

    return cmd


def build_env_vars(
    pg_password: str,
    aws_access_key: str,
    aws_secret_key: str,
    aws_endpoint_url: str | None = None,
) -> list[dict[str, str]]:
    """Build environment variables for the container.

    Args:
        pg_password: PostgreSQL password
        aws_access_key: AWS access key ID
        aws_secret_key: AWS secret access key
        aws_endpoint_url: Custom AWS endpoint URL (optional)

    Returns:
        List of environment variable dicts
    """
    env_vars = [
        {"name": "PGPASSWORD", "value": pg_password},
        {"name": "AWS_ACCESS_KEY_ID", "value": aws_access_key},
        {"name": "AWS_SECRET_ACCESS_KEY", "value": aws_secret_key},
    ]

    if aws_endpoint_url:
        env_vars.append({"name": "AWS_ENDPOINT_URL", "value": aws_endpoint_url})

    return env_vars


def build_job_manifest(
    job_name: str,
    image: str,
    image_pull_policy: str,
    command_args: list[str],
    env_vars: list[dict[str, str]],
    backoff_limit: int,
    ttl_seconds_after_finished: int,
) -> dict[str, Any]:
    """Build Kubernetes Job manifest.

    Args:
        job_name: Name for the Kubernetes Job
        image: Docker image to use
        image_pull_policy: Image pull policy
        command_args: Command arguments for the container
        env_vars: Environment variables for the container
        backoff_limit: Job backoff limit
        ttl_seconds_after_finished: Job TTL after completion

    Returns:
        Kubernetes Job manifest dict
    """
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "labels": {
                "app": APP_LABEL,
                "prefect-flow": FLOW_LABEL,
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
                            "name": CONTAINER_NAME,
                            "image": image,
                            "imagePullPolicy": image_pull_policy,
                            "command": [BACKUP_COMMAND],
                            "args": command_args,
                            "env": env_vars,
                        }
                    ],
                }
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
        prefect variable set pg_backup_aws_endpoint_url "https://s3.custom.com" --prod

        # Sensitive Secrets (create via Prefect UI or CLI):
        from prefect.blocks.system import Secret
        Secret(value="your-password").save("pg-password", overwrite=True)
        Secret(value="your-access-key").save("aws-access-key", overwrite=True)
        Secret(value="your-secret-key").save("aws-secret-key", overwrite=True)

    Args:
        namespace: Kubernetes namespace to run the job in (default: prefect)
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

    # Load configuration from Prefect Variables (with fallback to parameters)
    bucket = load_config_value(VAR_BUCKET, bucket)
    prefix = load_config_value(VAR_PREFIX, prefix)
    host = load_config_value(VAR_HOST, host)
    dbname = load_config_value(VAR_DBNAME, dbname)
    user = load_config_value(VAR_USER, user)
    aws_region = load_config_value(VAR_AWS_REGION, aws_region)
    aws_endpoint_url = load_config_value(VAR_AWS_ENDPOINT_URL, aws_endpoint_url)

    # Load secrets from Prefect Secret blocks
    pg_password = load_secret_value(SECRET_PG_PASSWORD)
    aws_access_key = load_secret_value(SECRET_AWS_ACCESS_KEY)
    aws_secret_key = load_secret_value(SECRET_AWS_SECRET_KEY)

    # Build command arguments
    command_args = build_command_args(
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

    # Build environment variables
    env_vars = build_env_vars(
        pg_password=pg_password,
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        aws_endpoint_url=aws_endpoint_url,
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
        command_args=command_args,
        env_vars=env_vars,
        backoff_limit=backoff_limit,
        ttl_seconds_after_finished=ttl_seconds_after_finished,
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
