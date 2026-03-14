"""News-domain service for LongBridge HTTP endpoints."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

import config


class LongbridgeNewsService:
    """Encapsulates news HTTP operations."""

    def __init__(self, *, http_host: str, access_token: str | None, timeout: int = 30) -> None:
        self.http_host = http_host.rstrip("/")
        self.access_token = access_token
        self.timeout = timeout

    def _news_headers(self) -> dict[str, str]:
        headers = {
            "Accept": config.get_text("longbridge.news_accept"),
            "User-Agent": config.get_text("longbridge.news_user_agent"),
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def news(self, symbol: str) -> Any:
        url = f"{self.http_host}/v1/content/{symbol}/news"
        request = Request(url, headers=self._news_headers(), method="GET")
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

