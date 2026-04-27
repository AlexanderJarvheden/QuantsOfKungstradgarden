import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import glob
import numpy as np
from scipy.stats import norm

def load_data():
    trade_files = glob.glob('R4Data/trades_round_4_day_*.csv')
    price_files = glob.glob('R4Data/prices_round_4_day_*.csv')
    
    if not trade_files:
        trade_files = glob.glob('../R4Data/trades_round_4_day_*.csv')
        price_files = glob.glob('../R4Data/prices_round_4_day_*.csv')

    if not trade_files:
        raise FileNotFoundError("Could not find data files in R4Data/ or ../R4Data/")
    
    trades_list = []
    for f in trade_files:
        df = pd.read_csv(f, sep=';')
        try:
            day_str = f.split('_day_')[1].split('.')[0]
            day = int(day_str)
        except (IndexError, ValueError):
            day = 0
        df['day'] = day
        trades_list.append(df)
    
    trades_df = pd.concat(trades_list, ignore_index=True)
    prices_df = pd.concat((pd.read_csv(f, sep=';') for f in price_files), ignore_index=True)
    
    trades_df['global_timestamp'] = (trades_df['day'] - 1) * 1000000 + trades_df['timestamp']
    prices_df['global_timestamp'] = (prices_df['day'] - 1) * 1000000 + prices_df['timestamp']
    
    trades_df.sort_values(by=['global_timestamp'], inplace=True)
    prices_df.sort_values(by=['global_timestamp'], inplace=True)
    
    return trades_df, prices_df

def black_scholes_iv(S, K, T, r, C_market):
    low, high = 0.0001, 5.0
    for _ in range(50):
        sigma = (low + high) / 2
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        C_calc = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        
        if C_calc < C_market:
            low = sigma
        else:
            high = sigma
    return (low + high) / 2

def get_arbitrage_view_fig(prices_df):
    velvet = prices_df[prices_df['product'] == 'VELVETFRUIT_EXTRACT'].set_index(['day', 'timestamp'])
    
    products = prices_df['product'].unique()
    vev_products = [p for p in products if p.startswith('VEV_')]
    
    fig = make_subplots(rows=2, cols=1, subplot_titles=('Underlying Price vs Voucher Intrinsic Value', 'Implied Volatility Surface'))
    
    fig.add_trace(go.Scatter(
        x=velvet.index.get_level_values('timestamp'), 
        y=velvet['mid_price'], 
        mode='lines',
        name='VELVETFRUIT_EXTRACT',
        line=dict(color='black')
    ), row=1, col=1)
    
    if len(vev_products) > 0:
        sample_vev = vev_products[len(vev_products)//2]
        strike = int(sample_vev.split('_')[1])
        vev_data = prices_df[prices_df['product'] == sample_vev].set_index(['day', 'timestamp'])
        
        common_idx = velvet.index.intersection(vev_data.index)
        S = velvet.loc[common_idx, 'mid_price']
        intrinsic_value = np.maximum(S - strike, 0)
        
        fig.add_trace(go.Scatter(
            x=common_idx.get_level_values('timestamp'), 
            y=intrinsic_value, 
            mode='lines',
            name=f'{sample_vev} Intrinsic Value',
            line=dict(dash='dash')
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=common_idx.get_level_values('timestamp'), 
            y=vev_data.loc[common_idx, 'mid_price'], 
            mode='lines',
            name=f'{sample_vev} Market Price',
            opacity=0.7
        ), row=1, col=1)
        
    T = 252 
    r = 0.0 
    last_day = prices_df['day'].max()
    last_timestamp = prices_df[prices_df['day'] == last_day]['timestamp'].max()
    
    strikes = []
    ivs = []
    
    for vev in vev_products:
        strike = int(vev.split('_')[1])
        vev_row = prices_df[(prices_df['product'] == vev) & (prices_df['day'] == last_day) & (prices_df['timestamp'] == last_timestamp)]
        velvet_row = prices_df[(prices_df['product'] == 'VELVETFRUIT_EXTRACT') & (prices_df['day'] == last_day) & (prices_df['timestamp'] == last_timestamp)]
        
        if not vev_row.empty and not velvet_row.empty:
            S = velvet_row.iloc[0]['mid_price']
            C_market = vev_row.iloc[0]['mid_price']
            iv = black_scholes_iv(S, strike, 1.0, r, C_market)
            strikes.append(strike)
            ivs.append(iv)
            
    if strikes:
        sorted_indices = np.argsort(strikes)
        strikes = np.array(strikes)[sorted_indices]
        ivs = np.array(ivs)[sorted_indices]
        
        fig.add_trace(go.Scatter(
            x=strikes, 
            y=ivs, 
            mode='lines+markers',
            name=f'IV at Day {last_day}, TS {last_timestamp}',
            line=dict(color='purple')
        ), row=2, col=1)
        
        fig.update_xaxes(title_text="Strike", row=2, col=1)
        fig.update_yaxes(title_text="Implied Volatility", row=2, col=1)

    fig.update_layout(height=800, hovermode='x unified', dragmode='pan')
    return fig

def get_trader_alpha_profile_fig(trades_df, prices_df, trader_id, target_asset='VELVETFRUIT_EXTRACT'):
    asset_prices = prices_df[prices_df['product'] == target_asset]
    trader_buys = trades_df[(trades_df['buyer'] == trader_id) & (trades_df['symbol'] == target_asset)]
    trader_sells = trades_df[(trades_df['seller'] == trader_id) & (trades_df['symbol'] == target_asset)]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=asset_prices['global_timestamp'], 
        y=asset_prices['mid_price'],
        mode='lines',
        name=f'{target_asset} Price',
        line=dict(color='blue'),
        opacity=0.5
    ))
    
    fig.add_trace(go.Scatter(
        x=trader_buys['global_timestamp'], 
        y=trader_buys['price'],
        mode='markers',
        name='Buy',
        marker=dict(color='green', symbol='triangle-up', size=12),
    ))
    
    fig.add_trace(go.Scatter(
        x=trader_sells['global_timestamp'], 
        y=trader_sells['price'],
        mode='markers',
        name='Sell',
        marker=dict(color='red', symbol='triangle-down', size=12),
    ))
    
    fig.update_layout(
        title=f'Alpha Profile for Counterparty: {trader_id} on {target_asset}',
        xaxis_title='Global Timestamp',
        yaxis_title='Price',
        hovermode='x unified',
        dragmode='pan'
    )
    return fig

