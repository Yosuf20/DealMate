"""
POST /quotes

Called by the SELLER PORTAL when a seller responds to a quote request
with a price. Body matches shared/schemas/seller_quote.json (minus
generated fields like quote_id / created_at).
"""

import json
from pydantic import ValidationError
from ..db.models import Quote
from ..db.dynamo_client import put_item, get_item


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        quote = Quote(**body)
    except (ValidationError, TypeError) as e:
        return _response(400, {"error": "invalid quote", "details": str(e)})

    # sanity check: the quote request it's responding to must exist
    qr = get_item("quote_request", {"quote_request_id": quote.quote_request_id})
    if qr is None:
        return _response(404, {"error": "quote_request not found"})

    put_item("quote", quote.model_dump())

    return _response(201, quote.model_dump())


def _response(status: int, body: dict):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
