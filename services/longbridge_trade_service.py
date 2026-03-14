"""Trade-domain service for LongBridge."""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from longbridge.openapi import (
    Market,
    OrderSide,
    OrderStatus,
    OrderType,
    OutsideRTH,
    TimeInForceType,
    TopicType,
    TradeContext,
)

from services.longbridge_shared import enum_from_name, enum_list, to_date, to_datetime, to_decimal, to_list


class LongbridgeTradeService:
    """Encapsulates trade-related operations."""

    def __init__(self, trade_ctx: TradeContext) -> None:
        self.trade_ctx = trade_ctx

    def history_executions(
        self,
        symbol: Optional[str] = None,
        start_at: Optional[Any] = None,
        end_at: Optional[Any] = None,
    ) -> Any:
        return self.trade_ctx.history_executions(
            symbol=symbol,
            start_at=to_datetime(start_at),
            end_at=to_datetime(end_at),
        )

    def today_executions(self, symbol: Optional[str] = None, order_id: Optional[str] = None) -> Any:
        return self.trade_ctx.today_executions(symbol=symbol, order_id=order_id)

    def estimate_max_purchase_quantity(
        self,
        symbol: str,
        order_type: Any,
        side: Any,
        price: Optional[Any] = None,
        currency: Optional[str] = None,
    ) -> Any:
        return self.trade_ctx.estimate_max_purchase_quantity(
            symbol=symbol,
            order_type=enum_from_name(OrderType, order_type),
            side=enum_from_name(OrderSide, side),
            price=to_decimal(price),
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
        return self.trade_ctx.submit_order(
            symbol,
            enum_from_name(OrderType, order_type),
            enum_from_name(OrderSide, side),
            to_decimal(submitted_quantity),
            enum_from_name(TimeInForceType, time_in_force),
            submitted_price=to_decimal(submitted_price),
            trigger_price=to_decimal(trigger_price),
            limit_offset=to_decimal(limit_offset),
            trailing_amount=to_decimal(trailing_amount),
            trailing_percent=to_decimal(trailing_percent),
            expire_date=to_date(expire_date),
            outside_rth=enum_from_name(OutsideRTH, outside_rth),
            remark=remark,
            limit_depth_level=limit_depth_level,
            monitor_price=to_decimal(monitor_price),
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
        return self.trade_ctx.replace_order(
            order_id=order_id,
            quantity=to_decimal(quantity),
            price=to_decimal(price),
            trigger_price=to_decimal(trigger_price),
            limit_offset=to_decimal(limit_offset),
            trailing_amount=to_decimal(trailing_amount),
            trailing_percent=to_decimal(trailing_percent),
            remark=remark,
            limit_depth_level=limit_depth_level,
            monitor_price=to_decimal(monitor_price),
            trigger_count=trigger_count,
        )

    def cancel_order(self, order_id: str) -> Any:
        return self.trade_ctx.cancel_order(order_id)

    def today_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[Iterable[Any]] = None,
        side: Optional[Any] = None,
        market: Optional[Any] = None,
        order_id: Optional[str] = None,
    ) -> Any:
        return self.trade_ctx.today_orders(
            symbol=symbol,
            status=enum_list(OrderStatus, status),
            side=enum_from_name(OrderSide, side),
            market=enum_from_name(Market, market),
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
        return self.trade_ctx.history_orders(
            symbol=symbol,
            status=enum_list(OrderStatus, status),
            side=enum_from_name(OrderSide, side),
            market=enum_from_name(Market, market),
            start_at=to_datetime(start_at),
            end_at=to_datetime(end_at),
        )

    def order_detail(self, order_id: str) -> Any:
        return self.trade_ctx.order_detail(order_id)

    def account_balance(self, currency: Optional[str] = None) -> Any:
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
        return self.trade_ctx.cash_flow(
            start_at=to_datetime(start_at),
            end_at=to_datetime(end_at),
            business_type=business_type,
            symbol=symbol,
            page=page,
            size=size,
        )

    def fund_positions(self, symbols: Optional[Iterable[str]] = None) -> Any:
        return self.trade_ctx.fund_positions(symbols=to_list(symbols))

    def margin_ratio(self, symbol: str) -> Any:
        return self.trade_ctx.margin_ratio(symbol)

    def stock_positions(self, symbols: Optional[Iterable[str]] = None) -> Any:
        return self.trade_ctx.stock_positions(symbols=to_list(symbols))

    def subscribe_private(self, callback: Optional[Callable[[Any], None]] = None) -> Any:
        if callback is not None:
            self.trade_ctx.set_on_order_changed(callback)
        return self.trade_ctx.subscribe([TopicType.Private])

    def unsubscribe_private(self) -> Any:
        return self.trade_ctx.unsubscribe([TopicType.Private])


