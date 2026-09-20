"""
product_agent.py

Defines the Product Understanding Agent for DealSetu.
Converts raw natural language shopping queries into structured product requests
or flags when clarification is needed.
"""

import json
import re
from typing import Any, Dict

from strands import Agent

from agent.src.model_provider import get_model
from agent.src.prompts.product_prompt import PRODUCT_AGENT_SYSTEM_PROMPT


def _build_product_agent() -> Agent:
    model = get_model()
    return Agent(
        model=model,
        system_prompt=PRODUCT_AGENT_SYSTEM_PROMPT,
        tools=[],
    )


def _extract_json(text: str) -> Dict[str, Any]:
    """Best-effort extraction of a JSON object from the agent's text response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in Product Agent response:\n{text}")
    return json.loads(match.group(0))


def run_product_agent(user_query: str) -> Dict[str, Any]:
    """
    Run the Product Agent to understand the user's shopping query.

    Args:
        user_query: Raw natural language string from the user, e.g.
                    "iPhone 16 128GB under 65k in Delhi"

    Returns:
        Dict matching either:
        {
            "status": "ready",
            "structured_request": {
                "product": "iPhone 16",
                "variant": "128GB",
                "budget": 65000,
                "location": "Delhi",
                "condition": "new"
            }
        }
        or:
        {
            "status": "needs_clarification",
            "question": "..."
        }
    """
    agent = _build_product_agent()

    prompt = (
        f"Parse this user shopping request and respond with the required JSON structure:\n"
        f"User Query: {user_query}\n\n"
        f"Remember: write your answer directly as a single JSON object."
    )

    response = agent(prompt)
    response_text = str(response)

    return _extract_json(response_text)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    test_query = "iPhone 16 128GB under 65k in Delhi"
    print(f"Testing Product Agent with query: {test_query}")
    res = run_product_agent(test_query)
    print(json.dumps(res, indent=2))
