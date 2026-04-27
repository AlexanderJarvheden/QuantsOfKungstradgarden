import pandas as pd
import numpy as np

df1 = pd.read_csv('R4Data/trades_round_4_day_1.csv', sep=';')
df2 = pd.read_csv('R4Data/trades_round_4_day_2.csv', sep=';')
df3 = pd.read_csv('R4Data/trades_round_4_day_3.csv', sep=';')

trades_list = []
for i, df in enumerate([df1, df2, df3]):
    df['day'] = i + 1
    trades_list.append(df)
df_trades = pd.concat(trades_list)
df_trades['global_timestamp'] = (df_trades['day'] - 1) * 1000000 + df_trades['timestamp']

p1 = pd.read_csv('R4Data/prices_round_4_day_1.csv', sep=';')
p2 = pd.read_csv('R4Data/prices_round_4_day_2.csv', sep=';')
p3 = pd.read_csv('R4Data/prices_round_4_day_3.csv', sep=';')

prices_list = []
for i, df in enumerate([p1, p2, p3]):
    df['day'] = i + 1
    prices_list.append(df)
df_prices = pd.concat(prices_list)
df_prices['global_timestamp'] = (df_prices['day'] - 1) * 1000000 + df_prices['timestamp']

# Look at HYDROGEL_PACK
for product in ['HYDROGEL_PACK', 'VELVETFRUIT_EXTRACT']:
    print(f"\n--- {product} ---")
    prod_trades = df_trades[df_trades['symbol'] == product]
    prod_prices = df_prices[df_prices['product'] == product].set_index('global_timestamp')
    
    traders = set(prod_trades['buyer'].dropna().unique()).union(set(prod_trades['seller'].dropna().unique()))
    
    for trader in traders:
        if trader == 'Mark 55': continue # That's me
        
        # Calculate PnL for this trader based on their trades
        trader_buys = prod_trades[prod_trades['buyer'] == trader].copy()
        trader_sells = prod_trades[prod_trades['seller'] == trader].copy()
        
        trader_buys['qty'] = trader_buys['quantity']
        trader_sells['qty'] = -trader_sells['quantity']
        
        trader_all = pd.concat([trader_buys, trader_sells]).sort_values('global_timestamp')
        
        if len(trader_all) == 0: continue
        
        trader_all['cash'] = -trader_all['qty'] * trader_all['price']
        
        # Merge with prices to get mark-to-market PnL over time
        pos = 0
        cash = 0
        pnl_diffs = []
        
        # Just check the price change 5 timestamps later
        future_prices = []
        for _, row in trader_all.iterrows():
            ts = row['global_timestamp']
            qty = row['qty']
            
            # Find price 5 timestamps later (500ms)
            future_ts = ts + 500
            
            # Try to get price
            idx = prod_prices.index.searchsorted(future_ts)
            if idx < len(prod_prices):
                future_price = prod_prices.iloc[idx]['mid_price']
                trade_price = row['price']
                
                # If bought, profit is future - trade
                # If sold, profit is trade - future
                profit = (future_price - trade_price) if qty > 0 else (trade_price - future_price)
                pnl_diffs.append(profit)
                
        if pnl_diffs:
            avg_edge = np.mean(pnl_diffs)
            print(f"{trader}: trades={len(trader_all)}, avg edge 5 steps later={avg_edge:.2f}")

