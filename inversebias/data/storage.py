"""Database backup and restore functions for inversebias database."""

import os
import subprocess
from datetime import datetime
from pathlib import Path
import boto3
from dotenv import load_dotenv
import argparse

from inversebias.config import settings
from inversebias.data.db import ensure_volume_dirs

# Load environment variables
load_dotenv()

# Get S3 configuration from environment
S3_CONFIG = {
    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "endpoint_url": os.getenv("AWS_ENDPOINT_URL_S3"),
    "region_name": os.getenv("AWS_REGION", "auto"),
}
BUCKET_NAME = os.getenv("BUCKET_NAME")


def get_db_connection_params():
    """Extract PostgreSQL connection parameters from the database URI.

    Returns:
        dict: Dictionary with connection parameters
    """
    # Get the URI directly from settings
    db_uri = settings.database.uri

    # Remove the postgresql:// prefix
    conn_string = db_uri.replace("postgresql://", "")

    # Extract username:password@host:port/database
    auth_host, database = conn_string.split("/", 1)
    auth, host = auth_host.split("@", 1)

    if ":" in auth:
        username, password = auth.split(":", 1)
    else:
        username = auth
        password = ""

    if ":" in host:
        hostname, port = host.split(":", 1)
    else:
        hostname = host
        port = "5432"  # Default PostgreSQL port

    return {
        "host": hostname,
        "port": port,
        "database": database,
        "username": username,
        "password": password,
    }


def backup_db(output_path=None):
    """Create a PostgreSQL database dump.

    Args:
        output_path: Optional file path to save the dump. Defaults to timestamped file in data directory.

    Returns:
        Path: The path to the backup file
    """
    # Ensure data directory exists
    data_dir = ensure_volume_dirs()

    # Create timestamped filename if not provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = data_dir / f"inversebias_backup_{timestamp}.sql"

    # Get connection parameters
    conn_params = get_db_connection_params()

    # Set environment variables for pg_dump
    env = os.environ.copy()
    if conn_params["password"]:
        env["PGPASSWORD"] = conn_params["password"]

    # Build pg_dump command
    cmd = [
        "pg_dump",
        "-h",
        conn_params["host"],
        "-p",
        conn_params["port"],
        "-U",
        conn_params["username"],
        "-F",
        "c",  # Custom format (compressed)
        "-f",
        str(output_path),
        conn_params["database"],
    ]

    # Execute pg_dump
    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"Database backup created at {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error backing up database: {e}")
        raise


def restore_db(backup_path):
    """Restore a PostgreSQL database from a dump file.

    Args:
        backup_path: Path to the dump file

    Returns:
        bool: True if successful, False otherwise
    """
    # Get connection parameters
    conn_params = get_db_connection_params()

    # Set environment variables for pg_restore
    env = os.environ.copy()
    if conn_params["password"]:
        env["PGPASSWORD"] = conn_params["password"]

    # Build pg_restore command
    cmd = [
        "pg_restore",
        "-h",
        conn_params["host"],
        "-p",
        conn_params["port"],
        "-U",
        conn_params["username"],
        "-d",
        conn_params["database"],
        "--clean",  # Clean (drop) database objects before recreating
        "--if-exists",  # Add IF EXISTS to DROP commands
        str(backup_path),
    ]

    # Execute pg_restore
    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"Database restored from {backup_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restoring database: {e}")
        return False


def upload_backup_to_s3(backup_path=None, versioned=True):
    """Create a database backup and upload it to S3.

    Args:
        backup_path: Optional path to an existing backup file. If None, a new backup is created.
        versioned: If True, creates a versioned filename with timestamp.

    Returns:
        dict: Upload result with key and version info
    """
    # Create backup if path not provided
    if backup_path is None:
        backup_path = backup_db()
    elif not Path(backup_path).exists():
        raise FileNotFoundError(f"Backup file not found at {backup_path}")

    backup_path = Path(backup_path)

    # Initialize S3 client
    s3 = boto3.client("s3", **S3_CONFIG)

    # Define key names
    main_key = "inversebias_backup_latest.sql"
    result = {"key": main_key}

    # Upload main backup
    s3.upload_file(Filename=str(backup_path), Bucket=BUCKET_NAME, Key=main_key)

    # Create versioned copy if requested
    if versioned:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        versioned_key = f"inversebias_backup_{timestamp}.sql"
        s3.upload_file(Filename=str(backup_path), Bucket=BUCKET_NAME, Key=versioned_key)
        result["versioned_key"] = versioned_key

    return result


