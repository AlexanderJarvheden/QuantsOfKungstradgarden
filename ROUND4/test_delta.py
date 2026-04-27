import math

def norm_cdf(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def bs_delta_call(S, K, T, r, sigma):
    if T <= 0:
        return 1.0 if S > K else 0.0
    if S <= 0 or K <= 0 or sigma <= 0:
        return 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return norm_cdf(d1)

S = 5245.0
print("VEV_4000 delta:", bs_delta_call(S, 4000, 2.0/252.0, 0.0, 2.51))
print("VEV_5200 delta:", bs_delta_call(S, 5200, 2.0/252.0, 0.0, 2.51))
print("VEV_7000 delta:", bs_delta_call(S, 7000, 2.0/252.0, 0.0, 2.51))
