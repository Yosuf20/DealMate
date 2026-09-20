"""
model_provider.py

Single place that decides which Strands model backend to build, based on
config.MODEL_PROVIDER. Every agent file should call get_model() instead of
constructing a model directly - that way switching providers (e.g. Groq for
local dev -> Bedrock for the deployed "Ship It" submission) is a one-line
"""

from agent.src import config


def get_model():
    if config.MODEL_PROVIDER == "groq":
        if not config.GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free key at "
                "https://console.groq.com -> API Keys, then run:\n"
                "  export GROQ_API_KEY=your_key_here"
            )
        from strands.models.openai import OpenAIModel

        return OpenAIModel(
            client_args={
                "api_key": config.GROQ_API_KEY,
                "base_url": config.GROQ_BASE_URL,
            },
            model_id=config.GROQ_MODEL_ID,
        )

    if config.MODEL_PROVIDER == "bedrock":
        from strands.models import BedrockModel

        return BedrockModel(
            model_id=config.BEDROCK_MODEL_ID,
            region_name=config.AWS_REGION,
        )

    raise ValueError(f"Unknown MODEL_PROVIDER: {config.MODEL_PROVIDER!r}")
