"""Quote-domain service for LongBridge."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable, Optional

import config
from longbridge.openapi import (
    AdjustType,
    CalcIndex,
    FilterWarrantExpiryDate,
    FilterWarrantInOutBoundsType,
    Market,
    Period,
    QuoteContext,
    SecuritiesUpdateMode,
    SecurityListCategory,
    SortOrderType,
    SubType,
    TradeSessions,
    WarrantSortBy,
    WarrantStatus,
    WarrantType,
)

from services.longbridge_shared import (
    enum_from_name,
    enum_list,
    serialize_sdk_value,
    to_date,
    to_datetime,
)


class LongbridgeQuoteService:
    """Encapsulates quote-related operations."""

    def __init__(self, quote_ctx: QuoteContext) -> None:
        self.quote_ctx = quote_ctx

    def static_info(self, symbols: Iterable[str]) -> Any:
        return self.quote_ctx.static_info(list(symbols))

    def quote(self, symbols: Iterable[str]) -> Any:
        return self.quote_ctx.quote(list(symbols))

    def option_quote(self, symbols: Iterable[str]) -> Any:
        return self.quote_ctx.option_quote(list(symbols))

    def warrant_quote(self, symbols: Iterable[str]) -> Any:
        return self.quote_ctx.warrant_quote(list(symbols))

    def depth(self, symbol: str) -> Any:
        return self.quote_ctx.depth(symbol)

    def brokers(self, symbol: str) -> Any:
        return self.quote_ctx.brokers(symbol)

    def participants(self) -> Any:
        return self.quote_ctx.participants()

    def trades(self, symbol: str, count: int = 100) -> Any:
        return self.quote_ctx.trades(symbol, count)

    def intraday(self, symbol: str, trade_session: Optional[Any] = None) -> Any:
        return self.quote_ctx.intraday(
            symbol,
            enum_from_name(TradeSessions, trade_session) if trade_session is not None else None,
        )

    def candlesticks(self, symbol: str, period: Any, count: int, adjust_type: Any) -> Any:
        return self.quote_ctx.candlesticks(
            symbol,
            enum_from_name(Period, period),
            count,
            enum_from_name(AdjustType, adjust_type),
        )

    def history_candlesticks_by_offset(
        self,
        symbol: str,
        period: Any,
        adjust_type: Any,
        forward: bool,
        count: int,
        time: Any,
    ) -> Any:
        return self.quote_ctx.history_candlesticks_by_offset(
            symbol,
            enum_from_name(Period, period),
            enum_from_name(AdjustType, adjust_type),
            forward,
            count,
            to_datetime(time),
        )

    def history_candlesticks_by_date(
        self,
        symbol: str,
        period: Any,
        adjust_type: Any,
        start: Any,
        end: Any,
    ) -> Any:
        return self.quote_ctx.history_candlesticks_by_date(
            symbol,
            enum_from_name(Period, period),
            enum_from_name(AdjustType, adjust_type),
            to_date(start),
            to_date(end),
        )

    def option_chain_expiry_date_list(self, symbol: str) -> Any:
        return self.quote_ctx.option_chain_expiry_date_list(symbol)

    def option_chain_info_by_date(self, symbol: str, expiry_date: Any) -> Any:
        return self.quote_ctx.option_chain_info_by_date(symbol, to_date(expiry_date))

    def warrant_issuers(self) -> Any:
        return self.quote_ctx.warrant_issuers()

    def warrant_list(
        self,
        symbol: str,
        sort_by: Optional[Any] = None,
        sort_order: Optional[Any] = None,
        warrant_type: Optional[Any] = None,
        issuer: Optional[int] = None,
        expiry_date: Optional[Any] = None,
        price_type: Optional[Any] = None,
        status: Optional[Any] = None,
    ) -> Any:
        kwargs = {}
        if sort_by is not None:
            kwargs["sort_by"] = enum_from_name(WarrantSortBy, sort_by)
        if sort_order is not None:
            kwargs["sort_order"] = enum_from_name(SortOrderType, sort_order)
        if warrant_type is not None:
            kwargs["warrant_type"] = enum_from_name(WarrantType, warrant_type)
        if issuer is not None:
            kwargs["issuer"] = issuer
        if expiry_date is not None:
            kwargs["expiry_date"] = enum_from_name(FilterWarrantExpiryDate, expiry_date)
        if price_type is not None:
            kwargs["price_type"] = enum_from_name(FilterWarrantInOutBoundsType, price_type)
        if status is not None:
            kwargs["status"] = enum_from_name(WarrantStatus, status)
        return self.quote_ctx.warrant_list(symbol, **kwargs)

    def trading_session(self, market: Any) -> Any:
        return self.quote_ctx.trading_session(enum_from_name(Market, market))

    def trading_days(self, market: Any, begin: Any, end: Any) -> Any:
        return self.quote_ctx.trading_days(
            enum_from_name(Market, market),
            to_date(begin),
            to_date(end),
        )

    def capital_flow(self, symbol: str) -> Any:
        return self.quote_ctx.capital_flow(symbol)

    def capital_distribution(self, symbol: str) -> Any:
        return self.quote_ctx.capital_distribution(symbol)

    def calc_indexes(self, symbols: Iterable[str], indexes: Iterable[Any]) -> Any:
        return self.quote_ctx.calc_indexes(list(symbols), enum_list(CalcIndex, indexes))

    def security_list(self, market: Any, category: Any) -> Any:
        return self.quote_ctx.security_list(
            enum_from_name(Market, market),
            enum_from_name(SecurityListCategory, category),
        )

    def market_temperature(self, market: Any) -> Any:
        return self.quote_ctx.market_temperature(enum_from_name(Market, market))

    def history_market_temperature(self, market: Any, period: int) -> Any:
        return self.quote_ctx.history_market_temperature(enum_from_name(Market, market), period)

    def realtime_quote(self, symbols: Iterable[str]) -> Any:
        return self.quote_ctx.realtime_quote(list(symbols))

    def realtime_depth(self, symbol: str) -> Any:
        return self.quote_ctx.realtime_depth(symbol)

    def realtime_brokers(self, symbol: str) -> Any:
        return self.quote_ctx.realtime_brokers(symbol)

    def realtime_trades(self, symbol: str, count: int = 100) -> Any:
        return self.quote_ctx.realtime_trades(symbol, count)

    def realtime_candlesticks(self, symbol: str, period: Any) -> Any:
        return self.quote_ctx.realtime_candlesticks(symbol, enum_from_name(Period, period))

    def set_on_quote(self, callback: Callable[[str, Any], None]) -> None:
        self.quote_ctx.set_on_quote(callback)

    def set_on_depth(self, callback: Callable[[str, Any], None]) -> None:
        self.quote_ctx.set_on_depth(callback)

    def set_on_brokers(self, callback: Callable[[str, Any], None]) -> None:
        self.quote_ctx.set_on_brokers(callback)

    def set_on_trades(self, callback: Callable[[str, Any], None]) -> None:
        self.quote_ctx.set_on_trades(callback)

    def set_on_candlestick(self, callback: Callable[[str, Any], None]) -> None:
        self.quote_ctx.set_on_candlestick(callback)

    def subscribe(self, symbols: Iterable[str], sub_types: Iterable[Any], is_first_push: bool = False) -> Any:
        return self.quote_ctx.subscribe(list(symbols), enum_list(SubType, sub_types), is_first_push=is_first_push)

    def unsubscribe(self, symbols: Iterable[str], sub_types: Iterable[Any]) -> Any:
        return self.quote_ctx.unsubscribe(list(symbols), enum_list(SubType, sub_types))

    def subscriptions(self) -> Any:
        return self.quote_ctx.subscriptions()

    def subscribe_candlesticks(self, symbol: str, period: Any) -> Any:
        return self.quote_ctx.subscribe_candlesticks(symbol, enum_from_name(Period, period))

    def unsubscribe_candlesticks(self, symbol: str, period: Any) -> Any:
        return self.quote_ctx.unsubscribe_candlesticks(symbol, enum_from_name(Period, period))

    def watchlist(self) -> Any:
        return self.quote_ctx.watchlist()

    def create_watchlist_group(self, name: str, securities: Optional[Iterable[str]] = None) -> Any:
        if securities is None:
            return self.quote_ctx.create_watchlist_group(name=name)
        return self.quote_ctx.create_watchlist_group(name=name, securities=list(securities))

    def delete_watchlist_group(self, group_id: int, purge: bool = False) -> Any:
        return self.quote_ctx.delete_watchlist_group(group_id=group_id, purge=purge)

    def update_watchlist_group(
        self,
        group_id: int,
        name: Optional[str] = None,
        securities: Optional[Iterable[str]] = None,
        mode: Optional[Any] = None,
    ) -> Any:
        kwargs = {"group_id": group_id}
        if name is not None:
            kwargs["name"] = name
        if securities is not None:
            kwargs["securities"] = list(securities)
        if mode is not None:
            kwargs["mode"] = enum_from_name(SecuritiesUpdateMode, mode)
        return self.quote_ctx.update_watchlist_group(**kwargs)


def capture_snapshot_item(
    symbol_payload: dict[str, Any],
    *,
    key: str,
    error_key: str,
    fn: Callable[[], Any],
) -> None:
    try:
        symbol_payload[key] = serialize_sdk_value(fn())
    except Exception as error:
        symbol_payload[error_key] = str(error)


def build_symbol_snapshot(
    quote: LongbridgeQuoteService,
    *,
    symbol: str,
    period: str,
    adjust_type: str,
    candlestick_count: int,
    offset_count: int,
    forward: bool,
    snapshot_time: datetime,
) -> dict[str, Any]:
    symbol_payload: dict[str, Any] = {}
    capture_snapshot_item(
        symbol_payload,
        key="realtime_quote",
        error_key="realtime_quote_error",
        fn=lambda: quote.realtime_quote([symbol]),
    )
    capture_snapshot_item(
        symbol_payload,
        key="candlesticks",
        error_key="candlesticks_error",
        fn=lambda: quote.candlesticks(
            symbol=symbol,
            period=period,
            count=candlestick_count,
            adjust_type=adjust_type,
        ),
    )
    capture_snapshot_item(
        symbol_payload,
        key="offset_candlesticks",
        error_key="offset_candlesticks_error",
        fn=lambda: quote.history_candlesticks_by_offset(
            symbol=symbol,
            period=period,
            adjust_type=adjust_type,
            forward=forward,
            count=offset_count,
            time=snapshot_time,
        ),
    )
    return symbol_payload


def build_market_snapshot_payload(
    quote: LongbridgeQuoteService,
    symbols: list[str],
    *,
    period: str | None = None,
    adjust_type: str | None = None,
    candlestick_count: int | None = None,
    offset_count: int | None = None,
    forward: bool | None = None,
) -> dict[str, Any]:
    """Build askstock payload with realtime quote + kline + offset kline."""

    resolved_period = period or str(config.get_text("longbridge.snapshot_period"))
    resolved_adjust_type = adjust_type or str(config.get_text("longbridge.snapshot_adjust_type"))
    resolved_candlestick_count = int(
        candlestick_count
        if candlestick_count is not None
        else config.get_text("longbridge.snapshot_candlestick_count")
    )
    resolved_offset_count = int(
        offset_count
        if offset_count is not None
        else config.get_text("longbridge.snapshot_offset_count")
    )
    resolved_forward = bool(
        forward if forward is not None else config.get_text("longbridge.snapshot_forward")
    )

    snapshot_time = datetime.now()
    payload: dict[str, Any] = {
        "generated_at": snapshot_time.isoformat(timespec="seconds"),
        "period": resolved_period,
        "adjust_type": resolved_adjust_type,
        "candlestick_count": resolved_candlestick_count,
        "offset_count": resolved_offset_count,
        "forward": resolved_forward,
        "symbols": symbols,
        "market_data": {},
    }

    for symbol in symbols:
        payload["market_data"][symbol] = build_symbol_snapshot(
            quote,
            symbol=symbol,
            period=resolved_period,
            adjust_type=resolved_adjust_type,
            candlestick_count=resolved_candlestick_count,
            offset_count=resolved_offset_count,
            forward=resolved_forward,
            snapshot_time=snapshot_time,
        )
    return payload


