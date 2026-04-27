import json
import math
from datamodel import OrderDepth, TradingState, Order, Trade

class Trader:
    def __init__(self, params=None):
        self.limits = {
            'HYDROGEL_PACK': 200,
            'VELVETFRUIT_EXTRACT': 200,
        }
        for i in range(4000, 7100, 100):
            self.limits[f'VEV_{i}'] = 300
            
        if params is None:
            params = {}
            
        self.decay_factor = params.get('decay_factor', 0.608)
        self.toxicity_multiplier = params.get('toxicity_multiplier', 0.06)
        self.skew_multiplier = params.get('skew_multiplier', 2.38)
        self.skew_power = params.get('skew_power', 3.39)
        self.scratch_threshold = params.get('scratch_threshold', 0.83)
        self.option_transaction_costs = params.get('option_transaction_costs', 1.49)
        self.annualized_vol = params.get('annualized_vol', 2.29)
            
    def get_intrinsic_value(self, strike: int, underlying_price: float) -> float:
        return max(underlying_price - strike, 0.0)
        
    def run(self, state: TradingState):
        result = {}
        conversions = 0
        
        # 1. Persistent Alpha Engine (Stateful Toxicity)
        try:
            toxicity_score = json.loads(state.trader_data) if state.trader_data else {}
        except Exception:
            toxicity_score = {}
            
        for product in ['HYDROGEL_PACK', 'VELVETFRUIT_EXTRACT']:
            if product not in toxicity_score:
                toxicity_score[product] = 0.0
                
            old_score = toxicity_score[product]
            new_signal = 0.0
            
            if product in state.market_trades:
                for trade in state.market_trades[product]:
                    if product == 'HYDROGEL_PACK':
                        if trade.buyer == 'Mark 14':
                            new_signal += trade.quantity * 1.0
                        elif trade.seller == 'Mark 14':
                            new_signal -= trade.quantity * 1.0
                            
                        if trade.buyer == 'Mark 38':
                            new_signal -= trade.quantity * 1.0 # Reverse toxic
                        elif trade.seller == 'Mark 38':
                            new_signal += trade.quantity * 1.0 # Reverse toxic
                            
                    elif product == 'VELVETFRUIT_EXTRACT':
                        if trade.buyer in ['Mark 14', 'Mark 01']:
                            new_signal += trade.quantity * 1.0
                        elif trade.seller in ['Mark 14', 'Mark 01']:
                            new_signal -= trade.quantity * 1.0
                            
                        if trade.buyer == 'Mark 67':
                            new_signal += trade.quantity * 0.5
                        elif trade.seller == 'Mark 67':
                            new_signal -= trade.quantity * 0.5
                            
                        if trade.buyer == 'Mark 49':
                            new_signal -= trade.quantity * 0.5
                        elif trade.seller == 'Mark 49':
                            new_signal += trade.quantity * 0.5
                        
            updated_score = (old_score * self.decay_factor) + new_signal
            toxicity_score[product] = updated_score
            
        # Serialize for next tick
        trader_data = json.dumps(toxicity_score)
        
        # 2. Replace Mid-Price with Microprice
        microprices = {}
        bids = {}
        asks = {}
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            if len(order_depth.buy_orders) > 0 and len(order_depth.sell_orders) > 0:
                best_bid = max(order_depth.buy_orders.keys())
                best_ask = min(order_depth.sell_orders.keys())
                
                v_bid = order_depth.buy_orders[best_bid]
                v_ask = abs(order_depth.sell_orders[best_ask])
                
                if v_bid + v_ask > 0:
                    microprice = (best_bid * v_ask + best_ask * v_bid) / (v_bid + v_ask)
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
        T_days = 2.0 / 252.0
        
        for product, pos in state.position.items():
            if product.startswith('VEV_'):
                try:
                    strike = float(product.split('_')[1])
                    delta = bs_delta_call(fruit_price, strike, T_days, 0.0, self.annualized_vol)
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
            
            # Incorporate toxicity into fair value
            toxicity_impact = toxicity_score.get(product, 0.0) * self.toxicity_multiplier
            fair = microprices[product] + toxicity_impact
            
            if product == 'VELVETFRUIT_EXTRACT':
                pos_diff = pos - target_fruit_position
            else:
                pos_diff = pos
                
            # Convex Inventory Penalty: Skew using a Power function
            z = pos_diff / limit
            skew = (abs(z) ** self.skew_power) * math.copysign(1, z) * self.skew_multiplier
            
            my_bid = math.floor(fair - 1.0 - skew)
            my_ask = math.ceil(fair + 1.0 - skew)
            
            if my_ask <= my_bid:
                my_ask = my_bid + 1
                
            # "Oh No" button: Aggressive crossing if heavily skewed
            if pos_diff > limit * self.scratch_threshold:
                my_ask = math.floor(fair - 1)  # Cross spread to pay up and exit
            elif pos_diff < -limit * self.scratch_threshold:
                my_bid = math.ceil(fair + 1)   # Cross spread to pay up and exit
                
            buy_volume = limit - pos
            sell_volume = -limit - pos
            
            orders = []
            if buy_volume > 0:
                orders.append(Order(product, my_bid, buy_volume))
            if sell_volume < 0:
                orders.append(Order(product, my_ask, sell_volume))
                
            result[product] = orders
            
        # 5. Intrinsic Price Floors (The "Hard Stop")
        if 'VELVETFRUIT_EXTRACT' in bids and 'VELVETFRUIT_EXTRACT' in asks:
            fruit_bid = bids['VELVETFRUIT_EXTRACT']
            fruit_ask = asks['VELVETFRUIT_EXTRACT']
            
            for strike in range(4000, 7100, 100):
                vev_product = f'VEV_{strike}'
                if vev_product not in state.order_depths:
                    continue
                    
                order_depth = state.order_depths[vev_product]
                vev_pos = state.position.get(vev_product, 0)
                vev_limit = self.limits.get(vev_product, 300)
                
                intrinsic_for_buy = self.get_intrinsic_value(strike, fruit_ask)
                intrinsic_for_sell = self.get_intrinsic_value(strike, fruit_bid)
                
                orders = []
                
                # Arbitrage: Buying undervalued vouchers
                if len(order_depth.sell_orders) > 0:
                    vev_ask = min(order_depth.sell_orders.keys())
                    vev_ask_vol = -order_depth.sell_orders[vev_ask]
                    
                    if vev_ask <= intrinsic_for_buy - self.option_transaction_costs:
                        vol_to_buy = min(vev_ask_vol, vev_limit - vev_pos)
                        if vol_to_buy > 0:
                            orders.append(Order(vev_product, vev_ask, vol_to_buy))
                            vev_pos += vol_to_buy
                            
                # Volatility Harvesting: Selling overvalued vouchers
                if len(order_depth.buy_orders) > 0:
                    vev_bid = max(order_depth.buy_orders.keys())
                    vev_bid_vol = order_depth.buy_orders[vev_bid]
                    
                    if vev_bid >= intrinsic_for_sell + self.option_transaction_costs:
                        vol_to_sell = min(vev_bid_vol, vev_limit + vev_pos)
                        if vol_to_sell > 0:
                            orders.append(Order(vev_product, vev_bid, -vol_to_sell))
                            vev_pos -= vol_to_sell
                            
                if orders:
                    result[vev_product] = orders

        return result, conversions, trader_data