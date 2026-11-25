import argparse
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from quant_trade.config import BacktestConfig
from quant_trade.data import load_market_data
from quant_trade.engine import BacktestEngine
from quant_trade.reporting import format_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the intraday NVDA backtest prototype.")
    parser.add_argument(
        "csv",
        nargs="?",
        type=Path,
        default=Path("data") / "NVDA_clean_1min.csv",
        help="one-minute OHLCV CSV (default: data/NVDA_clean_1min.csv)",
    )
    parser.add_argument("--cash", type=Decimal, default=Decimal("100000"))
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--target-pct", type=Decimal, default=Decimal("0.02"))
    parser.add_argument("--stop-pct", type=Decimal, default=Decimal("0.01"))
    parser.add_argument("--slippage-bps", type=Decimal, default=Decimal("5"))
    parser.add_argument("--commission", type=Decimal, default=Decimal("1"))
    args = parser.parse_args()

    config = BacktestConfig(
        starting_cash=args.cash,
        order_size=args.size,
        profit_target_pct=args.target_pct,
        stop_loss_pct=args.stop_pct,
        slippage_bps=args.slippage_bps,
        commission_per_fill=args.commission,
    )
    market_data = load_market_data(args.csv)
    result = BacktestEngine(config).run(market_data.sessions)
    result = replace(result, data_issues=market_data.issues)
    print(format_report(result))
    return 2 if market_data.invalid_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
