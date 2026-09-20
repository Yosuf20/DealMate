"""
Run with: pytest seller-backend/tests/test_models.py

These only test the Pydantic models — no AWS needed, so they work
fine from a Codespace or any machine with just `pip install pydantic pytest`.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.models import (  # noqa: E402
    Seller, QuoteRequest, Quote, ProductCatalog, PriceHistory,
)


def test_seller_defaults():
    s = Seller(name="Ramesh", shop_name="Ramesh Electronics",
                category="electronics", phone="9999999999", city="Delhi")
    assert s.seller_id.startswith("seller_")
    assert s.is_active is True


def test_quote_request_roundtrip():
    qr = QuoteRequest(product_name="iPhone 15", category="electronics",
                       specifications={"storage": "128GB"})
    data = qr.model_dump()
    qr2 = QuoteRequest(**data)
    assert qr2.product_name == "iPhone 15"


def test_quote_requires_quote_request_id():
    q = Quote(quote_request_id="qr_abc123", seller_id="seller_xyz",
              product_name="iPhone 15", price=64999, in_stock=True)
    assert q.price == 64999
    assert q.currency == "INR"


def test_product_catalog_defaults_source():
    p = ProductCatalog(product_name="Nike Air Max", category="shoes")
    assert p.source == "cache"


def test_price_history_requires_product_id():
    ph = PriceHistory(product_id="prod_123", source="online:amazon", price=4999)
    assert ph.price == 4999
