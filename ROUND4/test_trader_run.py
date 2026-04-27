import sys
import json
from Trader import Trader
from datamodel import TradingState, OrderDepth, Trade

def test_trader():
    trader = Trader()
    
    order_depths = {
        'VELVETFRUIT_EXTRACT': OrderDepth(buy_orders={5000: 10}, sell_orders={5002: -10}),
        'HYDROGEL_PACK': OrderDepth(buy_orders={2000: 10}, sell_orders={2002: -10}),
        'VEV_5000': OrderDepth(buy_orders={100: 5}, sell_orders={105: -5})
    }
    
    market_trades = {
        'VELVETFRUIT_EXTRACT': [Trade('VELVETFRUIT_EXTRACT', 5002, 5, 'Mark 14', 'Mark 22', 100)]
    }
    
    state = TradingState(
        traderData="",
        timestamp=1000,
        listings={},
        order_depths=order_depths,
        own_trades={},
        market_trades=market_trades,
        position={'VELVETFRUIT_EXTRACT': 100, 'VEV_5000': 150},
        observations={}
    )
    
    orders, conversions, trader_data = trader.run(state)
    print("Orders generated:", orders)
    print("Trader data updated:", json.loads(trader_data))

test_trader()