def get_inventory_and_pnl_fig(trades_df, prices_df, trader_id, target_asset='VELVETFRUIT_EXTRACT'):
    asset_prices = prices_df[prices_df['product'] == target_asset].copy()
    trader_buys = trades_df[(trades_df['buyer'] == trader_id) & (trades_df['symbol'] == target_asset)].copy()
    trader_sells = trades_df[(trades_df['seller'] == trader_id) & (trades_df['symbol'] == target_asset)].copy()
    
    trader_buys['trade_quantity'] = trader_buys['quantity']
    trader_sells['trade_quantity'] = -trader_sells['quantity']
    
    trader_trades = pd.concat([trader_buys, trader_sells]).sort_values('global_timestamp')
    
    if trader_trades.empty:
        return None

    trader_trades['position'] = trader_trades['trade_quantity'].cumsum()
    trader_trades['cash_flow'] = -(trader_trades['trade_quantity'] * trader_trades['price'])
    trader_trades['cumulative_cash'] = trader_trades['cash_flow'].cumsum()
    
    asset_prices = asset_prices.sort_values('global_timestamp')
    trader_trades = pd.merge_asof(trader_trades, asset_prices[['global_timestamp', 'mid_price']], on='global_timestamp')
    trader_trades['pnl'] = trader_trades['cumulative_cash'] + (trader_trades['position'] * trader_trades['mid_price'])
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Scatter(
            x=trader_trades['global_timestamp'], 
            y=trader_trades['position'],
            name='Net Position',
            line=dict(color='blue'),
            fill='tozeroy'
        ),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Scatter(
            x=trader_trades['global_timestamp'],
            y=trader_trades['pnl'],
            name='Cumulative PnL',
            line=dict(color='green', dash='dash')
        ),
        secondary_y=True,
    )
    
    fig.update_layout(
        title_text=f'Inventory and Position Risk for {trader_id} on {target_asset}',
        hovermode='x unified',
        dragmode='pan'
    )
    
    fig.update_xaxes(title_text='Global Timestamp')
    fig.update_yaxes(title_text='Net Position', color='blue', secondary_y=False)
    fig.update_yaxes(title_text='Cumulative PnL', color='green', secondary_y=True)
    return fig

if __name__ == "__main__":
    print("Loading data...")
    try:
        trades, prices = load_data()
        print("Data loaded. Total trades:", len(trades))
        
        figs = []
        
        # Arbitrage view
        print("Generating Arbitrage View...")
        fig_arb = get_arbitrage_view_fig(prices)
        if fig_arb:
            figs.append(fig_arb)
            
        velvet_trades = trades[trades['symbol'] == 'VELVETFRUIT_EXTRACT']
        sample_traders = velvet_trades['buyer'].dropna().unique()
        
        if len(sample_traders) > 0:
            target_trader = sample_traders[0]
            print(f"Generating visualizations for sample trader: {target_trader}")
            
            # Alpha profile
            fig_alpha = get_trader_alpha_profile_fig(trades, prices, target_trader)
            if fig_alpha:
                figs.append(fig_alpha)
                
            # Inventory risk
            fig_inv = get_inventory_and_pnl_fig(trades, prices, target_trader)
            if fig_inv:
                figs.append(fig_inv)
        else:
            print("No traders found for VELVETFRUIT_EXTRACT.")
            
        # Combine into one HTML file
        out_dir = 'out'
        if os.path.basename(os.getcwd()) != 'visualizations':
            out_dir = os.path.join('visualizations', 'out')
            
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, 'combined_views.html')
        
        print(f"Saving all plots to {out_file}...")
        html_content = "<html><head><title>Combined Visualizations</title></head><body>"
        
        for i, fig in enumerate(figs):
            include_js = 'cdn' if i == 0 else False
            html_content += fig.to_html(full_html=False, include_plotlyjs=include_js)
            
        html_content += "</body></html>"
        
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"Successfully saved combined interactive plot to {out_file}")
            
    except Exception as e:
        print(f"Error: {e}")
