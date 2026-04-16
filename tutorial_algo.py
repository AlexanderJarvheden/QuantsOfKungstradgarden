import json
from typing import List, Dict, Any, Optional, Tuple
from datamodel import OrderDepth, TradingState, Order


class Trader:

    def run(self, state: TradingState):
        """
        Tutorial Round Trading Algorithm
        Products: EMERALDS (stable ~10,000) and TOMATOES (mean-reverting ~5,000)

        Strategy:
        - EMERALDS: Aggressive market making around fair value of 10,000.
          Take any mispriced orders, then post passive bids/asks to earn spread.
        - TOMATOES: EMA-based mean reversion with adaptive thresholds.
          Track the drifting fair value with an EMA, trade deviations.
        """
        result = {}
        conversions = 0

        # --- Deserialize persistent state ---
        try:
            trader_state = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            trader_state = {}

        # EMA state for tomatoes
        tomato_ema = trader_state.get("tomato_ema", None)

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Current position and limits
            pos = state.position.get(product, 0)
            limit = 80
            max_buy = limit - pos      # > 0 means we can buy this many more
            max_sell = -limit - pos     # < 0 means we can sell (short) this many more

            if product == "EMERALDS":
                orders = self.trade_emeralds(product, order_depth, pos, max_buy, max_sell)

            elif product == "TOMATOES":
                orders, tomato_ema = self.trade_tomatoes(
                    product, order_depth, pos, max_buy, max_sell, tomato_ema
                )

            result[product] = orders

        # --- Serialize persistent state ---
        trader_state["tomato_ema"] = tomato_ema
        traderData = json.dumps(trader_state)

        return result, conversions, traderData

    def trade_emeralds(
        self,
        product: str,
        order_depth: OrderDepth,
        pos: int,
        max_buy: int,
        max_sell: int,
    ) -> List[Order]:
        """
        EMERALDS: Pure market making around fair value = 10,000.

        Phase 1 — Aggressive taking:
          Buy everything offered at <= 9,999 (below fair value)
          Sell to every bid at >= 10,001 (above fair value)

        Phase 2 — Passive posting:
          Bid at 9,998, Ask at 10,002 with remaining capacity
        """
        orders: List[Order] = []
        fair_value = 10_000

        # --- Phase 1: Take mispriced sell orders (buy cheap) ---
        # sell_orders keys are prices, values are NEGATIVE quantities
        if order_depth.sell_orders:
            sorted_asks = sorted(order_depth.sell_orders.items())  # lowest first
            for ask_price, ask_vol in sorted_asks:
                if ask_price <= fair_value - 1 and max_buy > 0:
                    # ask_vol is negative; we buy the absolute amount
                    buy_qty = min(-ask_vol, max_buy)
                    orders.append(Order(product, ask_price, buy_qty))
                    max_buy -= buy_qty

        # --- Phase 1: Take mispriced buy orders (sell high) ---
        # buy_orders keys are prices, values are POSITIVE quantities
        if order_depth.buy_orders:
            sorted_bids = sorted(order_depth.buy_orders.items(), reverse=True)  # highest first
            for bid_price, bid_vol in sorted_bids:
                if bid_price >= fair_value + 1 and max_sell < 0:
                    sell_qty = max(-bid_vol, max_sell)  # negative
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

    def trade_tomatoes(
        self,
        product: str,
        order_depth: OrderDepth,
        pos: int,
        max_buy: int,
        max_sell: int,
        ema: Optional[float],
    ) -> Tuple[List[Order], Optional[float]]:
        """
        TOMATOES: EMA-based mean reversion.

        The fair value drifts over time (~50 ticks/day), so we track it
        with an Exponential Moving Average (alpha=0.1).

        Phase 1 — Aggressive taking:
          Buy if best ask < ema - threshold (undervalued)
          Sell if best bid > ema + threshold (overvalued)

        Phase 2 — Passive posting:
          Post bids/asks around the EMA to capture spread
        """
        orders: List[Order] = []
        alpha = 0.1       # EMA smoothing factor (~10-tick effective lookback)
        take_threshold = 3  # ticks away from EMA to take aggressively
        post_offset = 5     # ticks away from EMA for passive orders

        # Calculate current mid price
        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None

        if best_ask is None or best_bid is None:
            return orders, ema

        mid_price = (best_ask + best_bid) / 2.0

        # Update EMA
        if ema is None:
            ema = mid_price
        else:
            ema = alpha * mid_price + (1 - alpha) * ema

        fair = round(ema)

        # --- Phase 1: Aggressive taking when price diverges from EMA ---

        # Take cheap asks (price well below fair value)
        if order_depth.sell_orders:
            sorted_asks = sorted(order_depth.sell_orders.items())
            for ask_price, ask_vol in sorted_asks:
                if ask_price < fair - take_threshold and max_buy > 0:
                    buy_qty = min(-ask_vol, max_buy)
                    orders.append(Order(product, ask_price, buy_qty))
                    max_buy -= buy_qty
                else:
                    break  # asks are sorted ascending, no point continuing

        # Take expensive bids (price well above fair value)
        if order_depth.buy_orders:
            sorted_bids = sorted(order_depth.buy_orders.items(), reverse=True)
            for bid_price, bid_vol in sorted_bids:
                if bid_price > fair + take_threshold and max_sell < 0:
                    sell_qty = max(-bid_vol, max_sell)
                    orders.append(Order(product, bid_price, sell_qty))
                    max_sell -= sell_qty
                else:
                    break  # bids are sorted descending

        # --- Phase 2: Post passive orders around the EMA ---
        passive_bid = fair - post_offset
        passive_ask = fair + post_offset

        if max_buy > 0:
            orders.append(Order(product, passive_bid, max_buy))
        if max_sell < 0:
            orders.append(Order(product, passive_ask, max_sell))

        return orders, ema