def download_backup_from_s3(local_path=None, use_latest=True, key=None):
    """Download a database backup from S3.

    Args:
        local_path: Optional path to save the backup file. Defaults to data directory with timestamp.
        use_latest: If True, downloads the latest backup file.
        key: Optional specific S3 key to download. Overrides use_latest if provided.

    Returns:
        Path: The path to the downloaded backup file
    """
    # Ensure the data directory exists
    data_dir = ensure_volume_dirs()

    # Create timestamped filename if not provided
    if local_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_path = data_dir / f"inversebias_backup_downloaded_{timestamp}.sql"

    # Initialize S3 client
    s3 = boto3.client("s3", **S3_CONFIG)

    # Determine which key to download
    download_key = key
    if not download_key:
        if use_latest:
            download_key = "inversebias_backup_latest.sql"
        else:
            # Find the latest versioned backup
            prefix = "inversebias_backup_"
            objects = list_objects(prefix=prefix)

            if objects:
                # Sort by LastModified (most recent first)
                latest = sorted(objects, key=lambda x: x["LastModified"], reverse=True)[
                    0
                ]
                download_key = latest["Key"]
            else:
                raise FileNotFoundError("No backup files found in S3 bucket")

    print(f"Downloading backup from S3: {download_key}")

    # Download file
    s3.download_file(Bucket=BUCKET_NAME, Key=download_key, Filename=str(local_path))

    return local_path


def list_objects(prefix=None, max_keys=1000):
    """List objects in the S3 bucket.

    Args:
        prefix: Optional prefix to filter objects. Default None lists all objects.
        max_keys: Maximum number of keys to return. Default 1000.

    Returns:
        list: List of dictionaries containing object details (Key, Size, LastModified)
    """
    # Create S3 client
    s3 = boto3.client("s3", **S3_CONFIG)

    # Prepare params for list_objects_v2
    params = {
        "Bucket": BUCKET_NAME,
        "MaxKeys": max_keys,
    }

    if prefix:
        params["Prefix"] = prefix

    # List objects
    response = s3.list_objects_v2(**params)

    # Extract relevant information
    objects = []
    if "Contents" in response:
        objects = [
            {
                "Key": obj["Key"],
                "Size": obj["Size"],
                "LastModified": obj["LastModified"],
            }
            for obj in response["Contents"]
        ]

    return objects


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Database backup and restore operations"
    )
    parser.add_argument(
        "--backup", action="store_true", help="Create a database backup"
    )
    parser.add_argument(
        "--restore", type=str, help="Restore the database from a backup file"
    )
    parser.add_argument("--upload", action="store_true", help="Upload backup to S3")
    parser.add_argument(
        "--download", action="store_true", help="Download backup from S3"
    )

    args = parser.parse_args()

    if args.backup:
        backup_path = backup_db()
        print(f"Database backup created: {backup_path}")

        if args.upload:
            result = upload_backup_to_s3(backup_path)
            print(f"Backup uploaded to S3: {result}")

    elif args.restore:
        if not os.path.exists(args.restore):
            if args.download:
                # Try to download the backup first
                backup_path = download_backup_from_s3(local_path=args.restore)
            else:
                raise FileNotFoundError(f"Backup file not found: {args.restore}")
        else:
            backup_path = args.restore

        success = restore_db(backup_path)
        if success:
            print("Database restore completed successfully")
        else:
            print("Database restore failed")

    elif args.download:
        backup_path = download_backup_from_s3()
        print(f"Backup downloaded from S3: {backup_path}")

    elif args.upload:
        # Just upload the latest backup
        backup_path = backup_db()
        result = upload_backup_to_s3(backup_path)
        print(f"Backup uploaded to S3: {result}")

    else:
        # Default behavior if no flags specified
        print("No action specified. Use --backup, --restore, --upload, or --download.")
        parser.print_help()
