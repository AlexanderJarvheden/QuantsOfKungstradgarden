import pandas as pd

df1 = pd.read_csv('R4Data/prices_round_4_day_1.csv', sep=';')
df_v = df1[df1['product'].str.startswith('VEV_')].copy()
df_f = df1[df1['product'] == 'VELVETFRUIT_EXTRACT'].copy()

df_v = df_v.set_index(['timestamp', 'product'])
df_f = df_f.set_index('timestamp')

arb_count = 0
total_profit = 0

for (ts, prod), row in df_v.iterrows():
    if ts in df_f.index:
        # We can buy the option at ask, sell the underlying at bid
        fruit_bid = df_f.loc[ts, 'bid_price_1']
        fruit_ask = df_f.loc[ts, 'ask_price_1']
        strike = int(prod.split('_')[1])
        
        # Risk free arb:
        # Buy option at ask
        # Short underlying at bid
        # Payoff at expiry: max(S - K, 0). But wait, does it settle at expiry or can we hold it?
        # The prompt for round 4 says "trade the products". Options are probably cash settled at expiry.
        # Wait, if we exercise immediately? They are European options, probably.
        
        intrinsic_sell = fruit_bid - strike # intrinsic if we short fruit at bid
        option_ask = row['ask_price_1']
        
        if pd.notna(option_ask) and pd.notna(fruit_bid):
            if option_ask < intrinsic_sell:
                # We can buy option, short fruit for guaranteed profit
                profit = intrinsic_sell - option_ask
                arb_count += 1
                total_profit += profit

print(f"Arbitrage opportunities (ask < intrinsic_bid): {arb_count}")
print(f"Total theoretical profit per unit: {total_profit}")
