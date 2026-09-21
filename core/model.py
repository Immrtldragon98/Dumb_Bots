from __future__ import annotations

import os
from typing import Any

from ollama import Client

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("DUMBBOTS_MODEL", "qwen2.5-coder:3b")

client = Client(host=OLLAMA_HOST)


def available_models() -> list[str]:
    """Return models available in local Ollama."""
    response = client.list()
    return [model.model for model in response.models]


def ask_model(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Send one normal controlled request to the local model."""
    response = client.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are DumbBots, a careful software engineer. "
                    "Give concise, precise answers and follow instructions exactly."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0, "num_ctx": 4096},
    )
    return response.message.content.strip()


def ask_model_json(
    prompt: str,
    schema: dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> str:
    """Ask Ollama to return JSON matching a supplied schema."""
    response = client.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are DumbBots, a careful software engineer. "
                    "Return only valid JSON that satisfies the requested schema."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        format=schema,
        options={"temperature": 0, "num_ctx": 4096},
    )
    return response.message.content.strip()
