import numpy as np

def run_aether_crystal_optimization():
    print("Initializing Aether Crystal pricing engine...")
    print("Simulating 500,000 discrete paths (this may take a few seconds)...\n")

    # --- 1. Environmental Parameters ---
    S0 = 50.0  
    VOL = 2.51
    DAYS_YEAR = 252
    STEPS_DAY = 4
    DT = 1.0 / (DAYS_YEAR * STEPS_DAY)
    SIMS = 500000 
    
    STEPS_14 = 14 * STEPS_DAY  # 56 steps
    STEPS_21 = 21 * STEPS_DAY  # 84 steps

    # --- 2. Market Book (Bid, Ask, Max Volume) ---
    market_book = {
        "AC_50_P":    [12.00, 12.05, 50],
        "AC_50_C":    [12.00, 12.05, 50],
        "AC_35_P":    [4.33, 4.35, 50],
        "AC_40_P":    [6.50, 6.55, 50],
        "AC_45_P":    [9.05, 9.10, 50],
        "AC_60_C":    [8.80, 8.85, 50],
        "AC_50_P_2":  [9.70, 9.75, 50],
        "AC_50_C_2":  [9.70, 9.75, 50],
        "AC_50_CO":   [22.20, 22.30, 50],
        "AC_40_BP":   [5.00, 5.10, 50],
        "AC_45_KO":   [0.15, 0.175, 500]
    }

    # Set seed for reproducibility if you want consistent runs, 
    # though 500k is high enough for convergence
    np.random.seed(42)

    # --- 3. Discrete GBM Simulation ---
    Z = np.random.standard_normal((SIMS, STEPS_21))
    drift = -0.5 * VOL**2 * DT 
    diffusion = VOL * np.sqrt(DT)
    
    log_returns = drift + diffusion * Z
    log_paths = np.cumsum(log_returns, axis=1)
    paths = S0 * np.exp(log_paths)

    # Prepend Day 0 to the paths
    S = np.hstack([np.full((SIMS, 1), S0), paths])

    # Extract the required timeframes for payouts
    S_14 = S[:, STEPS_14]
    S_21 = S[:, STEPS_21]
    S_min_21 = np.min(S, axis=1)

    # --- 4. Fair Value Pricing Models ---
    fv = {}
    
    # Standard 21-Day Options
    fv["AC_50_P"] = np.maximum(50 - S_21, 0).mean()
    fv["AC_50_C"] = np.maximum(S_21 - 50, 0).mean()
    fv["AC_35_P"] = np.maximum(35 - S_21, 0).mean()
    fv["AC_40_P"] = np.maximum(40 - S_21, 0).mean()
    fv["AC_45_P"] = np.maximum(45 - S_21, 0).mean()
    fv["AC_60_C"] = np.maximum(S_21 - 60, 0).mean()

    # Standard 14-Day Options
    fv["AC_50_P_2"] = np.maximum(50 - S_14, 0).mean()
    fv["AC_50_C_2"] = np.maximum(S_14 - 50, 0).mean()

    # Chooser Exotic (Strike 50, converts to ITM side at Day 14)
    is_call = S_14 > 50
    chooser_payoff = np.where(is_call, np.maximum(S_21 - 50, 0), np.maximum(50 - S_21, 0))
    fv["AC_50_CO"] = chooser_payoff.mean()

    # Binary Put Exotic (Pays 10 if S21 < 40)
    fv["AC_40_BP"] = np.where(S_21 < 40, 10, 0).mean()

    # Knock-Out Put Exotic (Strike 45, Barrier 35 checked at every step)
    ko_payoff = np.where(S_min_21 < 35, 0, np.maximum(45 - S_21, 0))
    fv["AC_45_KO"] = ko_payoff.mean()

    # --- 5. Generate Trade Orders ---
    print(f"{'Contract':<12} | {'Fair Value':<10} | {'Action':<6} | {'Volume':<6}")
    print("-" * 45)
    
    for contract, (bid, ask, max_vol) in market_book.items():
        fair_value = fv[contract]
        
        if fair_value > ask:
            action = "BUY"
            vol = max_vol
        elif fair_value < bid:
            action = "SELL"
            vol = max_vol
        else:
            action = "NONE"
            vol = 0
            
        print(f"{contract:<12} | {fair_value:<10.3f} | {action:<6} | {vol:<6}")

if __name__ == "__main__":
    run_aether_crystal_optimization()