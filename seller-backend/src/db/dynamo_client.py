"""
Thin wrapper around boto3's DynamoDB resource.

Table names are read from environment variables so the same code works
in dev/staging/prod without edits. Set these in template.yaml or your
local .env when testing.
"""

import os
import boto3
from typing import Optional, Dict, Any, List

_dynamodb = boto3.resource("dynamodb")

TABLE_NAMES = {
    "seller": os.environ.get("SELLER_TABLE", "dealsetu-sellers"),
    "quote_request": os.environ.get("QUOTE_REQUEST_TABLE", "dealsetu-quote-requests"),
    "quote": os.environ.get("QUOTE_TABLE", "dealsetu-quotes"),
    "product_catalog": os.environ.get("PRODUCT_CATALOG_TABLE", "dealsetu-product-catalog"),
    "price_history": os.environ.get("PRICE_HISTORY_TABLE", "dealsetu-price-history"),
}


def table(name: str):
    """name is one of the keys in TABLE_NAMES, e.g. 'seller', 'quote'."""
    return _dynamodb.Table(TABLE_NAMES[name])


def put_item(table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    table(table_name).put_item(Item=item)
    return item


def get_item(table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    resp = table(table_name).get_item(Key=key)
    return resp.get("Item")


def query_by_key(table_name: str, key_name: str, key_value: str,
                  index_name: Optional[str] = None) -> List[Dict[str, Any]]:
    from boto3.dynamodb.conditions import Key
    kwargs = {"KeyConditionExpression": Key(key_name).eq(key_value)}
    if index_name:
        kwargs["IndexName"] = index_name
    resp = table(table_name).query(**kwargs)
    return resp.get("Items", [])


def delete_item(table_name: str, key: Dict[str, Any]) -> None:
    table(table_name).delete_item(Key=key)
