"""LongBridge service layer.

Dependencies:
- config.py: auth config builders (OAuth + fallback)
- longbridge.openapi: QuoteContext / TradeContext

Public APIs used by the bot:
- get_inspected_quotes_text(...)
- get_stock_positions(...)
"""

from __future__ import annotations

import inspect
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


class LongbridgeOpenAPIBasic:
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
        self.http_host = (http_host or os.getenv("LONGBRIDGE_HTTP_HOST") or "https://openapi.longportapp.com").rstrip("/")
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
            "Accept": "application/json",
            "User-Agent": "LongbridgeOpenAPIBasic/1.0",
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

def setup_quote_context(client_id: str | None):
    """Create QuoteContext using OAuth-first config strategy."""

    quote_config, source = config.build_config_with_fallback(client_id=client_id)
    return QuoteContext(quote_config), source


def setup_trade_context(client_id: str | None):
    """Create TradeContext using OAuth-first config strategy."""

    trade_config, source = config.build_config_with_fallback(client_id=client_id)
    return TradeContext(trade_config), source


def fetch_security_quotes(ctx: QuoteContext, symbols):
    """Fetch quote objects for provided symbols."""

    return ctx.quote(symbols)


def fetch_stock_positions(ctx: TradeContext):
    """Fetch current stock positions from trade account."""

    return ctx.stock_positions()


def fetch_static_info(ctx: QuoteContext, symbols):
    """Fetch static security information for provided symbols."""

    return ctx.static_info(symbols)


def inspect_and_call_methods(resp):
    """Inspect SDK objects into serializable dicts.

    For each item:
    - collect non-callable attributes
    - best-effort call no-arg methods
    """

    results = []

    for item in resp:
        item_entry = {
            "type": str(type(item)),
            "attributes": {},
            "methods": {},
        }

        members = [m for m in dir(item) if not (m.startswith("__") and m.endswith("__"))]
        for name in members:
            try:
                attr = getattr(item, name)
            except Exception as error:
                item_entry["attributes"][name] = f"<attribute access error: {error}>"
                continue

            if not callable(attr):
                try:
                    item_entry["attributes"][name] = str(attr)
                except Exception:
                    item_entry["attributes"][name] = "<unprintable>"
                continue

            method_entry = {"status": None, "result": None}

            try:
                sig = inspect.signature(attr)
                params = [
                    p
                    for p in sig.parameters.values()
                    if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
                    and p.default is p.empty
                ]
                if params:
                    method_entry["status"] = "skipped"
                    method_entry["result"] = f"requires parameters: {[p.name for p in params]}"
                    item_entry["methods"][name] = method_entry
                    continue
            except (TypeError, ValueError):
                method_entry["status"] = "no_signature"

            try:
                result = attr()
                method_entry["status"] = "called"
                try:
                    method_entry["result"] = json.dumps(result, ensure_ascii=False, default=str, indent=2)
                except Exception:
                    method_entry["result"] = str(result)
            except Exception as error:
                method_entry["status"] = "error"
                method_entry["result"] = str(error)

            item_entry["methods"][name] = method_entry

        results.append(item_entry)

    return results


def show_methods(obj) -> None:
    """Debug helper: print callable methods on an object."""

    obj_type = type(obj)
    print(f"Object type: {obj_type}")

    methods = [
        name
        for name in dir(obj)
        if not (name.startswith("__") and name.endswith("__"))
        and callable(getattr(obj, name, None))
    ]

    if not methods:
        print("No callable methods found.")
        return

    print("Available methods:")
    for name in methods:
        print(f"  - {name}")


def format_item_entry(item_entry) -> str:
    """Format one inspected entry for readable text output."""

    lines = [f"Type: {item_entry.get('type')}\n"]

    attributes = item_entry.get("attributes", {})
    if attributes:
        lines.append("Attributes:")
        for name, value in sorted(attributes.items()):
            if name in ("pre_market_quote", "post_market_quote"):
                try:
                    parsed = json.loads(value) if isinstance(value, str) else value
                    pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
                except Exception:
                    pretty = str(value)

                lines.append(f"  {name}:")
                for subline in pretty.splitlines():
                    lines.append(f"    {subline}")
            else:
                lines.append(f"  {name}: {value}")
    else:
        lines.append("Attributes: (none)")

    return "\n".join(lines)


DEFAULT_CLIENT_ID = config.LONGBRIDGE_CLIENT_ID
DEFAULT_SYMBOLS = config.DEFAULT_SYMBOLS


def get_inspected_quotes(client_id: str | None = None, symbols=None):
    """Fetch quote objects and return inspected structured data."""

    if client_id is None:
        client_id = DEFAULT_CLIENT_ID
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    ctx, source = setup_quote_context(client_id)
    try:
        resp = fetch_security_quotes(ctx, symbols)
    except Exception as oauth_error:
        # Retry once with API-key env config if OAuth path failed.
        if source != "oauth":
            raise
        print(f"OAuth quote request failed, retry with from_apikey_env(): {oauth_error}")
        fallback_ctx = QuoteContext(config.build_apikey_env_config())
        resp = fetch_security_quotes(fallback_ctx, symbols)

    return inspect_and_call_methods(resp)


def get_stock_positions(client_id: str | None = None):
    """Fetch stock positions, with OAuth fallback retry once."""

    if client_id is None:
        client_id = DEFAULT_CLIENT_ID

    ctx, source = setup_trade_context(client_id)
    try:
        return fetch_stock_positions(ctx)
    except Exception as oauth_error:
        if source != "oauth":
            raise
        print(f"OAuth positions request failed, retry with from_apikey_env(): {oauth_error}")
        fallback_ctx = TradeContext(config.build_apikey_env_config())
        return fetch_stock_positions(fallback_ctx)


def get_static_info(client_id: str | None = None, symbols=None):
    """Fetch static info with OAuth fallback retry once.

    If `symbols` is not provided, reuse `DEFAULT_SYMBOLS` from config.
    """

    if client_id is None:
        client_id = DEFAULT_CLIENT_ID
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    ctx, source = setup_quote_context(client_id)
    try:
        resp = fetch_static_info(ctx, symbols)
        return resp
    except Exception as oauth_error:
        if source != "oauth":
            raise
        print(f"OAuth static_info request failed, retry with from_apikey_env(): {oauth_error}")
        fallback_ctx = QuoteContext(config.build_apikey_env_config())
        resp = fetch_static_info(fallback_ctx, symbols)
        return resp


def get_inspected_quotes_text(client_id: str | None = None, symbols=None) -> str:
    """Return inspected quote result as pretty JSON text."""

    inspected = get_inspected_quotes(client_id=client_id, symbols=symbols)
    try:
        return json.dumps(inspected, ensure_ascii=False, indent=2)
    except Exception:
        return str(inspected)


def main() -> None:
    """Manual debug entry for quote inspection."""

    inspected = get_inspected_quotes()
    for idx, item in enumerate(inspected, start=1):
        print("=" * 80)
        print(f"Item {idx}/{len(inspected)}")
        print("=" * 80)
        print(format_item_entry(item))


if __name__ == "__main__":
    main()
