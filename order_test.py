from longbridge.openapi import TradeContext, Config, OrderType, OrderSide, TimeInForceType, OAuthBuilder

client_id="ca9f761d-bb7f-44a4-a4f0-b6c952eb3090"
oauth = OAuthBuilder(client_id).build(
    lambda url: print(f"Open this URL to authorize: {url}")
)
# Create a context for trade APIs
config = Config.from_oauth(oauth)
ctx = TradeContext(config)
resp = ctx.stock_positions()
print(resp)