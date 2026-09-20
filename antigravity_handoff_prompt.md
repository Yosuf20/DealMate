# DealSetu — Agent Build Continuation Prompt

## Context

You are continuing development of **DealSetu**, an AI shopping agent built for
an AWS-focused hackathon. This prompt hands off a partially-built codebase —
read it fully before writing any code, since several architectural decisions
were already made deliberately (including workarounds for real bugs hit
during development). Follow the established patterns; don't re-architect.

**Time is very limited. Prioritize a working end-to-end flow over polish.**

---

## What DealSetu does

DealSetu is a shopping agent that finds the best deal for a product by
searching BOTH online e-commerce sites AND local/offline sellers, then
compares them and recommends the best actionable option (not just cheapest
price — also considers delivery, warranty, availability).

Example: user asks "iPhone 16 128GB under ₹65,000 in Delhi" →
agent searches online stores, finds local sellers, gets quotes from them,
compares everything, returns the best deal with reasoning.

---

## Tech stack decisions already locked in (do not change these)

- **Package manager**: `uv` (not pip). Project has `pyproject.toml` + `uv.lock`.
  Add dependencies with `uv add <package>`, not pip.
- **Agent framework**: **Strands Agents SDK** (`from strands import Agent, tool`).
- **LLM provider**: **Groq API**, NOT AWS Bedrock. This was a deliberate
  pivot — Bedrock's Claude models require an AWS support case for new
  accounts (multi-day wait), which isn't viable on a hackathon timeline.
  Groq is free-tier, instant signup, OpenAI-compatible API.
  - Model: `openai/gpt-oss-120b` (see "Known bug" section below for why
    this specific model, not `llama-3.3-70b-versatile`).
  - Wired via Strands' `strands.models.openai.OpenAIModel` pointed at
    Groq's OpenAI-compatible endpoint (`https://api.groq.com/openai/v1`).
