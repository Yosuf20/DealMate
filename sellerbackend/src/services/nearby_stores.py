"""
nearby_stores.py

Turns your Seller + Quote records into the exact `nearby_stores` shape
that frontend/mock_data.py's MOCK_RESULT expects:

    {
        "user_location": {"pincode": ..., "lat": ..., "lon": ...},
        "radius_km": 10,
        "stores": [
            {
                "store_name": ...,
                "distance_km": ...,
                "price": ... or None,
                "quote_status": "received" | "pending" | "not_requested",
                "maps_url": ...,
            },
            ...
        ]
    }

Works entirely on local Python objects right now — no DynamoDB/AWS
needed. Swap `sellers`/`quotes` for real DB queries later; nothing
else about this function needs to change.
"""

from __future__ import annotations
from math import radians, sin, cos, sqrt, atan2
from typing import List, Optional
from urllib.parse import quote as url_quote

from ..db.models import Seller, Quote


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance between two lat/lon points, in km."""
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return round(R * c, 1)


def maps_url_for(seller: Seller) -> str:
    query = url_quote(f"{seller.shop_name} {seller.city}")
    return f"https://maps.google.com/?q={query}"


def build_nearby_stores(
    user_lat: float,
    user_lon: float,
    user_pincode: str,
    sellers: List[Seller],
    quotes: List[Quote],
    quote_request_id: Optional[str] = None,
    radius_km: float = 10.0,
) -> dict:
    """
    sellers: sellers in the relevant category (you filter this upstream,
             e.g. by category == quote_request.category)
    quotes:  all Quote records for the current quote_request_id
    quote_request_id: if given, only quotes matching this id count as
             "received" — otherwise any quote for that seller counts
    """
    quotes_by_seller = {}
    for q in quotes:
        if quote_request_id is None or q.quote_request_id == quote_request_id:
            quotes_by_seller[q.seller_id] = q

    stores = []
    for seller in sellers:
        if seller.lat is None or seller.lng is None:
            continue  # can't compute distance without coordinates

        distance = haversine_km(user_lat, user_lon, seller.lat, seller.lng)
        if distance > radius_km:
            continue

        quote = quotes_by_seller.get(seller.seller_id)
        stores.append({
            "store_name": seller.shop_name,
            "distance_km": distance,
            "price": quote.price if quote else None,
            "quote_status": "received" if quote else "pending",
            "maps_url": maps_url_for(seller),
        })

    stores.sort(key=lambda s: s["distance_km"])

    return {
        "user_location": {"pincode": user_pincode, "lat": user_lat, "lon": user_lon},
        "radius_km": radius_km,
        "stores": stores,
    }
