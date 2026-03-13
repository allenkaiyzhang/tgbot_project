from longbridge.openapi import TradeContext

from longbridge_config import build_apikey_env_config, build_config_with_fallback


def get_trade_context(client_id: str | None = None):
    trade_config, source = build_config_with_fallback(client_id=client_id)
    return TradeContext(trade_config), source


def get_stock_positions(client_id: str | None = None):
    ctx, source = get_trade_context(client_id=client_id)
    try:
        resp = ctx.stock_positions()
        return resp
    except Exception as oauth_error:
        if source != "oauth":
            raise
        print(f"OAuth request failed, retry with from_apikey_env(): {oauth_error}")
        fallback_ctx = TradeContext(build_apikey_env_config())
        resp = fallback_ctx.stock_positions()
        return resp


if __name__ == "__main__":
    print(get_stock_positions())
