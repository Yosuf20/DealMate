"""
search_online_products.py

Free, no-API-key technique for finding online prices:
We use DuckDuckGo web search (via the `ddgs` package) scoped to major
Indian e-commerce domains, then extract price-looking snippets from the
result text. This avoids needing paid e-commerce APIs (Amazon/Flipkart
partner APIs require approval) while still returning real, current
search-result data.

Spec-matching behaviour:
Exact requested specs (e.g. "300L", "128GB") are often out of stock in
practice. So this tool:
  1. Searches for the exact requested spec first.
  2. If too few exact matches come back, automatically broadens the search
     (drops the exact number from the query) and classifies each result as
     "exact", "close" (within tolerance of the requested number), or
     "other" (spec doesn't match / couldn't be determined).
This lets the agent tell the user "300L wasn't available, but here's 331L
and 321L which are close" instead of silently returning nothing.

Install:
    pip install ddgs
"""

import re
from typing import Optional

from strands import tool

# Domains we scope the search to. Add/remove as needed for the demo.
ECOMMERCE_SITES = [
    "amazon.in",
    "flipkart.com",
    "croma.com",
    "reliancedigital.in",
]

# Matches Indian rupee amounts like "₹58,900", "Rs. 58999", "58,900"
PRICE_PATTERN = re.compile(r"(?:₹|Rs\.?\s?)\s?([\d,]{4,})")

# Matches a number + unit like "300L", "331 Litre", "128GB", "1.5 Ton"
SPEC_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(L|Litre|Litres|GB|TB|KG|Kg|Inch|Inches|inch|ML|Ton|Tons)\b",
    re.IGNORECASE,
)

# How far a found spec can be from the requested spec to still count as "close"
CLOSE_TOLERANCE_PCT = 0.15  # ±15%
MIN_EXACT_RESULTS = 2       # if we have fewer exact matches than this, broaden the search


def _extract_price(text: str) -> Optional[int]:
    """Pull the first plausible price out of a snippet of text."""
    match = PRICE_PATTERN.search(text)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _extract_spec(text: str) -> Optional[tuple]:
    """Pull the first number+unit spec out of a snippet of text, e.g. (331.0, 'l')."""
    match = SPEC_PATTERN.search(text)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower().rstrip("s")  # normalize "litres"/"Litre" -> "litre"
    unit = {"l": "l", "litre": "l"}.get(unit, unit)  # normalize litre variants to "l"
    return (value, unit)


def _classify_match(requested: Optional[tuple], found: Optional[tuple]) -> tuple:
    """
    Compare a found spec against the requested spec.
    Returns (match_type, detected_spec_str).
    """
    if found is None:
        return ("unspecified", None)

    detected_str = f"{found[0]:g}{found[1].upper()}"

    if requested is None:
        return ("unspecified", detected_str)

    if requested[1] != found[1]:
        return ("other", detected_str)

    if requested[0] == found[0]:
        return ("exact", detected_str)

    tolerance = requested[0] * CLOSE_TOLERANCE_PCT
    if abs(requested[0] - found[0]) <= tolerance:
        return ("close", detected_str)

    return ("other", detected_str)


def _run_search(ddgs, product: str, variant: str) -> list[dict]:
    """Run one search pass across all configured sites and return raw offers."""
    query_terms = " ".join(filter(None, [product, variant, "price india"]))
    offers = []

    for site in ECOMMERCE_SITES:
        query = f"site:{site} {query_terms}"
        try:
            results = list(ddgs.text(query, max_results=3))
        except Exception:
            # Don't let one site's failure kill the whole search
            continue

        for r in results:
            title = r.get("title", "")
            snippet = r.get("body", "")
            url = r.get("href", "")
            price = _extract_price(snippet) or _extract_price(title)

            offers.append({
                "source": site,
                "title": title,
                "price": price,
                "url": url,
                "snippet": snippet,
            })

    return offers


@tool
def search_online_products(product: str, variant: str = "", budget: Optional[float] = None) -> list[dict]:
    """
    Search online e-commerce stores for a product and return candidate offers.

    Automatically falls back to nearby specs if the exact requested spec
    (e.g. "300L", "128GB") doesn't return enough results in stock, so the
    caller can still surface a usable alternative to the user.

    Args:
        product: The product name, e.g. "Refrigerator" or "iPhone 16".
        variant: Variant/spec details, e.g. "300L" or "128GB".
        budget: Optional max budget in INR, used only to prioritize relevant results.

    Returns:
        A list of offers, each shaped like:
        {
            "source": "amazon.in",
            "title": "<result title>",
            "price": 61999,             # int, or None if a price couldn't be extracted
            "url": "<result link>",
            "snippet": "<raw text used for extraction>",
            "match_type": "exact" | "close" | "other" | "unspecified",
            "detected_spec": "331L"     # the spec actually found in the listing, or None
        }
        Sorted so exact matches come first, then close matches, then others,
        each group sorted by price ascending.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        raise RuntimeError(
            "The 'ddgs' package is required. Install with: pip install ddgs"
        )

    requested_spec = _extract_spec(variant) if variant else None

    with DDGS() as ddgs:
        offers = _run_search(ddgs, product, variant)

        for o in offers:
            match_type, detected = _classify_match(requested_spec, _extract_spec(o["title"]) or _extract_spec(o["snippet"]))
            o["match_type"] = match_type
            o["detected_spec"] = detected

        exact_with_price = [o for o in offers if o["match_type"] == "exact" and o["price"] is not None]

        # Not enough exact matches -> broaden the search by dropping the exact
        # number from the query, so we pick up nearby-spec listings too.
        if requested_spec is not None and len(exact_with_price) < MIN_EXACT_RESULTS:
            broadened_offers = _run_search(ddgs, product, "")  # search without the exact spec constraint
            seen_urls = {o["url"] for o in offers}

            for o in broadened_offers:
                if o["url"] in seen_urls:
                    continue
                match_type, detected = _classify_match(requested_spec, _extract_spec(o["title"]) or _extract_spec(o["snippet"]))
                o["match_type"] = match_type
                o["detected_spec"] = detected
                offers.append(o)
                seen_urls.add(o["url"])

    match_rank = {"exact": 0, "close": 1, "unspecified": 2, "other": 3}
    offers.sort(key=lambda o: (
        match_rank.get(o["match_type"], 4),
        o["price"] is None,
        o["price"] or 0,
    ))
    return offers

