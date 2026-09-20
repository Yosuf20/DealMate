import sys
import os

# seller-backend has a hyphen in its folder name, so it can't be imported
# as a normal Python package — add it to the path directly instead.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "seller-backend"))

from flask import Flask, render_template
from mock_data import MOCK_RESULT
from src.services.nearby_stores import build_nearby_stores
from src.demo_data import (
    DEMO_SELLERS, DEMO_QUOTES, DEMO_USER_LAT, DEMO_USER_LON,
    DEMO_USER_PINCODE, DEMO_QUOTE_REQUEST_ID,
)

app = Flask(__name__)


def process_result(result):
    pc = result["price_comparison"]
    pc["sources"].sort(key=lambda s: s["price"])
    for index, source in enumerate(pc["sources"]):
        source["is_best"] = index == 0
        source["price_formatted"] = f"₹{source['price']:,}"

    pc["lowest_price"] = pc["sources"][0]["price"]
    pc["lowest_price_store"] = pc["sources"][0]["store"]
    pc["lowest_price_formatted"] = f"₹{pc['lowest_price']:,}"

    rs = result["review_summary"]
    full_stars = round(rs["rating_avg"])
    rs["stars_full"] = full_stars
    rs["stars_empty"] = 5 - full_stars

    # --- real seller-backend logic replaces the hardcoded nearby_stores ---
    result["nearby_stores"] = build_nearby_stores(
        DEMO_USER_LAT, DEMO_USER_LON, DEMO_USER_PINCODE,
        sellers=DEMO_SELLERS, quotes=DEMO_QUOTES,
        quote_request_id=DEMO_QUOTE_REQUEST_ID,
    )

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
    # TODO: Supervisor Agent replaces this with a real call,
    # e.g. raw_result = call_supervisor_agent(query)
    raw_result = MOCK_RESULT
    result = process_result(raw_result)
    return render_template("results.html", result=result)


if __name__ == "__main__":
    app.run(debug=True)
