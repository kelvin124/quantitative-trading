from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

from quant_trade.config import BacktestConfig
from quant_trade.models import (
    BacktestResult,
    Candle,
    Fill,
    RejectedOrder,
    SessionData,
    SessionResult,
    Trade,
    UnresolvedPosition,
)
from quant_trade.strategies import BullishEngulfingStrategy, Strategy


@dataclass
class _Position:
    entry_timestamp: datetime
    entry_price: Decimal
    entry_commission: Decimal
    target: Decimal
    stop: Decimal
    reliable: bool = True


class BacktestEngine:
    def __init__(
        self,
        config: BacktestConfig | None = None,
        strategy: Strategy | None = None,
    ) -> None:
        self.config = config or BacktestConfig()
        self.strategy = strategy or BullishEngulfingStrategy()

    def run(self, sessions: tuple[SessionData, ...] | list[SessionData]) -> BacktestResult:
        results = tuple(self.run_session(session) for session in sessions)
        return BacktestResult(sessions=results)

    def run_session(self, session: SessionData) -> SessionResult:
        self.strategy.reset(session.session_date)
        result = SessionResult(
            session_date=session.session_date,
            starting_cash=self.config.starting_cash,
        )
        cash = self.config.starting_cash
        position: _Position | None = None
        pending_signal = False
        previous: Candle | None = None

        for index, candle in enumerate(session.candles):
            is_final_candle = candle.timestamp == session.expected_last_timestamp
            is_consecutive = (
                previous is not None
                and candle.timestamp - previous.timestamp == timedelta(minutes=1)
            )

            if previous is not None and not is_consecutive:
                if position is not None:
                    position.reliable = False
                    result.warnings.append(
                        f"Open position crossed a data gap between "
                        f"{previous.timestamp.isoformat()} and "
                        f"{candle.timestamp.isoformat()}"
                    )
                if pending_signal:
                    result.rejected_orders.append(
                        RejectedOrder(
                            timestamp=candle.timestamp,
                            side="BUY",
                            quantity=self.config.order_size,
                            reason="next-minute entry candle is missing",
                        )
                    )
                    pending_signal = False

            if pending_signal:
                if is_final_candle:
                    result.rejected_orders.append(
                        RejectedOrder(
                            timestamp=candle.timestamp,
                            side="BUY",
                            quantity=self.config.order_size,
                            reason="entry suppressed at the final session candle",
                        )
                    )
                elif is_consecutive:
                    entry_price = self._market_price(candle.open, side="BUY")
                    commission = self.config.commission_per_fill
                    required_cash = entry_price * self.config.order_size + commission
                    if required_cash > cash:
                        result.rejected_orders.append(
                            RejectedOrder(
                                timestamp=candle.timestamp,
                                side="BUY",
                                quantity=self.config.order_size,
                                reason=(
                                    f"insufficient cash: need {required_cash:.4f}, "
                                    f"available {cash:.4f}"
                                ),
                            )
                        )
                    else:
                        cash -= required_cash
                        result.fills.append(
                            Fill(
                                timestamp=candle.timestamp,
                                side="BUY",
                                order_type="MARKET",
                                quantity=self.config.order_size,
                                price=entry_price,
                                commission=commission,
                            )
                        )
                        position = _Position(
                            entry_timestamp=candle.timestamp,
                            entry_price=entry_price,
                            entry_commission=commission,
                            target=self._round_up(
                                entry_price
                                * (Decimal("1") + self.config.profit_target_pct)
                            ),
                            stop=self._round_down(
                                entry_price * (Decimal("1") - self.config.stop_loss_pct)
                            ),
                        )
                pending_signal = False

            if position is not None:
                if is_final_candle:
                    cash, position = self._exit_if_open_triggered(
                        result, position, candle, cash
                    )
                    if position is not None:
                        cash, position = self._close_position(
                            result,
                            position,
                            candle,
                            reference_price=candle.open,
                            order_type="MARKET_EOD",
                            apply_slippage=True,
                            cash=cash,
                        )
                else:
                    cash, position = self._process_exits(result, position, candle, cash)

            if (
                position is None
                and not pending_signal
                and not is_final_candle
                and previous is not None
                and is_consecutive
                and self.strategy.should_enter(previous, candle)
                and index + 1 < len(session.candles)
            ):
                pending_signal = True

            previous = candle

        has_final_candle = bool(session.candles) and (
            session.candles[-1].timestamp == session.expected_last_timestamp
        )
        if position is not None:
            reason = (
                "session has no final scheduled candle; position was not fabricated "
                "as closed"
                if not has_final_candle
                else "position remained open at session end"
            )
            result.unresolved_position = UnresolvedPosition(
                symbol=self.config.symbol,
                quantity=self.config.order_size,
                entry_timestamp=position.entry_timestamp,
                entry_price=position.entry_price,
                reason=reason,
            )
            result.warnings.append(reason)

        if pending_signal:
            result.rejected_orders.append(
                RejectedOrder(
                    timestamp=session.candles[-1].timestamp,
                    side="BUY",
                    quantity=self.config.order_size,
                    reason="no next-minute candle is available",
                )
            )

        if session.missing_minutes:
            result.warnings.append(
                f"{len(session.missing_minutes)} scheduled minute candle(s) missing; "
                "trades spanning a gap are excluded from reliable P&L"
            )
        return result

    def _process_exits(
        self,
        result: SessionResult,
        position: _Position,
        candle: Candle,
        cash: Decimal,
    ) -> tuple[Decimal, _Position | None]:
        stopped_at_open = candle.open <= position.stop
        targeted_at_open = candle.open >= position.target
        if stopped_at_open:
            return self._close_position(
                result,
                position,
                candle,
                reference_price=candle.open,
                order_type="MARKET_STOP",
                apply_slippage=True,
                cash=cash,
            )
        if targeted_at_open:
            return self._close_position(
                result,
                position,
                candle,
                reference_price=candle.open,
                order_type="LIMIT_TARGET",
                apply_slippage=False,
                cash=cash,
            )

        stop_touched = candle.low <= position.stop
        target_touched = candle.high >= position.target
        if stop_touched:
            return self._close_position(
                result, position, candle, position.stop, "MARKET_STOP", True, cash
            )
        if target_touched:
            return self._close_position(
                result, position, candle, position.target, "LIMIT_TARGET", False, cash
            )
        return cash, position

    def _exit_if_open_triggered(
        self,
        result: SessionResult,
        position: _Position,
        candle: Candle,
        cash: Decimal,
    ) -> tuple[Decimal, _Position | None]:
        if candle.open <= position.stop:
            return self._close_position(
                result,
                position,
                candle,
                reference_price=candle.open,
                order_type="MARKET_STOP",
                apply_slippage=True,
                cash=cash,
            )
        if candle.open >= position.target:
            return self._close_position(
                result,
                position,
                candle,
                reference_price=candle.open,
                order_type="LIMIT_TARGET",
                apply_slippage=False,
                cash=cash,
            )
        return cash, position

    def _close_position(
        self,
        result: SessionResult,
        position: _Position,
        candle: Candle,
        reference_price: Decimal,
        order_type: str,
        apply_slippage: bool,
        cash: Decimal,
    ) -> tuple[Decimal, None]:
        exit_price = (
            self._market_price(reference_price, side="SELL")
            if apply_slippage
            else max(reference_price, position.target)
            if order_type == "LIMIT_TARGET"
            else reference_price
        )
        commission = self.config.commission_per_fill
        cash += exit_price * self.config.order_size - commission
        pnl = (
            (exit_price - position.entry_price) * self.config.order_size
            - position.entry_commission
            - commission
        )
        result.fills.append(
            Fill(
                timestamp=candle.timestamp,
                side="SELL",
                order_type=order_type,
                quantity=self.config.order_size,
                price=exit_price,
                commission=commission,
            )
        )
        result.trades.append(
            Trade(
                symbol=self.config.symbol,
                quantity=self.config.order_size,
                entry_order_type="MARKET",
                exit_order_type=order_type,
                entry_timestamp=position.entry_timestamp,
                exit_timestamp=candle.timestamp,
                entry_price=position.entry_price,
                exit_price=exit_price,
                entry_commission=position.entry_commission,
                exit_commission=commission,
                realized_pnl=pnl,
                reliable=position.reliable,
            )
        )
        return cash, None

    def _market_price(self, reference_price: Decimal, side: str) -> Decimal:
        slippage = self.config.slippage_bps / Decimal("10000")
        raw_price = reference_price * (
            Decimal("1") + slippage if side == "BUY" else Decimal("1") - slippage
        )
        tick_count = raw_price / self.config.tick_size
        rounding = ROUND_CEILING if side == "BUY" else ROUND_FLOOR
        return tick_count.to_integral_value(rounding=rounding) * self.config.tick_size

    def _round_up(self, price: Decimal) -> Decimal:
        return (
            (price / self.config.tick_size).to_integral_value(rounding=ROUND_CEILING)
            * self.config.tick_size
        )

    def _round_down(self, price: Decimal) -> Decimal:
        return (
            (price / self.config.tick_size).to_integral_value(rounding=ROUND_FLOOR)
            * self.config.tick_size
        )
