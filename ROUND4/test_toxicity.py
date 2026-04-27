import pandas as pd

df1 = pd.read_csv('R4Data/trades_round_4_day_1.csv', sep=';')
df2 = pd.read_csv('R4Data/trades_round_4_day_2.csv', sep=';')
df3 = pd.read_csv('R4Data/trades_round_4_day_3.csv', sep=';')
df_trades = pd.concat([df1, df2, df3])

p1 = pd.read_csv('R4Data/prices_round_4_day_1.csv', sep=';')
p2 = pd.read_csv('R4Data/prices_round_4_day_2.csv', sep=';')
p3 = pd.read_csv('R4Data/prices_round_4_day_3.csv', sep=';')
df_prices = pd.concat([p1, p2, p3])

velvet_trades = df_trades[df_trades['symbol'] == 'VELVETFRUIT_EXTRACT'].copy()
velvet_prices = df_prices[df_prices['product'] == 'VELVETFRUIT_EXTRACT'].copy()

velvet_trades['global_timestamp'] = (velvet_trades['timestamp']) # simplifying since timestamp resets
# Actually let's use the provided logic from combined_visualizations
def add_global_ts(df):
    try:
        # In this dataset, there's no day in trades, but we merged them. We should iterate and add day.
        pass
    except Exception:
        pass

trades_list = []
for i, f in enumerate(['R4Data/trades_round_4_day_1.csv', 'R4Data/trades_round_4_day_2.csv', 'R4Data/trades_round_4_day_3.csv']):
    df = pd.read_csv(f, sep=';')
    df['day'] = i + 1
    trades_list.append(df)
df_trades = pd.concat(trades_list)
df_trades['global_timestamp'] = (df_trades['day'] - 1) * 1000000 + df_trades['timestamp']

prices_list = []
for i, f in enumerate(['R4Data/prices_round_4_day_1.csv', 'R4Data/prices_round_4_day_2.csv', 'R4Data/prices_round_4_day_3.csv']):
    df = pd.read_csv(f, sep=';')
    df['day'] = i + 1
    prices_list.append(df)
df_prices = pd.concat(prices_list)
df_prices['global_timestamp'] = (df_prices['day'] - 1) * 1000000 + df_prices['timestamp']

velvet_trades = df_trades[df_trades['symbol'] == 'VELVETFRUIT_EXTRACT']
velvet_prices = df_prices[df_prices['product'] == 'VELVETFRUIT_EXTRACT']

# Match each trade to price at next timestamp (t+100 or something)
velvet_prices = velvet_prices.sort_values('global_timestamp')

for trader in velvet_trades['buyer'].dropna().unique():
    if trader == 'Mark 55': continue
    
    trader_buys = velvet_trades[velvet_trades['buyer'] == trader]
    # Check if price goes UP after they buy
    # ...
    
    print(f"{trader} bought {len(trader_buys)} times")
    
for trader in velvet_trades['seller'].dropna().unique():
    if trader == 'Mark 55': continue
    trader_sells = velvet_trades[velvet_trades['seller'] == trader]
    print(f"{trader} sold {len(trader_sells)} times")

