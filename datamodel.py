import json
from typing import Dict, List
from json import JSONEncoder
import jsonpickle

Time = int
Symbol = str
Product = str
Position = int
UserId = str
ObservationValue = int


class Listing:

    def __init__(self, symbol: Symbol, product: Product, denomination: Product):
        self.symbol = symbol
        self.product = product
        self.denomination = denomination
        
                 
class ConversionObservation:

    def __init__(self, bidPrice: float, askPrice: float, transportFees: float, exportTariff: float, importTariff: float, sunlight: float, humidity: float):
        self.bidPrice = bidPrice
        self.askPrice = askPrice
        self.transportFees = transportFees
        self.exportTariff = exportTariff
        self.importTariff = importTariff
        self.sugarPrice = sugarPrice
        self.sunlightIndex = sunlightIndex
        

class Observation:

    def __init__(self, plainValueObservations: Dict[Product, ObservationValue], conversionObservations: Dict[Product, ConversionObservation]) -> None:
        self.plainValueObservations = plainValueObservations
        self.conversionObservations = conversionObservations
        
    def __str__(self) -> str:
        return "(plainValueObservations: " + jsonpickle.encode(self.plainValueObservations) + ", conversionObservations: " + jsonpickle.encode(self.conversionObservations) + ")"
     

class Order:
    """
    Each order has three important properties. These are:
        1. The symbol of the product for which the order is sent.
        2. The price of the order: the maximum price at which the algorithm wants to buy in case 
            of a BUY order, or the minimum price at which the algorithm wants to sell in case of a SELL order.
        3. The quantity of the order: the maximum quantity that the algorithm wishes to buy or sell. 
        If the sign of the quantity is positive, the order is a buy order, if the sign of the quantity 
        is negative it is a sell order.
    """
    def __init__(self, symbol: Symbol, price: int, quantity: int) -> None:
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

    def __str__(self) -> str:
        return "(" + self.symbol + ", " + str(self.price) + ", " + str(self.quantity) + ")"

    def __repr__(self) -> str:
        return "(" + self.symbol + ", " + str(self.price) + ", " + str(self.quantity) + ")"
    

class OrderDepth:
    """
        This object contains the collection of all outstanding buy and sell orders, 
        or “quotes” that were sent by the trading bots, for a certain symbol. 
    """
    def __init__(self):
        """
            the keys indicate the price associated with the order, and the 
            corresponding values indicate the total volume on that price level. 
            
            Examples: 
            self.buy_orders = {9: 5, 10: 4}, then there is a total buy order quantity of 
            5 at the price level of 9, and a total buy order quantity of 4 at a price level of 10.
            
            self.sell_orders = {12: -3, 11: -2} would mean that the aggregated sell order volume 
            at price level 12 is 3, and 2 at price level 11.
        """
        self.buy_orders: Dict[int, int] = {}
        self.sell_orders: Dict[int, int] = {}


class Trade:

    def __init__(self, symbol: Symbol, price: int, quantity: int, buyer: UserId=None, seller: UserId=None, timestamp: int=0) -> None:
        """
            Args:
                buyer/seller: if algorithm acts as a buyer then “SUBMISSION”, if algorithm acts as a seller then “SUBMISSION”
        """
        self.symbol = symbol
        self.price: int = price
        self.quantity: int = quantity
        self.buyer = buyer
        self.seller = seller
        self.timestamp = timestamp

    def __str__(self) -> str:
        return "(" + self.symbol + ", " + self.buyer + " << " + self.seller + ", " + str(self.price) + ", " + str(self.quantity) + ", " + str(self.timestamp) + ")"

    def __repr__(self) -> str:
        return "(" + self.symbol + ", " + self.buyer + " << " + self.seller + ", " + str(self.price) + ", " + str(self.quantity) + ", " + str(self.timestamp) + ")"


class TradingState(object):

    def __init__(self,
                 traderData: str,
                 timestamp: Time,
                 listings: Dict[Symbol, Listing],
                 order_depths: Dict[Symbol, OrderDepth],
                 own_trades: Dict[Symbol, List[Trade]],
                 market_trades: Dict[Symbol, List[Trade]],
                 position: Dict[Product, Position],
                 observations: Observation):
        """
            Args:
                own_trades:    
                    the trades the algorithm itself has done since the last TradingState came in. 
                    This property is a dictionary of Trade objects with key being a product name. 
                market_trades: 
                    the trades that other market participants have done since the last TradingState came in. 
                    This property is also a dictionary of Trade objects with key being a product name.
                position: 
                    the long or short position that the player holds in every tradable product. 
                    This property is a dictionary with the product as the key for which the value is a 
                    signed integer denoting the position, e.g. {product1: 2, product2: -1}.
                order_depths: 
                    all the buy and sell orders per product that other market participants have sent and that the 
                    algorithm is able to trade with. This property is a dict where the keys are the products and 
                    the corresponding values are instances of the OrderDepth class. This OrderDepth class then 
                    contains all the buy and sell orders.

        """
        self.traderData = traderData
        self.timestamp = timestamp
        self.listings = listings
        self.order_depths = order_depths
        self.own_trades = own_trades
        self.market_trades = market_trades
        self.position = position
        self.observations = observations
        
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)

    
class ProsperityEncoder(JSONEncoder):

        def default(self, o):
            return o.__dict__