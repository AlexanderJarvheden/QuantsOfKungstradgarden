import pandas as pd
import numpy as np

df1 = pd.read_csv('R4Data/trades_round_4_day_1.csv', sep=';')
df_trades = df1

print("Mark 01 buys VEV:")
m01_buys = df_trades[(df_trades['buyer'] == 'Mark 01') & (df_trades['symbol'].str.startswith('VEV'))]
print(m01_buys.groupby('symbol')['quantity'].sum())

print("Mark 22 sells VEV:")
m22_sells = df_trades[(df_trades['seller'] == 'Mark 22') & (df_trades['symbol'].str.startswith('VEV'))]
print(m22_sells.groupby('symbol')['quantity'].sum())
