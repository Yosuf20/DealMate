"""
GET /quote-requests/{quote_request_id}/quotes

Called by the AI AGENT to collect all seller responses for comparison
(this is what feeds agent's compare_deals tool).
"""

import json
from ..db.dynamo_client import query_by_key


def handler(event, context):
    path_params = event.get("pathParameters") or {}
    quote_request_id = path_params.get("quote_request_id")

    if not quote_request_id:
        return _response(400, {"error": "quote_request_id is required"})

    # requires a GSI on the 'quote' table: quote_request_id -> quote_id
    quotes = query_by_key(
        "quote",
        key_name="quote_request_id",
        key_value=quote_request_id,
        index_name="quote_request_id-index",
    )

    return _response(200, {"quote_request_id": quote_request_id, "quotes": quotes})


def _response(status: int, body: dict):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
