"""LLM service layer.

Dependency map:
- Reads runtime settings from `config.py`
- Uses OpenAI-compatible SDK client for both providers

Function map:
- `get_deepseek_response`: DeepSeek text response
- `get_chatgpt_response`: ChatGPT-compatible text response
- `get_llm_response`: provider-based unified entrypoint
"""

from __future__ import annotations

from openai import OpenAI

import config

# Reuse client instances to avoid rebuilding connections on each request.
_deepseek_client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

_chatgpt_client = OpenAI(
    api_key=config.CHATGPT_API_KEY,
    base_url=config.CHATGPT_BASE_URL,
)


def _chat_completion(
    *,
    client: OpenAI,
    model: str,
    prompt: str,
    system_prompt: str = "You are a helpful assistant",
) -> str:
    """Send a standard chat completion request and return text content."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    return response.choices[0].message.content or ""


def get_deepseek_response(prompt: str, model: str = "deepseek-chat") -> str:
    """Call DeepSeek chat model and return plain text response."""

    return _chat_completion(client=_deepseek_client, model=model, prompt=prompt)


def get_chatgpt_response(
    prompt: str,
    model: str | None = None,
    system_prompt: str = "You are a helpful assistant",
) -> str:
    """Call ChatGPT-compatible API and return plain text response."""

    resolved_model = model or config.CHATGPT_MODEL
    return _chat_completion(
        client=_chatgpt_client,
        model=resolved_model,
        prompt=prompt,
        system_prompt=system_prompt,
    )


def get_llm_response(
    prompt: str,
    *,
    provider: str = "deepseek",
    model: str | None = None,
    system_prompt: str = "You are a helpful assistant",
) -> str:
    """Unified LLM entrypoint for future provider expansion."""

    provider_name = provider.strip().lower()
    if provider_name == "deepseek":
        return get_deepseek_response(prompt=prompt, model=model or "deepseek-chat")
    if provider_name in {"chatgpt", "openai"}:
        return get_chatgpt_response(prompt=prompt, model=model, system_prompt=system_prompt)
    raise ValueError(f"Unsupported provider: {provider}")


__all__ = [
    "get_deepseek_response",
    "get_chatgpt_response",
    "get_llm_response",
]
