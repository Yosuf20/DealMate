from flask import Flask, render_template
from mock_data import MOCK_RESULT

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