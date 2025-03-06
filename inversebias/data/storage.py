"""S3 storage functions for inversebias database."""

import os
from datetime import datetime
from pathlib import Path
import boto3
from dotenv import load_dotenv

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
DB_FILENAME = "inverse_bias.db"


def download_db(local_path=None, use_latest=True, key=None):
    """Download the database file from S3.

    Args:
        local_path: Optional path to save the file. Defaults to project root.
        use_latest: If True, downloads the latest versioned file instead of the main file.
        key: Optional specific key to download. Overrides use_latest if provided.

    Returns:
        Path: The path to the downloaded file
    """
    local_path = local_path or Path(DB_FILENAME)

    # Create S3 client
    s3 = boto3.client("s3", **S3_CONFIG)

    # Determine which key to download
    download_key = key
    if not download_key:
        if use_latest:
            # Find the latest versioned file
            base_name = DB_FILENAME.split(".")[0]
            prefix = f"{base_name}_"
            objects = list_objects(prefix=prefix)

            if objects:
                # Sort by LastModified (most recent first)
                latest = sorted(objects, key=lambda x: x["LastModified"], reverse=True)[
                    0
                ]
                download_key = latest["Key"]

            else:
                # No versioned files found, fall back to main file
                download_key = DB_FILENAME
        else:
            download_key = DB_FILENAME
    print(f"Downloading {download_key}")
    # Download file
    s3.download_file(Bucket=BUCKET_NAME, Key=download_key, Filename=str(local_path))

    return local_path


def upload_db(local_path=None, versioned=True):
    """Upload the database file to S3.

    Args:
        local_path: Optional path to the file. Defaults to project root.
        versioned: If True, creates a versioned copy alongside the main file.

    Returns:
        dict: Upload result with key and version info
    """
    local_path = local_path or Path(DB_FILENAME)

    # Ensure file exists
    if not local_path.exists():
        raise FileNotFoundError(f"Database file not found at {local_path}")

    s3 = boto3.client("s3", **S3_CONFIG)
    result = {"key": DB_FILENAME}

    # Upload main file
    s3.upload_file(Filename=str(local_path), Bucket=BUCKET_NAME, Key=DB_FILENAME)

    # Create versioned copy if requested
    if versioned:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        versioned_key = f"{DB_FILENAME.split('.')[0]}_{timestamp}.db"
        s3.upload_file(Filename=str(local_path), Bucket=BUCKET_NAME, Key=versioned_key)
        result["versioned_key"] = versioned_key

    return result


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
