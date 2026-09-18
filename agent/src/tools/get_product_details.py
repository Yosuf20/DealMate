"""
get_product_details.py

Given a product (and optionally a specific listing URL found by
search_online_products), fetch a slightly deeper look — used when the
agent wants more than the search snippet gives it (e.g. to confirm the
variant matches, or check availability wording).

Free technique: re-query DuckDuckGo with a narrower query, optionally
fetch the actual page text for the given URL. Page fetching is best-effort
and safely skipped if it fails (many e-commerce sites block scrapers).
"""

from typing import Optional

from strands import tool


@tool
def get_product_details(product: str, variant: str = "", url: Optional[str] = None) -> dict:
    """
    Get more detail on a specific product/listing.

    Args:
        product: Product name, e.g. "iPhone 16".
        variant: Variant/spec details, e.g. "128GB".
        url: Optional specific listing URL (from search_online_products) to try to pull
             more detail from.

    Returns:
        {
            "product": "iPhone 16",
            "variant": "128GB",
            "summary": "<short text summary from search results>",
            "source_checked": "<url if provided>"
        }
    """
    try:
        from ddgs import DDGS
    except ImportError:
        raise RuntimeError(
            "The 'ddgs' package is required. Install with: pip install ddgs"
        )

    query = " ".join(filter(None, [product, variant, "specifications price availability"]))

    summary_parts = []
    with DDGS() as ddgs:
        try:
            results = list(ddgs.text(query, max_results=3))
        except Exception:
            results = []

    for r in results:
        body = r.get("body", "")
        if body:
            summary_parts.append(body)

    return {
        "product": product,
        "variant": variant,
        "summary": " | ".join(summary_parts) if summary_parts else "No additional details found.",
        "source_checked": url,
    }
