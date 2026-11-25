# Framework decision: NautilusTrader

## Selection

Use [NautilusTrader](https://nautilustrader.io/) as the backtesting framework.
It is a local-first platform with swappable strategies and room to expand
beyond the initial prototype. Prefer adapting the prototype's execution
assumptions to the framework over building a separate engine that must later
be replaced.

The functional goals remain in [BACKTEST_SCOPE.md](./BACKTEST_SCOPE.md): one
symbol, one-minute candles, a bullish engulfing strategy, intraday long-only
trading, configurable risk parameters, and console reporting.

## Execution assumptions to reconcile

The execution rules in the scope were drafted before the framework was chosen.
They are provisional where they differ from NautilusTrader's behavior:

- **Entry timing:** NautilusTrader does not provide a native next-bar-open fill
  mode. With bar data and no latency model, an order submitted from `on_bar`
  can settle against the book at the completed bar's close. A same-close fill
  is a simulation assumption, not a guarantee of real execution.
- **Stop and target in the same candle:** the default simulated bar path is
  open, high, low, close, not the previously proposed stop-first rule. The
  resulting order of fills depends on the configured path.
- **Slippage:** the built-in L1 fill model supports probabilistic one-tick
  slippage, not the previously proposed fixed 5-basis-point market-order
  adjustment. Choose and document the model and its effect on each order type.
- **End-of-session exit:** choose a cutoff before the session ends and verify
  actual fills and order cancellation; do not assume the previous final-open
  rule is provided by the framework.

See the NautilusTrader documentation on
[bar execution](https://nautilustrader.io/docs/latest/concepts/backtesting/bar-execution/)
and [fill models](https://nautilustrader.io/docs/latest/concepts/backtesting/fill-models/).
Pin a framework version when implementation begins and verify its behavior
against these assumptions.

## Prototype integration

NautilusTrader supplies the backtesting and order-execution framework. The
project still needs CSV ingestion, exchange-calendar and session controls,
the strategy and its configuration, daily balance resets, and console reporting.
Confirm the CSV's timestamp convention before converting candles to framework
bars. Each session must start with the configured balance and end without
positions or pending orders.

Before committing to detailed implementation, validate a small controlled
example covering:

- Swapping strategies and detecting signals without look-ahead.
- Entry timing, bracket exits, gap behavior, and both thresholds touched.
- A configurable $1 commission per fill, slippage, and any partial fills.
- Regular hours, early closes, forced exits, cancellations, and missing data.
- Independent daily balances, transaction history, and realized P&L.

Record the final framework-compatible choices in the scope once verified.
