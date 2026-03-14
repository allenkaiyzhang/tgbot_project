"""LongBridge service layer.

Dependencies:
- config.py: auth config builders (OAuth + fallback)
- longbridge.openapi: QuoteContext / TradeContext

Public APIs used by the bot:
- get_inspected_quotes_text(...)
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from decimal import Decimal
from pprint import pprint
from typing import Any, Callable, Iterable, List, Optional
from urllib.request import Request, urlopen

import config
from longbridge.openapi import (
    AdjustType,
    CalcIndex,
    Config,
    FilterWarrantExpiryDate,
    FilterWarrantInOutBoundsType,
    Market,
    OrderSide,
    OrderStatus,
    OrderType,
    OutsideRTH,
    Period,
    QuoteContext,
    SecuritiesUpdateMode,
    SecurityListCategory,
    SortOrderType,
    SubType,
    TimeInForceType,
    TopicType,
    TradeContext,
    TradeSessions,
    WarrantSortBy,
    WarrantStatus,
    WarrantType,
)

# Merged from longbridge_openapi_basic_qtn.py (deduplicated into service module).
def _to_decimal(value: Optional[Any]) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _to_date(value: Optional[Any]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"不支持的 date 类型: {type(value)}")


def _to_datetime(value: Optional[Any]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace(" ", "T"))
    raise TypeError(f"不支持的 datetime 类型: {type(value)}")


def _to_list(value: Optional[Iterable[Any]]) -> Optional[List[Any]]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _enum_from_name(enum_cls: Any, value: Optional[Any]) -> Optional[Any]:
    """
    允许你传:
    - SDK 枚举对象
    - 枚举名称字符串，例如 "Buy" / "LO" / "Day"
    - None
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    return getattr(enum_cls, value)


def _enum_list(enum_cls: Any, values: Optional[Iterable[Any]]) -> Optional[List[Any]]:
    if values is None:
        return None
    return [_enum_from_name(enum_cls, v) for v in values]


