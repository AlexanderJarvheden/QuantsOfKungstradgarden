import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('R4Data/prices_round_4_day_1.csv', sep=';')

# Analyze VEV_6500
vev_6500 = df[df['product'] == 'VEV_6500'].set_index(['day', 'timestamp'])
velvet = df[df['product'] == 'VELVETFRUIT_EXTRACT'].set_index(['day', 'timestamp'])

common = vev_6500.index.intersection(velvet.index)

print("VEV_6500 mean price:", vev_6500.loc[common, 'mid_price'].mean())
print("Velvet mean price:", velvet.loc[common, 'mid_price'].mean())

