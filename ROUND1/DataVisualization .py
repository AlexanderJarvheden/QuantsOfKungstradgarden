import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_visualizations():
    data_dir = "Datasets/ROUND1"
    
    # Check if directory exists
    if not os.path.exists(data_dir):
        print(f"Data directory {data_dir} not found.")
        return

    days = ["-2", "-1", "0"]
    products = ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]

    for day in days:
        filename = f"prices_round_1_day_{day}.csv"
        filepath = os.path.join(data_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"File {filepath} not found.")
            continue
            
        print(f"Processing {filepath}...")
        
        # Read the csv file
        df = pd.read_csv(filepath, sep=";")
        
        # Create a figure with 4 subplots (two for each product: price and spread)
        fig, axes = plt.subplots(4, 1, figsize=(12, 16), sharex=True)
        fig.suptitle(f"Bid/Ask Prices and Spread for Day {day}", fontsize=16)
        
        for i, product in enumerate(products):
            # Filter data for the specific product
            product_data = df[df["product"] == product].copy()
            product_data.sort_values("timestamp", inplace=True)
            
            # Calculate spread
            product_data["spread"] = product_data["ask_price_1"] - product_data["bid_price_1"]
            
            ax_price = axes[i * 2]
            ax_spread = axes[i * 2 + 1]
            
            # Plot bid and ask prices
            ax_price.plot(product_data["timestamp"], product_data["bid_price_1"], label="Bid Price", color="green", linewidth=1.5)
            ax_price.plot(product_data["timestamp"], product_data["ask_price_1"], label="Ask Price", color="red", linewidth=1.5)
            ax_price.set_title(f"Product: {product} - Prices")
            ax_price.set_ylabel("Price")
            ax_price.legend()
            ax_price.grid(True, alpha=0.3)
            
            # Plot spread
            ax_spread.plot(product_data["timestamp"], product_data["spread"], label="Spread", color="blue", linewidth=1.5)
            ax_spread.set_title(f"Product: {product} - Spread")
            ax_spread.set_ylabel("Spread")
            ax_spread.legend()
            ax_spread.grid(True, alpha=0.3)
            
        # Set x-axis label on the bottom subplot
        axes[-1].set_xlabel("Timestamp")
        
        plt.tight_layout()
        
        # Save the figure
        out_filename = f"visualization_day_{day}.png"
        plt.savefig(out_filename)
        print(f"Saved {out_filename}")
        plt.close()

if __name__ == "__main__":
    generate_visualizations()
