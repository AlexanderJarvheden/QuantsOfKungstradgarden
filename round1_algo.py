import json
from typing import List, Dict, Any, Optional, Tuple
from datamodel import OrderDepth, TradingState, Order


class Trader:

    def run(self, state: TradingState):
        """
        Round 1 Trading Algorithm
        Products: ASH_COATED_OSMIUM and INTARIAN_PEPPER_ROOT

        Strategy:
        - ASH_COATED_OSMIUM: Aggressive market making around fair value ~10,000.
          Take mispriced orders, then post passive bids/asks to earn spread.
        - INTARIAN_PEPPER_ROOT: Linear trend rider. Price rises at exactly
          +0.1 per tick (~1,000 per trading day) with R²=0.9999.
          Buy and hold at max position to ride the trend.
        """
        result = {}
        conversions = 0

        # --- Deserialize persistent state ---
        try:
            trader_state = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            trader_state = {}

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Current position and limits
            pos = state.position.get(product, 0)
            limit = 80
            max_buy = limit - pos      # > 0 means we can buy this many more
            max_sell = -limit - pos     # < 0 means we can sell (short) this many more

            if product == "ASH_COATED_OSMIUM":
                orders = self.trade_osmium(product, order_depth, pos, max_buy, max_sell)

            elif product == "INTARIAN_PEPPER_ROOT":
                orders, trader_state = self.trade_pepper_root(
                    product, order_depth, pos, max_buy, max_sell,
                    trader_state, state.timestamp
                )

            result[product] = orders

        # --- Serialize persistent state ---
        traderData = json.dumps(trader_state)
        return result, conversions, traderData

    # ─────────────────────────────────────────────────────────────────────
    # ASH_COATED_OSMIUM — Aggressive Market Making
    # ─────────────────────────────────────────────────────────────────────
    def trade_osmium(
        self,
        product: str,
        order_depth: OrderDepth,
        pos: int,
        max_buy: int,
        max_sell: int,
    ) -> List[Order]:
        """
        ASH_COATED_OSMIUM: Mean-reverting around ~10,000.
        StdDev ≈ 5, range ≈ 9,977–10,023, spread ≈ 16.

        Phase 1 — Aggressive taking:
          Buy everything offered at ≤ 9,999 (below fair value)
          Sell to every bid at ≥ 10,001 (above fair value)

        Phase 2 — Passive posting:
          Bid at 9,998 / Ask at 10,002 with remaining capacity
        """
        orders: List[Order] = []
        fair_value = 10_000

        # --- Phase 1: Take mispriced sell orders (buy cheap) ---
        if order_depth.sell_orders:
            sorted_asks = sorted(order_depth.sell_orders.items())  # lowest price first
            for ask_price, ask_vol in sorted_asks:
                if ask_price <= fair_value - 1 and max_buy > 0:
                    # ask_vol is negative in the datamodel; buy the absolute amount
                    buy_qty = min(-ask_vol, max_buy)
                    orders.append(Order(product, ask_price, buy_qty))
                    max_buy -= buy_qty

        # --- Phase 1: Take mispriced buy orders (sell high) ---
        if order_depth.buy_orders:
            sorted_bids = sorted(order_depth.buy_orders.items(), reverse=True)  # highest first
            for bid_price, bid_vol in sorted_bids:
                if bid_price >= fair_value + 1 and max_sell < 0:
                    sell_qty = max(-bid_vol, max_sell)  # sell_qty is negative
                    orders.append(Order(product, bid_price, sell_qty))
                    max_sell -= sell_qty

        # --- Phase 2: Post passive orders to earn spread ---
        passive_bid = fair_value - 2   # 9,998
        passive_ask = fair_value + 2   # 10,002

        if max_buy > 0:
            orders.append(Order(product, passive_bid, max_buy))
        if max_sell < 0:
            orders.append(Order(product, passive_ask, max_sell))

        return orders

    # ─────────────────────────────────────────────────────────────────────
    # INTARIAN_PEPPER_ROOT — Linear Trend Rider
    # ─────────────────────────────────────────────────────────────────────
    def trade_pepper_root(
        self,
        product: str,
        order_depth: OrderDepth,
        pos: int,
        max_buy: int,
        max_sell: int,
        trader_state: Dict,
        timestamp: int,
    ) -> Tuple[List[Order], Dict]:
        """
        INTARIAN_PEPPER_ROOT: Near-perfect linear uptrend.

        Data analysis shows:
          - Slope: exactly +0.1 per tick (+0.001 per timestamp unit)
          - R² = 0.9999, residual noise = ±2 ticks
          - Rises ~1,000 per trading day across all 3 sample days

        Strategy: Get to max long position (+80) ASAP and hold.
          - Aggressively buy anything at or below estimated fair value
          - Post passive bids near fair value to accumulate more
          - Never sell — we want to ride the full trend
        """
        orders: List[Order] = []
        trend_slope = 0.001  # price increase per timestamp unit (0.1 per tick)

        # --- Estimate current fair value from the trend ---
        # Calculate mid price for intercept calibration
        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None

        if best_ask is None and best_bid is None:
            return orders, trader_state

        # Compute current observed mid price
        if best_ask is not None and best_bid is not None:
            mid_price = (best_ask + best_bid) / 2.0
        elif best_ask is not None:
            mid_price = float(best_ask)
        else:
            mid_price = float(best_bid)

        # Estimate the intercept (price at t=0) on first observation,
        # then slowly adapt it to correct for any drift
        observed_intercept = mid_price - trend_slope * timestamp

        if "pepper_intercept" not in trader_state:
            trader_state["pepper_intercept"] = observed_intercept
        else:
            # Slowly adapt intercept (1% update per tick) to correct for
            # any discrepancy between our model and reality
            stored = trader_state["pepper_intercept"]
            trader_state["pepper_intercept"] = 0.99 * stored + 0.01 * observed_intercept

        intercept = trader_state["pepper_intercept"]
        fair = intercept + trend_slope * timestamp

        # -------------------------------------------------------------------
        # STRATEGY: BUY AND HOLD
        # We want to be max long (position = +80) as quickly as possible.
        # Every tick we hold 80 units, we earn 80 × 0.1 = 8 seashells.
        # Over 10,000 ticks that's 80,000 profit from holding alone.
        # -------------------------------------------------------------------

        # Phase 1: Aggressively take all sell orders at or below fair + 2
        # Even buying slightly above fair is profitable because the price
        # will be higher next tick. The residual noise is only ±2.
        if order_depth.sell_orders and max_buy > 0:
            sorted_asks = sorted(order_depth.sell_orders.items())
            for ask_price, ask_vol in sorted_asks:
                if ask_price <= fair + 2 and max_buy > 0:
                    buy_qty = min(-ask_vol, max_buy)
                    orders.append(Order(product, ask_price, buy_qty))
                    max_buy -= buy_qty
                else:
                    break  # asks sorted ascending, done

        # Phase 2: Post passive bid near fair value to accumulate more
        if max_buy > 0:
            passive_bid = int(round(fair - 1))
            orders.append(Order(product, passive_bid, max_buy))

        # We do NOT post any sell orders.
        # We WANT to hold max long position and ride the trend.

        return orders, trader_state
