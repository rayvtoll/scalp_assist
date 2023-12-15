from datetime import datetime
from functools import cached_property
import ccxt
from dataclasses import dataclass


@dataclass
class TriggerOrder:
    """Holds all order data"""

    ticker: str
    price: float
    direction: str
    exchange: ccxt.bybit
    trading_size: float
    trigger_order_price: float
    order_offset: float
    finished: bool = False
    triggered: bool = False
    trigger_order: dict | None = None

    @cached_property
    def trigger_price(self) -> float:
        return round(
            self.price * (1 + self.order_offset)
            if self.direction == "short"
            else self.price * (1 - self.order_offset),
            1,
        )

    def check_for_trigger(self, price: float):
        """See if price is at POI"""

        if (self.direction == "long" and price <= self.trigger_price) or (
            self.direction == "short" and price >= self.trigger_price
        ):
            self.triggered = True

    @property
    async def current_price(self) -> float:
        if not hasattr(self, "_current_price"):
            await self.set_current_price()

        return self._current_price

    async def set_current_price(self) -> None:
        orderbook = await self.exchange.watch_order_book(self.ticker)
        self._current_price = orderbook["bids" if self.direction == "long" else "asks"][
            0
        ][0]

    @property
    async def stop_loss(self) -> float:
        if not hasattr(self, "_stop_loss"):
            await self.set_stop_loss()
        return self._stop_loss

    async def set_stop_loss(self) -> None:
        """Calculate stoploss for order"""

        price = await self.current_price

        if not hasattr(self, "_stop_loss"):
            self._stop_loss = round(
                max(price, self.trigger_order_price * 1.0025)
                if self.direction == "short"
                else min(price, self.trigger_order_price * (1 - 0.0025)),
                1,
            )

        match self.direction:
            case "long":
                if price < self._stop_loss:
                    self._stop_loss = round(
                        min(price, self.trigger_order_price * (1 - 0.0025)), 1
                    )
            case "short":
                if price > self._stop_loss:
                    self._stop_loss = round(max(price, self.trigger_order_price * 1.0025), 1)

    @property
    async def target(self) -> float:
        if not hasattr(self, "_target"):
            await self.set_target()
        return self._target

    async def set_target(self) -> None:
        self._target = round(
            (self.trigger_order_price * (1 + (await self.stop_loss_percentage * 2)))
            if self.direction == "long"
            else self.trigger_order_price * (1 - (await self.stop_loss_percentage * 2)),
            1,
        )

    @property
    async def amount(self) -> float:
        if not hasattr(self, "_amount"):
            await self.set_amount()

        return self._amount

    async def set_amount(self) -> None:
        """Calculate ordersize"""

        self._amount = round(
            (1 / (await self.stop_loss_percentage * 100)) * self.trading_size, 3
        )

    @property
    async def stop_loss_percentage(self) -> float:
        if not hasattr(self, "_stop_loss_percentage"):
            await self.set_stop_loss_percentage()
        return self._stop_loss_percentage

    async def set_stop_loss_percentage(self):
        self._stop_loss_percentage = (
            ((await self.stop_loss - self.trigger_order_price) / self.trigger_order_price)
            if self.direction == "short"
            else ((self.trigger_order_price - await self.stop_loss) / self.trigger_order_price)
        )

    async def create_order(self):
        await self.set_order_variables()

        if await self.stop_loss_percentage > 0.01:
            print("stop loss is too wide, cancelling order")
            self.finished = True
        else:
            try:
                self.trigger_order = await self.exchange.create_order(
                    symbol=self.ticker,
                    type="market",
                    side="sell" if self.direction == "short" else "buy",
                    amount=await self.amount,
                    params={
                        "positionIdx": "2" if self.direction == "short" else "1",
                        "triggerPrice": str(self.trigger_order_price),
                        "triggerBy": "LastPrice",
                        "triggerDirection": "above"
                        if self.direction == "long"
                        else "below",
                        "stopLoss": {"triggerPrice": str(await self.stop_loss), "tpTriggerBy": "LastPrice"},
                        "takeProfit": {"triggerPrice": str(await self.target),  "slTriggerBy": "LastPrice"},
                    },
                )
                self.order_last_update = datetime.now()
            except Exception as e:
                print(e)
                self.finished = True

    async def set_order_variables(self) -> None:
        """Adjust order on exchange"""

        await self.set_current_price()
        await self.set_stop_loss()
        await self.set_stop_loss_percentage()
        await self.set_target()
        await self.set_amount()

        if self.trigger_order:
            await self.set_order_status()

    async def did_stop_loss_change(self) -> bool:
        stop_loss_changed = False
        current_stoploss = await self.stop_loss

        if not hasattr(self, "_previous_stop_loss"):
            stop_loss_changed = True
        else:
            if self._previous_stop_loss != current_stoploss:
                stop_loss_changed = True

        self._previous_stop_loss = current_stoploss

        return stop_loss_changed

    @property
    async def order_status(self) -> str:
        if not hasattr(self, "_order_status"):
            await self.set_order_status()

        return self._order_status

    async def set_order_status(self) -> None:
        try:
            self._order_status = await self.exchange.fetch_order_status(
                id=self.trigger_order.get("id"),
                symbol=self.ticker,
                params={"trigger": True},
            )
        except Exception as e:
            print(e)
            self._order_status = "not open"
            print("order status: not open")


    async def update_order(self) -> None:
        """Use calculated data to adjust order on exchange"""

        if await self.order_status == "open":
            await self.exchange.edit_order(
                id=self.trigger_order.get("id"),
                symbol=self.ticker,
                type="market",
                side="buy" if self.direction == "long" else "sell",
                amount=await self.amount,
                params={
                    "stopLoss": {"triggerPrice": await self.stop_loss},
                    "takeProfit": {"triggerPrice": await self.target},
                },
            )
            self.order_last_update = datetime.now()
        else:
            self.finished = True

    async def cancel_order(self) -> None:
        """If SL gets too big, cancel trade"""

        await self.exchange.cancel_all_orders(symbol="BTCUSDT")
