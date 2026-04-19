import json
from datamodel import Order, TradingState, OrderDepth
from typing import List, Dict

class Trader:
    LIMITS = {"ASH_COATED_OSMIUM": 80, "INTARIAN_PEPPER_ROOT": 80}
    
    # CONSTANTS FROM DATA
    OSMIUM_MEAN = 10000.88
    OSMIUM_STD = 5.10
    PEPPER_DRIFT = 0.1001
    PEPPER_MAX_DD = 21.0

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        trader_state = json.loads(state.traderData) if state.traderData else {}

        for product in state.order_depths:
            od = state.order_depths[product]
            pos = state.position.get(product, 0)
            limit = self.LIMITS[product]

            if product == "ASH_COATED_OSMIUM":
                result[product] = self._optimize_osmium(od, pos, limit, trader_state)
            elif product == "INTARIAN_PEPPER_ROOT":
                result[product] = self._optimize_pepper(od, pos, limit, trader_state)

        return result, 0, json.dumps(trader_state)

    def _optimize_osmium(self, od, pos, limit, ts) -> List[Order]:
        orders = []
        # Use a very fast alpha due to the 2.65 half-life
        mid = (max(od.buy_orders) + min(od.sell_orders)) / 2
        ema = ts.get("ao_ema", self.OSMIUM_MEAN)
        ema = 0.4 * mid + 0.6 * ema # Fast EMA
        ts["ao_ema"] = ema

        buy_cap = limit - pos
        sell_cap = limit + pos

        # 1. LIQUIDITY PROVIDING (The core profit)
        # We place orders at Fair Price +/- 8 (half the spread)
        # We skew by position to stay near zero
        bid_price = int(ema - 8 - (pos / 10))
        ask_price = int(ema + 8 - (pos / 10))

        if buy_cap > 0:
            orders.append(Order("ASH_COATED_OSMIUM", bid_price, buy_cap))
        if sell_cap > 0:
            orders.append(Order("ASH_COATED_OSMIUM", ask_price, -sell_cap))

        # 2. SNIPING (Aggressive taking of outliers)
        # Only take if the price is > 2 sigma away
        for ask, qty in od.sell_orders.items():
            if ask < ema - 11 and buy_cap > 0:
                orders.append(Order("ASH_COATED_OSMIUM", ask, min(-qty, buy_cap)))
        
        return orders

    def _optimize_pepper(self, od, pos, limit, ts) -> List[Order]:
        orders = []
        best_ask = min(od.sell_orders.keys())
        
        # Tracking the Peak Price to calculate drawdown
        peak = ts.get("ip_peak", 0)
        if best_ask > peak: ts["ip_peak"] = best_ask
        
        drawdown = peak - best_ask
        buy_cap = limit - pos

        # If drawdown is less than max historical (21), we keep buying
        if drawdown < self.PEPPER_MAX_DD and buy_cap > 0:
            # Hit the asks immediately (Market Order logic)
            # Fill probability for limits is too low to wait.
            for ask, qty in sorted(od.sell_orders.items()):
                if buy_cap > 0:
                    take_qty = min(-qty, buy_cap)
                    orders.append(Order("INTARIAN_PEPPER_ROOT", ask, take_qty))
                    buy_cap -= take_qty
        
        return orders