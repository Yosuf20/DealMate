"""
create_table.py

One-time setup script: creates the SellerQuotes table in LocalStack.
Run once after LocalStack is up:  python create_table.py

Uses boto3 directly instead of the AWS CLI - avoids needing the CLI
installed/on PATH at all, and boto3 is needed for the real agent code
anyway.
"""

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.client(
    "dynamodb",
    endpoint_url="http://localhost:4566",
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

try:
    dynamodb.create_table(
        TableName="SellerQuotes",
        AttributeDefinitions=[
            {"AttributeName": "request_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "request_id", "KeyType": "HASH"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    print("Table 'SellerQuotes' created.")
except ClientError as e:
    if e.response["Error"]["Code"] == "ResourceInUseException":
        print("Table 'SellerQuotes' already exists.")
    else:
        raise

# Confirm it exists
tables = dynamodb.list_tables()["TableNames"]
print("Current tables:", tables)
