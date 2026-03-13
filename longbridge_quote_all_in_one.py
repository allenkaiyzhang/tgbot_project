#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Longbridge Quote API 单文件工具箱（Python / 同步版）
================================================

用途
----
把 Longbridge OpenAPI 文档中 Quote 模块分散的 Python 能力，集中到一个可运行的单文件里，
便于你在本地 / ECS / VSCode / Codex 环境下统一测试。

支持内容（按 QuoteContext 当前 Python SDK 能力整理）
--------------------------------------------------
1. 拉取类（Pull）
   - static_info
   - quote
   - option_quote
   - warrant_quote
   - depth
   - brokers
   - participants
   - trades
   - intraday
   - candlesticks
   - history_candlesticks_by_offset
   - history_candlesticks_by_date
   - option_chain_expiry_date_list
   - option_chain_info_by_date
   - warrant_issuers
   - warrant_list
   - trading_session
   - trading_days
   - capital_flow
   - capital_distribution
   - calc_indexes
   - security_list
   - market_temperature
   - history_market_temperature
   - realtime_quote
   - realtime_depth
   - realtime_brokers
   - realtime_trades
   - realtime_candlesticks

2. 订阅类（Subscription / Push）
   - subscribe
   - unsubscribe
   - subscriptions
   - subscribe_candlesticks
   - unsubscribe_candlesticks
   - set_on_quote / set_on_depth / set_on_brokers / set_on_trades / set_on_candlestick

3. 自选股（Watchlist / Individual）
   - watchlist
   - create_watchlist_group
   - delete_watchlist_group
   - update_watchlist_group

认证方式
--------
A. OAuth 2.0（推荐）
   python longbridge_quote_all_in_one.py quote --client-id YOUR_CLIENT_ID --symbols 700.HK,AAPL.US

B. 传统 API Key 环境变量
   export LONGBRIDGE_APP_KEY="..."
   export LONGBRIDGE_APP_SECRET="..."
   export LONGBRIDGE_ACCESS_TOKEN="..."
   python longbridge_quote_all_in_one.py quote --symbols 700.HK,AAPL.US

依赖安装
--------
pip install longbridge

说明
----
1. 本文件优先基于 Longbridge 当前 Python SDK 的 `QuoteContext` 方法签名组织。
2. 订阅/推送相关功能需要保持进程存活；否则你看不到 push 数据。
3. 结果对象多数是 SDK 自定义类型，本文件默认优先 `pprint()`，必要时退回 `repr()`。
4. 某些接口受市场、账号权限、行情包等级、标的类型限制；报错时请先检查权限与订阅等级。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime
from decimal import Decimal
from pprint import pprint
from typing import Any, Iterable, List, Optional

try:
    from longbridge.openapi import (
        AdjustType,
        CalcIndex,
        Config,
        FilterWarrantExpiryDate,
        FilterWarrantInOutBoundsType,
        Market,
        OAuthBuilder,
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
except ImportError as exc:
    print(
        "未检测到 longbridge SDK，请先执行: pip install longbridge\n"
        f"原始错误: {exc}",
        file=sys.stderr,
    )
    raise


# ==============================
# 通用工具函数
# ==============================

def parse_csv(value: Optional[str]) -> List[str]:
    """把逗号分隔字符串转成列表。

    示例:
        "700.HK,AAPL.US" -> ["700.HK", "AAPL.US"]
    """
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_date(value: Optional[str]) -> Optional[date]:
    """解析 YYYY-MM-DD 格式日期。"""
    if not value:
        return None
    return date.fromisoformat(value)


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """解析 ISO 8601 日期时间。

    支持示例:
        2026-03-13T09:30:00
        2026-03-13 09:30:00
    """
    if not value:
        return None
    value = value.strip().replace(" ", "T")
    return datetime.fromisoformat(value)


def enum_from_name(enum_cls: Any, name: str) -> Any:
    """把字符串映射到 Longbridge SDK 中的“类枚举”。

    Longbridge 的 Python SDK 这类枚举不是标准 Enum，而是类似：
        Period.Day
        Market.HK
        SubType.Quote

    所以这里通过 getattr 做映射。
    """
    if not name:
        raise ValueError(f"缺少 {enum_cls.__name__} 的名称")
    try:
        return getattr(enum_cls, name)
    except AttributeError as exc:
        available = [k for k in dir(enum_cls) if not k.startswith("_")]
        raise ValueError(
            f"{enum_cls.__name__} 不支持 '{name}'，可选值: {', '.join(sorted(available))}"
        ) from exc


def enum_list_from_csv(enum_cls: Any, csv_value: Optional[str]) -> Optional[List[Any]]:
    """把逗号分隔字符串转成枚举列表；空值返回 None。"""
    items = parse_csv(csv_value)
    if not items:
        return None
    return [enum_from_name(enum_cls, item) for item in items]


def to_jsonable(obj: Any) -> Any:
    """尽量把 SDK 返回对象转成 JSON 可打印结构。"""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, tuple):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}

    # SDK 对象通常会有 __dict__ 或者属性字段
    if hasattr(obj, "__dict__"):
        return {k: to_jsonable(v) for k, v in vars(obj).items() if not k.startswith("_")}

    # 最后退回 repr，避免直接报错
    return repr(obj)


