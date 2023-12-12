from datetime import datetime, timedelta
from typing import Tuple
import ccxt
from dataclasses import dataclass
import json

from trigger import Trigger
from price import get_price


@dataclass
class Order:
    """Holds all order data"""

    trigger: Trigger
    size: float | None = None
    leverage: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    waiting_order: dict | None = None
    is_live: bool = False

    @property
    def ticker(self) -> str:
        return self.trigger.ticker

    @property
    def exchange(self) -> ccxt.bybit:
        return self.trigger.exchange

    @property
    def price(self) -> float:
        return self.trigger.price

    @property
    def direction(self) -> str:
        return self.trigger.direction

    @property
    def trading_size(self) -> float:
        return self.trigger.trading_size

    async def create(self, orderbook_focus: str):
        price: float = await get_price(self.exchange, self.ticker, orderbook_focus)
        stop_loss, stoploss_percentage = self.set_stop_loss(price)
        take_profit = self.set_take_profit(stoploss_percentage)

        self.waiting_order = await self.exchange.create_order(
            symbol=self.ticker,
            type="market",
            side="sell" if self.direction == "short" else "buy",
            amount=self.set_size(),
            params={
                "positionIdx": "2" if self.direction == "short" else "1",
                "triggerPrice": str(self.price),
                "triggerDirection": "above" if self.direction == "long" else "below",
                "stopLoss": {"triggerPrice": str(round(stop_loss, 1))},
                "takeProfit": {"triggerPrice": str(round(take_profit, 1))},
            },
        )
        self.order_last_update = datetime.now()
        print(json.dumps(self.waiting_order, indent=2))

    async def adjust_order(self, price: float, balance: dict, delay: int) -> None:
        """Adjust order on exchange"""

        self.get_balance(balance)
        _, stop_loss_percentage = self.set_stop_loss(price)
        self.set_take_profit(stop_loss_percentage)
        self.set_size()
        await self.update_order(delay)

    def set_stop_loss(self, price: float) -> Tuple[float, float]:
        """Calculate stoploss for order"""

        if not self.stop_loss:
            self.stop_loss = (
                round(max(price, self.trigger.price * 1.0025), 2)
                if self.trigger.direction == "short"
                else round(min(price, self.trigger.price * (1 - 0.0025)), 2)
            )
            print(f"stoploss set to {str(self.stop_loss)}")
            return self.stop_loss, (
                ((self.stop_loss - self.price) / self.price)
                if self.direction == "short"
                else ((self.price - self.stop_loss) / self.price)
            )

        temp_sl = self.stop_loss
        match self.trigger.direction:
            case "long":
                if price < self.stop_loss:
                    self.stop_loss = round(
                        min(price, self.trigger.price * (1 - 0.0025)), 1
                    )
            case "short":
                if price > self.stop_loss:
                    self.stop_loss = round(max(price, self.trigger.price * 1.0025), 1)
        if temp_sl != self.stop_loss:
            print(f"stoploss changed to {str(self.stop_loss)}")

        self.stop_loss_percentage: float = (
            ((self.stop_loss - self.price) / self.price)
            if self.direction == "short"
            else ((self.price - self.stop_loss) / self.price)
        )
        return self.stop_loss, self.stop_loss_percentage

    def set_take_profit(self, stop_loss_percentage: float) -> float:
        temp_take_profit = self.take_profit if hasattr(self, "take_profit") else 0
        self.take_profit = (
            round((self.price * (1 + (stop_loss_percentage * 2))), 1)
            if self.direction == "long"
            else round(self.price * (1 - (stop_loss_percentage * 2)), 1)
        )
        if temp_take_profit != self.take_profit:
            print(f"take profit changed to {str(self.take_profit)}")
        return self.take_profit

    def set_size(self) -> float:
        """TODO: Calculate ordersize"""
        if hasattr(self, "stop_loss_percentage"):
            match int(self.stop_loss_percentage * 10000):
                case num if num <= 25:
                    self.size = self.trading_size * 4
                case num if num in range(25, 50):
                    self.size = self.trading_size * 3
                case num if num in range(50, 75):
                    self.size = self.trading_size * 2
                case num if num >= 75:
                    self.size = self.trading_size
        else:
            self.size = self.trading_size
        return self.size

    async def update_order(self, delay: int) -> None:
        """Use calculated data to adjust order on exchange"""
        if self.stop_loss_percentage > 0.25:
            await self.cancel_order()
            return

        if self.order_last_update + timedelta(seconds=delay) < (now := datetime.now()):
            order_status = await self.exchange.fetch_order_status(
                id=self.waiting_order.get("id"), symbol=self.ticker
            )
            if order_status == "open":
                await self.exchange.edit_order(
                    id=self.waiting_order.get("id"),
                    symbol=self.ticker,
                    type="market",
                    side="buy" if self.direction == "long" else "sell",
                    amount=self.set_size(),
                    params={
                        "stopLoss": {"triggerPrice": self.stop_loss},
                        "takeProfit": {"triggerPrice": self.take_profit},
                    },
                )
                self.order_last_update = now

            else:
                self.is_live = True

    async def cancel_order(self) -> None:
        """If SL gets too big, cancel trade"""

        await self.exchange.cancel_all_orders(symbol="BTCUSDT")

    def get_balance(self, balance: dict) -> dict:
        """Calculate free USDT to use for order depending on SL"""

        return balance.get("USDT", {})
