"""
Run with: pytest seller-backend/tests/test_nearby_stores.py

Uses sample Seller/Quote objects directly (no AWS) to prove the
translation logic produces the exact shape frontend expects.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.models import Seller, Quote  # noqa: E402
from src.services.nearby_stores import build_nearby_stores, haversine_km  # noqa: E402


# Delhi-ish coordinates for realistic demo distances
USER_LAT, USER_LON = 28.5535, 77.2588  # near Saket, Delhi

SAMPLE_SELLERS = [
    Seller(name="Ramesh", shop_name="Croma - Saket", category="electronics",
           phone="9999999999", city="Delhi", lat=28.5245, lng=77.2066),
    Seller(name="Suresh", shop_name="Reliance Digital - Nehru Place", category="electronics",
           phone="9888888888", city="Delhi", lat=28.5494, lng=77.2500),
    Seller(name="Far Away Seller", shop_name="Out of Range Store", category="electronics",
           phone="9777777777", city="Delhi", lat=29.5, lng=78.5),  # way outside 10km
]


def test_distance_calculation_sane():
    # Saket to Nehru Place is roughly 6-7km in real life
    d = haversine_km(USER_LAT, USER_LON, 28.5494, 77.2500)
    assert 0 < d < 15


def test_out_of_range_store_excluded():
    result = build_nearby_stores(
        USER_LAT, USER_LON, "110025",
        sellers=SAMPLE_SELLERS, quotes=[], radius_km=10.0,
    )
    names = [s["store_name"] for s in result["stores"]]
    assert "Out of Range Store" not in names


def test_seller_with_quote_shows_received():
    quote = Quote(
        quote_request_id="qr_test1", seller_id=SAMPLE_SELLERS[0].seller_id,
        product_name="Samsung Galaxy S24 Ultra", price=128999, in_stock=True,
    )
    result = build_nearby_stores(
        USER_LAT, USER_LON, "110025",
        sellers=SAMPLE_SELLERS, quotes=[quote], quote_request_id="qr_test1",
    )
    croma = next(s for s in result["stores"] if s["store_name"] == "Croma - Saket")
    assert croma["quote_status"] == "received"
    assert croma["price"] == 128999


def test_seller_without_quote_shows_pending():
    result = build_nearby_stores(
        USER_LAT, USER_LON, "110025",
        sellers=SAMPLE_SELLERS, quotes=[], radius_km=10.0,
    )
    croma = next(s for s in result["stores"] if s["store_name"] == "Croma - Saket")
    assert croma["quote_status"] == "pending"
    assert croma["price"] is None


def test_stores_sorted_by_distance():
    result = build_nearby_stores(
        USER_LAT, USER_LON, "110025",
        sellers=SAMPLE_SELLERS, quotes=[], radius_km=10.0,
    )
    distances = [s["distance_km"] for s in result["stores"]]
    assert distances == sorted(distances)


def test_shape_matches_mock_data_contract():
    """Confirms the output has exactly the keys frontend/mock_data.py expects."""
    result = build_nearby_stores(
        USER_LAT, USER_LON, "110025",
        sellers=SAMPLE_SELLERS, quotes=[], radius_km=10.0,
    )
    assert set(result.keys()) == {"user_location", "radius_km", "stores"}
    assert set(result["user_location"].keys()) == {"pincode", "lat", "lon"}
    for store in result["stores"]:
        assert set(store.keys()) == {"store_name", "distance_km", "price", "quote_status", "maps_url"}
