"""Generic DynamoDB storage helpers.

These helpers contain no feature-specific logic. They provide reusable
plumbing for any DynamoDB-backed feature package.
"""

import os


def get_dynamodb_table(table_name=None):
    """Return a DynamoDB Table resource.

    If *table_name* is ``None``, read it from the ``DYNAMODB_TABLE``
    environment variable.  Raises ``ValueError`` when neither is set.
    """
    import boto3  # lazy import

    resolved = table_name if table_name else os.environ.get("DYNAMODB_TABLE")
    if not resolved:
        raise ValueError(
            "DYNAMODB_TABLE environment variable is required "
            "when STORAGE_BACKEND=dynamodb"
        )
    dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION"))
    return dynamodb.Table(resolved)


def query_all_items(table, hash_key_name, hash_key_value):
    """Return all items for the given hash key, newest first.

    Handles pagination internally.  The table must have a sort key that
    supports ``ScanIndexForward=False`` (descending order).
    """
    response = table.query(
        KeyConditionExpression=f"{hash_key_name} = :hv",
        ExpressionAttributeValues={":hv": hash_key_value},
        ScanIndexForward=False,
    )
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=f"{hash_key_name} = :hv",
            ExpressionAttributeValues={":hv": hash_key_value},
            ScanIndexForward=False,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    return items
