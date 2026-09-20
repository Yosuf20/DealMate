"""
POST /quote-requests

Called by the AI AGENT when it wants local sellers to quote a product.
Body matches shared/schemas/product_request.json.
"""

import json
from pydantic import ValidationError
from ..db.models import QuoteRequest
from ..db.dynamo_client import put_item


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        quote_request = QuoteRequest(**body)
    except (ValidationError, TypeError) as e:
        return _response(400, {"error": "invalid request", "details": str(e)})

    put_item("quote_request", quote_request.model_dump())

    return _response(201, quote_request.model_dump())


def _response(status: int, body: dict):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
