from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BacktestConfig:
    symbol: str = "NVDA"
    starting_cash: Decimal = Decimal("100000")
    order_size: int = 100
    profit_target_pct: Decimal = Decimal("0.02")
    stop_loss_pct: Decimal = Decimal("0.01")
    slippage_bps: Decimal = Decimal("5")
    commission_per_fill: Decimal = Decimal("1")
    tick_size: Decimal = Decimal("0.0001")

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.starting_cash <= 0:
            raise ValueError("starting_cash must be positive")
        if self.order_size <= 0:
            raise ValueError("order_size must be positive")
        if not Decimal("0") < self.profit_target_pct < Decimal("1"):
            raise ValueError("profit_target_pct must be between 0 and 1")
        if not Decimal("0") < self.stop_loss_pct < Decimal("1"):
            raise ValueError("stop_loss_pct must be between 0 and 1")
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps must not be negative")
        if self.commission_per_fill < 0:
            raise ValueError("commission_per_fill must not be negative")
        if self.tick_size <= 0:
            raise ValueError("tick_size must be positive")
