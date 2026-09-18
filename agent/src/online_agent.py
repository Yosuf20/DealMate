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
from strands.models import BedrockModel

from src.prompts.online_prompt import ONLINE_AGENT_SYSTEM_PROMPT
from src.tools.online_tools.search_online_products import search_online_products
from src.tools.online_tools.get_product_details import get_product_details
from src import config


def _build_online_agent() -> Agent:
    model = BedrockModel(
        model_id=config.BEDROCK_MODEL_ID,
        region_name=config.AWS_REGION,
    )
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
        f"Remember: respond ONLY with the JSON object described in your instructions."
    )

    response = agent(prompt)
    response_text = str(response)

    return _extract_json(response_text)


if __name__ == "__main__":
    # Quick manual test:
    #   python -m src.agents.online_agent
    test_request = {
        "product": "iPhone 16",
        "variant": "128GB",
        "budget": 65000,
        "location": "Delhi",
        "condition": "new",
    }
    result = run_online_agent(test_request)
    print(json.dumps(result, indent=2))