def print_result(obj: Any, as_json: bool = False) -> None:
    """统一输出函数。

    --json 开启时尝试 JSON 化；否则使用 pprint，保留 SDK 对象原貌更利于调试。
    """
    if as_json:
        print(json.dumps(to_jsonable(obj), ensure_ascii=False, indent=2))
    else:
        pprint(obj)


def build_config(client_id: Optional[str]) -> Config:
    """创建 SDK 配置。

    优先级：
    1. 若传入 --client-id，则走 OAuth 2.0。
    2. 否则走 Config.from_apikey_env()，读取环境变量。
    """
    if client_id:
        oauth = OAuthBuilder(client_id).build(
            lambda url: print(f"请在浏览器中打开并授权: {url}", file=sys.stderr)
        )
        return Config.from_oauth(oauth)
    return Config.from_apikey_env()


def build_ctx(client_id: Optional[str]) -> QuoteContext:
    """创建 QuoteContext。"""
    return QuoteContext(build_config(client_id))


# ==============================
# Push / 订阅回调
# ==============================

def install_push_callbacks(ctx: QuoteContext) -> None:
    """安装所有常见 push 回调，便于订阅时直接观察输出。"""

    def on_quote(symbol: str, event: Any) -> None:
        print(f"\n[QUOTE PUSH] {symbol}")
        print_result(event)

    def on_depth(symbol: str, event: Any) -> None:
        print(f"\n[DEPTH PUSH] {symbol}")
        print_result(event)

    def on_brokers(symbol: str, event: Any) -> None:
        print(f"\n[BROKERS PUSH] {symbol}")
        print_result(event)

    def on_trades(symbol: str, event: Any) -> None:
        print(f"\n[TRADES PUSH] {symbol}")
        print_result(event)

    def on_candlestick(symbol: str, event: Any) -> None:
        print(f"\n[CANDLESTICK PUSH] {symbol}")
        print_result(event)

    ctx.set_on_quote(on_quote)
    ctx.set_on_depth(on_depth)
    ctx.set_on_brokers(on_brokers)
    ctx.set_on_trades(on_trades)
    ctx.set_on_candlestick(on_candlestick)


# ==============================
# CLI 具体执行逻辑
# ==============================

