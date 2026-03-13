"""Helpers to build Longbridge Config with OAuth-first fallback."""

from __future__ import annotations

from typing import Callable, Tuple

import config as app_config
from longbridge.openapi import Config, OAuthBuilder


AuthUrlHandler = Callable[[str], None]


def _default_auth_url_handler(url: str) -> None:
    print(f"Open this URL to authorize: {url}")


def build_oauth_config(
    client_id: str | None = None,
    on_auth_url: AuthUrlHandler | None = None,
) -> Config:
    """Build Config from OAuth flow."""

    resolved_client_id = client_id or app_config.LONGBRIDGE_CLIENT_ID
    handler = on_auth_url or _default_auth_url_handler
    oauth = OAuthBuilder(resolved_client_id).build(handler)
    return Config.from_oauth(oauth)


def build_apikey_env_config() -> Config:
    """Build Config from LONGPORT_* or equivalent API key env vars."""

    return Config.from_apikey_env()


def build_config_with_fallback(
    client_id: str | None = None,
    on_auth_url: AuthUrlHandler | None = None,
) -> Tuple[Config, str]:
    """Try OAuth first, fallback to from_apikey_env() when OAuth fails."""

    try:
        return build_oauth_config(client_id=client_id, on_auth_url=on_auth_url), "oauth"
    except Exception as oauth_error:
        print(f"OAuth config failed, fallback to from_apikey_env(): {oauth_error}")
        return build_apikey_env_config(), "apikey_env"
