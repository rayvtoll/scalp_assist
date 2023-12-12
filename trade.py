import ccxt
from dataclasses import dataclass

from trigger import Trigger


@dataclass
class Order:
    """Holds all order data"""

    trigger: Trigger
    size: float | None = None
    leverage: float | None = None
    stop_loss: float | None = None
    target: float | None = None

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
    def is_live(self) -> bool:
        return False

    async def get_or_set_order(self, price: float, balance: dict) -> None:
        """Adjust order on exchange"""

        self.get_free_balance(balance)
        self.set_stop_loss(price)
        self.set_size()
        await self.update_exchange()

    def set_stop_loss(self, price: float) -> None:
        """Calculate stoploss for order"""

        if not self.stop_loss:
            self.stop_loss = (
                round(max(price, self.trigger.price * 1.0025), 2)
                if self.trigger.direction == "short"
                else round(min(price, self.trigger.price * (1 - 0.0025)), 2)
            )
            print(f"stoploss set to {str(self.stop_loss)}")
            return

        temp_sl = self.stop_loss
        match self.trigger.direction:
            case "long":
                if price < self.stop_loss:
                    self.stop_loss = round(
                        min(price, self.trigger.price * (1 - 0.0025)), 2
                    )
            case "short":
                if price > self.stop_loss:
                    self.stop_loss = round(max(price, self.trigger.price * 1.0025), 2)
        if temp_sl != self.stop_loss:
            print(f"stoploss changed to {str(self.stop_loss)}")

    def set_size(self) -> None:
        """TODO: Calculate ordersize"""

        self.size = 0.001

    async def update_exchange(self) -> None:
        """Use calculated data to adjust order on exchange"""

        # leverage = await self.exchange.private_post_v5_position_set_leverage(
        #     params={"category": "LinearFutures"}
        # )
        # print(leverage)
        # print("exchange updated")
        pass

    def cancel_trade(self) -> None:
        """If SL gets too big, cancel trade"""

        print("cancel trade")

    def get_free_balance(self, balance: dict) -> float:
        """Calculate free USDT to use for order depending on SL"""

        usdt = balance.get("USDT", {})
        free = usdt.get("free", 0)
        return free