class LB:
    """
    Quote + Trade + News 的统一基础封装。

    用法示例
    --------
    client = LongbridgeOpenAPIBasic(client_id="YOUR_CLIENT_ID")
    resp = client.quote(["700.HK", "AAPL.US"])
    news = client.news("AAPL.US")
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        http_host: Optional[str] = None,
        access_token: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        参数:
        - client_id:
          OAuth 2.0 Client ID。传入后走 OAuth 授权。
        - http_host:
          HTTP API Host。默认 `https://openapi.longportapp.com`。
          中国大陆可切换到 `https://openapi.longportapp.cn`。
        - access_token:
          News HTTP 接口可显式传入 Bearer Token。
          若不传，则优先从环境变量读取。
        - timeout:
          News HTTP 请求超时时间（秒）。
        """
        self.client_id = client_id
        self.timeout = timeout
        text_http_host = config.get_text("longbridge.http_host")
        self.http_host = (http_host or os.getenv("LONGBRIDGE_HTTP_HOST") or text_http_host).rstrip("/")
        self.access_token = (
            access_token
            or os.getenv("LONGBRIDGE_ACCESS_TOKEN")
            or os.getenv("LONGPORT_ACCESS_TOKEN")
            or os.getenv("ACCESS_TOKEN")
        )

        self.config = self._build_config()
        self.quote_ctx = QuoteContext(self.config)
        self.trade_ctx = TradeContext(self.config)

    # ==========
    # Core / Auth
    # ==========
    def _build_config(self) -> Config:
        resolved_config, _source = config.build_config_with_fallback(client_id=self.client_id)
        return resolved_config

    def pretty(self, obj: Any) -> Any:
        pprint(obj)
        return obj

    # =========================
    # Quote - Pull
    # =========================
    def static_info(self, symbols: Iterable[str]) -> Any:
        """获取标的基础信息。"""
        return self.quote_ctx.static_info(list(symbols))

    def quote(self, symbols: Iterable[str]) -> Any:
        """获取标的实时行情。"""
        return self.quote_ctx.quote(list(symbols))

    def option_quote(self, symbols: Iterable[str]) -> Any:
        """获取期权实时行情。"""
        return self.quote_ctx.option_quote(list(symbols))

    def warrant_quote(self, symbols: Iterable[str]) -> Any:
        """获取轮证实时行情。"""
        return self.quote_ctx.warrant_quote(list(symbols))

    def depth(self, symbol: str) -> Any:
        """获取标的盘口。"""
        return self.quote_ctx.depth(symbol)

    def brokers(self, symbol: str) -> Any:
        """获取标的经纪队列。"""
        return self.quote_ctx.brokers(symbol)

    def participants(self) -> Any:
        """获取券商席位 ID。"""
        return self.quote_ctx.participants()

    def trades(self, symbol: str, count: int = 100) -> Any:
        """获取标的成交明细。"""
        return self.quote_ctx.trades(symbol, count)

    def intraday(self, symbol: str, trade_session: Optional[Any] = None) -> Any:
        """获取标的当日分时。"""
        return self.quote_ctx.intraday(
            symbol,
            _enum_from_name(TradeSessions, trade_session) if trade_session is not None else None,
        )

    def candlesticks(self, symbol: str, period: Any, count: int, adjust_type: Any) -> Any:
        """获取标的 K 线。"""
        return self.quote_ctx.candlesticks(
            symbol,
            _enum_from_name(Period, period),
            count,
            _enum_from_name(AdjustType, adjust_type),
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
        """按时间偏移获取历史 K 线。"""
        return self.quote_ctx.history_candlesticks_by_offset(
            symbol,
            _enum_from_name(Period, period),
            _enum_from_name(AdjustType, adjust_type),
            forward,
            count,
            _to_datetime(time),
        )

    def history_candlesticks_by_date(
        self,
        symbol: str,
        period: Any,
        adjust_type: Any,
        start: Any,
        end: Any,
    ) -> Any:
        """按日期区间获取历史 K 线。"""
        return self.quote_ctx.history_candlesticks_by_date(
            symbol,
            _enum_from_name(Period, period),
            _enum_from_name(AdjustType, adjust_type),
            _to_date(start),
            _to_date(end),
        )

    def option_chain_expiry_date_list(self, symbol: str) -> Any:
        """获取标的的期权链到期日列表。"""
        return self.quote_ctx.option_chain_expiry_date_list(symbol)

    def option_chain_info_by_date(self, symbol: str, expiry_date: Any) -> Any:
        """获取标的的期权链到期日期权标的列表。"""
        return self.quote_ctx.option_chain_info_by_date(symbol, _to_date(expiry_date))

    def warrant_issuers(self) -> Any:
        """获取轮证发行商 ID。"""
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
        """获取轮证筛选列表。"""
        kwargs = {}
        if sort_by is not None:
            kwargs["sort_by"] = _enum_from_name(WarrantSortBy, sort_by)
        if sort_order is not None:
            kwargs["sort_order"] = _enum_from_name(SortOrderType, sort_order)
        if warrant_type is not None:
            kwargs["warrant_type"] = _enum_from_name(WarrantType, warrant_type)
        if issuer is not None:
            kwargs["issuer"] = issuer
        if expiry_date is not None:
            kwargs["expiry_date"] = _enum_from_name(FilterWarrantExpiryDate, expiry_date)
        if price_type is not None:
            kwargs["price_type"] = _enum_from_name(FilterWarrantInOutBoundsType, price_type)
        if status is not None:
            kwargs["status"] = _enum_from_name(WarrantStatus, status)
        return self.quote_ctx.warrant_list(symbol, **kwargs)

    def trading_session(self, market: Any) -> Any:
        """获取各市场当日交易时段。"""
        return self.quote_ctx.trading_session(_enum_from_name(Market, market))

    def trading_days(self, market: Any, begin: Any, end: Any) -> Any:
        """获取市场交易日。"""
        return self.quote_ctx.trading_days(
            _enum_from_name(Market, market),
            _to_date(begin),
            _to_date(end),
        )

    def capital_flow(self, symbol: str) -> Any:
        """获取标的当日资金流向。"""
        return self.quote_ctx.capital_flow(symbol)

    def capital_distribution(self, symbol: str) -> Any:
        """获取标的当日资金分布。"""
        return self.quote_ctx.capital_distribution(symbol)

    def calc_indexes(self, symbols: Iterable[str], indexes: Iterable[Any]) -> Any:
        """获取标的计算指标。"""
        return self.quote_ctx.calc_indexes(
            list(symbols),
            _enum_list(CalcIndex, indexes),
        )

    def security_list(self, market: Any, category: Any) -> Any:
        """获取标的列表。"""
        return self.quote_ctx.security_list(
            _enum_from_name(Market, market),
            _enum_from_name(SecurityListCategory, category),
        )

    def market_temperature(self, market: Any) -> Any:
        """当前市场温度。"""
        return self.quote_ctx.market_temperature(_enum_from_name(Market, market))

    def history_market_temperature(self, market: Any, period: int) -> Any:
        """历史市场温度。"""
        return self.quote_ctx.history_market_temperature(
            _enum_from_name(Market, market),
            period,
        )

    def realtime_quote(self, symbols: Iterable[str]) -> Any:
        """实时价格拉取。"""
        return self.quote_ctx.realtime_quote(list(symbols))

    def realtime_depth(self, symbol: str) -> Any:
        """实时盘口拉取。"""
        return self.quote_ctx.realtime_depth(symbol)

    def realtime_brokers(self, symbol: str) -> Any:
        """实时经纪队列拉取。"""
        return self.quote_ctx.realtime_brokers(symbol)

    def realtime_trades(self, symbol: str, count: int = 100) -> Any:
        """实时成交明细拉取。"""
        return self.quote_ctx.realtime_trades(symbol, count)

    def realtime_candlesticks(self, symbol: str, period: Any) -> Any:
        """实时 K 线拉取。"""
        return self.quote_ctx.realtime_candlesticks(
            symbol,
            _enum_from_name(Period, period),
        )

    # =========================
    # Quote - Subscription / Push
    # =========================
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

    def subscribe(
        self,
        symbols: Iterable[str],
        sub_types: Iterable[Any],
        is_first_push: bool = False,
    ) -> Any:
        """订阅行情数据。"""
        return self.quote_ctx.subscribe(
            list(symbols),
            _enum_list(SubType, sub_types),
            is_first_push=is_first_push,
        )

    def unsubscribe(self, symbols: Iterable[str], sub_types: Iterable[Any]) -> Any:
        """取消订阅行情数据。"""
        return self.quote_ctx.unsubscribe(
            list(symbols),
            _enum_list(SubType, sub_types),
        )

    def subscriptions(self) -> Any:
        """获取已订阅标的行情。"""
        return self.quote_ctx.subscriptions()

    def subscribe_candlesticks(self, symbol: str, period: Any) -> Any:
        """订阅 K 线推送。"""
        return self.quote_ctx.subscribe_candlesticks(
            symbol,
            _enum_from_name(Period, period),
        )

    def unsubscribe_candlesticks(self, symbol: str, period: Any) -> Any:
        """取消 K 线推送。"""
        return self.quote_ctx.unsubscribe_candlesticks(
            symbol,
            _enum_from_name(Period, period),
        )

    # =========================
    # Quote - Watchlist / Individual
    # =========================
    def watchlist(self) -> Any:
        """获取自选股分组。"""
        return self.quote_ctx.watchlist()

    def create_watchlist_group(
        self,
        name: str,
        securities: Optional[Iterable[str]] = None,
    ) -> Any:
        """创建自选股分组。"""
        if securities is None:
            return self.quote_ctx.create_watchlist_group(name=name)
        return self.quote_ctx.create_watchlist_group(name=name, securities=list(securities))

    def delete_watchlist_group(self, group_id: int, purge: bool = False) -> Any:
        """删除自选股分组。"""
        return self.quote_ctx.delete_watchlist_group(group_id=group_id, purge=purge)

    def update_watchlist_group(
        self,
        group_id: int,
        name: Optional[str] = None,
        securities: Optional[Iterable[str]] = None,
        mode: Optional[Any] = None,
    ) -> Any:
        """更新自选股分组。"""
        kwargs = {"group_id": group_id}
        if name is not None:
            kwargs["name"] = name
        if securities is not None:
            kwargs["securities"] = list(securities)
        if mode is not None:
            kwargs["mode"] = _enum_from_name(SecuritiesUpdateMode, mode)
        return self.quote_ctx.update_watchlist_group(**kwargs)

    # =========================
    # Trade - Execution
    # =========================
    def history_executions(
        self,
        symbol: Optional[str] = None,
        start_at: Optional[Any] = None,
        end_at: Optional[Any] = None,
    ) -> Any:
        """获取历史成交明细。"""
        return self.trade_ctx.history_executions(
            symbol=symbol,
            start_at=_to_datetime(start_at),
            end_at=_to_datetime(end_at),
        )

    def today_executions(
        self,
        symbol: Optional[str] = None,
        order_id: Optional[str] = None,
    ) -> Any:
        """获取当日成交明细。"""
        return self.trade_ctx.today_executions(symbol=symbol, order_id=order_id)

    # =========================
    # Trade - Order
    # =========================
    def estimate_max_purchase_quantity(
        self,
        symbol: str,
        order_type: Any,
        side: Any,
        price: Optional[Any] = None,
        currency: Optional[str] = None,
    ) -> Any:
        """预估最大购买数量。"""
        return self.trade_ctx.estimate_max_purchase_quantity(
            symbol=symbol,
            order_type=_enum_from_name(OrderType, order_type),
            side=_enum_from_name(OrderSide, side),
            price=_to_decimal(price),
            currency=currency,
        )

    def submit_order(
        self,
        symbol: str,
        order_type: Any,
        side: Any,
        submitted_quantity: Any,
        time_in_force: Any,
        submitted_price: Optional[Any] = None,
        trigger_price: Optional[Any] = None,
        limit_offset: Optional[Any] = None,
        trailing_amount: Optional[Any] = None,
        trailing_percent: Optional[Any] = None,
        expire_date: Optional[Any] = None,
        outside_rth: Optional[Any] = None,
        remark: Optional[str] = None,
        limit_depth_level: Optional[int] = None,
        monitor_price: Optional[Any] = None,
        trigger_count: Optional[int] = None,
    ) -> Any:
        """委托下单。"""
        return self.trade_ctx.submit_order(
            symbol,
            _enum_from_name(OrderType, order_type),
            _enum_from_name(OrderSide, side),
            _to_decimal(submitted_quantity),
            _enum_from_name(TimeInForceType, time_in_force),
            submitted_price=_to_decimal(submitted_price),
            trigger_price=_to_decimal(trigger_price),
            limit_offset=_to_decimal(limit_offset),
            trailing_amount=_to_decimal(trailing_amount),
            trailing_percent=_to_decimal(trailing_percent),
            expire_date=_to_date(expire_date),
            outside_rth=_enum_from_name(OutsideRTH, outside_rth),
            remark=remark,
            limit_depth_level=limit_depth_level,
            monitor_price=_to_decimal(monitor_price),
            trigger_count=trigger_count,
        )

    def replace_order(
        self,
        order_id: str,
        quantity: Any,
        price: Optional[Any] = None,
        trigger_price: Optional[Any] = None,
        limit_offset: Optional[Any] = None,
        trailing_amount: Optional[Any] = None,
        trailing_percent: Optional[Any] = None,
        remark: Optional[str] = None,
        limit_depth_level: Optional[int] = None,
        monitor_price: Optional[Any] = None,
        trigger_count: Optional[int] = None,
    ) -> Any:
        """修改订单。"""
        return self.trade_ctx.replace_order(
            order_id=order_id,
            quantity=_to_decimal(quantity),
            price=_to_decimal(price),
            trigger_price=_to_decimal(trigger_price),
            limit_offset=_to_decimal(limit_offset),
            trailing_amount=_to_decimal(trailing_amount),
            trailing_percent=_to_decimal(trailing_percent),
            remark=remark,
            limit_depth_level=limit_depth_level,
            monitor_price=_to_decimal(monitor_price),
            trigger_count=trigger_count,
        )

    def cancel_order(self, order_id: str) -> Any:
        """撤销订单。"""
        return self.trade_ctx.cancel_order(order_id)

    def today_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[Iterable[Any]] = None,
        side: Optional[Any] = None,
        market: Optional[Any] = None,
        order_id: Optional[str] = None,
    ) -> Any:
        """获取当日订单。"""
        return self.trade_ctx.today_orders(
            symbol=symbol,
            status=_enum_list(OrderStatus, status),
            side=_enum_from_name(OrderSide, side),
            market=_enum_from_name(Market, market),
            order_id=order_id,
        )

    def history_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[Iterable[Any]] = None,
        side: Optional[Any] = None,
        market: Optional[Any] = None,
        start_at: Optional[Any] = None,
        end_at: Optional[Any] = None,
    ) -> Any:
        """获取历史订单。"""
        return self.trade_ctx.history_orders(
            symbol=symbol,
            status=_enum_list(OrderStatus, status),
            side=_enum_from_name(OrderSide, side),
            market=_enum_from_name(Market, market),
            start_at=_to_datetime(start_at),
            end_at=_to_datetime(end_at),
        )

    def order_detail(self, order_id: str) -> Any:
        """订单详情。"""
        return self.trade_ctx.order_detail(order_id)

    # =========================
    # Trade - Asset
    # =========================
    def account_balance(self, currency: Optional[str] = None) -> Any:
        """获取账户资金。"""
        return self.trade_ctx.account_balance(currency=currency)

    def cash_flow(
        self,
        start_at: Any,
        end_at: Any,
        business_type: Optional[int] = None,
        symbol: Optional[str] = None,
        page: Optional[int] = None,
        size: Optional[int] = None,
    ) -> Any:
        """获取资金流水。"""
        return self.trade_ctx.cash_flow(
            start_at=_to_datetime(start_at),
            end_at=_to_datetime(end_at),
            business_type=business_type,
            symbol=symbol,
            page=page,
            size=size,
        )

    def fund_positions(self, symbols: Optional[Iterable[str]] = None) -> Any:
        """获取基金持仓。"""
        return self.trade_ctx.fund_positions(symbols=_to_list(symbols))

    def margin_ratio(self, symbol: str) -> Any:
        """获取保证金比例。"""
        return self.trade_ctx.margin_ratio(symbol)

    def stock_positions(self, symbols: Optional[Iterable[str]] = None) -> Any:
        """获取股票持仓。"""
        return self.trade_ctx.stock_positions(symbols=_to_list(symbols))

    # =========================
    # Trade - Push
    # =========================
    def subscribe_private(self, callback: Optional[Callable[[Any], None]] = None) -> Any:
        """
        订阅交易推送。
        - callback:
          若传入，则先注册 `set_on_order_changed`。
        """
        if callback is not None:
            self.trade_ctx.set_on_order_changed(callback)
        return self.trade_ctx.subscribe([TopicType.Private])

    def unsubscribe_private(self) -> Any:
        """取消订阅交易推送。"""
        return self.trade_ctx.unsubscribe([TopicType.Private])

    # =========================
    # News - HTTP
    # =========================
    def _news_headers(self) -> dict:
        headers = {
            "Accept": config.get_text("longbridge.news_accept"),
            "User-Agent": config.get_text("longbridge.news_user_agent"),
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def news(self, symbol: str) -> Any:
        """
        获取指定股票的资讯列表。

        文档接口:
        GET /v1/content/{symbol}/news

        参数:
        - symbol:
          股票代码，格式如 `AAPL.US` / `700.HK`
        """
        url = f"{self.http_host}/v1/content/{symbol}/news"
        request = Request(url, headers=self._news_headers(), method="GET")
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))


