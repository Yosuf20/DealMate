# DealSetu — API Contracts (seller-backend)

This is the contract your teammates (agent + frontend) build against.
Keep this file up to date whenever a request/response shape changes —
this is what prevents merge-day surprises.

## POST /quote-requests
Called by: **agent**
Body: `shared/schemas/product_request.json`
Response: `201` + the created QuoteRequest (with generated `quote_request_id`)

## POST /quotes
Called by: **seller portal** (frontend-for-sellers, part of seller-backend)
Body: `shared/schemas/seller_quote.json` (minus `quote_id`, `created_at` — generated server-side)
Response: `201` + the created Quote

## GET /quote-requests/{quote_request_id}/quotes
Called by: **agent** — to collect all seller responses for comparison
Response: `200` + `{ "quote_request_id": ..., "quotes": [ ...Quote ] }`

## POST /sellers
Called by: seller onboarding flow
Body: `{ name, shop_name, category, phone, city, lat?, lng? }`

## GET /sellers/{seller_id}
Response: `200` + Seller object, or `404` if not found

---

## Still open / to confirm with the agent side
- Does the agent need a `chat history` endpoint from us, or does it manage that itself?
- Exact fields the agent needs in `specifications` for spec-based queries (currently free-form dict)
- Whether `PriceHistory` should be written by us (when a seller submits a quote) or by the agent (when it scrapes online prices) — likely **both** write to the same table with different `source` values
