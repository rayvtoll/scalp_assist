from dataclasses import dataclass
from datetime import datetime, timedelta

import ccxt


@dataclass
class Trigger:
    price: float
    direction: str
    exchange: ccxt.bybit

    triggered: bool = False
    finished: bool = False

    def check_for_trigger(self, price: float):
        if (
            self.direction == "long" and price < self.price
        ) or (
            self.direction == "short" and price > self.price
        ):
            self.triggered = True
            self.datetime = datetime.now()
    
    def enough_delay(self, **kwargs) -> bool:
        return self.datetime + timedelta(**kwargs) < datetime.now()
