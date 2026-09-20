"""
compare_deals.py

Deterministic comparison engine for DealSetu.
Evaluates both online and local offers using explainable scoring based on:
1. Price & total effective cost
2. Spec match accuracy (prefers 'exact' over 'close', demotes 'other')
3. Delivery speed & immediacy (instant pickup / same-day vs multi-day shipping)
4. Warranty & buyer confidence
5. Availability (penalizes out-of-stock)

Plain Python - NO LLM calls. Fast, reproducible, and easily testable.
"""

from typing import Any, Dict, List, Optional


def _normalize_availability(avail: Optional[str]) -> str:
    if not avail:
        return "in_stock"
    avail_lower = str(avail).lower()
    if any(term in avail_lower for term in ["out of stock", "unavailable", "sold out"]):
        return "out_of_stock"
    if any(term in avail_lower for term in ["today", "instant", "immediate", "ready"]):
        return "available_today"
    return "in_stock"


def _calculate_deal_score(
    offer: Dict[str, Any],
    min_price: int,
    max_price: int,
) -> tuple[float, Dict[str, Any]]:
    """
    Computes a composite score (0 to 100) and factor breakdown for an offer.
    """
    price = offer.get("price")
    match_type = str(offer.get("match_type", "unspecified")).lower()
    avail = _normalize_availability(offer.get("availability"))
    delivery = str(offer.get("delivery", "")).lower()
    warranty = str(offer.get("warranty", "")).lower()
    source_type = offer.get("type", "online")

    # 1. Spec match points (max 25)
    spec_points = 25.0
    if match_type == "exact":
        spec_points = 25.0
    elif match_type == "close":
        spec_points = 18.0
    elif match_type == "unspecified":
        spec_points = 15.0
    else:  # "other"
        spec_points = 0.0

    # 2. Price points (max 45)
    price_points = 0.0
    if price is not None and price > 0:
        if max_price == min_price:
            price_points = 45.0
        else:
            # Linear score from 45 (cheapest) down to 15 (most expensive)
            ratio = (price - min_price) / max((max_price - min_price), 1)
            price_points = max(10.0, 45.0 - (ratio * 35.0))

    # 3. Delivery & convenience points (max 20)
    delivery_points = 10.0
    if avail == "out_of_stock":
        delivery_points = 0.0
    elif (
        avail == "available_today"
        or "instant" in delivery
        or "today" in delivery
        or "pickup" in delivery
        or "same day" in delivery
    ):
        # Local instant pickup / same day advantage
        delivery_points = 20.0
    elif "next day" in delivery or "1 day" in delivery:
        delivery_points = 15.0
    elif "free" in delivery:
        delivery_points = 12.0

    # 4. Warranty & confidence points (max 10)
    warranty_points = 5.0
    if any(k in warranty for k in ["brand", "manufacturer", "official", "apple", "samsung"]):
        warranty_points = 10.0
    elif any(k in warranty for k in ["year", "yr", "dealer"]):
        warranty_points = 8.0
    elif warranty:
        warranty_points = 6.0

    # Penalty for out of stock or other spec
    penalty = 0.0
    if avail == "out_of_stock":
        penalty += 40.0
    if match_type == "other":
        penalty += 30.0

    total_score = max(0.0, round(spec_points + price_points + delivery_points + warranty_points - penalty, 1))

    breakdown = {
        "spec_match_pts": spec_points,
        "price_pts": round(price_points, 1),
        "delivery_pts": delivery_points,
        "warranty_pts": warranty_points,
        "penalty": penalty,
    }

    return total_score, breakdown


