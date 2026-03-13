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

import config
from longbridge.openapi import QuoteContext, TradeContext


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
