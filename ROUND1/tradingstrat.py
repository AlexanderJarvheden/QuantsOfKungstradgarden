import pandas as pd
# Round 1:

# Primary focus: turn these products into profit
products = ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]

# value of INTARIAN_PEPPER_ROOT is quite steady, but keep in mind that it’s a hardy, slow-growing root
# ASH_COATED_OSMIUM more volatile, it's unpredictability may follow a hidden pattern

# The product limits `ASH_COATED_OSMIUM`: 80, `INTARIAN_PEPPER_ROOT`: 80
limits = {products[0]: 80, products[1]: 80}

path = "Datasets/ROUND1/prices_round_1_day_"
df = pd.read_csv(path+"-1"+".csv")

df

# Bonus: Exchange Auction during round 1