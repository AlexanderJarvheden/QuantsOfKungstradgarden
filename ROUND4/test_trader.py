from Trader import Trader
from datamodel import TradingState, OrderDepth, Trade

t = Trader()
state = TradingState(
    traderData="",
    timestamp=0,
    listings={},
    order_depths={
        'HYDROGEL_PACK': OrderDepth(buy_orders={10: 5}, sell_orders={12: -5}),
        'VELVETFRUIT_EXTRACT': OrderDepth(buy_orders={10: 5}, sell_orders={12: -5}),
        'VEV_5000': OrderDepth(buy_orders={10: 5}, sell_orders={12: -5})
    },
    own_trades={},
    market_trades={
        'HYDROGEL_PACK': [Trade('HYDROGEL_PACK', 11, 1, 'Mark 14', 'Some Guy', 0)]
    },
    position={},
    observations={}
)
try:
    res = t.run(state)
    print(res)
except Exception as e:
    import traceback
    traceback.print_exc()
