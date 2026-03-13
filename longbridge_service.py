import json
import inspect

import config
from longbridge.openapi import QuoteContext, TradeContext



def setup_quote_context(client_id):
    """Set up OAuth and create a QuoteContext for fetching security quotes."""
    quote_config, source = config.build_config_with_fallback(client_id=client_id)
    return QuoteContext(quote_config), source


def setup_trade_context(client_id):
    """Set up OAuth and create a TradeContext for account/trade APIs."""
    trade_config, source = config.build_config_with_fallback(client_id=client_id)
    return TradeContext(trade_config), source


def fetch_security_quotes(ctx, symbols):
    """Fetch basic information of securities using the provided context."""
    return ctx.quote(symbols)


def fetch_stock_positions(ctx):
    """Fetch current stock positions from the provided trade context."""
    return ctx.stock_positions()


def inspect_and_call_methods(resp):
    """Inspect each element in resp, call no-argument methods, and return the gathered results.

    Returns a list of dicts, one per item in resp.
    Each dict contains:
      - "type": string representation of the item type
      - "attributes": mapping of non-callable attribute names to their values (as strings)
      - "methods": mapping of callable method names to a dict with keys:
            "status": "called" | "skipped" | "error" | "no_signature"
            "result": result or exception message (when applicable)
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
            except Exception as e:
                item_entry["attributes"][name] = f"<attribute access error: {e}>"
                continue

            if not callable(attr):
                # Not a method; store value as string
                try:
                    item_entry["attributes"][name] = str(attr)
                except Exception:
                    item_entry["attributes"][name] = "<unprintable>"
                continue

            method_entry = {"status": None, "result": None}

            # Try to call only methods with no required parameters
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
            except (ValueError, TypeError):
                # Builtins or C methods may not have signatures
                method_entry["status"] = "no_signature"

            try:
                result = attr()
                method_entry["status"] = "called"
                try:
                    method_entry["result"] = json.dumps(result, ensure_ascii=False, default=str, indent=2)
                except Exception:
                    method_entry["result"] = str(result)
            except Exception as e:
                method_entry["status"] = "error"
                method_entry["result"] = str(e)

            item_entry["methods"][name] = method_entry

        results.append(item_entry)

    return results


def show_methods(obj):
    """Print the type of the object and list all of its available methods."""
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


def format_item_entry(item_entry):
    """Format the inspection result for a single item into a readable string."""

    lines = [f"Type: {item_entry.get('type')}\n"]

    attributes = item_entry.get("attributes", {})
    if attributes:
        lines.append("Attributes:")
        for name, value in sorted(attributes.items()):
            # Pretty-print JSON-like values for specific quote fields
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

    # Only output attributes (methods are collected but not printed)
    return "\n".join(lines)


DEFAULT_CLIENT_ID = config.LONGBRIDGE_CLIENT_ID
DEFAULT_SYMBOLS = config.DEFAULT_SYMBOLS


def get_inspected_quotes(client_id: str = None, symbols=None):
    """Return the current inspected quote data (same format as `inspected` in main)."""

    if client_id is None:
        client_id = DEFAULT_CLIENT_ID
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    ctx, source = setup_quote_context(client_id)
    try:
        resp = fetch_security_quotes(ctx, symbols)
    except Exception as oauth_error:
        if source != "oauth":
            raise
        print(f"OAuth quote request failed, retry with from_apikey_env(): {oauth_error}")
        fallback_ctx = QuoteContext(config.build_apikey_env_config())
        resp = fetch_security_quotes(fallback_ctx, symbols)
    inspected = inspect_and_call_methods(resp)
    return inspected


def get_stock_positions(client_id: str = None):
    """Return current stock positions via LongBridge Trade API."""

    if client_id is None:
        client_id = DEFAULT_CLIENT_ID

    ctx, source = setup_trade_context(client_id)
    try:
        resp = fetch_stock_positions(ctx)
        return resp
    except Exception as oauth_error:
        if source != "oauth":
            raise
        print(f"OAuth positions request failed, retry with from_apikey_env(): {oauth_error}")
        fallback_ctx = TradeContext(config.build_apikey_env_config())
        resp = fetch_stock_positions(fallback_ctx)
        return resp


def get_inspected_quotes_text(client_id: str = None, symbols=None):
    """Return inspected quotes as a pretty JSON string."""

    inspected = get_inspected_quotes(client_id=client_id, symbols=symbols)
    try:
        return json.dumps(inspected, ensure_ascii=False, indent=2)
    except Exception:
        return str(inspected)


def main():
    """Main function to orchestrate the quote fetching and inspection."""
    inspected = get_inspected_quotes()

    # Print formatted inspection results
    for idx, item in enumerate(inspected, start=1):
        print("=" * 80)
        print(f"Item {idx}/{len(inspected)}")
        print("=" * 80)
        print(format_item_entry(item))


if __name__ == "__main__":
    main()

