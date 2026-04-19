"""
Fast Backtester + Grid Search Optimizer for IMC Prosperity strategies.

Usage:
    python Backtester.py              # Run single backtest with current hyperparameters
    python Backtester.py --optimize   # Run grid search over all hyperparameter combos
"""

import pandas as pd
import numpy as np
import os
import sys
import time
import itertools

from datamodel import OrderDepth, TradingState, Listing, Order
from Trader import Trader


# ====================================================================
# DATA LOADING (cached)
# ====================================================================
_CACHED_TICK_DATA = None

def load_and_cache():
    global _CACHED_TICK_DATA
    if _CACHED_TICK_DATA is not None:
        return _CACHED_TICK_DATA

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_paths = {}
    for root, dirs, files in os.walk(script_dir):
        for f in files:
            if f.endswith('.csv'):
                file_paths[f] = os.path.join(root, f)

    prices_list = []
    for day in [-1, 0, 1]:
        p_name = f"prices_round_2_day_{day}.csv"
        if p_name in file_paths:
            pdf = pd.read_csv(file_paths[p_name], sep=';')
            pdf['day'] = day
            prices_list.append(pdf)

    prices = pd.concat(prices_list, ignore_index=True)

    cols = ['day', 'timestamp', 'product',
            'bid_price_1', 'bid_volume_1', 'bid_price_2', 'bid_volume_2', 'bid_price_3', 'bid_volume_3',
            'ask_price_1', 'ask_volume_1', 'ask_price_2', 'ask_volume_2', 'ask_price_3', 'ask_volume_3',
            'mid_price']
    records = prices[cols].to_dict('records')

    tick_data = {}
    for rec in records:
        key = (rec['day'], rec['timestamp'])
        if key not in tick_data:
            tick_data[key] = {}
        tick_data[key][rec['product']] = rec

    sorted_ticks = sorted(tick_data.keys())
    _CACHED_TICK_DATA = (tick_data, sorted_ticks)
    return _CACHED_TICK_DATA


# ====================================================================
# ORDER MATCHING ENGINE
# ====================================================================
def build_od(row_dict):
    od = OrderDepth()
    for i in range(1, 4):
        bp, bv = row_dict.get(f'bid_price_{i}'), row_dict.get(f'bid_volume_{i}')
        ap, av = row_dict.get(f'ask_price_{i}'), row_dict.get(f'ask_volume_{i}')
        if bp is not None and bv is not None and not np.isnan(bp) and not np.isnan(bv) and bv > 0:
            od.buy_orders[int(bp)] = int(bv)
        if ap is not None and av is not None and not np.isnan(ap) and not np.isnan(av) and av > 0:
            od.sell_orders[int(ap)] = int(-av)
    return od


def match_orders(orders, row_dict, position, limit, product):
    # Build fresh OD for matching (positive volumes for easier math)
    bids = {}
    asks = {}
    for i in range(1, 4):
        bp, bv = row_dict.get(f'bid_price_{i}'), row_dict.get(f'bid_volume_{i}')
        ap, av = row_dict.get(f'ask_price_{i}'), row_dict.get(f'ask_volume_{i}')
        if bp is not None and bv is not None and not np.isnan(bp) and not np.isnan(bv) and bv > 0:
            bids[int(bp)] = int(bv)
        if ap is not None and av is not None and not np.isnan(ap) and not np.isnan(av) and av > 0:
            asks[int(ap)] = int(av)

    pos = position
    cash = 0.0
    fills = 0

    for order in orders:
        if order.symbol != product:
            continue
        if order.quantity > 0:
            remaining = order.quantity
            for ask_p in sorted(asks.keys()):
                if ask_p > order.price or remaining <= 0:
                    break
                avail = asks[ask_p]
                if avail <= 0:
                    continue
                fq = min(remaining, avail, limit - pos)
                if fq <= 0:
                    break
                cash -= ask_p * fq
                pos += fq
                remaining -= fq
                fills += fq
                asks[ask_p] -= fq
        elif order.quantity < 0:
            remaining = -order.quantity
            for bid_p in sorted(bids.keys(), reverse=True):
                if bid_p < order.price or remaining <= 0:
                    break
                avail = bids[bid_p]
                if avail <= 0:
                    continue
                fq = min(remaining, avail, pos + limit)
                if fq <= 0:
                    break
                cash += bid_p * fq
                pos -= fq
                remaining -= fq
                fills += fq
                bids[bid_p] -= fq

    return pos, cash, fills