CLIENT_ID = config.LONGBRIDGE_CLIENT_ID
SYMBOLS = config.SYMBOLS


def _serialize_sdk_value(value: Any, *, depth: int = 0, max_depth: int = 4) -> Any:
    """Convert SDK objects into JSON-serializable structures."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (Decimal, date, datetime)):
        return str(value)

    if isinstance(value, dict):
        return {str(k): _serialize_sdk_value(v, depth=depth + 1, max_depth=max_depth) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_serialize_sdk_value(v, depth=depth + 1, max_depth=max_depth) for v in value]

    if depth >= max_depth:
        return str(value)

    attrs: dict[str, Any] = {}
    for name in dir(value):
        if name.startswith("_"):
            continue
        try:
            attr = getattr(value, name)
        except Exception:
            continue
        if callable(attr):
            continue
        attrs[name] = _serialize_sdk_value(attr, depth=depth + 1, max_depth=max_depth)

    if attrs:
        return attrs
    return str(value)


def _build_market_snapshot_payload(
    client: LB,
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
        symbol_payload: dict[str, Any] = {}

        try:
            symbol_payload["realtime_quote"] = _serialize_sdk_value(client.realtime_quote([symbol]))
        except Exception as error:
            symbol_payload["realtime_quote_error"] = str(error)

        try:
            symbol_payload["candlesticks"] = _serialize_sdk_value(
                client.candlesticks(
                    symbol=symbol,
                    period=resolved_period,
                    count=resolved_candlestick_count,
                    adjust_type=resolved_adjust_type,
                )
            )
        except Exception as error:
            symbol_payload["candlesticks_error"] = str(error)

        try:
            symbol_payload["offset_candlesticks"] = _serialize_sdk_value(
                client.history_candlesticks_by_offset(
                    symbol=symbol,
                    period=resolved_period,
                    adjust_type=resolved_adjust_type,
                    forward=resolved_forward,
                    count=resolved_offset_count,
                    time=snapshot_time,
                )
            )
        except Exception as error:
            symbol_payload["offset_candlesticks_error"] = str(error)

        payload["market_data"][symbol] = symbol_payload

    return payload


def get_inspected_quotes_text(client_id: str | None = None, symbols=None) -> str:
    """Return askstock market snapshot as pretty JSON text.

    Includes per-symbol:
    - realtime quote
    - candlesticks
    - history candlesticks by offset
    """

    resolved_client_id = client_id or CLIENT_ID
    resolved_symbols = list(SYMBOLS if symbols is None else symbols)
    client = LB(client_id=resolved_client_id)
    snapshot = _build_market_snapshot_payload(client, resolved_symbols)

    try:
        return json.dumps(snapshot, ensure_ascii=False, indent=2)
    except Exception:
        return str(snapshot)


def main() -> None:
    """Manual debug entry."""
    pass


if __name__ == "__main__":
    main()
