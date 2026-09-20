# DealMate

An AI price comparison agent that checks online stores and nearby local shops for you, then tells you where the best deal is.

Built by team **Rigs** for the **First Commit** AWS hackathon by WeMakeDevs (Build It track).

## The problem

Comparing prices online is easy enough, but it still means opening Amazon, Flipkart, Croma and a few other tabs one by one. Comparing against local shops is almost impossible, because their prices aren't listed anywhere. Most people never ask, so they end up overpaying without knowing a shop down the road had a better price.

## What DealMate does

You describe what you want in plain language, for example `300 litre fridge under 30000 in Delhi`. A team of AI agents takes it from there:

1. Understands the request and asks follow up questions if specs are missing.
2. Searches online stores for matching products and prices.
3. Finds nearby local sellers and requests quotes from them.
4. Compares everything side by side and highlights the best deal.

If the exact spec isn't available, DealMate also shows close matches. Ask for a 300 litre fridge and it will surface the 321 and 331 litre models too, labelled clearly as close matches instead of returning nothing.

## How it works

```
                      User query
                          |
                    Supervisor Agent
                          |
        +-----------------+-----------------+
        |                 |                 |
  Product Agent      Online Agent       Local Agent
  (understands and   (searches online   (finds nearby shops,
   clarifies specs)   stores for prices) requests quotes)
        |                 |                 |
        +-----------------+-----------------+
                          |
                    compare_deals
                          |
                  Best deal + activity log
```

- The **Supervisor Agent** coordinates the other three and produces the activity log shown in the UI.
- Agents are built with the **Strands Agents SDK**, and each one is used as a tool by the supervisor.
- The **Online Agent** searches a fixed set of stores (amazon.in, flipkart.com, croma.com, reliancedigital.in) and pulls prices out of the results. It classifies each result as an exact match, a close match (within 15 percent of the requested spec) or something else, so users can see what is a real match and what is a substitute.
- The **Local Agent** discovers nearby shops and requests quotes. Seller responses are simulated for the demo, see the note below.
- Comparison is plain deterministic Python, not an LLM call, so scoring stays fast and predictable.

## AWS and open source stack

| Piece | What it does here |
| --- | --- |
| Strands Agents SDK | Multi agent orchestration, tools written as plain Python functions |
| Amazon Bedrock | Foundation model behind the agents, switchable through an environment variable |
| DynamoDB | Stores sellers, quote requests, quotes, product catalog and price history |
| Lambda + API Gateway | Each seller backend endpoint runs as its own function behind a REST API |
| AWS SAM | Defines the backend stack (functions, tables, routes) in one template |
| LocalStack | Runs AWS services locally so no AWS account is needed for development |

Other tools: FastAPI (agent API), Flask + Jinja2 + Tailwind CSS (frontend), `ddgs` (free web search), `uv` (dependency management).

The model layer is wrapped in a single `get_model()` helper, so switching providers is a config change and not a code change.

## Project structure

```
DealMate/
├── agent/                      # multi agent system and FastAPI layer
│   ├── data/
│   │   └── quote_requests.json
│   └── src/
│       ├── api.py              # FastAPI app (POST /search)
│       ├── config.py
│       ├── model_provider.py   # get_model(), swaps between Bedrock and Groq
│       ├── supervisor.py
│       ├── product_agent.py
│       ├── online_agent.py
│       ├── local_agent.py
│       ├── main.py
│       ├── prompts/            # system prompts for each agent
│       └── tools/              # search_online_products, get_product_details,
│                               # find_local_sellers, get_seller_quotes, compare_deals
├── frontend/                   # Flask + Jinja2 + Tailwind UI
│   ├── app.py
│   ├── mock_data.py
│   ├── static/css/style.css
│   └── templates/
│       ├── index.html
│       ├── loading.html
│       ├── results.html
│       └── cards/              # price, nearby stores, reviews, sales,
│                               # similar and related product cards
├── seller-backend/             # serverless seller API
│   ├── src/
│   │   ├── db/                 # DynamoDB client and models
│   │   ├── handlers/           # create_quote_request, submit_quote,
│   │   │                       # get_quotes, seller_crud
│   │   └── services/           # nearby_stores
│   ├── tests/
│   ├── template.yaml           # AWS SAM template
│   └── requirements.txt
├── shared/schemas/             # product_request.json, seller_quote.json
├── docs/
│   └── api-contracts.md        # request and response contracts between the parts
├── create_table.py             # creates the DynamoDB table
├── pyproject.toml
└── README.md
```

## Getting started

### Prerequisites

- Python 3.11 or newer (check `.python-version`)
- [uv](https://docs.astral.sh/uv/)
- Docker (only for LocalStack)
- A model provider key or Bedrock access (see below)

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure environment

Create a `.env` file in the project root. It is gitignored, so each teammate uses their own.

```env
# choose one provider
MODEL_PROVIDER=bedrock        # or groq
GROQ_API_KEY=your_key_here    # only needed if MODEL_PROVIDER=groq
AWS_REGION=us-east-1          # only needed for bedrock
```

### 3. Start the agent API

```bash
cd agent
uv run uvicorn src.api:app --reload --port 8000
```

The frontend talks to one endpoint:

```
POST http://localhost:8000/search
Content-Type: application/json

{ "query": "300 litre fridge under 30000 in Delhi" }
```

The response contains the final deal comparison along with the agent activity log.

### 4. Start local AWS services (optional)

```bash
docker run -d -p 4566:4566 localstack/localstack
```

Then create the table with `uv run python create_table.py`, or run the seller backend locally with `sam local start-api` from the `seller-backend` folder.

### 5. Start the frontend

```bash
cd frontend
uv run flask --app app run --debug
```

Open `http://localhost:5000`.

> Update steps 3 to 5 if your commands or folder names are different.

## Demo notes

- Online prices and close match logic use live web search results.
- **Local seller quotes are simulated** through the seller backend for the demo. Real seller outreach would need a messaging channel such as SMS or the WhatsApp Business API, which isn't free and needs approval, so it is left out of this MVP.
- Price extraction from search snippets is best effort. If a result has no clear price, DealMate leaves it empty instead of guessing.

## Dashboard

The results page is built from cards, one per kind of information:

- **Price card** for the online vs local price comparison
- **Nearby stores card** for local sellers found around the user
- **Review card** for what people are saying about the product
- **Similar and related product cards** for alternatives worth a look
- **Sales card** for upcoming sales, so users can buy at the right time

## Roadmap

- Real seller messaging through SMS or WhatsApp Business API
- Live data behind every dashboard card
- Price history tracking

## AI coding tools used

We used AI tools to move faster during the hackathon:

| Tool | Where we used it |
| --- | --- |
| Claude | Planning the multi agent architecture, scaffolding the agents and tools, debugging, and building the frontend templates |
| Google Antigravity | Continuing the agent build from a detailed handoff prompt |
| GitHub Copilot | Auditing the agent code and completing the remaining pieces |

## Team

| Name | GitHub | Role |
| --- | --- | --- |
| Yosuf Jamal | @bane | AI agents, model provider layer, agent API |
| Haris Nawaz | @haris_nawaz | Seller backend, DynamoDB models, Lambda handlers, SAM template, tests |
| Anamta Karim | @anamta | Frontend, Flask routing and UI |
