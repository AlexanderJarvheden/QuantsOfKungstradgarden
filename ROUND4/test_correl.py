import pandas as pd
import numpy as np

# Load data
df1 = pd.read_csv('R4Data/prices_round_4_day_1.csv', sep=';')
df2 = pd.read_csv('R4Data/prices_round_4_day_2.csv', sep=';')
df3 = pd.read_csv('R4Data/prices_round_4_day_3.csv', sep=';')

df_prices = pd.concat([df1, df2, df3])

# pivot to get mid prices
pivoted = df_prices.pivot(index=['day', 'timestamp'], columns='product', values='mid_price')

print("Correlation matrix:")
print(pivoted[['HYDROGEL_PACK', 'VELVETFRUIT_EXTRACT']].corr())

# Check for cointegration or spread
pivoted['spread'] = pivoted['VELVETFRUIT_EXTRACT'] - pivoted['HYDROGEL_PACK']
print("\nSpread stats:")
print(pivoted['spread'].describe())

