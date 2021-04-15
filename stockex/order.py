from enum import Enum
from time import time


class Side(Enum):
    BUY = 0
    SELL = 1


class Order(object):
    def __init__(self, order_id: int):
        self.order_id = order_id
        self.time = int(1e6 * time())

    def __getType__(self):
        return self.__class__


class CancelOrder(Order):
    def __init__(self, order_id):
        super().__init__(order_id)

    def __repr__(self):
        return "Cancel Order: {}.".format(self.order_id)


class MarketOrder(Order):
    def __init__(self, order_id: int, side: Side, size: int):
        super().__init__(order_id)
        self.side = side
        self.size = self.remainingToFill = size

    def __repr__(self):
        return "Market Order: {0} {1} units.".format(
            "BUY" if self.side == Side.BUY else "SELL",
            self.RemainingToFill)