from asyncio import run
import ccxt.pro as ccxt
from decouple import config

from print_there import print_there
from order import TriggerOrder

# GLOBALS
SECONDS_DELAY: int = 5
TICKER: str = "BTCUSDT"
PRICE: float = 42180
TRADE_DIRECTION: str = "short"
ONE_PERCENT_TRADING_SIZE: float = 0.002
ORDER_OFFSET: float = 0.00025
TRIGGER_ORDER_PRICE = round(
    PRICE * (1 - ORDER_OFFSET)
    if TRADE_DIRECTION == "short"
    else PRICE * (1 + ORDER_OFFSET),
    1,
)

exchange = ccxt.bybit(
    config={
        "apiKey": config("API_KEY"),
        "secret": config("API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
    }
)

async def main():
    trigger_order = TriggerOrder(
        ticker=TICKER,
        price=PRICE,
        direction=TRADE_DIRECTION,
        exchange=exchange,
        trading_size=ONE_PERCENT_TRADING_SIZE,
        trigger_order_price=TRIGGER_ORDER_PRICE,
        order_offset=ORDER_OFFSET,
    )
    last_changed_price: int = 0

    while not trigger_order.triggered:
        await trigger_order.set_current_price()
        trigger_order.check_for_trigger(await trigger_order.current_price)

        # print changing orderbook for fun
        if last_changed_price != await trigger_order.current_price:
            print_there(
                100, 0, f"""currentprice: {await trigger_order.current_price}\t\ttriggerprice: {trigger_order.trigger_price}"""
            )

        last_changed_price = await trigger_order.current_price

    await trigger_order.create_order()

    while not trigger_order.finished:
        await trigger_order.set_order_variables()
        print_there(
            100,
            0,
            f"""currentprice: {await trigger_order.current_price}\t\torderprice: {trigger_order.trigger_order_price}\t\tamount: {await trigger_order.amount}\t\ttarget: {await trigger_order.target}\t\tstoploss: {await trigger_order.stop_loss}""",
        )

        if await trigger_order.did_stop_loss_change():
            await trigger_order.update_order()

        if await trigger_order.stop_loss_percentage > 0.01:
            print()
            print("stop loss is too wide, cancelling order")
            await trigger_order.cancel_order()
            trigger_order.finished = True
        
        if await trigger_order.order_status != "open":
            print()
            print("Order status is no longer 'open'")
            trigger_order.finished = True

    print()
    await exchange.close()


if __name__ == "__main__":
    run(main())
