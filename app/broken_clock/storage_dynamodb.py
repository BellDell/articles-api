"""DynamoDB implementation for Broken Clock Calculator history storage.

This module has no Flask dependency. It stores calculation history
in a DynamoDB table for use with AWS App Runner.
"""

import json
import os
from datetime import datetime, timezone


APP_ID_DEFAULT = "articles-api"


def _get_table():
    """Return the DynamoDB table resource.

    Raises ValueError if DYNAMODB_TABLE env var is not set.
    """
    import boto3  # lazy import — boto3 may not be installed in all environments

    table_name = os.environ.get("DYNAMODB_TABLE")
    if not table_name:
        raise ValueError(
            "DYNAMODB_TABLE environment variable is required "
            "when STORAGE_BACKEND=dynamodb"
        )
    dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION"))
    return dynamodb.Table(table_name)


def get_db_path():
    """Return None — DynamoDB does not use a file path."""
    return None


def ensure_db_initialized(db_path):
    """No-op — DynamoDB table is created by Terraform, not at runtime."""


def save_calculation(db_path, real_observed_time, wrong_observed_time,
                     offset_minutes, offset_human, clock_status,
                     target_wrong_times, reference_points):
    """Insert a successful calculation into DynamoDB."""
    app_id = os.environ.get("APP_ID", APP_ID_DEFAULT)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    table = _get_table()
    table.put_item(Item={
        "app_id": app_id,
        "created_at": created_at,
        "real_observed_time": real_observed_time,
        "wrong_observed_time": wrong_observed_time,
        "offset_minutes": offset_minutes,
        "offset_human": offset_human,
        "clock_status": clock_status,
        "target_wrong_times": json.dumps(target_wrong_times),
        "reference_points": json.dumps(reference_points),
    })


def get_history(db_path):
    """Return all saved calculations, newest first, with JSON fields decoded."""
    app_id = os.environ.get("APP_ID", APP_ID_DEFAULT)
    table = _get_table()

    response = table.query(
        KeyConditionExpression="app_id = :aid",
        ExpressionAttributeValues={":aid": app_id},
        ScanIndexForward=False,  # newest first
    )

    items = response.get("Items", [])

    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression="app_id = :aid",
            ExpressionAttributeValues={":aid": app_id},
            ScanIndexForward=False,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    rows = []
    for idx, item in enumerate(items):
        rows.append({
            "id": idx + 1,  # ordinal, not a DynamoDB attribute
            "created_at": item["created_at"],
            "real_observed_time": item["real_observed_time"],
            "wrong_observed_time": item["wrong_observed_time"],
            "offset_minutes": item["offset_minutes"],
            "offset_human": item["offset_human"],
            "clock_status": item["clock_status"],
            "target_wrong_times": json.loads(item["target_wrong_times"]),
            "reference_points": json.loads(item["reference_points"]),
        })

    return rows
