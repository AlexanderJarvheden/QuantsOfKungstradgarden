import json
from datamodel import Order, TradingState, OrderDepth
from typing import List, Dict

class Trader:
    LIMITS = {"ASH_COATED_OSMIUM": 80, "INTARIAN_PEPPER_ROOT": 80}
    
    # CONSTANTS FROM YOUR HISTORIC DATA
    OSMIUM_MEAN = 10000.88
    OSMIUM_STD = 5.10
    PEPPER_MAX_DD = 21.0

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        
        # Robust trader_state loading
        trader_state = {}
        if state.traderData:
            try:
                trader_state = json.loads(state.traderData)
            except json.JSONDecodeError:
                trader_state = {}

        for product in self.LIMITS.keys():
            # Check if we actually have data for this product in this tick
            if product not in state.order_depths:
                continue
                
            od = state.order_depths[product]
            pos = state.position.get(product, 0)
            limit = self.LIMITS[product]

            if product == "ASH_COATED_OSMIUM":
                result[product] = self._optimize_osmium(od, pos, limit, trader_state)
            elif product == "INTARIAN_PEPPER_ROOT":
                result[product] = self._optimize_pepper(od, pos, limit, trader_state)

        return result, 0, json.dumps(trader_state)

    def _optimize_osmium(self, od: OrderDepth, pos: int, limit: int, ts: dict) -> List[Order]:
        orders = []
        
        # Safety Guard: Ensure we have both sides of the book
        if not od.buy_orders or not od.sell_orders:
            return orders

        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())
        mid = (best_bid + best_ask) / 2
        
        # EMA Logic
        ema = ts.get("ao_ema", self.OSMIUM_MEAN)
        ema = 0.4 * mid + 0.6 * ema 
        ts["ao_ema"] = ema

        buy_cap = limit - pos
        sell_cap = limit + pos

        # 1. LIQUIDITY PROVIDING (Passive Orders)
        # We target a spread around the EMA, skewed by our position
        bid_price = int(round(ema - 8 - (pos / 10)))
        ask_price = int(round(ema + 8 - (pos / 10)))

        if buy_cap > 0:
            orders.append(Order("ASH_COATED_OSMIUM", bid_price, buy_cap))
        if sell_cap > 0:
            orders.append(Order("ASH_COATED_OSMIUM", ask_price, -sell_cap))

        # 2. SNIPING (Taking existing mispriced orders)
        for ask, qty in sorted(od.sell_orders.items()):
            if ask < ema - 11 and buy_cap > 0:
                take_qty = min(-qty, buy_cap)
                orders.append(Order("ASH_COATED_OSMIUM", ask, take_qty))
                buy_cap -= take_qty
        
        return orders

    def _optimize_pepper(self, od: OrderDepth, pos: int, limit: int, ts: dict) -> List[Order]:
        orders = []
        if not od.sell_orders:
            return orders

        best_ask = min(od.sell_orders.keys())
        
        # Peak Tracking for Drawdown Protection
        peak = ts.get("ip_peak", best_ask)
        if best_ask > peak:
            peak = best_ask
        ts["ip_peak"] = peak
        
        drawdown = peak - best_ask
        buy_cap = limit - pos

        # Aggressive Market Taking
        if drawdown < self.PEPPER_MAX_DD and buy_cap > 0:
            for ask, qty in sorted(od.sell_orders.items()):
                if buy_cap > 0:
                    take_qty = min(-qty, buy_cap)
                    orders.append(Order("INTARIAN_PEPPER_ROOT", ask, take_qty))
                    buy_cap -= take_qty
        
        return orders