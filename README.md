# IMC Prosperity trading competition
### Round 1:
* Your goal: earn at least a net 200,000 XIRECs by the end of Round 2.
#### Algorithmic challenge *FIRST INTARIAN GOODS*
Start building your Python program with the first two available tradable goods: 
1. Ash-coated Osmium and,
2. Intarian Pepper Root.

Use the historical data from the Data Capsule to develop a profitable strategy, translate it to a Python program and upload it to the network.
- Data is stored in ```Datasets/ROUND1```.

#### Steps:
1. Write your trading algorithm as a Python file.
2. Upload your Python program. The latest upload replaces the previous one.
3. Upload complete? Check the simulated results in the Performance tab.
4. Final performance results will be calculated after the round closes.

# Trading Algorithm
Algorithm uses the `Trader` class:
- `run()` method = trading logic coded by us.
- *For Algorithmic Trading Round 2, the `Trader` class should also define a `bid()` method. It is fine to have a `bid()` method in every submission for every round, it will be ignored for all rounds except Round 2.*

After upload, it is simulated:
- Simulation consists of the following iterations:
  1. 1_000 during testing when you develop your algorithm on historical data;
  2. 10_000 for the final simulation that determines your PnL for the round
- During each iteration the run method will be called and provided with a `TradingState` object.
  - Contains an overview of all the trades that have happened since the last iteration,
    - The algorithms own trades, and
    - Trades that happened between other market participants.
  - `TradingState` will contain a per product overview of all the outstanding buy and sell orders originating from the bots.
  - The `run` method decides to either send orders that will fully or partially match with the existing orders
    - sending a buy (sell) order with a price equal to or higher (lower) than one of the outstanding bot quotes, which will result in a trade.
    - If the algorithm sends a buy (sell) order with an associated quantity that is larger than the bot sell (buy) quote that it is matched to, the remaining quantity will be left as an outstanding buy (sell) quote with which the trading bots will then potentially trade.
  - Next iteration -> `TradingState` reveals whether any of the bots decided to “trade on” the player’s outstanding quote.
    - If none of the bots trade on an outstanding player quote, the quote is automatically cancelled at the end of the iteration.
- Every trade done by the algorithm in a certain product changes the “position” of the algorithm in that product.
  - A position just specifies how much of a product you hold, e.g. “position=3 in NVIDIA” could mean holding 3 stocks in NVIDIA.
- Restrictions:
  - Algorithms are restricted by per product position limits, which define the absolute position (long or short) that the algorithm is not allowed to exceed.
    - If the aggregated quantity of all the buy (sell) orders an algorithm sends during a certain iteration would, if all fully matched, result in the algorithm obtaining a long (short) position exceeding the position limit, all the orders are cancelled by the exchange.
