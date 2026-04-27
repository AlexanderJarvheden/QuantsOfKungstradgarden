import pandas as pd

df1 = pd.read_csv('R4Data/trades_round_4_day_1.csv', sep=';')
df2 = pd.read_csv('R4Data/trades_round_4_day_2.csv', sep=';')
df3 = pd.read_csv('R4Data/trades_round_4_day_3.csv', sep=';')
df = pd.concat([df1, df2, df3])

# Counterparties on options
df_options = df[df['symbol'].str.startswith('VEV_')]
print("Options buyers:", df_options['buyer'].dropna().unique())
print("Options sellers:", df_options['seller'].dropna().unique())

print("Options Buyer Volume:\n", df_options.groupby('buyer')['quantity'].sum())
print("Options Seller Volume:\n", df_options.groupby('seller')['quantity'].sum())

