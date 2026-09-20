"""
supervisor.py

Supervisor orchestrator for DealSetu.
Coordinates:
1. Product Understanding Agent (converts query to structured request / clarification)
2. Online Search Agent (crawls Amazon, Flipkart, Croma, Reliance Digital)
3. Local Search Agent (discovers nearby stores via OSM & gets local quotes)
4. Compare Deals Engine (scores and ranks all deals deterministically)
5. Activity Log (captures real-time pipeline milestones for UI/CLI display)
"""

from typing import Any, Dict, List, Optional

from agent.src.product_agent import run_product_agent
from agent.src.online_agent import run_online_agent
from agent.src.local_agent import run_local_agent
from agent.src.tools.compare_deals import compare_deals


def _normalize_online_offer(offer: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes an offer from the online agent into the universal comparison shape."""
    source = offer.get("source", "E-Commerce Online")
    return {
        "source": source,
        "type": "online",
        "title": offer.get("title", f"Online listing on {source}"),
        "price": offer.get("price"),
        "url": offer.get("url"),
        "delivery": "Free standard delivery (2-4 business days)",
        "warranty": "1 Year Official Brand Warranty",
        "availability": "in_stock" if offer.get("price") else "out_of_stock",
        "match_type": offer.get("match_type", "unspecified"),
        "detected_spec": offer.get("detected_spec"),
        "notes": offer.get("snippet") or offer.get("notes") or "",
    }


def run_dealsetu(user_query: str, location_override: Optional[str] = None) -> Dict[str, Any]:
    """
    Main orchestration entrypoint for DealSetu.

    Args:
        user_query: Raw natural language query from the shopper, e.g.
                    "iPhone 16 128GB under 65k in Delhi"
        location_override: Optional explicit city/location override.

    Returns:
        Structured result dictionary including best deal, ranked offers,
        price comparison, reasoning, and real-time activity log.
    """
    activity_log: List[str] = []

    # 1. Understand product requirements
    activity_log.append(f"Analyzing shopper request: \"{user_query}\"")
    product_result = run_product_agent(user_query)

    if product_result.get("status") == "needs_clarification":
        question = product_result.get("question", "Could you provide more details about the product and location?")
        activity_log.append(f"Clarification needed: {question}")
        return {
            "status": "needs_clarification",
            "question": question,
            "activity_log": activity_log,
        }

    structured_request = product_result.get("structured_request", {})
    if location_override:
        structured_request["location"] = location_override
    if not structured_request.get("location"):
        structured_request["location"] = "Delhi"

    prod_name = structured_request.get("product", "Product")
    prod_var = structured_request.get("variant") or "Standard"
    budget = structured_request.get("budget")
    loc = structured_request.get("location", "Delhi")

    budget_str = f"under ₹{budget:,}" if budget else "best price"
    activity_log.append(
        f"Understood request: {prod_name} ({prod_var}) {budget_str} in {loc}"
    )

    # 2. Search Online Retailers
    activity_log.append("Searching online stores (Amazon, Flipkart, Croma, Reliance Digital)...")
    try:
        online_result = run_online_agent(structured_request)
        raw_online_offers = online_result.get("offers", [])
        online_offers = [_normalize_online_offer(o) for o in raw_online_offers]
        activity_log.append(
            f"Found {len(online_offers)} online listings across e-commerce platforms."
        )
    except Exception as e:
        activity_log.append(f"Online search encountered an error: {e}")
        online_result = {"offers": [], "notes": f"Error: {e}"}
        online_offers = []

    # 3. Discover Nearby Stores & Fetch Local Quotes
    activity_log.append(f"Finding nearby offline electronics stores & requesting quotes in {loc}...")
    try:
        local_result = run_local_agent(structured_request)
        local_offers = local_result.get("offers", [])
        activity_log.append(
            f"Received {len(local_offers)} local store quotes with same-day/instant availability."
        )
    except Exception as e:
        activity_log.append(f"Local search encountered an error: {e}")
        local_result = {"offers": [], "notes": f"Error: {e}"}
        local_offers = []

    # 4. Compare Deals & Synthesize Best Recommendation
    all_offers = online_offers + local_offers
    activity_log.append(
        f"Evaluating total {len(all_offers)} offers considering price, delivery speed, and warranty..."
    )

    comparison = compare_deals(all_offers)
    best_deal = comparison.get("best_deal")

    if best_deal:
        best_price = f"₹{best_deal['price']:,}" if best_deal.get("price") else "N/A"
        activity_log.append(
            f"Top Deal Selected: {best_deal.get('source')} at {best_price} (Score: {best_deal.get('score')}/100)"
        )
    else:
        activity_log.append("No competitive offers could be verified.")

    return {
        "status": "success",
        "structured_request": structured_request,
        "best_deal": best_deal,
        "reasoning": comparison.get("reasoning", ""),
        "ranked_offers": comparison.get("ranked_offers", []),
        "price_spread": comparison.get("price_spread", {}),
        "summary": comparison.get("summary", {}),
        "online_result": online_result,
        "local_result": local_result,
        "activity_log": activity_log,
    }


if __name__ == "__main__":
    import sys
    import json
    sys.stdout.reconfigure(encoding="utf-8")
    query = "iPhone 16 128GB under 65000 in Delhi"
    print(f"Running DealSetu Supervisor with: '{query}'\n")
    res = run_dealsetu(query)
    print(json.dumps(res, indent=2))