# ====================================================================
# BACKTEST ENGINE
# ====================================================================
def run_backtest(trader, verbose=True):
    tick_data, sorted_ticks = load_and_cache()
    products = list(trader.LIMITS.keys())

    positions = {p: 0 for p in products}
    cash = 0.0
    trader_data = ""
    total_trades = 0

    current_day = None
    day_trades = 0
    day_results = []

    def liquidate_at_mid(tick_key):
        """Force-sell all positions at mid price (end-of-day settlement)."""
        nonlocal cash, total_trades, day_trades
        for p in products:
            if positions[p] != 0 and p in tick_data[tick_key]:
                mid = tick_data[tick_key][p].get('mid_price', 0)
                if mid and not np.isnan(mid) and mid > 0:
                    # Sell longs / buy back shorts at mid price
                    cash += positions[p] * mid
                    total_trades += abs(positions[p])
                    day_trades += abs(positions[p])
                    positions[p] = 0

    for tick_idx, (day, ts_val) in enumerate(sorted_ticks):
        if day != current_day:
            if current_day is not None:
                # END OF DAY: Liquidate everything at last tick's mid price
                last_key = sorted_ticks[tick_idx - 1]
                liquidate_at_mid(last_key)
                if verbose:
                    day_results.append({'day': current_day, 'trades': day_trades, 'pnl': cash})
                    print(f"  Day {current_day}: {day_trades} trades | PnL: {cash:>14,.2f} (liquidated)")
            current_day = day
            day_trades = 0

        prod_data = tick_data[(day, ts_val)]

        order_depths = {}
        for p in products:
            if p in prod_data:
                order_depths[p] = build_od(prod_data[p])

        if not order_depths:
            continue

        state = TradingState(
            traderData=trader_data, timestamp=int(ts_val),
            listings={p: Listing(p, p, "XIRECS") for p in products},
            order_depths=order_depths, own_trades={}, market_trades={},
            position=dict(positions), observations=None
        )

        try:
            result, _, trader_data = trader.run(state)
        except Exception as e:
            continue

        for p in products:
            if p not in result or p not in prod_data:
                continue
            if not result[p]:
                continue
            new_pos, cash_d, f = match_orders(result[p], prod_data[p], positions[p], trader.LIMITS[p], p)
            positions[p] = new_pos
            cash += cash_d
            day_trades += f
            total_trades += f

    # Final day: liquidate everything
    last_key = sorted_ticks[-1]
    liquidate_at_mid(last_key)

    total_pnl = cash  # All positions are now flat

    if verbose:
        day_results.append({'day': current_day, 'trades': day_trades, 'pnl': cash})
        print(f"  Day {current_day}: {day_trades} trades | PnL: {cash:>14,.2f} (liquidated)")
        print(f"\n  FINAL: Cash={cash:,.2f} | Positions: {positions} (all flat)")
        print(f"  Total PnL: {total_pnl:,.2f} | Total Trades: {total_trades}")

    return total_pnl


# ====================================================================
# GRID SEARCH OPTIMIZER
# ====================================================================
def optimize():
    print("=" * 60)
    print("  HYPERPARAMETER GRID SEARCH")
    print("=" * 60)

    # Pre-load data
    load_and_cache()

    # Define search grid
    param_grid = {
        'PEPPER_MAX_LEVELS':    [1, 2, 3],
        'PEPPER_PASSIVE_OFFSET': [0, 1, 2, 3],
        'OSMIUM_SPREAD':         [1, 2, 3, 4],
        'OSMIUM_AGGR_THRESH':    [0, 1, 2, 3],
        'OSMIUM_SKEW_FACTOR':    [2, 4, 6],
    }

    keys = list(param_grid.keys())
    combos = list(itertools.product(*[param_grid[k] for k in keys]))
    print(f"  Testing {len(combos)} hyperparameter combinations...\n")

    best_pnl = -float('inf')
    best_params = {}
    results = []

    for i, combo in enumerate(combos):
        params = dict(zip(keys, combo))

        trader = Trader()
        for k, v in params.items():
            setattr(trader, k, v)

        pnl = run_backtest(trader, verbose=False)
        results.append((pnl, params))

        if pnl > best_pnl:
            best_pnl = pnl
            best_params = params.copy()

        if (i + 1) % 50 == 0 or i == len(combos) - 1:
            print(f"  [{i+1}/{len(combos)}] Current best PnL: {best_pnl:>14,.2f}")

    # Sort and show top 10
    results.sort(key=lambda x: x[0], reverse=True)

    print("\n" + "=" * 60)
    print("  TOP 10 HYPERPARAMETER COMBINATIONS")
    print("=" * 60)
    for rank, (pnl, params) in enumerate(results[:10], 1):
        print(f"\n  #{rank} — PnL: {pnl:>14,.2f}")
        for k, v in params.items():
            print(f"    {k}: {v}")

    print("\n" + "=" * 60)
    print(f"  BEST PnL: {best_pnl:>14,.2f}")
    print(f"  BEST PARAMS: {best_params}")
    print("=" * 60)

    return best_params, best_pnl


# ====================================================================
# MAIN
# ====================================================================
if __name__ == "__main__":
    if "--optimize" in sys.argv:
        best_params, best_pnl = optimize()

        # Run the winner one more time with verbose output
        print("\n\n  Running best configuration with full output...\n")
        trader = Trader()
        for k, v in best_params.items():
            setattr(trader, k, v)
        run_backtest(trader, verbose=True)
    else:
        print("=" * 60)
        print("  BACKTESTER — Single Run")
        print("=" * 60)
        trader = Trader()
        pnl = run_backtest(trader, verbose=True)
