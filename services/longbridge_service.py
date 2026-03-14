"""LongBridge facade service (quote + trade)."""

from __future__ import annotations

import json
import logging
from typing import Any

import config
from longbridge.openapi import Config, QuoteContext, TradeContext

from services.longbridge_quote_service import LongbridgeQuoteService, build_market_snapshot_payload
from services.longbridge_trade_service import LongbridgeTradeService
from services.service_result import ServiceResult, failure, success

logger = logging.getLogger(__name__)

CLIENT_ID = config.LONGBRIDGE_CLIENT_ID
SYMBOLS = config.SYMBOLS


class LB:
    """Facade that aggregates quote and trade services."""

    def __init__(
        self,
        client_id: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.client_id = client_id
        self.timeout = timeout

        self.config = self._build_config()
        self.quote_ctx = QuoteContext(self.config)
        self.trade_ctx = TradeContext(self.config)

        self.quote = LongbridgeQuoteService(self.quote_ctx)
        self.trade = LongbridgeTradeService(self.trade_ctx)

    def _build_config(self) -> Config:
        resolved_config, _ = config.build_config_with_fallback(client_id=self.client_id)
        return resolved_config

    def __getattr__(self, name: str) -> Any:
        """Backward-compatible delegation for old LB.method() calls."""

        for service in (self.quote, self.trade):
            if hasattr(service, name):
                return getattr(service, name)
        raise AttributeError(f"{self.__class__.__name__!s} has no attribute {name!r}")

    @staticmethod
    def pretty(obj: Any) -> Any:
        from pprint import pprint

        pprint(obj)
        return obj


def get_market_snapshot_payload(client: LB, symbols: list[str]) -> dict[str, Any]:
    return build_market_snapshot_payload(client.quote, symbols)


def get_inspected_quotes_text(client_id: str | None = None, symbols=None) -> str:
    """Return askstock market snapshot as pretty JSON text."""

    resolved_client_id = client_id or CLIENT_ID
    resolved_symbols = list(SYMBOLS if symbols is None else symbols)
    client = LB(client_id=resolved_client_id)
    snapshot = get_market_snapshot_payload(client, resolved_symbols)
    try:
        return json.dumps(snapshot, ensure_ascii=False, indent=2)
    except Exception:
        return str(snapshot)


def get_inspected_quotes_result(client_id: str | None = None, symbols=None) -> ServiceResult:
    """Return snapshot text wrapped as service result."""

    try:
        return success(get_inspected_quotes_text(client_id=client_id, symbols=symbols))
    except Exception as error:
        logger.error("LongBridge snapshot failed symbols=%s error=%s", symbols, error)
        return failure("LONGBRIDGE_SNAPSHOT_FAILED", str(error))


def main() -> None:
    """Manual debug entry."""

    pass


if __name__ == "__main__":
    main()
