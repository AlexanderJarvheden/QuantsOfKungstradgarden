import pandas as pd

df1 = pd.read_csv('R4Data/prices_round_4_day_1.csv', sep=';')
df_v = df1[df1['product'].str.startswith('VEV_')].copy()

# Pivot so that columns are products and rows are timestamps
pivoted = df_v.pivot(index='timestamp', columns='product', values='mid_price')
strikes = sorted([int(c.split('_')[1]) for c in pivoted.columns])
sorted_cols = [f'VEV_{s}' for s in strikes]
pivoted = pivoted[sorted_cols]

# Check if C(K1) < C(K2) for K1 < K2 (this would be an arbitrage opportunity since lower strike should be more expensive)
for i in range(len(sorted_cols) - 1):
    c1 = sorted_cols[i]
    c2 = sorted_cols[i+1]
    arb = pivoted[c1] < pivoted[c2]
    if arb.any():
        print(f"Arbitrage! {c1} is cheaper than {c2} at {arb.sum()} timestamps.")

# Check for butterfly spread arbitrage
# C(K1) + C(K3) >= 2*C(K2) if K1, K2, K3 are equally spaced
for i in range(len(sorted_cols) - 2):
    c1 = sorted_cols[i]
    c2 = sorted_cols[i+1]
    c3 = sorted_cols[i+2]
    arb = (pivoted[c1] + pivoted[c3]) < 2 * pivoted[c2]
    if arb.any():
        print(f"Butterfly Arbitrage! {c1} + {c3} < 2*{c2} at {arb.sum()} timestamps.")