def cmd_info(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(
        {
            "member_id": ctx.member_id(),
            "quote_level": ctx.quote_level(),
            "quote_package_details": ctx.quote_package_details(),
        },
        as_json=args.json,
    )


def cmd_static_info(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.static_info(parse_csv(args.symbols)), as_json=args.json)


def cmd_quote(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.quote(parse_csv(args.symbols)), as_json=args.json)


def cmd_option_quote(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.option_quote(parse_csv(args.symbols)), as_json=args.json)


def cmd_warrant_quote(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.warrant_quote(parse_csv(args.symbols)), as_json=args.json)


def cmd_depth(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.depth(args.symbol), as_json=args.json)


def cmd_brokers(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.brokers(args.symbol), as_json=args.json)


def cmd_participants(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.participants(), as_json=args.json)


def cmd_trades(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.trades(args.symbol, args.count), as_json=args.json)


def cmd_intraday(ctx: QuoteContext, args: argparse.Namespace) -> None:
    trade_sessions = enum_from_name(TradeSessions, args.trade_sessions)
    print_result(ctx.intraday(args.symbol, trade_sessions), as_json=args.json)


def cmd_candlesticks(ctx: QuoteContext, args: argparse.Namespace) -> None:
    period = enum_from_name(Period, args.period)
    adjust_type = enum_from_name(AdjustType, args.adjust_type)
    trade_sessions = enum_from_name(TradeSessions, args.trade_sessions)
    print_result(
        ctx.candlesticks(args.symbol, period, args.count, adjust_type, trade_sessions),
        as_json=args.json,
    )


def cmd_history_candlesticks_by_offset(ctx: QuoteContext, args: argparse.Namespace) -> None:
    period = enum_from_name(Period, args.period)
    adjust_type = enum_from_name(AdjustType, args.adjust_type)
    trade_sessions = enum_from_name(TradeSessions, args.trade_sessions)
    anchor_time = parse_datetime(args.time)
    print_result(
        ctx.history_candlesticks_by_offset(
            args.symbol,
            period,
            adjust_type,
            args.forward,
            args.count,
            anchor_time,
            trade_sessions,
        ),
        as_json=args.json,
    )


def cmd_history_candlesticks_by_date(ctx: QuoteContext, args: argparse.Namespace) -> None:
    period = enum_from_name(Period, args.period)
    adjust_type = enum_from_name(AdjustType, args.adjust_type)
    trade_sessions = enum_from_name(TradeSessions, args.trade_sessions)
    start = parse_date(args.start)
    end = parse_date(args.end)
    print_result(
        ctx.history_candlesticks_by_date(
            args.symbol,
            period,
            adjust_type,
            start,
            end,
            trade_sessions,
        ),
        as_json=args.json,
    )


def cmd_option_chain_expiry_date_list(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.option_chain_expiry_date_list(args.symbol), as_json=args.json)


def cmd_option_chain_info_by_date(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(
        ctx.option_chain_info_by_date(args.symbol, parse_date(args.expiry_date)),
        as_json=args.json,
    )


def cmd_warrant_issuers(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.warrant_issuers(), as_json=args.json)


def cmd_warrant_list(ctx: QuoteContext, args: argparse.Namespace) -> None:
    sort_by = enum_from_name(WarrantSortBy, args.sort_by)
    sort_order = enum_from_name(SortOrderType, args.sort_order)
    warrant_type = enum_list_from_csv(WarrantType, args.warrant_type)
    issuer = [int(x) for x in parse_csv(args.issuer)] if args.issuer else None
    expiry_date = enum_list_from_csv(FilterWarrantExpiryDate, args.expiry_date)
    price_type = enum_list_from_csv(FilterWarrantInOutBoundsType, args.price_type)
    status = enum_list_from_csv(WarrantStatus, args.status)

    print_result(
        ctx.warrant_list(
            args.symbol,
            sort_by,
            sort_order,
            warrant_type,
            issuer,
            expiry_date,
            price_type,
            status,
        ),
        as_json=args.json,
    )


def cmd_trading_session(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.trading_session(), as_json=args.json)


def cmd_trading_days(ctx: QuoteContext, args: argparse.Namespace) -> None:
    market = enum_from_name(Market, args.market)
    begin = parse_date(args.begin)
    end = parse_date(args.end)
    print_result(ctx.trading_days(market, begin, end), as_json=args.json)


def cmd_capital_flow(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.capital_flow(args.symbol), as_json=args.json)


def cmd_capital_distribution(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.capital_distribution(args.symbol), as_json=args.json)


def cmd_calc_indexes(ctx: QuoteContext, args: argparse.Namespace) -> None:
    indexes = enum_list_from_csv(CalcIndex, args.indexes) or []
    print_result(ctx.calc_indexes(parse_csv(args.symbols), indexes), as_json=args.json)


def cmd_watchlist(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.watchlist(), as_json=args.json)


def cmd_create_watchlist_group(ctx: QuoteContext, args: argparse.Namespace) -> None:
    group_id = ctx.create_watchlist_group(args.name, parse_csv(args.securities) or None)
    print_result({"group_id": group_id}, as_json=args.json)


def cmd_delete_watchlist_group(ctx: QuoteContext, args: argparse.Namespace) -> None:
    ctx.delete_watchlist_group(args.id, args.purge)
    print("删除完成")


def cmd_update_watchlist_group(ctx: QuoteContext, args: argparse.Namespace) -> None:
    mode = enum_from_name(SecuritiesUpdateMode, args.mode) if args.mode else None
    ctx.update_watchlist_group(
        args.id,
        name=args.name,
        securities=parse_csv(args.securities) or None,
        mode=mode,
    )
    print("更新完成")


def cmd_security_list(ctx: QuoteContext, args: argparse.Namespace) -> None:
    market = enum_from_name(Market, args.market)
    category = enum_from_name(SecurityListCategory, args.category) if args.category else None
    print_result(ctx.security_list(market, category), as_json=args.json)


def cmd_market_temperature(ctx: QuoteContext, args: argparse.Namespace) -> None:
    market = enum_from_name(Market, args.market)
    print_result(ctx.market_temperature(market), as_json=args.json)


def cmd_history_market_temperature(ctx: QuoteContext, args: argparse.Namespace) -> None:
    market = enum_from_name(Market, args.market)
    print_result(
        ctx.history_market_temperature(
            market,
            parse_date(args.start_date),
            parse_date(args.end_date),
        ),
        as_json=args.json,
    )


def cmd_realtime_quote(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.realtime_quote(parse_csv(args.symbols)), as_json=args.json)


def cmd_realtime_depth(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.realtime_depth(args.symbol), as_json=args.json)


def cmd_realtime_brokers(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.realtime_brokers(args.symbol), as_json=args.json)


def cmd_realtime_trades(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.realtime_trades(args.symbol, args.count), as_json=args.json)


def cmd_realtime_candlesticks(ctx: QuoteContext, args: argparse.Namespace) -> None:
    period = enum_from_name(Period, args.period)
    print_result(ctx.realtime_candlesticks(args.symbol, period, args.count), as_json=args.json)


def cmd_subscribe(ctx: QuoteContext, args: argparse.Namespace) -> None:
    install_push_callbacks(ctx)
    sub_types = enum_list_from_csv(SubType, args.sub_types) or []
    ctx.subscribe(parse_csv(args.symbols), sub_types)
    print(f"已订阅，开始监听 {args.listen_seconds} 秒。按 Ctrl+C 可提前结束。")
    try:
        time.sleep(args.listen_seconds)
    finally:
        if args.auto_unsubscribe:
            ctx.unsubscribe(parse_csv(args.symbols), sub_types)
            print("已自动取消订阅")


def cmd_unsubscribe(ctx: QuoteContext, args: argparse.Namespace) -> None:
    sub_types = enum_list_from_csv(SubType, args.sub_types) or []
    ctx.unsubscribe(parse_csv(args.symbols), sub_types)
    print("取消订阅完成")


def cmd_subscriptions(ctx: QuoteContext, args: argparse.Namespace) -> None:
    print_result(ctx.subscriptions(), as_json=args.json)


def cmd_subscribe_candlesticks(ctx: QuoteContext, args: argparse.Namespace) -> None:
    install_push_callbacks(ctx)
    period = enum_from_name(Period, args.period)
    trade_sessions = enum_from_name(TradeSessions, args.trade_sessions)
    resp = ctx.subscribe_candlesticks(args.symbol, period, trade_sessions)
    print("初始 K 线快照:")
    print_result(resp, as_json=args.json)
    print(f"开始监听 {args.listen_seconds} 秒。按 Ctrl+C 可提前结束。")
    try:
        time.sleep(args.listen_seconds)
    finally:
        if args.auto_unsubscribe:
            ctx.unsubscribe_candlesticks(args.symbol, period)
            print("已自动取消 K 线订阅")


def cmd_unsubscribe_candlesticks(ctx: QuoteContext, args: argparse.Namespace) -> None:
    period = enum_from_name(Period, args.period)
    ctx.unsubscribe_candlesticks(args.symbol, period)
    print("取消 K 线订阅完成")


# ==============================
# argparse 定义
# ==============================

def add_common_flags(parser: argparse.ArgumentParser) -> None:
    """为每个子命令追加通用参数。"""
    parser.add_argument(
        "--client-id",
        help="OAuth 2.0 的 client_id。传入后走 OAuth；不传则走环境变量认证。",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="把结果尽量以 JSON 格式输出，便于二次处理。",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Longbridge Quote API 单文件工具箱",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # 0. 基础信息
    p = sub.add_parser("info", help="查看 member_id / quote_level / quote_package_details")
    add_common_flags(p)
    p.set_defaults(func=cmd_info)

    # 1. Pull / 常规查询
    p = sub.add_parser("static_info", help="获取标的基础信息")
    p.add_argument("--symbols", required=True, help="标的代码，逗号分隔，例如 700.HK,AAPL.US")
    add_common_flags(p)
    p.set_defaults(func=cmd_static_info)

    p = sub.add_parser("quote", help="获取标的实时行情")
    p.add_argument("--symbols", required=True, help="标的代码，逗号分隔")
    add_common_flags(p)
    p.set_defaults(func=cmd_quote)

    p = sub.add_parser("option_quote", help="获取期权实时行情")
    p.add_argument("--symbols", required=True, help="期权代码，逗号分隔")
    add_common_flags(p)
    p.set_defaults(func=cmd_option_quote)

    p = sub.add_parser("warrant_quote", help="获取窝轮/权证实时行情")
    p.add_argument("--symbols", required=True, help="权证代码，逗号分隔")
    add_common_flags(p)
    p.set_defaults(func=cmd_warrant_quote)

    p = sub.add_parser("depth", help="获取标的盘口")
    p.add_argument("--symbol", required=True, help="单个标的代码，例如 700.HK")
    add_common_flags(p)
    p.set_defaults(func=cmd_depth)

    p = sub.add_parser("brokers", help="获取标的经纪队列")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    add_common_flags(p)
    p.set_defaults(func=cmd_brokers)

    p = sub.add_parser("participants", help="获取 broker IDs / 参与者信息")
    add_common_flags(p)
    p.set_defaults(func=cmd_participants)

    p = sub.add_parser("trades", help="获取成交明细")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    p.add_argument("--count", type=int, default=10, help="返回条数")
    add_common_flags(p)
    p.set_defaults(func=cmd_trades)

    p = sub.add_parser("intraday", help="获取当日分时")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    p.add_argument(
        "--trade-sessions",
        default="Intraday",
        help="TradeSessions 枚举名称，默认 Intraday；可选一般为 Intraday / All",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_intraday)

    p = sub.add_parser("candlesticks", help="获取当前 K 线快照")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    p.add_argument("--period", required=True, help="Period 枚举，如 Day / Min_1 / Week")
    p.add_argument(
        "--count", type=int, required=True, help="返回 K 线数量，例如 10 / 100 / 500"
    )
    p.add_argument(
        "--adjust-type",
        default="NoAdjust",
        help="AdjustType 枚举，默认 NoAdjust；可选 NoAdjust / ForwardAdjust",
    )
    p.add_argument(
        "--trade-sessions",
        default="Intraday",
        help="TradeSessions 枚举，默认 Intraday",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_candlesticks)

    p = sub.add_parser("history_candlesticks_by_offset", help="按锚点时间与方向拉取历史 K 线")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    p.add_argument("--period", required=True, help="Period 枚举")
    p.add_argument(
        "--adjust-type",
        default="NoAdjust",
        help="AdjustType 枚举，默认 NoAdjust",
    )
    p.add_argument(
        "--forward",
        action="store_true",
        help="是否向前取数；不传则默认 False（按 SDK 默认语义执行）",
    )
    p.add_argument("--count", type=int, required=True, help="返回 K 线数量")
    p.add_argument(
        "--time",
        help="锚点时间，ISO 8601，例如 2026-03-13T09:30:00；不传则由 SDK 用默认时间",
    )
    p.add_argument(
        "--trade-sessions",
        default="Intraday",
        help="TradeSessions 枚举，默认 Intraday",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_history_candlesticks_by_offset)

    p = sub.add_parser("history_candlesticks_by_date", help="按日期区间拉取历史 K 线")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    p.add_argument("--period", required=True, help="Period 枚举")
    p.add_argument(
        "--adjust-type",
        default="NoAdjust",
        help="AdjustType 枚举，默认 NoAdjust",
    )
    p.add_argument("--start", help="开始日期，YYYY-MM-DD")
    p.add_argument("--end", help="结束日期，YYYY-MM-DD")
    p.add_argument(
        "--trade-sessions",
        default="Intraday",
        help="TradeSessions 枚举，默认 Intraday",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_history_candlesticks_by_date)

    p = sub.add_parser("option_chain_expiry_date_list", help="获取期权链可用到期日列表")
    p.add_argument("--symbol", required=True, help="正股代码，例如 AAPL.US")
    add_common_flags(p)
    p.set_defaults(func=cmd_option_chain_expiry_date_list)

    p = sub.add_parser("option_chain_info_by_date", help="获取指定到期日的期权链")
    p.add_argument("--symbol", required=True, help="正股代码，例如 AAPL.US")
    p.add_argument("--expiry-date", required=True, help="到期日，YYYY-MM-DD")
    add_common_flags(p)
    p.set_defaults(func=cmd_option_chain_info_by_date)

    p = sub.add_parser("warrant_issuers", help="获取权证发行商列表")
    add_common_flags(p)
    p.set_defaults(func=cmd_warrant_issuers)

    p = sub.add_parser("warrant_list", help="筛选权证列表")
    p.add_argument("--symbol", required=True, help="正股代码，例如 700.HK")
    p.add_argument(
        "--sort-by",
        required=True,
        help="WarrantSortBy 枚举，如 LastDone / Volume / Premium / Status",
    )
    p.add_argument(
        "--sort-order",
        default="Descending",
        help="SortOrderType 枚举，默认 Descending；可选 Ascending / Descending",
    )
    p.add_argument(
        "--warrant-type",
        help="WarrantType 多选，逗号分隔，例如 Call,Put,Bull,Bear",
    )
    p.add_argument(
        "--issuer",
        help="发行商 ID 多选，逗号分隔，例如 1,2,3",
    )
    p.add_argument(
        "--expiry-date",
        help="FilterWarrantExpiryDate 多选，逗号分隔，例如 LT_3,Between_3_6",
    )
    p.add_argument(
        "--price-type",
        help="FilterWarrantInOutBoundsType 多选，逗号分隔，例如 In,Out",
    )
    p.add_argument(
        "--status",
        help="WarrantStatus 多选，逗号分隔，例如 Normal,Suspend",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_warrant_list)

    p = sub.add_parser("trading_session", help="获取当日各市场交易时段")
    add_common_flags(p)
    p.set_defaults(func=cmd_trading_session)

    p = sub.add_parser("trading_days", help="获取市场交易日历")
    p.add_argument("--market", required=True, help="Market 枚举，如 HK / US / CN / SG")
    p.add_argument("--begin", required=True, help="开始日期，YYYY-MM-DD")
    p.add_argument("--end", required=True, help="结束日期，YYYY-MM-DD")
    add_common_flags(p)
    p.set_defaults(func=cmd_trading_days)

    p = sub.add_parser("capital_flow", help="获取资金流向（分时）")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    add_common_flags(p)
    p.set_defaults(func=cmd_capital_flow)

    p = sub.add_parser("capital_distribution", help="获取资金分布")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    add_common_flags(p)
    p.set_defaults(func=cmd_capital_distribution)

    p = sub.add_parser("calc_indexes", help="批量计算指标")
    p.add_argument("--symbols", required=True, help="标的代码，逗号分隔")
    p.add_argument(
        "--indexes",
        required=True,
        help="CalcIndex 多选，逗号分隔，例如 LastDone,ChangeRate,Volume,PbRatio",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_calc_indexes)

    p = sub.add_parser("security_list", help="获取市场证券列表")
    p.add_argument("--market", required=True, help="Market 枚举，例如 HK / US / CN / SG")
    p.add_argument(
        "--category",
        help="SecurityListCategory 枚举，例如 Overnight；不传则取默认分类",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_security_list)

    p = sub.add_parser("market_temperature", help="获取当前市场温度")
    p.add_argument("--market", required=True, help="Market 枚举，例如 HK / US")
    add_common_flags(p)
    p.set_defaults(func=cmd_market_temperature)

    p = sub.add_parser("history_market_temperature", help="获取历史市场温度")
    p.add_argument("--market", required=True, help="Market 枚举，例如 HK / US")
    p.add_argument("--start-date", required=True, help="开始日期，YYYY-MM-DD")
    p.add_argument("--end-date", required=True, help="结束日期，YYYY-MM-DD")
    add_common_flags(p)
    p.set_defaults(func=cmd_history_market_temperature)

    p = sub.add_parser("realtime_quote", help="获取实时 quote（实时接口）")
    p.add_argument("--symbols", required=True, help="标的代码，逗号分隔")
    add_common_flags(p)
    p.set_defaults(func=cmd_realtime_quote)

    p = sub.add_parser("realtime_depth", help="获取实时 depth（实时接口）")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    add_common_flags(p)
    p.set_defaults(func=cmd_realtime_depth)

    p = sub.add_parser("realtime_brokers", help="获取实时 brokers（实时接口）")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    add_common_flags(p)
    p.set_defaults(func=cmd_realtime_brokers)

    p = sub.add_parser("realtime_trades", help="获取实时 trades（实时接口）")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    p.add_argument("--count", type=int, default=500, help="返回条数，SDK 默认 500")
    add_common_flags(p)
    p.set_defaults(func=cmd_realtime_trades)

    p = sub.add_parser("realtime_candlesticks", help="获取实时 K 线（实时接口）")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    p.add_argument("--period", required=True, help="Period 枚举，例如 Min_1 / Day")
    p.add_argument("--count", type=int, default=500, help="返回条数，SDK 默认 500")
    add_common_flags(p)
    p.set_defaults(func=cmd_realtime_candlesticks)

    # 2. 订阅 / Push
    p = sub.add_parser("subscribe", help="订阅行情并监听 push")
    p.add_argument("--symbols", required=True, help="标的代码，逗号分隔")
    p.add_argument(
        "--sub-types",
        required=True,
        help="SubType 多选，逗号分隔，例如 Quote,Depth,Brokers,Trade",
    )
    p.add_argument(
        "--listen-seconds",
        type=int,
        default=30,
        help="监听时长（秒），默认 30",
    )
    p.add_argument(
        "--auto-unsubscribe",
        action="store_true",
        help="退出前自动取消订阅",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_subscribe)

    p = sub.add_parser("unsubscribe", help="取消普通行情订阅")
    p.add_argument("--symbols", required=True, help="标的代码，逗号分隔")
    p.add_argument(
        "--sub-types",
        required=True,
        help="SubType 多选，逗号分隔，例如 Quote,Depth",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_unsubscribe)

    p = sub.add_parser("subscriptions", help="查看当前订阅信息")
    add_common_flags(p)
    p.set_defaults(func=cmd_subscriptions)

    p = sub.add_parser("subscribe_candlesticks", help="订阅 K 线 push")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    p.add_argument("--period", required=True, help="Period 枚举，例如 Min_1 / Day")
    p.add_argument(
        "--trade-sessions",
        default="Intraday",
        help="TradeSessions 枚举，默认 Intraday",
    )
    p.add_argument(
        "--listen-seconds",
        type=int,
        default=30,
        help="监听时长（秒），默认 30",
    )
    p.add_argument(
        "--auto-unsubscribe",
        action="store_true",
        help="退出前自动取消订阅",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_subscribe_candlesticks)

    p = sub.add_parser("unsubscribe_candlesticks", help="取消 K 线订阅")
    p.add_argument("--symbol", required=True, help="单个标的代码")
    p.add_argument("--period", required=True, help="Period 枚举，例如 Min_1 / Day")
    add_common_flags(p)
    p.set_defaults(func=cmd_unsubscribe_candlesticks)

    # 3. Watchlist / 自选股
    p = sub.add_parser("watchlist", help="查看自选股分组")
    add_common_flags(p)
    p.set_defaults(func=cmd_watchlist)

    p = sub.add_parser("create_watchlist_group", help="创建自选股分组")
    p.add_argument("--name", required=True, help="分组名称")
    p.add_argument(
        "--securities",
        help="初始证券列表，逗号分隔，例如 700.HK,AAPL.US",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_create_watchlist_group)

    p = sub.add_parser("delete_watchlist_group", help="删除自选股分组")
    p.add_argument("--id", type=int, required=True, help="分组 ID")
    p.add_argument(
        "--purge",
        action="store_true",
        help="是否把该分组证券迁移到默认分组",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_delete_watchlist_group)

    p = sub.add_parser("update_watchlist_group", help="更新自选股分组")
    p.add_argument("--id", type=int, required=True, help="分组 ID")
    p.add_argument("--name", help="新的分组名称")
    p.add_argument("--securities", help="证券列表，逗号分隔")
    p.add_argument(
        "--mode",
        help="SecuritiesUpdateMode 枚举，例如 Add / Remove / Replace",
    )
    add_common_flags(p)
    p.set_defaults(func=cmd_update_watchlist_group)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        ctx = build_ctx(getattr(args, "client_id", None))
        args.func(ctx, args)
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
