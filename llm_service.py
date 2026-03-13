"""LLM service layer.

This module provides one unified function:
`get_llm_response(...)`

Supported providers:
- `deepseek`
- `chatgpt` (or alias `openai`) via OpenAI-compatible gateway
"""

from __future__ import annotations

from openai import OpenAI

import config


# Reuse clients to avoid creating new HTTP pools on every request.
_DEEPSEEK_CLIENT = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

_CHATGPT_CLIENT = OpenAI(
    api_key=config.CHATGPT_API_KEY,
    base_url=config.CHATGPT_BASE_URL,
)


def _normalize_provider(provider: str) -> str:
    """Normalize provider aliases to canonical names."""

    normalized = provider.strip().lower()
    if normalized in {"openai", "chatgpt"}:
        return "chatgpt"
    return normalized


def _resolve_client_and_model(provider: str, model: str | None) -> tuple[OpenAI, str]:
    """Resolve client and model based on provider."""

    normalized = _normalize_provider(provider)
    if normalized == "deepseek":
        return _DEEPSEEK_CLIENT, model or "deepseek-chat"
    if normalized == "chatgpt":
        return _CHATGPT_CLIENT, model or config.CHATGPT_MODEL
    raise ValueError(f"Unsupported provider: {provider}")


def get_llm_response(
    prompt: str,
    *,
    provider: str = "deepseek",
    model: str | None = None,
    system_prompt: str = "You are a helpful assistant",
) -> str:
    """Call an LLM provider and return plain text response.

    Args:
        prompt: User input text.
        provider: `deepseek`, `chatgpt`, or `openai`.
        model: Optional model override. If omitted, provider default is used.
        system_prompt: System role content.
    """

    client, resolved_model = _resolve_client_and_model(provider, model)
    response = client.chat.completions.create(
        model=resolved_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    return response.choices[0].message.content or ""


__all__ = ["get_llm_response"]