def _generate_reasoning(
    best_offer: Dict[str, Any],
    all_offers: List[Dict[str, Any]],
    cheapest_offer: Optional[Dict[str, Any]],
) -> str:
    """Generates concise, human-readable reasoning explaining why the best deal was chosen."""
    if not best_offer:
        return "No valid offers were found matching your criteria."

    best_source = best_offer.get("source", "Unknown Seller")
    best_price = best_offer.get("price")
    best_type = best_offer.get("type", "online")
    best_delivery = best_offer.get("delivery", "Standard delivery")
    best_warranty = best_offer.get("warranty", "Standard warranty")
    best_match = best_offer.get("match_type", "exact")

    price_str = f"₹{best_price:,}" if best_price else "Price on inquiry"

    reasons = []

    if best_match == "exact":
        reasons.append("Exact variant specification match.")
    elif best_match == "close":
        detected = best_offer.get("detected_spec")
        reasons.append(f"Close specification match ({detected or 'variant alternative'}).")

    if cheapest_offer and best_offer == cheapest_offer:
        reasons.append(f"Lowest price available across all online and local sources ({price_str}).")
    elif cheapest_offer and cheapest_offer.get("price") and best_price:
        diff = best_price - cheapest_offer["price"]
        cheapest_src = cheapest_offer.get("source", "another seller")
        reasons.append(
            f"Offered at {price_str}, which is just ₹{diff:,} over the absolute lowest online price "
            f"at {cheapest_src} (₹{cheapest_offer['price']:,}), but offers superior advantages."
        )

    if best_type == "local":
        if any(term in str(best_delivery).lower() for term in ["today", "instant", "pickup", "same day"]):
            reasons.append(f"Local advantage: {best_delivery} without shipping wait or courier risk.")
    else:
        reasons.append(f"Online convenience with reliable fulfillment ({best_delivery}).")

    if best_warranty:
        reasons.append(f"Includes {best_warranty}.")

    explanation = (
        f"Recommended Deal: {best_source} ({best_type.capitalize()}) at {price_str}. "
        + " ".join(reasons)
    )
    return explanation


def compare_deals(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Takes a combined list of offers (online + local quotes, both normalized
    to the same shape: price, source, delivery, warranty, availability,
    match_type), scores them considering price + delivery cost + warranty +
    availability + match quality (prefer 'exact' over 'close' spec matches),
    and returns the single best deal plus a ranked list and the reasoning.

    Returns:
        {
            "best_deal": dict or None,
            "ranked_offers": list[dict],
            "reasoning": str,
            "price_spread": {
                "min": int or None,
                "max": int or None,
                "diff": int or None,
            },
            "summary": {
                "total_offers": int,
                "online_count": int,
                "local_count": int,
                "exact_matches": int,
            }
        }
    """
    if not offers:
        return {
            "best_deal": None,
            "ranked_offers": [],
            "reasoning": "No offers available to compare.",
            "price_spread": {"min": None, "max": None, "diff": None},
            "summary": {
                "total_offers": 0,
                "online_count": 0,
                "local_count": 0,
                "exact_matches": 0,
            },
        }

    # Extract valid prices for normalization
    valid_prices = [
        o["price"]
        for o in offers
        if o.get("price") is not None and isinstance(o.get("price"), (int, float)) and o["price"] > 0
    ]

    min_price = min(valid_prices) if valid_prices else 0
    max_price = max(valid_prices) if valid_prices else 0

    scored_offers = []
    cheapest_offer = None

    for offer in offers:
        # Create a clean normalized copy
        clean_offer = dict(offer)
        score, breakdown = _calculate_deal_score(clean_offer, min_price, max_price)
        clean_offer["score"] = score
        clean_offer["score_breakdown"] = breakdown
        scored_offers.append(clean_offer)

        # Track cheapest offer among exact/close matches that are in stock
        p = clean_offer.get("price")
        if p and p > 0 and clean_offer.get("match_type") in ["exact", "close"]:
            if cheapest_offer is None or p < cheapest_offer["price"]:
                cheapest_offer = clean_offer

    # Sort offers:
    # 1. Higher score first
    # 2. Prefer exact match
    # 3. Lower price
    scored_offers.sort(
        key=lambda o: (
            -o.get("score", 0),
            0 if o.get("match_type") == "exact" else 1,
            o.get("price") or 999999999,
        )
    )

    best_deal = scored_offers[0] if scored_offers else None
    reasoning = _generate_reasoning(best_deal, scored_offers, cheapest_offer)

    online_count = sum(1 for o in scored_offers if o.get("type") == "online")
    local_count = sum(1 for o in scored_offers if o.get("type") == "local")
    exact_matches = sum(1 for o in scored_offers if o.get("match_type") == "exact")

    return {
        "best_deal": best_deal,
        "ranked_offers": scored_offers,
        "reasoning": reasoning,
        "price_spread": {
            "min": min_price if valid_prices else None,
            "max": max_price if valid_prices else None,
            "diff": (max_price - min_price) if valid_prices else None,
        },
        "summary": {
            "total_offers": len(scored_offers),
            "online_count": online_count,
            "local_count": local_count,
            "exact_matches": exact_matches,
        },
    }