- **Web search for online prices**: `ddgs` (DuckDuckGo search, free, no API
  key) — NOT a paid e-commerce API (Amazon/Flipkart partner APIs require
  approval we don't have time for).
- **Local seller discovery**: plan is OpenStreetMap Overpass API +
  Nominatim (free, no API key) for finding real nearby shops — NOT yet
  implemented (see "What's left" below).
- **Local seller quotes**: given the time constraint, quotes should be
  **simulated via a simple local store** (a JSON file or in-memory dict is
  fine — do NOT attempt real DynamoDB integration or real WhatsApp/SMS
  messaging right now, that's explicitly out of scope for this pass).
- **Env vars**: loaded via `python-dotenv`'s `load_dotenv()` in `config.py`,
  reading a `.env` file in the project root (already gitignored). Required
  var: `GROQ_API_KEY`.

---

## Current file structure (flat, under `agent/src/`)

```
agent/src/
├── __init__.py
├── config.py            # env vars, model provider switch, Groq/Bedrock settings
├── model_provider.py    # get_model() -> builds the right Strands model object
├── online_agent.py      # DONE — Online Search Agent (see below)
├── local_agent.py       # STUB / IN PROGRESS — needs building
├── product_agent.py     # STUB / IN PROGRESS — needs building
├── supervisor.py        # STUB / IN PROGRESS — needs building
├── main.py              # STUB — local entrypoint to run the full flow
└── tools/
    ├── search_online_products.py   # DONE
    └── get_product_details.py      # DONE
```

Prompts currently live as string constants at the top of each agent's own
file (or in a shared `prompts.py` if that's how the repo evolved — check
before assuming).

---

## What's already built and working

### `config.py`
- `MODEL_PROVIDER` env var switches between `"groq"` (current default) and
  `"bedrock"` (kept for later, unused now).
- `GROQ_API_KEY`, `GROQ_BASE_URL`, `GROQ_MODEL_ID` (default
  `openai/gpt-oss-120b`).
- Calls `load_dotenv()` at import time.

### `model_provider.py`
- Single `get_model()` function every agent calls — do NOT construct
  `OpenAIModel`/`BedrockModel` directly in agent files. This keeps provider
  switching to one place.

### `tools/search_online_products.py`
A `@tool`-decorated function with real logic, not a stub:
- Searches `amazon.in`, `flipkart.com`, `croma.com`, `reliancedigital.in`
  via `ddgs`, scoped with `site:` queries.
- Extracts ₹ prices from result snippets via regex.
- **Spec-matching fallback** (important, don't remove): parses a
  number+unit spec from the requested variant (e.g. "300L", "128GB") and
  from each result's title/snippet, using a generic regex (works for
  litres, GB, TB, kg, inches, tons — not product-specific). Classifies
  each offer as `"exact"`, `"close"` (within ±15%), `"other"`, or
  `"unspecified"`. If fewer than 2 exact matches are found, it
  automatically runs a second broadened search (same query without the
  exact number) to surface nearby-spec alternatives — e.g. if "300L
  fridge" isn't in stock, it'll surface 321L/331L options and label them
  as close matches rather than silently returning nothing.
- Returns a sorted list: exact matches first, then close, then others,
  each group cheapest-first.

### `tools/get_product_details.py`
Simple follow-up search tool for when the agent needs more detail on a
specific listing/product than the search snippet gave it.

### `online_agent.py`
- Builds a Strands `Agent` with the two tools above, using `get_model()`.
- System prompt instructs it to search, classify matches, and return a
  **strict JSON object** (see prompt constant for exact shape: product,
  variant, offers[], cheapest_price, cheapest_exact_price, notes).
- `run_online_agent(structured_request: dict) -> dict` is the public
  function other code should call. It extracts the JSON object from the
  agent's text response via a regex fallback (`_extract_json`), so it's
  tolerant of extra prose around the JSON.

---

## Known bug already fixed — do not reintroduce

**Symptom**: `openai.APIError: Tool call validation failed: ... attempted
to call tool 'json' which was not in request.tools`

**Cause**: This is a documented Groq/Llama quirk. When a system prompt
says something like "Respond ONLY with a JSON object, no extra text" AND
real tools are registered, some Groq-hosted Llama models hallucinate a
fake tool call to a nonexistent `"json"` tool instead of just writing JSON
as plain text. `llama-3.3-70b-versatile` hit this reliably;
`openai/gpt-oss-120b` does not (or does so far less).

**Fixes already applied — keep both**:
1. Model set to `openai/gpt-oss-120b` in `config.py`.
2. Prompt wording avoids "ONLY ... no extra text" phrasing. Instead it
   says something like: "Once you're done using your tools, write your
   final answer as a single JSON object matching this shape. Do not call
   any tool named 'json' — just write the JSON directly as your text
   response." Every new agent's system prompt (Product, Local, Supervisor)
   should use this same soft phrasing, not a stricter version.
3. JSON extraction from agent responses always goes through a regex
   fallback (find `\{.*\}` in the response text) rather than assuming the
   response is pure JSON — because even with the above fixes, some prose
   may surround the JSON. Reuse this pattern in every agent file.

---

## What's left to build (in priority order)

### 1. `tools/compare_deals.py` (do this first — no dependencies, pure logic)
A plain Python function (NOT an LLM call — deterministic, fast, testable):
```python
def compare_deals(offers: list[dict]) -> dict:
    """
    Takes a combined list of offers (online + local quotes, both normalized
    to the same shape: price, source, delivery, warranty, availability,
    match_type), scores them considering price + delivery cost + warranty +
    availability + match quality (prefer "exact" over "close" spec matches),
    and returns the single best deal plus a ranked list and the reasoning.
    """
```
Keep the scoring simple and explainable (e.g. weighted score or clear
tie-breaking rules) — a hackathon demo needs to be able to explain *why*
a deal was chosen, not just show a number.

### 2. `product_agent.py`
- Takes raw natural language ("I need an iPhone 16 128GB under 65k in
  Delhi") and converts it to the structured request shape:
  ```json
  {"product": "iPhone 16", "variant": "128GB", "budget": 65000,
   "location": "Delhi", "condition": "new"}
  ```
- If critical info is missing (e.g. no budget, no location), it should
  ask a clarifying question rather than guessing — return a response
  shape that distinguishes "ready to proceed" from "need more info",
  e.g. `{"status": "needs_clarification", "question": "..."}` vs
  `{"status": "ready", "structured_request": {...}}`.
- No tools needed for this agent — it's pure language understanding, just
  an `Agent` with a system prompt and no `tools=[]` (or minimal).
- Follow the same `get_model()` + soft-JSON-prompt + regex-extraction
  pattern as `online_agent.py`.

### 3. `local_agent.py`
Given the time constraint, keep this simple:
- **Discovery tool** `find_local_sellers(product_category, location)`:
  use OSM Nominatim (geocode the location, free, no key) then Overpass
  API (query nearby shops by category, free, no key) to get real shop
  names/locations. Reference approach (adapt as needed):
  ```python
  import requests

  def find_local_sellers(product_category: str, location: str) -> list[dict]:
      geo = requests.get(
          "https://nominatim.openstreetmap.org/search",
          params={"q": location, "format": "json", "limit": 1},
          headers={"User-Agent": "DealSetu-Hackathon"},
      ).json()
      lat, lon = geo[0]["lat"], geo[0]["lon"]

      query = f"""
      [out:json];
      node["shop"~"mobile_phone|electronics"](around:5000,{lat},{lon});
      out;
      """
      resp = requests.post(
          "https://overpass-api.de/api/interpreter", data={"data": query}
      ).json()

      return [
          {
              "seller_name": el.get("tags", {}).get("name", "Unnamed Shop"),
              "lat": el["lat"], "lon": el["lon"],
              "phone": el.get("tags", {}).get("phone"),
          }
          for el in resp.get("elements", [])
      ]
  ```
- **Quote simulation tool** `request_seller_quote(seller, product_request)`
  and `get_seller_quotes(request_id)`: for now, DO NOT attempt real
  messaging (no WhatsApp API, no SMS — out of scope, no time, and
  previously flagged as something to avoid building fragile/unauthorized
  automation for). Instead:
  - Write the "quote request" to a simple local store — a JSON file
    (`data/quote_requests.json`) or in-memory dict is fine.
  - For the demo, quotes should be returned by a tiny mock/manual
    mechanism: either (a) a small hardcoded set of realistic quotes keyed
    by seller name for demo purposes, or (b) a trivial local script/page
    where a human (playing "the seller") can type in a price/warranty/
    delivery/availability response that gets read back by
    `get_seller_quotes`. Pick whichever is faster to build — (a) if truly
    out of time, (b) if there's an hour to spare, since it demos better.
  - Be honest in code comments that this is simulated for the hackathon
    MVP; real implementation would use a seller portal + SMS/WhatsApp
    Business API, both deferred due to cost/approval time.

### 4. `supervisor.py`
- Orchestrates: call Product Agent first (handle clarification loop if
  needed) → once structured request is ready, call Online Agent and
  Local Agent → normalize both sets of offers into the same shape → call
  `compare_deals` (plain tool, not an LLM call) → return final answer.
- Should also produce a simple activity log (list of strings like
  "Searching online stores...", "Finding local sellers...") as it
  goes, since the original spec wants this shown in a UI — just collect
  these as a list and return them alongside the final result for now,
  don't worry about streaming/websockets given the time constraint.
- Can be implemented as a plain Python function calling the other agents'
  public functions directly (`run_online_agent`, etc.) rather than as a
  Strands "agents-as-tools" pattern, if that's faster to get working
  reliably under time pressure. Correctness and demo-readiness over
  architectural purity right now.

### 5. `main.py`
- A simple local entrypoint (no Lambda/API Gateway needed right now —
  that's a later "Ship It" concern). Should accept a natural language
  query (hardcoded test string or `input()`/CLI arg) and print the full
  flow's output: clarification questions if any, then the final deal
  comparison with reasoning.

---

## Ground rules for anything you build

- Every new agent follows the `online_agent.py` pattern: `get_model()`
  from `model_provider.py`, soft JSON-only prompt wording (see "Known bug"
  section), regex-based JSON extraction from the response.
- No paid APIs anywhere. No AWS Bedrock right now. No WhatsApp Business
  API / Twilio / SMS right now — these are explicitly deferred.
- Keep `compare_deals` and any scoring/matching logic as **plain
  deterministic Python**, not LLM calls — faster, cheaper, and easier to
  debug live during a demo.
- Prioritize: does the end-to-end flow run and produce a sensible answer
  for one hardcoded demo query (e.g. "iPhone 16 128GB under 65000 in
  Delhi")? Get that working before generalizing or polishing.
- Add short comments noting what's simulated/mocked vs real, so it's easy
  to explain to hackathon judges what's a genuine integration vs a
  time-boxed placeholder.
