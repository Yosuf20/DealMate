"""
DealMate — mock data contract.

This is what the Supervisor Agent (team leader's side) is expected to
eventually return to the frontend. Build the Jinja templates against
this shape now; when real agent output arrives, only app.py's data
source changes — the templates shouldn't need to.
"""

MOCK_RESULT = {
    "query": {
        "product_name": "Samsung Galaxy S24 Ultra",
        "brand": "Samsung",
        "model": "Galaxy S24 Ultra",
        # answers gathered by the Product Agent's clarifying questions
        "specs_confirmed": {
            "storage": "256GB",
            "color": "Titanium Black",
            "budget_max": 130000
        }
    },

    # CARD 1: Price comparison — lowest-price highlight and chart
    # share this one array so the "big number" is just min(sources.price)
    "price_comparison": {
        "sources": [
            {"store": "Amazon", "price": 124999, "url": "https://amazon.in/dp/example"},
            {"store": "Flipkart", "price": 126999, "url": "https://flipkart.com/item/example"},
            {"store": "Reliance Digital", "price": 129999, "url": "https://reliancedigital.in/example"},
            {"store": "Croma", "price": 128499, "url": "https://croma.com/example"},
            {"store": "Vijay Sales", "price": 127999, "url": "https://vijaysales.com/example"}
        ],
        "lowest_price": 124999,          # derived: min(sources.price)
        "lowest_price_store": "Amazon"   # derived: store with min price
    },

    # CARD 2: General review summary
    "review_summary": {
        "overall_sentiment": "Positive",
        "rating_avg": 4.3,
        "review_count_analyzed": 1250,
        "highlights": [
            "Users love the camera quality and zoom",
            "Battery life praised for all-day use",
            "Some complaints about the price being high"
        ],
        # category-specific fields will vary by product type (electronics shown here)
        "category_specific": {
            "battery": "Excellent, lasts 1.5 days on average use",
            "performance": "Very fast, handles gaming well",
            "build_quality": "Premium titanium frame, durable"
        }
    },

    # CARD 3: Nearest local stores (10km radius)
    "nearby_stores": {
        "user_location": {"pincode": "110025", "lat": 28.5535, "lon": 77.2588},
        "radius_km": 10,
        "stores": [
            {
                "store_name": "Croma - Saket",
                "distance_km": 3.2,
                "price": 128999,
                "quote_status": "received",  # received | pending | not_requested
                "maps_url": "https://maps.google.com/?q=Croma+Saket+Delhi"
            },
            {
                "store_name": "Reliance Digital - Nehru Place",
                "distance_km": 6.8,
                "price": None,
                "quote_status": "pending",   # agent messaged the store, awaiting reply
                "maps_url": "https://maps.google.com/?q=Reliance+Digital+Nehru+Place"
            }
        ]
    },

    # CARD 4: Similar / better-value product suggestion
    "similar_product": {
        "reason": "out_of_stock",  # out_of_stock | better_value | fewer_features_lower_price
        "suggested_product": {
            "name": "Samsung Galaxy S24+",
            "price": 99999,
            "price_difference": -25000,
            "key_differences": [
                "Slightly smaller screen",
                "Same chipset",
                "5000 fewer mAh battery"
            ]
        }
    },

    # CARD 5: Related products
    "related_products": [
        {"name": "Samsung 25W Fast Charger", "price": 1499},
        {"name": "Galaxy S24 Ultra Silicone Case", "price": 1999},
        {"name": "Samsung Galaxy Buds2 Pro", "price": 13999}
    ],

    # CARD 6: Upcoming sales prediction
    "upcoming_sales": [
        {
            "sale_name": "Flipkart Big Billion Days",
            "platform": "Flipkart",
            "expected_start": "2026-10-03",
            "note": "Predicted based on historical timing"
        },
        {
            "sale_name": "Amazon Great Indian Festival",
            "platform": "Amazon",
            "expected_start": "2026-10-05",
            "note": "Predicted based on historical timing"
        }
    ],

    "search_metadata": {
        "search_id": "srch_8f3a2b1c",
        "timestamp": "2026-09-18T10:32:00Z",
        "status": "partial"  # partial (local quotes still pending) | complete
    }
}