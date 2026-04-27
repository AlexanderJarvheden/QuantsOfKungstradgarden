import numpy as np

# AETHER CRYSTAL Parameters
TRADING_DAYS_PER_YEAR = 252
STEPS_PER_DAY = 4
STEPS_PER_YEAR = TRADING_DAYS_PER_YEAR * STEPS_PER_DAY
ANNUAL_VOL = 2.51  # 251% annualized volatility
S0 = 100000.0  # Placeholder: User should update this with the actual current price!

def weeks_to_years(weeks: float) -> float:
    return (weeks * 5) / TRADING_DAYS_PER_YEAR

def steps_for_weeks(weeks: float) -> int:
    return int(round(weeks * 5 * STEPS_PER_DAY))

def simulate_gbm_paths(S0, weeks, num_simulations=100000):
    """
    Simulate GBM paths over discrete steps.
    Returns: paths array of shape (num_simulations, total_steps + 1)
    """
    total_steps = steps_for_weeks(weeks)
    dt = 1.0 / STEPS_PER_YEAR
    
    paths = np.zeros((num_simulations, total_steps + 1))
    paths[:, 0] = S0
    
    Z = np.random.normal(0, 1, (num_simulations, total_steps))
    
    # Precompute constants
    drift = -0.5 * (ANNUAL_VOL ** 2) * dt
    vol_sqrt_dt = ANNUAL_VOL * np.sqrt(dt)
    
    for t in range(1, total_steps + 1):
        paths[:, t] = paths[:, t-1] * np.exp(drift + vol_sqrt_dt * Z[:, t-1])
        
    return paths

def price_vanilla(S0, K, weeks, option_type='call', num_simulations=100000):
    paths = simulate_gbm_paths(S0, weeks, num_simulations)
    S_T = paths[:, -1]
    
    if option_type == 'call':
        payoffs = np.maximum(S_T - K, 0)
    else:
        payoffs = np.maximum(K - S_T, 0)
        
    return np.mean(payoffs)

def price_chooser(S0, K, weeks_total=3, weeks_choice=2, num_simulations=100000):
    """
    Expires in 3 weeks. After 2 weeks, chooses to be a call or put.
    It can be proven that a Chooser Option with strike K is equivalent to:
    Vanilla Call(T=3 weeks) + Vanilla Put(T=2 weeks)
    """
    call_val = price_vanilla(S0, K, weeks_total, 'call', num_simulations)
    put_val = price_vanilla(S0, K, weeks_choice, 'put', num_simulations)
    return call_val + put_val

def price_binary_put(S0, K, payout, weeks=3, num_simulations=100000):
    """
    Pays `payout` if S_T < K at expiry.
    """
    paths = simulate_gbm_paths(S0, weeks, num_simulations)
    S_T = paths[:, -1]
    
    payoffs = np.where(S_T < K, payout, 0)
    return np.mean(payoffs)

def price_knockout_put(S0, K, barrier, weeks=3, num_simulations=100000):
    """
    Behaves like a regular put unless it trades below `barrier`.
    If barrier is breached at any discrete point, option becomes worthless.
    """
    paths = simulate_gbm_paths(S0, weeks, num_simulations)
    
    # Check if barrier is ever breached across all steps
    breached = np.any(paths < barrier, axis=1)
    
    S_T = paths[:, -1]
    payoffs = np.maximum(K - S_T, 0)
    
    # If breached, payoff is 0
    payoffs[breached] = 0
    
    return np.mean(payoffs)

if __name__ == "__main__":
    print("=== Aether Crystal Manual Challenge Pricing ===")
    print(f"Assuming S0 = {S0}")
    print("Make sure to update S0 and the Strikes/Barriers in this script to match the platform!\n")
    
    # Example Parameters (UPDATE THESE)
    K_vanilla = 100000
    K_chooser = 100000
    K_binary = 95000
    Payout_binary = 10000
    K_knockout = 105000
    Barrier_knockout = 90000
    
    sims = 200000 # Increase for more accuracy
    
    # 1. Vanilla Options
    call_2w = price_vanilla(S0, K_vanilla, 2, 'call', sims)
    put_2w = price_vanilla(S0, K_vanilla, 2, 'put', sims)
    call_3w = price_vanilla(S0, K_vanilla, 3, 'call', sims)
    put_3w = price_vanilla(S0, K_vanilla, 3, 'put', sims)
    
    print(f"2-Week Vanilla Call (K={K_vanilla}): {call_2w:.2f}")
    print(f"2-Week Vanilla Put (K={K_vanilla}): {put_2w:.2f}")
    print(f"3-Week Vanilla Call (K={K_vanilla}): {call_3w:.2f}")
    print(f"3-Week Vanilla Put (K={K_vanilla}): {put_3w:.2f}")
    print("-" * 30)
    
    # 2. Exotics
    chooser = price_chooser(S0, K_chooser, 3, 2, sims)
    print(f"3-Week Chooser Option (K={K_chooser}): {chooser:.2f}")
    
    binary_put = price_binary_put(S0, K_binary, Payout_binary, 3, sims)
    print(f"3-Week Binary Put (K={K_binary}, Payout={Payout_binary}): {binary_put:.2f}")
    
    ko_put = price_knockout_put(S0, K_knockout, Barrier_knockout, 3, sims)
    print(f"3-Week Knock-Out Put (K={K_knockout}, Barrier={Barrier_knockout}): {ko_put:.2f}")
    print("-" * 30)
    
    print("\nCompare these 'Fair Values' to the cosmetic prices.")
    print("If Fair Value > Cost: BUY")
    print("If Fair Value < Cost: SELL")
