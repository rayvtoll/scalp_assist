from asyncio import run
import ccxt.pro as ccxt
from decouple import config
import time

from trade import Order
from trigger import Trigger


SECONDS_DELAY: int = 5
TICKER: str = "BTCUSDT"
TRIGGER_PRICE: float = config("TRIGGER_PRICE", cast=float)
TRADE_DIRECTION: str = "long"

exchange = ccxt.bybit(
    config={
        "apiKey": config("API_KEY"),
        "secret": config("API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
    }
)

trigger = Trigger(
    price=TRIGGER_PRICE,
    direction=TRADE_DIRECTION,
    exchange=exchange,
)
trade = Order(trigger=trigger)


async def main():
    ask_price: int = 0
    bid_price: int = 0
    orderbook_focus = "bids" if trigger.direction == "long" else "asks"

    while not trigger.triggered:
        orderbook = await exchange.watch_order_book(TICKER)
        price = orderbook[orderbook_focus][0][0]
        trigger.check_for_trigger(price)

        # print changing orderbook for fun
        if ask_price != orderbook["asks"][0][0] or bid_price != orderbook["bids"][0][0]:
            print(
                f'''{"{:.2f}".format(round(orderbook["asks"][0][0], 1))}\t{"{:.2f}".format(
                    round(orderbook["bids"][0][0], 1)
                )}'''
            )

        ask_price = orderbook["asks"][0][0]
        bid_price = orderbook["bids"][0][0]

        if trigger.triggered:
            trade = Order(trigger=trigger)

    # put in a delay before putting in a trade
    while not trigger.enough_delay(seconds=SECONDS_DELAY):
        print("sleep...")
        time.sleep(1)

    # TODO: adjust order with code from testing.py
    while not trade.is_live:
        orderbook = await exchange.watch_order_book(TICKER)
        price = orderbook[orderbook_focus][0][0]
        balance = await exchange.fetch_balance(params={"type": "unified"})
        await trade.get_or_set_order(price, balance)

    await exchange.close()


if __name__ == "__main__":
    run(main())
