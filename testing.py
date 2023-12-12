# from asyncio import run
from typing import List
import ccxt
from decouple import config
import json
       

exchange = ccxt.bybit(config={
    'apiKey': config("API_KEY"), 
    'secret': config("API_SECRET"),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})

def printer(name: str, list_or_dict: List[dict] | dict):
    print(name, json.dumps(list_or_dict, indent=2))

Target_Coin_Ticker = "BTC/USDT"
Target_Coin_Symbol = "BTCUSDT"

# balance = exchange.fetch_balance(params={"type": "unified"})
# printer("balance", balance)

"""Create order"""
# order = exchange.create_order(
#     symbol="BTCUSDT",
#     type="market",
#     side="sell",
#     amount=0.001,
#     params={
#         "positionIdx": "2",
#         "triggerPrice": 43000,
#         "triggerDirection": "above",
#         "stopLoss": {"triggerPrice": 44000},
#         "takeProfit": {"triggerPrice": 42000},
#     }
# )
# printer("order", order)
# order_id = order.get("id", "")

"""Edit order"""
# edit_order = exchange.edit_order(
#     id="e7c1bf43-988b-4a97-9520-ebb333a6250b",
#     symbol="BTCUSDT",
#     type="market",
#     side="buy",
#     amount=0.001,
#     params={
#         "stopLoss": {"triggerPrice": 44000},
#         "takeProfit": {"triggerPrice": 42000},
#     },
# )
# printer("edit_order", edit_order)

"""Get position"""
# fetch_position = exchange.fetch_position(symbol="BTCUSDT")
# printer("fetch_positions", fetch_position)

"""Edit position"""
# async def main():
#     while True:
#         edit_position = await exchange.watch_position(symbol="BTCUSDT")
#         print(edit_position)

# run(main())

"""Cancel order"""
# exchange.cancel_all_orders("BTCUSDT")

import sys
def print_there(x, y, text):
     sys.stdout.write("\x1b7\x1b[%d;%df%s\x1b8" % (x, y, text))
     sys.stdout.flush()
    