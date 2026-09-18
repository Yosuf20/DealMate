"""
search_online_products.py

Free, no-API-key technique for finding online prices:
We use DuckDuckGo web search (via the `ddgs` package) scoped to major
Indian e-commerce domains, then extract price-looking snippets from the
result text. This avoids needing paid e-commerce APIs (Amazon/Flipkart
partner APIs require approval) while still returning real, current
search-result data.

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


def _extract_price(text: str) -> Optional[int]:
    """Pull the first plausible price out of a snippet of text."""
    match = PRICE_PATTERN.search(text)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


@tool
def search_online_products(product: str, variant: str = "", budget: Optional[float] = None) -> list[dict]:
    """
    Search online e-commerce stores for a product and return candidate offers.

    Args:
        product: The product name, e.g. "iPhone 16".
        variant: Variant/spec details, e.g. "128GB".
        budget: Optional max budget in INR, used only to prioritize relevant results.

    Returns:
        A list of offers, each shaped like:
        {
            "source": "amazon.in",
            "title": "<result title>",
            "price": 61999,          # int, or None if a price couldn't be extracted
            "url": "<result link>",
            "snippet": "<raw text used for extraction>"
        }
    """
    try:
        from ddgs import DDGS
    except ImportError:
        raise RuntimeError(
            "The 'ddgs' package is required. Install with: pip install ddgs"
        )

    query_terms = " ".join(filter(None, [product, variant, "price india"]))
    offers = []

    with DDGS() as ddgs:
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

    # Sort: offers with a detected price first (cheapest first), undetected prices last
    offers.sort(key=lambda o: (o["price"] is None, o["price"] or 0))
    return offers
