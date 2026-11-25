# Backtest engine: first-draft scope

> NautilusTrader has since been selected. Execution rules below are provisional
> where they conflict with [the framework decision](./BACKTEST_FRAMEWORK.md);
> reconcile them after validating the framework's behavior.

## Goal

Build a small, reproducible backtest engine for a single stock using one-minute
candles. Use a candlestick-pattern strategy to exercise the engine; evaluating
or optimizing profitability is out of scope.

## Data and sessions

- Read one symbol from `data/NVDA_clean_1min.csv`, which contains `datetime`,
  OHLC, volume, and source columns.
- Interpret timestamps in `America/New_York`, including daylight-saving changes.
  Confirm whether each timestamp denotes the start or end of its candle before
  implementing the simulation.
- Use regular trading hours only. Use the exchange session calendar to account
  for holidays and early closes.
- Validate the input and report invalid or missing data explicitly. In
  particular, do not pretend a position was closed if the data needed for a
  reliable forced exit is missing.
- Begin each session with the same configurable cash balance. Do not carry
  positions or pending orders overnight; reset strategy state between sessions.

## Strategy

Strategies are swappable through a common interface. The engine provides
available market data and portfolio state; the strategy produces order requests.
The first strategy is long-only and uses a bullish engulfing pattern:

- The previous candle is bearish: its close is below its open.
- The current candle is bullish: its close is above its open.
- The current body fully covers the previous body: current open is less than
  or equal to previous close, and current close is greater than or equal to
  previous open.
- Both candles must belong to the same session.
- Detect the pattern only after the current candle closes. Submit a market buy
  for the next candle's open.

Use a configurable order size, initially 100 shares, and hold at most one
position. Reject an order if there is insufficient cash rather than silently
resizing it. Short selling and leverage are out of scope.

## Exits and execution

- Set the profit target and stop loss as configurable percentages of the
  actual entry fill price. They may trigger during the entry candle.
- The profit target is a sell limit; the stop loss is a sell stop executed as a
  market order.
- If a candle opens below the stop, use its open as the stop's reference price.
  Otherwise, when its low reaches the stop, use the stop price as the reference.
- If a candle opens above the profit target, fill the sell limit at the open.
  Otherwise, when its high reaches the target, fill at the target. Never fill
  the sell limit below its limit price.
- If neither exit triggers at the open and both levels are touched within the
  same candle, assume the stop triggers first.
- At the final candle's open, check existing exits first; if still holding,
  force a market sell. Do not open a new position at that point. Cancel any
  remaining pending orders at the end of the session.
- Apply configurable adverse slippage to market fills, initially 5 basis
  points: increase buy prices and decrease sell prices by 0.05% of the
  reference price. Do not apply this adjustment to profit-taking limit fills.
- Charge a configurable fixed commission, initially $1 per fill. A completed
  buy and sell therefore incurs $2 in commissions with the default settings.

These are simulation assumptions, not guarantees of real execution. The engine
must not use a candle's high, low, or close before that information is available.

## Reporting

Print results to the console:

- Transaction history with symbol, order type, size, buy and sell fill prices,
  commissions, and timestamps.
- Realized P&L per completed trade and per session, plus total realized P&L
  across sessions. Report P&L after commissions and make execution costs
  visible. Daily balances reset, so the total is not a compounded return.
- Unfilled or rejected orders and data problems that prevent a reliable result.

## Proposed modules

1. **Market data:** load and validate candles, timestamps, and sessions.
2. **Pattern detection:** identify candlestick patterns from completed candles.
3. **Strategy:** translate patterns and portfolio state into order requests.
4. **Engine:** advance through candles and enforce session boundaries.
5. **Execution:** process orders, fills, commissions, and slippage.
6. **Portfolio:** track cash, positions, and realized P&L.
7. **Configuration and reporting:** select strategy and assumptions, then print
   the run's results and transaction history.

## Out of scope

Multiple symbols, overnight positions, short selling, leverage, partial fills,
live trading, parameter optimization, and profitability assessment are deferred.
Aggregation into longer candles can be added later; the first draft uses
one-minute candles.

## Validation priorities

Test pattern boundaries, session resets, no look-ahead, next-open entries,
profit and stop exits (including gaps and same-candle ambiguity), forced
end-of-session exits, insufficient cash, commissions, and P&L reconciliation.
Check holiday and early-close handling and clearly report missing data that
would prevent a reliable simulation.
