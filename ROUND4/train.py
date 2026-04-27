import pandas as pd
import json
import math
from Trader_informed import Trader
from datamodel import OrderDepth, TradingState, Trade
import itertools
import random

def load_data():
    print("Loading data...")
    days = [1, 2, 3]
    prices_list = []
    trades_list = []

    for d in days:
        try:
            p = pd.read_csv(f'R4Data/prices_round_4_day_{d}.csv', sep=';')
            p['day'] = d
            prices_list.append(p)
            
            t = pd.read_csv(f'R4Data/trades_round_4_day_{d}.csv', sep=';')
            t['day'] = d
            trades_list.append(t)
        except Exception as e:
            print(f"Error loading day {d}: {e}")

    df_prices = pd.concat(prices_list)
    df_trades = pd.concat(trades_list)

    df_prices['global_timestamp'] = (df_prices['day'] - 1) * 1000000 + df_prices['timestamp']
    df_trades['global_timestamp'] = (df_trades['day'] - 1) * 1000000 + df_trades['timestamp']

    print("Grouping data...")
    prices_by_ts = df_prices.groupby('global_timestamp')
    trades_by_ts = df_trades.groupby('global_timestamp')
    unique_timestamps = sorted(df_prices['global_timestamp'].unique())
    
    return prices_by_ts, trades_by_ts, unique_timestamps

def evaluate_params(params, prices_by_ts, trades_by_ts, unique_timestamps):
    trader = Trader(params=params)
    
    position = {}
    cash = {}
    trader_data = ""
    
    for ts in unique_timestamps:
        if ts not in prices_by_ts.groups:
            continue
            
        p_df = prices_by_ts.get_group(ts)
        
        order_depths = {}
        for _, row in p_df.iterrows():
            product = row['product']
            buy_orders = {}
            sell_orders = {}
            if pd.notna(row['bid_price_1']): buy_orders[int(row['bid_price_1'])] = int(row['bid_volume_1'])
            if pd.notna(row['bid_price_2']): buy_orders[int(row['bid_price_2'])] = int(row['bid_volume_2'])
            if pd.notna(row['bid_price_3']): buy_orders[int(row['bid_price_3'])] = int(row['bid_volume_3'])
            if pd.notna(row['ask_price_1']): sell_orders[int(row['ask_price_1'])] = -int(row['ask_volume_1'])
            if pd.notna(row['ask_price_2']): sell_orders[int(row['ask_price_2'])] = -int(row['ask_volume_2'])
            if pd.notna(row['ask_price_3']): sell_orders[int(row['ask_price_3'])] = -int(row['ask_volume_3'])
            order_depths[product] = OrderDepth(buy_orders=buy_orders, sell_orders=sell_orders)
            
        market_trades = {}
        if ts in trades_by_ts.groups:
            t_df = trades_by_ts.get_group(ts)
            for _, row in t_df.iterrows():
                product = row['symbol']
                if product not in market_trades:
                    market_trades[product] = []
                market_trades[product].append(Trade(
                    symbol=product,
                    price=row['price'],
                    quantity=row['quantity'],
                    buyer=row.get('buyer', ''),
                    seller=row.get('seller', ''),
                    timestamp=row['timestamp']
                ))
                
        state = TradingState(
            traderData=trader_data,
            timestamp=ts,
            listings={},
            order_depths=order_depths,
            own_trades={},
            market_trades=market_trades,
            position=position.copy(),
            observations={}
        )
        
        orders, conversions, trader_data = trader.run(state)
        
        # Simple backtesting engine - conservative fills
        for product, product_orders in orders.items():
            if product not in position:
                position[product] = 0
                cash[product] = 0
                
            depth = order_depths.get(product)
            if not depth: continue
            
            market_ask = min(depth.sell_orders.keys()) if depth.sell_orders else float('inf')
            market_bid = max(depth.buy_orders.keys()) if depth.buy_orders else 0
            
            for o in product_orders:
                if o.quantity > 0: # BUY
                    # Fill if we crossed the spread
                    if o.price >= market_ask: 
                        fill_qty = min(o.quantity, abs(depth.sell_orders[market_ask]))
                        position[product] += fill_qty
                        cash[product] -= fill_qty * market_ask
                elif o.quantity < 0: # SELL
                    # Fill if we crossed the spread
                    if o.price <= market_bid: 
                        fill_qty = min(abs(o.quantity), depth.buy_orders[market_bid])
                        position[product] -= fill_qty
                        cash[product] += fill_qty * market_bid
                        
    # Mark to market at the end to calculate PnL
    total_pnl = 0
    last_ts = unique_timestamps[-1]
    p_df = prices_by_ts.get_group(last_ts)
    for product in position:
        prod_row = p_df[p_df['product'] == product]
        if not prod_row.empty:
            mid = prod_row.iloc[0]['mid_price']
            total_pnl += cash[product] + position[product] * mid
            
    return total_pnl

def train():
    prices_by_ts, trades_by_ts, unique_timestamps = load_data()
    
    best_pnl = -float('inf')
    best_params = None
    
    print("\nStarting Parameter Search...")
    for i in range(15):
        params = {
            'decay_factor': round(random.uniform(0.6, 0.95), 3),
            'toxicity_multiplier': round(random.uniform(0.01, 0.1), 3),
            'skew_multiplier': round(random.uniform(1.0, 10.0), 2),
            'skew_power': round(random.uniform(1.5, 4.0), 2),
            'scratch_threshold': round(random.uniform(0.6, 0.9), 2),
            'option_transaction_costs': round(random.uniform(0.0, 1.5), 2),
            'annualized_vol': round(random.uniform(1.5, 3.5), 2)
        }
        
        pnl = evaluate_params(params, prices_by_ts, trades_by_ts, unique_timestamps)
        print(f"Iteration {i+1} | PnL: {pnl:,.2f} | Params: {params}")
        
        if pnl > best_pnl:
            best_pnl = pnl
            best_params = params
            
    print(f"\n--- Training Complete ---")
    print(f"Best PnL: {best_pnl:,.2f}")
    print(f"Best Params: {json.dumps(best_params, indent=4)}")
    
    with open('best_params.json', 'w') as f:
        json.dump(best_params, f, indent=4)
    print("Saved best parameters to best_params.json")

if __name__ == "__main__":
    train()