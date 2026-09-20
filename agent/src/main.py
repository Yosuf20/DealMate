"""
main.py

Local CLI entrypoint for DealSetu AI Shopping Assistant.
Runs the complete multi-agent pipeline:
Product Agent -> Online Search Agent -> Local Search Agent -> Deal Comparator.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent.src.supervisor import run_dealsetu


def _print_banner():
    banner = """
========================================================================
           DealSetu — AI Shopping & Best-Deal Finder
       Bridging Online E-Commerce & Verified Local Merchants
========================================================================
"""
    print(banner)


def _format_currency(val: Any) -> str:
    if val is None or not isinstance(val, (int, float)):
        return "N/A"
    return f"₹{int(val):,}"


def _display_results(result: Dict[str, Any]):
    print("\n--- [Execution Progress & Activity Log] ---")
    for log_msg in result.get("activity_log", []):
        print(f"  ✓ {log_msg}")

    if result.get("status") == "needs_clarification":
        print("\n" + "=" * 60)
        print("  ⚠️  ADDITIONAL DETAILS NEEDED")
        print("=" * 60)
        print(f"\n{result.get('question')}\n")
        return

    req = result.get("structured_request", {})
    best = result.get("best_deal")
    reasoning = result.get("reasoning", "")
    ranked = result.get("ranked_offers", [])
    price_spread = result.get("price_spread", {})

    print("\n" + "=" * 72)
    print(f"  TARGET: {req.get('product', 'Product')} ({req.get('variant') or 'Standard'})")
    print(f"  LOCATION: {req.get('location', 'Delhi')} | BUDGET: {_format_currency(req.get('budget'))}")
    print("=" * 72)

    if best:
        print("\n🏆  RECOMMENDED TOP DEAL")
        print("-" * 72)
        print(f"  Seller / Store:   {best.get('source')} ({best.get('type', '').upper()})")
        print(f"  Price:            {_format_currency(best.get('price'))}")
        print(f"  Deal Score:       {best.get('score', 0):.1f} / 100")
        print(f"  Delivery / Speed: {best.get('delivery', 'Standard')}")
        print(f"  Warranty:         {best.get('warranty', 'Standard')}")
        if best.get("phone"):
            print(f"  Store Phone:      {best.get('phone')}")
        if best.get("notes"):
            print(f"  Perks & Notes:    {best.get('notes')}")

        print("\n💡  WHY THIS DEAL WAS CHOSEN (REASONING)")
        print("-" * 72)
        print(f"  {reasoning}")
    else:
        print("\n❌ No qualified deals found.")

    if ranked:
        print("\n📊  ALL EVALUATED DEALS (RANKED)")
        print("-" * 72)
        print(f"  {'#':<3} {'Source / Store':<32} {'Price':<11} {'Score':<8} {'Type':<8} {'Delivery'}")
        print("  " + "-" * 68)
        for idx, o in enumerate(ranked, 1):
            src = (o.get("source") or "Unknown")[:30]
            price = _format_currency(o.get("price"))
            score = f"{o.get('score', 0):.1f}"
            src_type = o.get("type", "online")
            deliv = (o.get("delivery") or "")[:20]
            print(f"  {idx:<3} {src:<32} {price:<11} {score:<8} {src_type:<8} {deliv}")

    if price_spread.get("diff"):
        min_p = _format_currency(price_spread.get('min'))
        max_p = _format_currency(price_spread.get('max'))
        diff_p = _format_currency(price_spread.get('diff'))
        print(f"\n💰  Price Spread: Lowest {min_p} | Highest {max_p} | Potential Savings: {diff_p}")

    print("\n" + "=" * 72)


def main():
    _print_banner()

    parser = argparse.ArgumentParser(description="DealSetu AI Shopping Assistant")
    parser.add_argument(
        "query",
        nargs="*",
        help="Shopping query, e.g. 'iPhone 16 128GB under 65000 in Delhi'",
    )
    parser.add_argument(
        "--location",
        "-l",
        type=str,
        default=None,
        help="Location override, e.g. 'Delhi', 'Mumbai'",
    )
    args = parser.parse_args()

    if args.query:
        user_query = " ".join(args.query)
    else:
        # Default demonstration query if none provided
        user_query = "iPhone 16 128GB under 65000 in Delhi"
        print(f"No query provided. Using default demo query:\n  \"{user_query}\"\n")

    print(f"Initiating DealSetu shopping agents for: \"{user_query}\"...\n")
    result = run_dealsetu(user_query, location_override=args.location)
    _display_results(result)


if __name__ == "__main__":
    main()
