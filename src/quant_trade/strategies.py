from typing import Protocol

from quant_trade.models import Candle


class Strategy(Protocol):
    name: str

    def reset(self, session_date: str) -> None:
        """Clear any strategy state before a new trading session."""

    def should_enter(self, previous: Candle, current: Candle) -> bool:
        """Return whether two completed, consecutive candles form an entry signal."""


class BullishEngulfingStrategy:
    name = "bullish-engulfing"

    def reset(self, session_date: str) -> None:
        pass

    def should_enter(self, previous: Candle, current: Candle) -> bool:
        return (
            previous.close < previous.open
            and current.close > current.open
            and current.open <= previous.close
            and current.close >= previous.open
        )
