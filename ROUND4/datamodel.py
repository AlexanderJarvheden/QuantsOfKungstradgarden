class OrderDepth:
    def __init__(self, buy_orders=None, sell_orders=None):
        self.buy_orders = buy_orders if buy_orders is not None else {}
        self.sell_orders = sell_orders if sell_orders is not None else {}

class Trade:
    def __init__(self, symbol, price, quantity, buyer=None, seller=None, timestamp=0):
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.buyer = buyer
        self.seller = seller
        self.timestamp = timestamp

class TradingState:
    def __init__(self, traderData, timestamp, listings, order_depths, own_trades, market_trades, position, observations):
        self.trader_data = traderData # Note: in real env this is traderData, but my code uses trader_data or traderData. Let's use traderData and trader_data properties.
        self.timestamp = timestamp
        self.listings = listings
        self.order_depths = order_depths
        self.own_trades = own_trades
        self.market_trades = market_trades
        self.position = position
        self.observations = observations

    @property
    def trader_data(self):
        return self._trader_data

    @trader_data.setter
    def trader_data(self, value):
        self._trader_data = value
        self.traderData = value

class Order:
    def __init__(self, symbol, price, quantity):
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
