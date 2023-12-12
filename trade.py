import ccxt
from dataclasses import dataclass

from trigger import Trigger


@dataclass
class Trade:
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

    async def get_or_set_order(self, price: float, balance: dict) -> None:
        self.get_free_balance(balance)
        self.set_stop_loss(price)
        self.set_size()
        await self.update_exchange()

    @property
    def is_live(self) -> bool:
        return False

    def set_stop_loss(self, price: float) -> None:
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

    def set_size(self) -> None:  # , price: int):
        self.size = 0.001

    async def update_exchange(self) -> None:
        # leverage = await self.exchange.private_post_v5_position_set_leverage(
        #     params={"category": "LinearFutures"}
        # )
        # print(leverage)
        # print("exchange updated")
        pass

    def cancel_trade(self) -> None:
        print("cancel trade")

    def get_free_balance(self, balance: dict) -> float:
        usdt = balance.get("USDT", {})
        free = usdt.get("free", 0)
        return free
