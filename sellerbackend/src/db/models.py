"""
DynamoDB table models for the DealSetu seller-backend.

Each class = one DynamoDB table. Keep fields flat where possible —
DynamoDB doesn't like deeply nested objects for querying/indexing.

Tables:
    Seller          - registered local sellers
    QuoteRequest    - a request from the agent asking for quotes
    Quote           - a seller's response to a QuoteRequest
    ProductCatalog  - fallback product data when live scraping fails
    PriceHistory    - price snapshots over time (per product/seller)
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Seller
# ---------------------------------------------------------------------------
class Seller(BaseModel):
    seller_id: str = Field(default_factory=lambda: new_id("seller"))
    name: str
    shop_name: str
    category: str  # electronics, shoes, cosmetics, etc.
    phone: str
    city: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_active: bool = True
    created_at: str = Field(default_factory=now_iso)


# ---------------------------------------------------------------------------
# QuoteRequest  (matches shared/schemas/product_request.json)
# ---------------------------------------------------------------------------
class QuoteRequest(BaseModel):
    quote_request_id: str = Field(default_factory=lambda: new_id("qr"))
    product_name: str
    category: str
    specifications: Dict[str, Any] = Field(default_factory=dict)
    user_city: Optional[str] = None
    max_price: Optional[float] = None
    created_at: str = Field(default_factory=now_iso)


# ---------------------------------------------------------------------------
# Quote  (matches shared/schemas/seller_quote.json)
# ---------------------------------------------------------------------------
class Quote(BaseModel):
    quote_id: str = Field(default_factory=lambda: new_id("quote"))
    quote_request_id: str
    seller_id: str
    product_name: str
    price: float
    currency: str = "INR"
    in_stock: bool
    quantity_available: int = 0
    notes: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)


# ---------------------------------------------------------------------------
# ProductCatalog — fallback when live scraping returns nothing
# ---------------------------------------------------------------------------
class ProductCatalog(BaseModel):
    product_id: str = Field(default_factory=lambda: new_id("prod"))
    product_name: str
    category: str
    brand: Optional[str] = None
    last_known_price: Optional[float] = None
    source: str = "cache"  # "cache" | "scrape" | "manual"
    updated_at: str = Field(default_factory=now_iso)


# ---------------------------------------------------------------------------
# PriceHistory — for the price-history / visualization feature
# ---------------------------------------------------------------------------
class PriceHistory(BaseModel):
    history_id: str = Field(default_factory=lambda: new_id("ph"))
    product_id: str
    source: str  # e.g. "online:amazon", "local:seller_xxx"
    price: float
    recorded_at: str = Field(default_factory=now_iso)
