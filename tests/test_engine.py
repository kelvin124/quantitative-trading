import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from quant_trade.config import BacktestConfig
from quant_trade.engine import BacktestEngine
from quant_trade.models import Candle, SessionData
from quant_trade.strategies import BullishEngulfingStrategy

UTC = timezone.utc


def candle(minute: int, open_: str, high: str, low: str, close: str) -> Candle:
    return Candle(
        timestamp=datetime(2024, 1, 2, 14, 30, tzinfo=UTC) + timedelta(minutes=minute),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=100,
    )


def session(bars: list[Candle], final_minute: int | None = None) -> SessionData:
    last_expected = datetime(2024, 1, 2, 14, 30, tzinfo=UTC) + timedelta(
        minutes=final_minute if final_minute is not None else bars[-1].timestamp.minute - 30
    )
    return SessionData("2024-01-02", tuple(bars), last_expected)


class BullishEngulfingTests(unittest.TestCase):
    def test_requires_full_body_engulfment_and_opposite_candle_colors(self) -> None:
        strategy = BullishEngulfingStrategy()
        previous = candle(0, "101", "102", "99", "100")
        engulfing = candle(1, "99", "103", "98", "102")
        partial = candle(1, "100.5", "103", "100", "102")
        self.assertTrue(strategy.should_enter(previous, engulfing))
        self.assertFalse(strategy.should_enter(previous, partial))
        self.assertFalse(strategy.should_enter(engulfing, previous))


class EngineTests(unittest.TestCase):
    def test_enters_next_open_and_forces_exit_with_costs(self) -> None:
        bars = [
            candle(0, "101", "102", "99", "100"),
            candle(1, "99", "103", "99", "102"),
            candle(2, "100", "100.5", "99.5", "100"),
            candle(3, "100", "100.5", "99.5", "100"),
        ]
        result = BacktestEngine().run_session(session(bars))
        trade = result.trades[0]
        self.assertEqual(trade.entry_timestamp, bars[2].timestamp)
        self.assertEqual(trade.entry_price, Decimal("100.0500"))
        self.assertEqual(trade.exit_order_type, "MARKET_EOD")
        self.assertEqual(trade.realized_pnl, Decimal("-12.0000"))
        self.assertEqual(result.reliable_realized_pnl, Decimal("-12.0000"))

    def test_stop_wins_when_both_levels_are_touched(self) -> None:
        bars = [
            candle(0, "101", "102", "99", "100"),
            candle(1, "99", "103", "99", "102"),
            candle(2, "100", "103", "98", "101"),
            candle(3, "100", "100.5", "99.5", "100"),
        ]
        result = BacktestEngine().run_session(session(bars))
        self.assertEqual(result.trades[0].exit_order_type, "MARKET_STOP")

    def test_limit_target_gets_price_improvement_without_slippage(self) -> None:
        bars = [
            candle(0, "101", "102", "99", "100"),
            candle(1, "99", "103", "99", "102"),
            candle(2, "100", "103", "99.5", "102"),
            candle(3, "100", "100.5", "99.5", "100"),
        ]
        result = BacktestEngine().run_session(session(bars))
        trade = result.trades[0]
        self.assertEqual(trade.exit_order_type, "LIMIT_TARGET")
        self.assertEqual(trade.exit_price, Decimal("102.0510"))

    def test_target_gap_fills_at_open_not_below_limit(self) -> None:
        bars = [
            candle(0, "101", "102", "99", "100"),
            candle(1, "99", "103", "99", "102"),
            candle(2, "100", "100.5", "99.5", "100"),
            candle(3, "103", "104", "102.5", "103.5"),
            candle(4, "100", "100.5", "99.5", "100"),
        ]
        result = BacktestEngine().run_session(session(bars))
        self.assertEqual(result.trades[0].exit_price, Decimal("103"))

    def test_stop_gap_uses_open_as_reference_then_applies_slippage(self) -> None:
        bars = [
            candle(0, "101", "102", "99", "100"),
            candle(1, "99", "103", "99", "102"),
            candle(2, "100", "100.5", "99.5", "100"),
            candle(3, "98", "99", "97", "98.5"),
            candle(4, "100", "100.5", "99.5", "100"),
        ]
        result = BacktestEngine().run_session(session(bars))
        trade = result.trades[0]
        self.assertEqual(trade.exit_order_type, "MARKET_STOP")
        self.assertLess(trade.exit_price, Decimal("98"))

    def test_rejects_insufficient_cash_without_resizing(self) -> None:
        bars = [
            candle(0, "101", "102", "99", "100"),
            candle(1, "99", "103", "99", "102"),
            candle(2, "100", "100.5", "99.5", "100"),
            candle(3, "100", "100.5", "99.5", "100"),
        ]
        config = BacktestConfig(starting_cash=Decimal("1000"), order_size=100)
        result = BacktestEngine(config).run_session(session(bars))
        self.assertEqual(result.trades, [])
        self.assertIn("insufficient cash", result.rejected_orders[0].reason)

    def test_does_not_fabricate_exit_when_final_candle_is_missing(self) -> None:
        bars = [
            candle(0, "101", "102", "99", "100"),
            candle(1, "99", "103", "99", "102"),
            candle(2, "100", "100.5", "99.5", "100"),
        ]
        result = BacktestEngine().run_session(session(bars, final_minute=3))
        self.assertIsNotNone(result.unresolved_position)
        self.assertEqual(result.trades, [])

    def test_does_not_enter_on_final_candle(self) -> None:
        bars = [
            candle(0, "101", "102", "99", "100"),
            candle(1, "99", "103", "99", "102"),
            candle(2, "100", "100.5", "99.5", "100"),
        ]
        result = BacktestEngine().run_session(session(bars))
        self.assertEqual(result.fills, [])
        self.assertIn("final session candle", result.rejected_orders[0].reason)

    def test_gap_while_holding_marks_trade_uncertain(self) -> None:
        bars = [
            candle(0, "101", "102", "99", "100"),
            candle(1, "99", "103", "99", "102"),
            candle(2, "100", "100.5", "99.5", "100"),
            candle(4, "100", "100.5", "99.5", "100"),
            candle(5, "100", "100.5", "99.5", "100"),
        ]
        result = BacktestEngine().run_session(session(bars, final_minute=5))
        self.assertEqual(len(result.trades), 1)
        self.assertFalse(result.trades[0].reliable)
        self.assertEqual(result.reliable_realized_pnl, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
