from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict
import json


class Trader:
    """
    Round 1 strategy for ASH_COATED_OSMIUM and INTARIAN_PEPPER_ROOT.

    ASH_COATED_OSMIUM  – stationary around 10 000, std ≈ 5, strong negative
    lag-1 autocorrelation (≈ −0.50).  Ideal for market making with inventory
    skew: post tight quotes inside the spread and let mean reversion drive
    round-trip profits.

    INTARIAN_PEPPER_ROOT – consistent uptrend of ≈ 1 000 per day (≈ 0.1 per
    tick).  Trend profit dwarfs the ≈ 13 half-spread cost, so the strategy
    aggressively accumulates a max-long position and holds it, selling only
    on short-term overshoots to capture additional mean-reversion alpha.
    """

    LIMITS: Dict[str, int] = {
        "ASH_COATED_OSMIUM": 80,
        "INTARIAN_PEPPER_ROOT": 80,
    }

    def bid(self) -> int:
        return 15

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}

        trader_state: dict = {}
        if state.traderData:
            try:
                trader_state = json.loads(state.traderData)
            except (json.JSONDecodeError, TypeError):
                trader_state = {}

        for product in state.order_depths:
            od = state.order_depths[product]
            pos = state.position.get(product, 0)
            limit = self.LIMITS.get(product, 80)

            if product == "ASH_COATED_OSMIUM":
                result[product] = self._trade_osmium(od, pos, limit, trader_state)
            elif product == "INTARIAN_PEPPER_ROOT":
                result[product] = self._trade_pepper(od, pos, limit, trader_state)
            else:
                result[product] = []

        return result, 0, json.dumps(trader_state)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mid(od: OrderDepth):
        best_bid = max(od.buy_orders) if od.buy_orders else None
        best_ask = min(od.sell_orders) if od.sell_orders else None
        if best_bid is not None and best_ask is not None:
            return (best_bid + best_ask) / 2
        return best_bid if best_bid is not None else best_ask

    # ------------------------------------------------------------------
    # ASH_COATED_OSMIUM  –  market making + mean reversion
    # ------------------------------------------------------------------

    def _trade_osmium(
        self,
        od: OrderDepth,
        pos: int,
        limit: int,
        ts: dict,
    ) -> List[Order]:
        orders: List[Order] = []
        mid = self._mid(od)
        if mid is None:
            return orders

        ema = ts.get("ao", mid)
        ema = 0.25 * mid + 0.75 * ema
        ts["ao"] = ema
        fair = round(ema)

        buy_cap = limit - pos
        sell_cap = limit + pos

        # --- aggressive layer: take any mispriced resting orders -----------
        for ask in sorted(od.sell_orders):
            if ask < fair and buy_cap > 0:
                qty = min(-od.sell_orders[ask], buy_cap)
                if qty > 0:
                    orders.append(Order("ASH_COATED_OSMIUM", ask, qty))
                    buy_cap -= qty

        for bid in sorted(od.buy_orders, reverse=True):
            if bid > fair and sell_cap > 0:
                qty = min(od.buy_orders[bid], sell_cap)
                if qty > 0:
                    orders.append(Order("ASH_COATED_OSMIUM", bid, -qty))
                    sell_cap -= qty

        # --- passive layer: post quotes inside the spread ------------------
        # Inventory skew shifts both prices to encourage position unwind.
        skew = round(pos / limit * 3)

        buy_price = int(fair - 2 - skew)
        sell_price = int(fair + 2 - skew)

        if buy_cap > 0:
            orders.append(Order("ASH_COATED_OSMIUM", buy_price, buy_cap))
        if sell_cap > 0:
            orders.append(Order("ASH_COATED_OSMIUM", sell_price, -sell_cap))

        return orders

    # ------------------------------------------------------------------
    # INTARIAN_PEPPER_ROOT  –  trend following
    # ------------------------------------------------------------------

    def _trade_pepper(
        self,
        od: OrderDepth,
        pos: int,
        limit: int,
        ts: dict,
    ) -> List[Order]:
        orders: List[Order] = []
        mid = self._mid(od)
        if mid is None:
            return orders

        ema = ts.get("ip", mid)
        ema = 0.4 * mid + 0.6 * ema
        ts["ip"] = ema
        fair = round(ema)

        buy_cap = limit - pos
        sell_cap = limit + pos

        # --- aggressive buy: take every available ask ----------------------
        # Trend profit (~1 000/day) vastly exceeds any spread cost (~8).
        for ask in sorted(od.sell_orders):
            if buy_cap > 0:
                qty = min(-od.sell_orders[ask], buy_cap)
                if qty > 0:
                    orders.append(Order("INTARIAN_PEPPER_ROOT", ask, qty))
                    buy_cap -= qty

        # --- sell only on significant overshoot ----------------------------
        for bid in sorted(od.buy_orders, reverse=True):
            if bid > fair + 3 and sell_cap > 0:
                qty = min(od.buy_orders[bid], sell_cap)
                if qty > 0:
                    orders.append(Order("INTARIAN_PEPPER_ROOT", bid, -qty))
                    sell_cap -= qty

        # --- passive buy to keep accumulating ------------------------------
        if buy_cap > 0:
            orders.append(Order("INTARIAN_PEPPER_ROOT", int(fair), buy_cap))

        # --- light passive sell at premium when heavily long ---------------
        if pos > 40 and sell_cap > 0:
            sell_qty = min(sell_cap, pos - 30)
            if sell_qty > 0:
                orders.append(
                    Order("INTARIAN_PEPPER_ROOT", int(fair + 5), -sell_qty)
                )

        return orders
