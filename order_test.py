from longbridge.openapi import Config, TradeContext

config = Config.from_apikey_env()
def get_stock_positions(config):
    ctx = TradeContext(config)
    resp = ctx.stock_positions()
    return resp


if __name__ == "__main__":
    print(get_stock_positions())
