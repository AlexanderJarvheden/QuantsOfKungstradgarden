from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict
import json


class Trader:
    """
    Round 1 strategy informed by both price CSVs and trade CSVs.

    PRICE DATA findings:
      - ASH_COATED_OSMIUM: stationary ~10 000, std ≈ 5, autocorr ≈ −0.50
      - INTARIAN_PEPPER_ROOT: uptrend ~1 000/day, intraday std ≈ 289

    TRADE DATA findings:
      - All bot trades happen at bid/ask levels (offset ±8 for ASH, ±6 for
        PEPPER), never inside the spread.  Our inside-spread quotes attract
        bots to better prices.
      - ASH flow signal is noise (corr ≈ 0.05, decays to 0 by 5 ticks).
      - PEPPER has strong momentum: net buy flow predicts +2.06 future
        return, net sell flow predicts −0.76 (corr ≈ 0.38, persists 10 ticks).
        Used to adjust passive buy aggressiveness during accumulation.
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

            market_trades = state.market_trades.get(product, []) if state.market_trades else []

            if product == "ASH_COATED_OSMIUM":
                result[product] = self._trade_osmium(od, pos, limit, trader_state)
            elif product == "INTARIAN_PEPPER_ROOT":
                result[product] = self._trade_pepper(od, pos, limit, trader_state, market_trades)
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
        """
        Trade data confirms ASH flow signal is noise (corr 0.05), so no
        flow adjustment here.  Keep the proven ±2 spread (most fills at
        fair+2 to fair+4 in v1 logs) with stronger skew for inventory mgmt.
        """
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
        skew = round(pos / limit * 5)

        buy_price = int(fair - 2 - skew)
        sell_price = int(fair + 2 - skew)

        if buy_cap > 0:
            orders.append(Order("ASH_COATED_OSMIUM", buy_price, buy_cap))
        if sell_cap > 0:
            orders.append(Order("ASH_COATED_OSMIUM", sell_price, -sell_cap))

        return orders

    # ------------------------------------------------------------------
    # INTARIAN_PEPPER_ROOT  –  trend following with momentum signal
    # ------------------------------------------------------------------

    def _trade_pepper(
        self,
        od: OrderDepth,
        pos: int,
        limit: int,
        ts: dict,
        market_trades: list,
    ) -> List[Order]:
        """
        Trade data reveals strong momentum signal (corr ≈ 0.38):
        positive net flow → expected +2.06 return, negative → −0.76.
        Used to adjust passive buy price during accumulation phase.
        """
        orders: List[Order] = []
        mid = self._mid(od)
        if mid is None:
            return orders

        ema = ts.get("ip", mid)
        ema = 0.4 * mid + 0.6 * ema
        ts["ip"] = ema
        fair = round(ema)

        # --- momentum signal from bot trades (corr ≈ 0.38) ----------------
        current_flow = 0
        for trade in market_trades:
            if trade.price > mid:
                current_flow += trade.quantity
            elif trade.price < mid:
                current_flow -= trade.quantity

        prev_flow = ts.get("ip_flow", 0.0)
        flow = 0.5 * prev_flow + 0.5 * current_flow
        ts["ip_flow"] = flow

        buy_cap = limit - pos

        # --- aggressive buy: take every available ask ----------------------
        for ask in sorted(od.sell_orders):
            if buy_cap > 0:
                qty = min(-od.sell_orders[ask], buy_cap)
                if qty > 0:
                    orders.append(Order("INTARIAN_PEPPER_ROOT", ask, qty))
                    buy_cap -= qty

        # --- passive buy: price adjusted by momentum -----------------------
        # Positive flow → price rising, pay more to accumulate faster.
        # Negative flow → price dipping, lower bid to get cheaper entry.
        if buy_cap > 0:
            if flow > 0:
                passive_price = int(fair + 1)
            elif flow < 0:
                passive_price = int(fair - 2)
            else:
                passive_price = int(fair)
            orders.append(Order("INTARIAN_PEPPER_ROOT", passive_price, buy_cap))

        return orders
