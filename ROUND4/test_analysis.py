import pandas as pd
import numpy as np

# Load data
df_p1 = pd.read_csv('R4Data/prices_round_4_day_1.csv', sep=';')
df_p2 = pd.read_csv('R4Data/prices_round_4_day_2.csv', sep=';')
df_p3 = pd.read_csv('R4Data/prices_round_4_day_3.csv', sep=';')

df = pd.concat([df_p1, df_p2, df_p3])

# Calculate intrinsic value of VEV_4500
vev_4500 = df[df['product'] == 'VEV_4500'].set_index(['day', 'timestamp'])
velvet = df[df['product'] == 'VELVETFRUIT_EXTRACT'].set_index(['day', 'timestamp'])

common = vev_4500.index.intersection(velvet.index)

vev_4500 = vev_4500.loc[common]
velvet = velvet.loc[common]

intrinsic = np.maximum(velvet['mid_price'] - 4500, 0)
diff = intrinsic - vev_4500['mid_price']

print("Max intrinsic vs market gap (Intrinsic - Market):", diff.max())
print("Min intrinsic vs market gap (Intrinsic - Market):", diff.min())
print("Average gap:", diff.mean())

