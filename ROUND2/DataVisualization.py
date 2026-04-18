import pandas as pd
import matplotlib.pyplot as plt
import glob
import os

def visualize_product(product_name, prices_df, trades_df, output_filename):
    # Filter data for the specific product
    p_df = prices_df[prices_df['product'] == product_name].copy()
    t_df = trades_df[trades_df['symbol'] == product_name].copy()
    
    if p_df.empty:
        print(f"No price data for {product_name}")
        return

    # Sort by day and timestamp
    p_df.sort_values(by=['day', 'timestamp'], inplace=True)
    # Create a continuous time index for plotting across days
    # Assuming each day has timestamps from 0 to roughly 1,000,000
    p_df['continuous_time'] = p_df['day'] * 1000000 + p_df['timestamp']
    
    if not t_df.empty:
        # We need day for trades to align them, let's assume we pass single day data
        # Or we can just plot single day for simplicity
        pass

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), gridspec_kw={'height_ratios': [3, 1]})
    
    # --- Top Plot: Prices and Trades ---
    ax1.set_title(f'{product_name} - Prices and Trades', fontsize=16)
    
    # Plot Mid Price
    ax1.plot(p_df['timestamp'], p_df['mid_price'], label='Mid Price', color='blue', alpha=0.7)
    
    # Plot Bid and Ask 1
    ax1.plot(p_df['timestamp'], p_df['bid_price_1'], label='Bid Price 1', color='green', alpha=0.3)
    ax1.plot(p_df['timestamp'], p_df['ask_price_1'], label='Ask Price 1', color='red', alpha=0.3)
    
    # Plot Trades
    if not t_df.empty:
        ax1.scatter(t_df['timestamp'], t_df['price'], color='black', marker='x', label='Trades', zorder=5)

    ax1.set_ylabel('Price')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # --- Bottom Plot: Volume Depth ---
    ax2.set_title('Top of Book Volume (Depth)', fontsize=14)
    ax2.bar(p_df['timestamp'], p_df['bid_volume_1'], color='green', alpha=0.5, label='Bid Vol 1', width=80)
    ax2.bar(p_df['timestamp'], -p_df['ask_volume_1'], color='red', alpha=0.5, label='Ask Vol 1', width=80)
    ax2.set_ylabel('Volume')
    ax2.set_xlabel('Timestamp')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_filename)
    print(f"Saved visualization to {output_filename}")
    plt.close()

if __name__ == "__main__":
    # Example: Visualizing Day 1
    day = 1
    prices_file = f"HistoricData/prices_round_2_day_{day}.csv"
    trades_file = f"HistoricData/trades_round_2_day_{day}.csv"
    
    print(f"Loading data from {prices_file} and {trades_file}...")
    prices_df = pd.read_csv(prices_file, sep=';')
    trades_df = pd.read_csv(trades_file, sep=';')
    
    products = prices_df['product'].unique()
    for product in products:
        output_name = f"plot_{product}_day_{day}.png"
        visualize_product(product, prices_df, trades_df, output_name)
