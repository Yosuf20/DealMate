# DealSetu — Agent Build: Audit & Complete

## Important — do this first, before writing any code

Another AI tool (Antigravity) was working on this codebase and ran out of
credits mid-task. **You do not know exactly what state the code is
currently in.** Before making any changes:

1. Open and read every file under `agent/src/` (all agent files, all
   tools, `config.py`, `model_provider.py`, `main.py`).
2. Compare what actually exists against the "Target state" checklist
   below, and report back a short status list: what's fully done, what's
   partially done/broken, what's missing entirely.
3. Only then start completing the remaining/broken pieces, following the
   established patterns described below. Don't re-architect or rewrite
   working code — Antigravity may have already correctly built things
   that match this spec; verify before replacing.

If something partially built contradicts the "Tech stack decisions" or
"Ground rules" sections below (e.g. it added a paid API, or hardcoded
Bedrock somewhere), flag it and fix it to match this spec rather than
leaving two inconsistent approaches in the codebase.

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
  accounts (multi-day wait), not viable on a hackathon timeline.
  Groq is free-tier, instant signup, OpenAI-compatible API.
  - Model: `openai/gpt-oss-120b` (see "Known bug" section for why this
    specific model, not `llama-3.3-70b-versatile`).
  - Wired via Strands' `strands.models.openai.OpenAIModel` pointed at
    Groq's OpenAI-compatible endpoint (`https://api.groq.com/openai/v1`).
- **Web search for online prices**: `ddgs` (DuckDuckGo search, free, no API
  key) — NOT a paid e-commerce API.
- **Local seller discovery**: OpenStreetMap Overpass API + Nominatim
  (free, no API key).
- **Local seller quotes**: **simulated via a simple local store** (a JSON
  file or in-memory dict). Do NOT build real DynamoDB integration or real
  WhatsApp/SMS messaging — explicitly out of scope for this pass.
- **Env vars**: loaded via `python-dotenv`'s `load_dotenv()` in
  `config.py`, reading a `.env` file in the project root (gitignored).
  Required var: `GROQ_API_KEY`.

---

## Target state — file structure (flat, under `agent/src/`)

```
agent/src/
├── __init__.py
├── config.py            # env vars, model provider switch, Groq/Bedrock settings
├── model_provider.py    # get_model() -> builds the right Strands model object
├── online_agent.py      # should be DONE
├── local_agent.py       # should be built (may be partial from Antigravity)
├── product_agent.py     # should be built (may be partial from Antigravity)
├── supervisor.py        # should be built (may be partial from Antigravity)
├── main.py              # should be built (may be partial from Antigravity)
└── tools/
    ├── search_online_products.py   # should be DONE
    ├── get_product_details.py      # should be DONE
    └── compare_deals.py            # should be built (may be partial from Antigravity)
```

---

## Established patterns — every agent file should follow these

### Model + provider
- Every agent calls `get_model()` from `model_provider.py`. Never
  construct `OpenAIModel`/`BedrockModel` directly inside an agent file.

### System prompt wording — avoid the Groq "json" tool bug
**Known bug already hit and fixed once**: `openai.APIError: Tool call
validation failed: ... attempted to call tool 'json' which was not in
request.tools`. This happens when a system prompt says something like
"Respond ONLY with a JSON object, no extra text" while real tools are
also registered — some Groq-hosted Llama models hallucinate a fake `json`
tool call instead of writing JSON as plain text.

Fix (apply to every agent's prompt, not just Online Agent):
1. Model must be `openai/gpt-oss-120b` (set in `config.py`), not
   `llama-3.3-70b-versatile`.
2. Prompt wording should be soft, e.g.: "Once you're done using your
   tools, write your final answer as a single JSON object matching this
   shape. Do not call any tool named 'json' — just write the JSON
   directly as your text response." Avoid "ONLY ... no extra text"
   phrasing.
3. JSON parsing from any agent's response must go through a regex
   fallback (find `\{.*\}` in the response text), not `json.loads()` on
   the raw response directly — there may be extra prose around it.

If you find any agent file using strict "ONLY JSON, no extra text"
wording or `llama-3.3-70b-versatile`, fix it to match this pattern.

---

## What each remaining piece should do

### `tools/compare_deals.py`
Plain deterministic Python function — **not an LLM call**:
```python
def compare_deals(offers: list[dict]) -> dict:
    """
    Takes a combined list of offers (online + local quotes, normalized to
    the same shape: price, source, delivery, warranty, availability,
    match_type), scores them considering price + delivery cost + warranty
    + availability + match quality (prefer "exact" over "close" spec
    matches), and returns the single best deal plus a ranked list and
    plain-language reasoning for why it won.
    """
```
Keep scoring simple and explainable — needs to be demo-able ("here's why
this deal won"), not a black box.

### `product_agent.py`
- Converts natural language ("I need an iPhone 16 128GB under 65k in
  Delhi") into the structured request shape:
  ```json
  {"product": "iPhone 16", "variant": "128GB", "budget": 65000,
   "location": "Delhi", "condition": "new"}
  ```
- If critical info is missing, it should ask a clarifying question
  instead of guessing. Response shape should distinguish "ready" from
  "needs clarification", e.g.:
  `{"status": "needs_clarification", "question": "..."}` vs
  `{"status": "ready", "structured_request": {...}}`.
- No tools needed — pure language understanding.

### `local_agent.py`
- **Discovery**: `find_local_sellers(product_category, location)` using
  OSM Nominatim (geocode) + Overpass API (nearby shops by category),
  both free/no key. Example approach:
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
- **Quote simulation**: `request_seller_quote(seller, product_request)`
  and `get_seller_quotes(request_id)`. No real messaging (no WhatsApp/SMS
  — explicitly deferred). Write requests to a simple local JSON file or
  in-memory dict; return quotes from either a small hardcoded realistic
  set, or a trivial manual-entry mechanism if there's time. Comment
  clearly that this is simulated for the MVP.

### `supervisor.py`
- Orchestrates: Product Agent first (handle clarification loop) → Online
  Agent + Local Agent → normalize both offer sets to the same shape →
  `compare_deals` (plain function call, not LLM) → final answer.
- Collects a simple activity log (list of strings like "Searching online
  stores...", "Finding local sellers...") alongside the result — no need
  for streaming/websockets given the time constraint.
- A plain Python function calling the other agents' public functions
  directly is fine — doesn't need to be a Strands "agents-as-tools"
  pattern if that's more reliable to get working fast.

### `main.py`
- Local CLI entrypoint (no Lambda/API Gateway yet — that's later). Takes
  a natural language query (hardcoded test string, `input()`, or CLI arg)
  and prints the full flow's output: clarifying question if any, else the
  final deal comparison with reasoning.

---

## Ground rules

- No paid APIs anywhere. No AWS Bedrock right now. No WhatsApp Business
  API / Twilio / SMS right now.
- `compare_deals` and any scoring/matching logic stays plain deterministic
  Python, not an LLM call.
- Priority: does the end-to-end flow run and produce a sensible answer for
  one hardcoded demo query (e.g. "iPhone 16 128GB under 65000 in Delhi")?
  Get that working before generalizing or polishing.
- Comment clearly what's simulated/mocked vs real, so it's easy to explain
  to hackathon judges what's a genuine integration vs a time-boxed
  placeholder.

---

## After you finish

Run `main.py` with the demo query and confirm it produces a final deal
comparison without errors. Report back: what you found already built,
what you fixed/completed, and any remaining known gaps given the time
constraint.
