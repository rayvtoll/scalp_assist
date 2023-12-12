import ccxt


async def get_price(exchange: ccxt.bybit, ticker: str, orderbook_focus: str):
    orderbook = await exchange.watch_order_book(ticker)
    return orderbook[orderbook_focus][0][0]
