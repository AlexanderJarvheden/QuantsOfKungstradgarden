import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

def visualize_all_products(prices_df, output_filename):
    # Sort products so they are always in the same place
    products = sorted(prices_df['product'].unique())
    n_products = len(products)
    
    # Create subplots: 2 rows (Price, Spread) and n_products columns
    fig = make_subplots(
        rows=2, cols=n_products,
        subplot_titles=[f'{p} - Price' for p in products] + [f'{p} - Spread' for p in products],
        vertical_spacing=0.1,
        horizontal_spacing=0.05
    )
    
    for col_idx, product in enumerate(products):
        p_df = prices_df[prices_df['product'] == product].copy()
        
        # Sort by day and timestamp
        p_df.sort_values(by=['day', 'timestamp'], inplace=True)
        
        # Calculate spread
        p_df['spread'] = p_df['ask_price_1'] - p_df['bid_price_1']
        
        col = col_idx + 1
        
        # Price Plot (Top Row)
        fig.add_trace(
            go.Scatter(x=p_df['timestamp'], y=p_df['bid_price_1'], name=f'{product} Bid', line=dict(color='green')),
            row=1, col=col
        )
        fig.add_trace(
            go.Scatter(x=p_df['timestamp'], y=p_df['ask_price_1'], name=f'{product} Ask', line=dict(color='red')),
            row=1, col=col
        )
        
        # Spread Plot (Bottom Row)
        fig.add_trace(
            go.Scatter(x=p_df['timestamp'], y=p_df['spread'], name=f'{product} Spread', line=dict(color='blue')),
            row=2, col=col
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="Time (Timestamp)", row=1, col=col)
        fig.update_yaxes(title_text="Price", row=1, col=col)
        fig.update_xaxes(title_text="Time (Timestamp)", row=2, col=col)
        fig.update_yaxes(title_text="Spread", row=2, col=col)

    fig.update_layout(
        height=800, 
        width=800 * n_products,
        title_text="Product Visualization",
        showlegend=True,
        hovermode="x unified"
    )
    
    fig.write_html(output_filename)
    print(f"Saved interactive visualization to {output_filename}")

if __name__ == "__main__":
    days = [-1, 0, 1]
    for day in days:
        prices_file = f"HistoricData/prices_round_2_day_{day}.csv"
        
        if os.path.exists(prices_file):
            print(f"Loading data from {prices_file}...")
            prices_df = pd.read_csv(prices_file, sep=';')
            
            output_name = f"plot_all_products_day_{day}.html"
            visualize_all_products(prices_df, output_name)
        else:
            print(f"File {prices_file} not found. Skipping...")
