import json
import math
from datamodel import OrderDepth, TradingState, Order, Trade

class Trader:
    def __init__(self):
        self.limits = {
            'HYDROGEL_PACK': 200,
            'VELVETFRUIT_EXTRACT': 200,
        }
        for i in range(4000, 7100, 100):
            self.limits[f'VEV_{i}'] = 300
            
    def get_intrinsic_value(self, strike: int, underlying_price: float) -> float:
        return max(underlying_price - strike, 0.0)
        
    def run(self, state: TradingState):
        result = {}
        conversions = 0
        
        # 1. Persistent Alpha Engine (Stateful Toxicity)
        decay_factor = 0.8
        toxicity_score = {'HYDROGEL_PACK': 0.0, 'VELVETFRUIT_EXTRACT': 0.0}
        if state.traderData:
            try:
                parts = state.traderData.split('|')
                if len(parts) == 2:
                    toxicity_score['HYDROGEL_PACK'] = float(parts[0])
                    toxicity_score['VELVETFRUIT_EXTRACT'] = float(parts[1])
            except Exception:
                pass
            
        for product in ['HYDROGEL_PACK', 'VELVETFRUIT_EXTRACT']:
                
            old_score = toxicity_score[product]
            new_signal = 0.0
            
            if product in state.market_trades:
                for trade in state.market_trades[product]:
                    if trade.buyer in ['Mark 14', 'Mark 01']:
                        new_signal += trade.quantity
                    elif trade.seller in ['Mark 14', 'Mark 01']:
                        new_signal -= trade.quantity
                        
            updated_score = (old_score * decay_factor) + new_signal
            toxicity_score[product] = updated_score
            
        # Serialize for next tick
        trader_data = f"{toxicity_score['HYDROGEL_PACK']}|{toxicity_score['VELVETFRUIT_EXTRACT']}"
        
        # 2. Total Book Imbalance Microprice
        microprices = {}
        bids = {}
        asks = {}
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            if len(order_depth.buy_orders) > 0 and len(order_depth.sell_orders) > 0:
                best_bid = max(order_depth.buy_orders.keys())
                best_ask = min(order_depth.sell_orders.keys())
                
                total_v_bid = sum(order_depth.buy_orders.values())
                total_v_ask = sum(abs(v) for v in order_depth.sell_orders.values())
                
                if total_v_bid + total_v_ask > 0:
                    microprice = (best_bid * total_v_ask + best_ask * total_v_bid) / (total_v_bid + total_v_ask)
                else:
                    microprice = (best_bid + best_ask) / 2.0
                    
                microprices[product] = microprice
                bids[product] = best_bid
                asks[product] = best_ask
            elif len(order_depth.buy_orders) > 0:
                best_bid = max(order_depth.buy_orders.keys())
                microprices[product] = best_bid
                bids[product] = best_bid
            elif len(order_depth.sell_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                microprices[product] = best_ask
                asks[product] = best_ask
                
        # 3. Delta-Neutral Hedging
        def norm_cdf(x):
            return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

        def bs_delta_call(S, K, T, r, sigma):
            if T <= 0:
                return 1.0 if S > K else 0.0
            if S <= 0 or K <= 0 or sigma <= 0:
                return 1.0 if S > K else 0.0
            d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            return norm_cdf(d1)
            
        net_voucher_position = 0.0
        fruit_price = microprices.get('VELVETFRUIT_EXTRACT', 5245.0)
        annualized_vol = 2.51
        T_days = 2.0 / 252.0
        
        for product, pos in state.position.items():
            if product.startswith('VEV_'):
                try:
                    strike = float(product.split('_')[1])
                    delta = bs_delta_call(fruit_price, strike, T_days, 0.0, annualized_vol)
                    net_voucher_position += pos * delta
                except Exception:
                    net_voucher_position += pos
                
        # Bound the target fruit position to its limits to avoid extreme quoting skews
        fruit_limit = self.limits['VELVETFRUIT_EXTRACT']
        target_fruit_position = max(-fruit_limit, min(fruit_limit, -1.0 * net_voucher_position))
        
        # 4. Convex Inventory Penalty & Market Making
        for product in ['HYDROGEL_PACK', 'VELVETFRUIT_EXTRACT']:
            if product not in state.order_depths or product not in microprices:
                continue
                
            pos = state.position.get(product, 0)
            limit = self.limits[product]
            
            if product == 'VELVETFRUIT_EXTRACT':
                pos_diff = pos - target_fruit_position
            else:
                pos_diff = pos
                
            # Avellaneda-Stoikov parameters
            gamma = 0.1  # Risk aversion
            kappa = 1.5  # Liquidity density
            sigma_sq = (annualized_vol if product == 'VELVETFRUIT_EXTRACT' else 1.0) ** 2
            T_minus_t = 1.0  # Normalized time
            
            # Reservation price
            s = microprices[product]
            r = s - pos_diff * gamma * sigma_sq * T_minus_t
            
            # Optimal spread
            delta = gamma * sigma_sq * T_minus_t + (2 / gamma) * math.log(1 + gamma / kappa)
            
            my_bid = math.floor(r - delta / 2.0)
            my_ask = math.ceil(r + delta / 2.0)
            
            # Non-Linear Toxicity Scaling
            tox = toxicity_score[product]
            tox_threshold = 20.0  # Hard threshold for toxicity
            
            if tox < -tox_threshold:
                # Heavy selling pressure: widen the bid drastically to avoid toxic flow
                my_bid -= 10
            elif tox > tox_threshold:
                # Heavy buying pressure: widen the ask drastically to avoid toxic flow
                my_ask += 10
                
            if my_ask <= my_bid:
                my_ask = my_bid + 1
                
            # "Oh No" button: Aggressive crossing if heavily skewed (> 80%)
            if pos_diff > limit * 0.8:
                my_ask = math.floor(s - 1)  # Cross spread to pay up and exit
            elif pos_diff < -limit * 0.8:
                my_bid = math.ceil(s + 1)   # Cross spread to pay up and exit
                
            buy_volume = limit - pos
            sell_volume = -limit - pos
            
            orders = []
            if buy_volume > 0 and tox >= -tox_threshold: # Stop quoting bid completely if extreme selling
                orders.append(Order(product, my_bid, buy_volume))
            if sell_volume < 0 and tox <= tox_threshold: # Stop quoting ask completely if extreme buying
                orders.append(Order(product, my_ask, sell_volume))
                
            result[product] = orders
            
        # 5. Intrinsic Price Floors (The "Hard Stop")
        if 'VELVETFRUIT_EXTRACT' in bids and 'VELVETFRUIT_EXTRACT' in asks:
            fruit_bid = bids['VELVETFRUIT_EXTRACT']
            fruit_ask = asks['VELVETFRUIT_EXTRACT']
            
            transaction_costs = 0.5
            
            for strike in range(4000, 7100, 100):
                vev_product = f'VEV_{strike}'
                if vev_product not in state.order_depths:
                    continue
                    
                order_depth = state.order_depths[vev_product]
                vev_pos = state.position.get(vev_product, 0)
                vev_limit = self.limits.get(vev_product, 300)
                
                # As per spec: "if buying a voucher, check the fruit's Ask price"
                intrinsic_for_buy = self.get_intrinsic_value(strike, fruit_ask)
                intrinsic_for_sell = self.get_intrinsic_value(strike, fruit_bid)
                
                orders = []
                
                # Arbitrage: Buying undervalued vouchers
                if len(order_depth.sell_orders) > 0:
                    vev_ask = min(order_depth.sell_orders.keys())
                    vev_ask_vol = -order_depth.sell_orders[vev_ask]
                    
                    # Hard Stop: Never send Buy Order where Price > Intrinsic - Transaction_Costs
                    if vev_ask <= intrinsic_for_buy - transaction_costs:
                        vol_to_buy = min(vev_ask_vol, vev_limit - vev_pos)
                        if vol_to_buy > 0:
                            orders.append(Order(vev_product, vev_ask, vol_to_buy))
                            vev_pos += vol_to_buy
                            
                # Volatility Harvesting: Selling overvalued vouchers
                if len(order_depth.buy_orders) > 0:
                    vev_bid = max(order_depth.buy_orders.keys())
                    vev_bid_vol = order_depth.buy_orders[vev_bid]
                    
                    # Hard Stop: Never send Sell Order where Price < Intrinsic + Transaction_Costs
                    if vev_bid >= intrinsic_for_sell + transaction_costs:
                        vol_to_sell = min(vev_bid_vol, vev_limit + vev_pos)
                        if vol_to_sell > 0:
                            orders.append(Order(vev_product, vev_bid, -vol_to_sell))
                            vev_pos -= vol_to_sell
                            
                if orders:
                    result[vev_product] = orders

        return result, conversions, trader_data