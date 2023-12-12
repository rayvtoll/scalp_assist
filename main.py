from asyncio import run
import ccxt.pro as ccxt
from decouple import config
import sys
import time

from order import Order
from trigger import Trigger
from price import get_price

# Trading variables
SECONDS_DELAY: int = 5
TICKER: str = "BTCUSDT"
TRIGGER_PRICE: float = 41320.9
TRADE_DIRECTION: str = "short"
ONE_PERCENT_TRADING_SIZE = 0.001

exchange = ccxt.bybit(
    config={
        "apiKey": config("API_KEY"),
        "secret": config("API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
    }
)

trigger = Trigger(
    ticker=TICKER,
    price=TRIGGER_PRICE,
    direction=TRADE_DIRECTION,
    exchange=exchange,
    trading_size=ONE_PERCENT_TRADING_SIZE,
)
orderbook_focus = "bids" if trigger.direction == "long" else "asks"


def print_there(x, y, text):
    sys.stdout.write("\x1b7\x1b[%d;%df%s\x1b8" % (x, y, text))
    sys.stdout.flush()


async def main():
    price_focus: int = 0

    while not trigger.triggered:
        price = await get_price(exchange, TICKER, orderbook_focus)
        trigger.check_for_trigger(price)

        # print changing orderbook for fun
        if price_focus != price:
            print_there(100, 00, f"""{"{:.1f}".format(round(price, 1))}""")

        price_focus = price

        if trigger.triggered:
            order = Order(trigger=trigger)

    # put in a delay before putting in a order
    while not trigger.enough_delay(seconds=SECONDS_DELAY):
        print("sleep...")
        time.sleep(1)

    await order.create(orderbook_focus)

    # # TODO: adjust order with code from testing.py
    while not order.is_live:
        price = await get_price(exchange, TICKER, orderbook_focus)
        balance = await exchange.fetch_balance(params={"type": "unified"})
        usdt_balance = balance.get("USDT", {})
        await order.adjust_order(price, usdt_balance, SECONDS_DELAY)

        if order.stop_loss_percentage > 0.01:
            print("stop loss is too wide, cancelling order")
            await order.cancel_order()
            order.is_live = True

    await exchange.close()


if __name__ == "__main__":
    run(main())
