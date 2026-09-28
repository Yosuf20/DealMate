"""
find_local_sellers.py

Free, no-API-key local seller discovery using OpenStreetMap:
1. Geocodes location using OSM Nominatim API.
2. Queries nearby shops (electronics, phones, appliances) using OSM Overpass API.
"""

from typing import Any, Dict, List
import requests
from strands import tool

@tool
def find_local_sellers(product_category: str = "electronics", location: str = "Delhi") -> List[Dict[str, Any]]:
    """
    Find nearby offline retail stores and electronic shops using OpenStreetMap.

    Args:
        product_category: Category like "mobile_phone", "electronics", or "appliances".
        location: City or area in India, e.g. "Delhi", "Connaught Place, Delhi", "Mumbai".

    Returns:
        List of shops with seller_name, lat, lon, and phone.
    """
    headers = {"User-Agent": "DealSetu-Hackathon-Agent/1.0"}
    lat, lon = None, None

    # Step 1: Geocoding via Nominatim
    try:
        geo_resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{location}, India", "format": "json", "limit": 1},
            headers=headers,
            timeout=5.0,
        )
        if geo_resp.status_code == 200:
            geo_data = geo_resp.json()
            if geo_data and len(geo_data) > 0:
                lat = float(geo_data[0]["lat"])
                lon = float(geo_data[0]["lon"])
    except requests.RequestException as e:
        raise RuntimeError(f"Nominatim request failed for {location!r}: {e}") from e

    if lat is None or lon is None:
        raise RuntimeError(f"Nominatim returned no coordinates for {location!r}")

    # Step 2: Overpass query for nearby shops within 5km
    try:
        category_filter = "mobile_phone|electronics|computer|appliance|department_store"
        query = f"""
        [out:json][timeout:15];
        (
          node["shop"~"{category_filter}"](around:5000,{lat},{lon});
          way["shop"~"{category_filter}"](around:5000,{lat},{lon});
        );
        out tags center 10;
        """
        overpass_resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            headers=headers,
            timeout=15.0,
        )
        overpass_resp.raise_for_status()
        elements = overpass_resp.json().get("elements", [])
        results = []
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("brand")
            if not name:
                continue
            node_lat = el.get("lat") or el.get("center", {}).get("lat")
            node_lon = el.get("lon") or el.get("center", {}).get("lon")
            phone = tags.get("phone") or tags.get("contact:phone")
            results.append({
                "seller_name": name,
                "lat": node_lat,
                "lon": node_lon,
                "phone": phone,
            })
        return results[:5]
    except requests.RequestException as e:
        raise RuntimeError(f"Overpass request failed for {location!r}: {e}") from e
