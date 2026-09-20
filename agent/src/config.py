import os
import sys
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

# --- Model provider config ---
#
# Using Groq for now (free tier, no AWS account/support-case friction).
# Groq exposes an OpenAI-compatible API, so Strands' OpenAIModel provider
# works by just pointing base_url at Groq instead of OpenAI.
#
# Get a free key at https://console.groq.com -> API Keys, then set it as:
#   export GROQ_API_KEY=your_key_here
#
# The selected model avoids a Groq tool-calling issue where strict JSON
# instructions can be misinterpreted as a request for a nonexistent tool.

GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL_ID = os.environ.get("GROQ_MODEL_ID", "openai/gpt-oss-120b")

# --- Bedrock config (kept for later, e.g. if you deploy for "Ship It") ---
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "us.amazon.nova-lite-v1:0",
)
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Which provider to actually use right now. Switch this one line later
# to move from Groq (dev) to Bedrock (deployed).
MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER", "groq")  # "groq" | "bedrock"
