# Backtest Engine Design Draft

Status: Draft for discussion. No implementation decisions are final.

## Goal

Build a reproducible backtest engine that runs swappable strategies against
historical market data. Start with a candlestick-pattern strategy to exercise
the engine's data, execution, portfolio, and reporting components.

Determining whether a strategy is profitable is not a goal of this prototype.

## Initial scope

- Use historical one-minute OHLCV candles as the base data.
- Support one instrument, long-only positions, and no leverage initially.
- Trade during regular market hours and close all positions before each
  session ends.
- Use a common strategy interface so adding a strategy does not require
  rewriting the engine.
- Simulate market orders, commissions, and slippage.
- Record enough information to explain orders, fills, and portfolio changes.
- Keep the design open to longer holding periods and other strategies later.

## Data and candle aggregation

The user will source one-minute data. The data module should load bars in
chronological order and validate required fields, timestamps, duplicates,
and OHLC values. The dataset's timezone, timestamp convention (bar start or
bar end), session coverage, and price-adjustment assumptions must be explicit.

An optional preprocessing step can aggregate one-minute bars into longer
intervals:

| Field | Aggregation |
| --- | --- |
| Open | First minute's open |
| High | Highest minute's high |
| Low | Lowest minute's low |
| Close | Last minute's close |
| Volume | Sum of minute volumes |

Aggregation must respect session boundaries. Handling of missing minutes,
incomplete candles, and sessions with irregular lengths needs to be defined
before implementation; missing data must not silently produce misleading bars.
The initial strategy can use one-minute candles; longer intervals are optional.

## Proposed modules

| Module | Responsibility |
| --- | --- |
| Market data | Load and validate one-minute bars and their metadata. |
| Session calendar | Identify regular trading sessions, holidays, and early closes for the chosen market. |
| Candle aggregation | Optionally derive longer candles without crossing session boundaries. |
| Pattern detection | Identify candlestick patterns from completed candles without placing trades. |
| Strategy | Consume available data and portfolio state and propose orders through a common interface. |
| Position-management policy | Apply sizing, holding-period, and session-exit rules independently of pattern detection. |
| Engine | Advance time and coordinate data, strategy, policy, execution, and portfolio. |
| Execution | Simulate eligible market-order fills, costs, and rejections. |
| Portfolio | Track cash, positions, and equity from fills and market prices. |
| Results | Record configuration, orders, fills, holdings, equity, and basic descriptive metrics. |

The strategy interface should only expose information available at the time of
the decision. New strategies should be selectable through run configuration
rather than requiring changes to the engine. The precise interface and division
of responsibilities between strategy and policy remain to be designed.

## Proposed simulation lifecycle

For each bar in chronological order:

1. At the bar's open, process eligible orders submitted earlier.
2. At the bar's close, value the portfolio.
3. After the bar closes, provide the completed bar and available history to the
   strategy and position-management policy.
4. Queue resulting orders for a future eligible open.

A signal based on a completed candle must not fill before that candle is
available. A next-bar-open fill is an idealized assumption that ignores latency;
commissions and slippage should be configurable.

### Intraday policy

For the first version, the policy should:

- Permit fills only during regular trading hours.
- Avoid entries that cannot be exited within the session.
- Schedule any open position to close at the open of the final one-minute bar,
  before the session ends.
- Leave no positions or pending orders carried into the next session.

The session calendar must account for early closes. If missing data prevents
a reliable forced exit, the run must surface the problem rather than silently
claiming the position was closed. Final-bar execution is a simulation rule, not
a guarantee of a real-world fill.

## First strategy: candlestick pattern

As a concrete prototype, consider a bullish engulfing pattern on two completed
candles:

- The previous candle closes below its open.
- The current candle closes above its open.
- The current candle's body fully covers the previous candle's body.

The strategy can propose an entry after detection, with a fixed quantity and
at most one open position. A simple holding-period rule can propose an exit,
subject to the intraday policy's earlier session cutoff. The exact pattern
boundaries and holding period are draft choices, not trading recommendations.
Initially, patterns are proposed to use candles within the same session only.

## Records and assumptions

Each run should capture:

- Input data identification and relevant data assumptions.
- Configuration, including strategy, candle interval, starting cash, sizing,
  fees, and slippage.
- Orders and their statuses, including rejection reasons.
- Fills with timestamps, quantities, prices, and fees.
- Portfolio snapshots with cash, positions, and equity.
- A basic summary, such as total return and drawdown, for inspection rather
  than a judgment of profitability.

The prototype proposes rejecting an unaffordable order rather than silently
resizing it. Other execution details, such as partial fills, are out of scope.

## Validation priorities

- Test pattern detection, including boundary cases.
- Verify that strategies cannot use future data and signals do not fill before
  their candles complete.
- Reconcile fills, costs, cash, positions, and equity.
- Test repeated signals, insufficient cash, session cutoffs, and early closes.
- Test data validation and aggregation, including missing and incomplete bars.
- Verify that an open position or pending order is never silently carried into
  the next session.

## Out of scope for the first version

- Live or paper trading and broker integrations.
- Short selling, leverage, derivatives, and complex order types.
- Tick-level or order-book simulation.
- Optimization, profitability research, and a web UI.
- Overnight positions and the additional accounting they require.

## Open decisions

- Which market and instrument will supply the initial data?
- What are the provider's timestamp, timezone, adjustment, and session conventions?
- How should missing minutes and incomplete aggregated candles be handled?
- What exact pattern boundary, holding period, and order size should the
  prototype use?
- For longer strategy candles, how should decisions and session cutoffs align
  with one-minute execution bars?
- Which calendar source and execution-cost model should be used?

## Suggested build sequence

1. Inspect the chosen dataset and agree on data and session contracts.
2. Define the strategy, policy, execution, and portfolio interfaces.
3. Build one end-to-end run using the candlestick example.
4. Validate timing, accounting, session exits, and data edge cases.
5. Add aggregation and further strategies as needed.
