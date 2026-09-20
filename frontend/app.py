import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Make both application packages importable when this file is started directly.
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "seller-backend"))

from flask import Flask, render_template, request
from sellerbackend.src.services.nearby_stores import build_nearby_stores
from sellerbackend.src.demo_data import (
    DEMO_SELLERS, DEMO_QUOTES, DEMO_USER_LAT, DEMO_USER_LON,
    DEMO_USER_PINCODE, DEMO_QUOTE_REQUEST_ID,
)
from agent.src.supervisor import run_dealsetu

app = Flask(__name__)


def process_result(agent_result):
    """Adapt the supervisor response to the data shape used by the cards."""
    request_data = agent_result.get("structured_request", {})
    offers = [
        offer for offer in agent_result.get("ranked_offers", [])
        if isinstance(offer.get("price"), (int, float)) and offer["price"] > 0
    ]
    sources = [
        {
            "store": offer.get("source", "Unknown seller").replace("local: ", ""),
            "price": offer["price"],
            "url": offer.get("url", "#"),
        }
        for offer in offers
    ]
    sources.sort(key=lambda source: source["price"])
    for index, source in enumerate(sources):
        source["is_best"] = index == 0
        source["price_formatted"] = f"₹{source['price']:,}"

    lowest_price = sources[0]["price"] if sources else None
    local_offers = [offer for offer in offers if offer.get("type") == "local"]
    nearby_stores = []
    for offer in local_offers:
        store_name = offer.get("seller_name") or offer.get("source", "Local store").replace("local: ", "")
        nearby_stores.append({
            "store_name": store_name,
            "distance_km": "nearby",
            "price": offer.get("price"),
            "quote_status": "received" if offer.get("price") else "pending",
            "maps_url": "https://www.google.com/maps/search/?api=1&query=" + store_name.replace(" ", "+"),
        })

    alternative = next(
        (
            offer for offer in offers
            if offer.get("match_type") in {"close", "other"}
        ),
        None,
    )
    if alternative:
        alternative_name = alternative.get("title") or request_data.get("product", "Alternative product")
        alternative_spec = alternative.get("detected_spec")
        differences = [
            f"Listing specification: {alternative_spec}" if alternative_spec else "Different specification from your request",
            f"Available from {alternative.get('source', 'another seller')}",
        ]
        similar_product = {
            "reason": "close_match" if alternative.get("match_type") == "close" else "alternative_match",
            "suggested_product": {
                "name": alternative_name,
                "price": alternative.get("price"),
                "price_difference": (alternative.get("price") or 0) - (lowest_price or alternative.get("price") or 0),
                "key_differences": differences,
            },
        }
    else:
        similar_product = None

    result = {
        "query": {
            "product_name": request_data.get("product", "Product"),
            "brand": "",
            "model": request_data.get("variant", ""),
            "specs_confirmed": request_data,
        },
        "price_comparison": {
            "sources": sources,
            "lowest_price": lowest_price,
            "lowest_price_store": sources[0]["store"] if sources else "No verified offer",
            "lowest_price_formatted": f"₹{lowest_price:,}" if lowest_price else "N/A",
        },
        "review_summary": {
            "overall_sentiment": "Deal analysis",
            "rating_avg": 0,
            "review_count_analyzed": 0,
            "highlights": [agent_result.get("reasoning", "No review data was returned.")],
            "category_specific": {},
        },
        "nearby_stores": {
            "user_location": {"pincode": "", "lat": 0, "lon": 0},
            "radius_km": 10,
            "stores": nearby_stores,
        },
        "similar_product": similar_product,
        "related_products": [],
        "upcoming_sales": [],
    }

    # Keep the seller demo available only when the agent returned no local offers.
    if not nearby_stores:
        result["nearby_stores"] = build_nearby_stores(
            DEMO_USER_LAT, DEMO_USER_LON, DEMO_USER_PINCODE,
            sellers=DEMO_SELLERS, quotes=DEMO_QUOTES,
            quote_request_id=DEMO_QUOTE_REQUEST_ID,
        )

    full_stars = round(result["review_summary"]["rating_avg"])
    result["review_summary"]["stars_full"] = full_stars
    result["review_summary"]["stars_empty"] = 5 - full_stars
    return result


@app.route("/")
def index():
    # TODO: this will become a form that collects the product query
    # + the Product Agent's clarifying-question answers
    return render_template("index.html")

@app.route("/searching")
def searching():
    return render_template("loading.html")

@app.route("/results")
def results():
    query = request.args.get("query", "").strip()
    if not query:
        return render_template("index.html", error="Enter a product to search.")

    raw_result = run_dealsetu(query)
    if raw_result.get("status") == "needs_clarification":
        return render_template(
            "index.html",
            query=query,
            error=raw_result.get("question", "Please add more product details."),
        )

    result = process_result(raw_result)
    return render_template("results.html", result=result)


if __name__ == "__main__":
    app.run(debug=True)
