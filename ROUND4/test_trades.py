import pandas as pd

df = pd.read_csv('R4Data/trades_round_4_day_1.csv', sep=';')
print("Unique buyers:", df['buyer'].dropna().unique())
print("Unique sellers:", df['seller'].dropna().unique())

# Analyze PnL of different traders for VELVETFRUIT_EXTRACT
velvet = df[df['symbol'] == 'VELVETFRUIT_EXTRACT']

buyers = velvet.groupby('buyer')['quantity'].sum()
sellers = velvet.groupby('seller')['quantity'].sum()
print("Velvet Buyers volume:\n", buyers)
print("Velvet Sellers volume:\n", sellers)
