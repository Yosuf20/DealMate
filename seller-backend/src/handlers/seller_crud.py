"""
Seller registration & profile management, used by the seller portal.

  POST /sellers            -> create_seller
  GET  /sellers/{seller_id} -> get_seller
"""

import json
from pydantic import ValidationError
from ..db.models import Seller
from ..db.dynamo_client import put_item, get_item


def create_seller(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        seller = Seller(**body)
    except (ValidationError, TypeError) as e:
        return _response(400, {"error": "invalid seller", "details": str(e)})

    put_item("seller", seller.model_dump())
    return _response(201, seller.model_dump())


def get_seller(event, context):
    path_params = event.get("pathParameters") or {}
    seller_id = path_params.get("seller_id")

    if not seller_id:
        return _response(400, {"error": "seller_id is required"})

    seller = get_item("seller", {"seller_id": seller_id})
    if seller is None:
        return _response(404, {"error": "seller not found"})

    return _response(200, seller)


def _response(status: int, body: dict):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
