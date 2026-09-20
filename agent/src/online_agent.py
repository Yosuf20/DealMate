"""
online_agent.py

Defines the Online Search Agent: a Strands Agent backed by Bedrock, wired
with the online-search tools. Exposed as a plain function so the Supervisor
agent (or a direct test script) can call it without needing to know
Strands internals.
"""

import json
import re

from strands import Agent

from agent.src.prompts.online_prompt import ONLINE_AGENT_SYSTEM_PROMPT
from agent.src.tools.search_online_products import search_online_products
from agent.src.tools.get_product_details import get_product_details
from agent.src.model_provider import get_model


def _build_online_agent() -> Agent:
    model = get_model()
    return Agent(
        model=model,
        system_prompt=ONLINE_AGENT_SYSTEM_PROMPT,
        tools=[search_online_products, get_product_details],
    )


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from the agent's text response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in Online Agent response:\n{text}")
    return json.loads(match.group(0))


def run_online_agent(structured_request: dict) -> dict:
    """
    Run the Online Agent for a given structured product request.

    Args:
        structured_request: e.g.
            {
                "product": "iPhone 16",
                "variant": "128GB",
                "budget": 65000,
                "location": "Delhi",
                "condition": "new"
            }

    Returns:
        Parsed JSON dict matching the shape described in online_prompt.py,
        e.g. {"product": ..., "variant": ..., "offers": [...], "cheapest_price": ..., "notes": ...}
    """
    agent = _build_online_agent()

    prompt = (
        f"Find online offers for this product request:\n"
        f"{json.dumps(structured_request, indent=2)}\n\n"
        f"Remember: once you are done using your tools, write your final answer as a single JSON object matching your instructions. Do not call any tool named 'json' — just write the JSON directly as your text response."
    )

    try:
        response = agent(prompt)
        response_text = str(response)
        return _extract_json(response_text)
    except Exception:
        # Fallback directly to the search tool if LLM response parsing had an issue
        offers = search_online_products(
            structured_request.get("product", ""),
            structured_request.get("variant", ""),
            structured_request.get("budget"),
        )
        valid_prices = [o["price"] for o in offers if o.get("price")]
        cheapest = min(valid_prices) if valid_prices else None
        exact_prices = [o["price"] for o in offers if o.get("price") and o.get("match_type") == "exact"]
        cheapest_exact = min(exact_prices) if exact_prices else None
        return {
            "product": structured_request.get("product"),
            "variant": structured_request.get("variant"),
            "offers": offers,
            "cheapest_price": cheapest,
            "cheapest_exact_price": cheapest_exact,
            "notes": "Online offers retrieved directly across e-commerce platforms.",
        }


if __name__ == "__main__":
    # Quick manual test:
    #   python -m src.agents.online_agent
    test_request = {
        "product": "Fridge",
        "variant": "300 Litres",
        "budget": 50000,
        "location": "Delhi",
        "condition": "new",
    }
    result = run_online_agent(test_request)
    print(json.dumps(result, indent=2))
