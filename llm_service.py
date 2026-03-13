"""LLM service layer with provider registry.

Public entrypoints:
- `get_llm_response(...)` (backward compatible function)
- `get_service()` / `set_service()` for global service instance
- `LLMService` class for extensible provider management
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from openai import OpenAI

import config

ProviderInvoker = Callable[[str, str, str], str]


@dataclass
class _ProviderRuntime:
    """Provider runtime metadata and invoker."""

    default_model: str
    invoker: ProviderInvoker


class LLMService:
    """Extensible LLM service with pluggable providers."""

    def __init__(self) -> None:
        self._providers: dict[str, _ProviderRuntime] = {}
        self._aliases: dict[str, str] = {}

    @staticmethod
    def _normalize_key(name: str) -> str:
        normalized = name.strip().lower()
        if not normalized:
            raise ValueError("Provider name cannot be empty.")
        return normalized

    def register_provider(
        self,
        name: str,
        *,
        default_model: str,
        invoker: ProviderInvoker,
        aliases: Iterable[str] | None = None,
    ) -> None:
        """Register a provider with custom invocation logic."""

        canonical = self._normalize_key(name)
        self._providers[canonical] = _ProviderRuntime(default_model=default_model, invoker=invoker)
        self._aliases[canonical] = canonical

        if aliases:
            for alias in aliases:
                self._aliases[self._normalize_key(alias)] = canonical

    def register_openai_provider(
        self,
        name: str,
        *,
        api_key: str,
        base_url: str,
        default_model: str,
        aliases: Iterable[str] | None = None,
    ) -> None:
        """Register an OpenAI-compatible provider using `openai.OpenAI` client."""

        client = OpenAI(api_key=api_key, base_url=base_url)

        def _invoke(prompt: str, model: str, system_prompt: str) -> str:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                stream=False,
            )
            return response.choices[0].message.content or ""

        self.register_provider(
            name,
            default_model=default_model,
            invoker=_invoke,
            aliases=aliases,
        )

    def _resolve_runtime(self, provider: str) -> tuple[str, _ProviderRuntime]:
        key = self._normalize_key(provider)
        canonical = self._aliases.get(key, key)
        runtime = self._providers.get(canonical)
        if runtime is None:
            raise ValueError(f"Unsupported provider: {provider}")
        return canonical, runtime

    def list_providers(self) -> list[str]:
        """List canonical provider names."""

        return sorted(self._providers.keys())

    def get_response(
        self,
        prompt: str,
        *,
        provider: str = "deepseek",
        model: str | None = None,
        system_prompt: str = "You are a helpful assistant",
    ) -> str:
        """Call selected provider and return plain text response."""

        _name, runtime = self._resolve_runtime(provider)
        resolved_model = model or runtime.default_model
        return runtime.invoker(prompt, resolved_model, system_prompt)


def _build_default_service() -> LLMService:
    service = LLMService()
    service.register_openai_provider(
        "deepseek",
        api_key=config.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
    )
    service.register_openai_provider(
        "chatgpt",
        api_key=config.CHATGPT_API_KEY,
        base_url=config.CHATGPT_BASE_URL,
        default_model=config.CHATGPT_MODEL,
        aliases=("openai",),
    )
    return service


_SERVICE = _build_default_service()


def set_service(service: LLMService) -> None:
    """Set global service instance."""

    global _SERVICE
    _SERVICE = service


def get_service() -> LLMService:
    """Get global service instance."""

    return _SERVICE


def get_llm_response(
    prompt: str,
    *,
    provider: str = "deepseek",
    model: str | None = None,
    system_prompt: str = "You are a helpful assistant",
) -> str:
    """Backward-compatible function wrapper."""

    return _SERVICE.get_response(
        prompt,
        provider=provider,
        model=model,
        system_prompt=system_prompt,
    )


__all__ = [
    "LLMService",
    "get_service",
    "set_service",
    "get_llm_response",
]
