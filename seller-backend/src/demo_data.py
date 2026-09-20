"""
demo_data.py

Hand-written sample Seller/Quote records for the DEMO ONLY — mirrors
the stores already referenced in frontend/mock_data.py (Croma - Saket,
Reliance Digital - Nehru Place) so the transition from hardcoded mock
to real backend logic is invisible to anyone watching the demo.

Swap this for real DynamoDB queries later — nothing else changes,
since build_nearby_stores() takes the same Seller/Quote objects either way.
"""

from .db.models import Seller, Quote

# Same product the rest of MOCK_RESULT is built around
DEMO_PRODUCT_NAME = "Samsung Galaxy S24 Ultra"
DEMO_QUOTE_REQUEST_ID = "qr_demo_s24ultra"

DEMO_SELLERS = [
    Seller(
        seller_id="seller_croma_saket",
        name="Store Manager", shop_name="Croma - Saket",
        category="electronics", phone="9999900001", city="Delhi",
        lat=28.5245, lng=77.2066,
    ),
    Seller(
        seller_id="seller_reliance_np",
        name="Store Manager", shop_name="Reliance Digital - Nehru Place",
        category="electronics", phone="9999900002", city="Delhi",
        lat=28.5494, lng=77.2500,
    ),
    Seller(
        seller_id="seller_vijay_gk",
        name="Store Manager", shop_name="Vijay Sales - GK1",
        category="electronics", phone="9999900003", city="Delhi",
        lat=28.5355, lng=77.2410,
    ),
]

# Only Croma has replied so far — Reliance & Vijay Sales are still "pending"
# (this matches the "partial" search_metadata.status already in mock_data.py)
DEMO_QUOTES = [
    Quote(
        quote_request_id=DEMO_QUOTE_REQUEST_ID,
        seller_id="seller_croma_saket",
        product_name=DEMO_PRODUCT_NAME,
        price=128999,
        in_stock=True,
    ),
]

# User's location, matches mock_data.py's nearby_stores.user_location
DEMO_USER_LAT = 28.5535
DEMO_USER_LON = 77.2588
DEMO_USER_PINCODE = "110025"
