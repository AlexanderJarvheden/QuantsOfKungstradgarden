import json
from datamodel import Order, TradingState, OrderDepth
from typing import List, Dict

class Trader:
    LIMITS = {"ASH_COATED_OSMIUM": 80, "INTARIAN_PEPPER_ROOT": 80}

    # ===================== HYPERPARAMETERS (OPTIMIZED) =====================
    # Pepper Root (Trend) — Buy & Hold
    PEPPER_MAX_LEVELS = 1       # Only take best ask (avoid slippage)
    PEPPER_PASSIVE_OFFSET = 0   # Bid at best_ask itself (max aggression for fast fill)
    
    # Osmium (Mean Reversion) — Market Making
    OSMIUM_FAIR = 10000         # Known mean
    OSMIUM_SPREAD = 2           # Passive quote distance from fair (fair ± 2)
    OSMIUM_AGGR_THRESH = 3      # Only snipe when mispriced by ≥3 (avoid toxic fills)
    OSMIUM_SKEW_FACTOR = 4      # Inventory skew multiplier
    # End-of-day: dump everything
    END_OF_DAY_TIMESTAMP = 998000
    # ===========================================================

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        trader_state = json.loads(state.traderData) if state.traderData else {}

        for product in self.LIMITS:
            if product not in state.order_depths:
                continue
            od = state.order_depths[product]
            pos = state.position.get(product, 0)
            limit = self.LIMITS[product]

            # END OF DAY: Liquidate all positions
            if state.timestamp >= self.END_OF_DAY_TIMESTAMP:
                result[product] = self._liquidate(od, pos, product)
            elif product == "INTARIAN_PEPPER_ROOT":
                result[product] = self._trade_pepper(od, pos, limit)
            elif product == "ASH_COATED_OSMIUM":
                result[product] = self._trade_osmium(od, pos, limit)

        return result, 0, json.dumps(trader_state)

    def _liquidate(self, od: OrderDepth, pos: int, product: str) -> List[Order]:
        """Dump entire position by sweeping the book."""
        orders = []
        if pos > 0 and od.buy_orders:
            remaining = pos
            for bid, qty in sorted(od.buy_orders.items(), reverse=True):
                if remaining > 0:
                    sell_qty = min(qty, remaining)
                    orders.append(Order(product, bid, -sell_qty))
                    remaining -= sell_qty
            # If book was thin, undercut to guarantee exit
            if remaining > 0:
                worst_bid = min(od.buy_orders.keys())
                orders.append(Order(product, worst_bid - 1, -remaining))
        elif pos < 0 and od.sell_orders:
            remaining = -pos
            for ask, qty in sorted(od.sell_orders.items()):
                if remaining > 0:
                    buy_qty = min(-qty, remaining)
                    orders.append(Order(product, ask, buy_qty))
                    remaining -= buy_qty
            if remaining > 0:
                worst_ask = max(od.sell_orders.keys())
                orders.append(Order(product, worst_ask + 1, remaining))
        return orders

    def _trade_pepper(self, od: OrderDepth, pos: int, limit: int) -> List[Order]:
        """Trend following: accumulate and hold max long position."""
        orders = []
        if not od.buy_orders or not od.sell_orders:
            return orders

        best_ask = min(od.sell_orders.keys())
        buy_cap = limit - pos

        if buy_cap <= 0:
            return orders

        # 1. Sweep ask levels up to PEPPER_MAX_LEVELS
        levels_taken = 0
        for ask, qty in sorted(od.sell_orders.items()):
            if buy_cap > 0 and levels_taken < self.PEPPER_MAX_LEVELS:
                take_qty = min(-qty, buy_cap)
                orders.append(Order("INTARIAN_PEPPER_ROOT", ask, take_qty))
                buy_cap -= take_qty
                levels_taken += 1

        # 2. Place passive bid for remaining
        if buy_cap > 0:
            passive_price = best_ask - self.PEPPER_PASSIVE_OFFSET
            orders.append(Order("INTARIAN_PEPPER_ROOT", passive_price, buy_cap))

        return orders

    def _trade_osmium(self, od: OrderDepth, pos: int, limit: int) -> List[Order]:
        """Market making: mean reversion around known fair value."""
        orders = []
        if not od.buy_orders or not od.sell_orders:
            return orders

        fair = self.OSMIUM_FAIR
        buy_cap = limit - pos
        sell_cap = limit + pos

        # AGGRESSIVE: Take mispriced orders beyond threshold
        for ask, qty in sorted(od.sell_orders.items()):
            if ask <= fair - self.OSMIUM_AGGR_THRESH and buy_cap > 0:
                take_qty = min(-qty, buy_cap)
                orders.append(Order("ASH_COATED_OSMIUM", ask, take_qty))
                buy_cap -= take_qty

        for bid, qty in sorted(od.buy_orders.items(), reverse=True):
            if bid >= fair + self.OSMIUM_AGGR_THRESH and sell_cap > 0:
                take_qty = min(qty, sell_cap)
                orders.append(Order("ASH_COATED_OSMIUM", bid, -take_qty))
                sell_cap -= take_qty

        # PASSIVE: Quote around fair, skewed by inventory
        skew = int((pos / limit) * self.OSMIUM_SKEW_FACTOR)
        if buy_cap > 0:
            orders.append(Order("ASH_COATED_OSMIUM", fair - self.OSMIUM_SPREAD - skew, buy_cap))
        if sell_cap > 0:
            orders.append(Order("ASH_COATED_OSMIUM", fair + self.OSMIUM_SPREAD - skew, -sell_cap))

        return orders