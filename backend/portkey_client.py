"""Shared Portkey-backed OpenAI client and model factory.

Every agent in this project must use gpt-6-luna and only gpt-6-luna
(assignment rule — points are deducted if any other model shows up), so
building the client/model in one place means there is exactly one spot
that could ever drift from that rule.

gpt-6-luna is a reasoning-family model: Portkey/Azure rejects it over the
plain Chat Completions API (it wants max_completion_tokens, not
max_tokens, and rejects function-tool calls there entirely), so it has to
be driven through OpenAIResponsesModel rather than OpenAIChatModel — this
was confirmed directly against the live Portkey account before wiring any
agents.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

MODEL_NAME = "gpt-6-luna"

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")


@lru_cache
def get_portkey_client() -> AsyncOpenAI:
    key = os.environ.get("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set — check the project root .env file.")
    return AsyncOpenAI(api_key=key, base_url="https://api.portkey.ai/v1")


@lru_cache
def get_model() -> OpenAIResponsesModel:
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=get_portkey_client()))
