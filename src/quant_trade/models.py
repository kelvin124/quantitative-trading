from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True)
class SessionData:
    session_date: str
    candles: tuple[Candle, ...]
    expected_last_timestamp: datetime
    missing_minutes: tuple[datetime, ...] = ()


@dataclass(frozen=True)
class Fill:
    timestamp: datetime
    side: str
    order_type: str
    quantity: int
    price: Decimal
    commission: Decimal


@dataclass(frozen=True)
class Trade:
    symbol: str
    quantity: int
    entry_order_type: str
    exit_order_type: str
    entry_timestamp: datetime
    exit_timestamp: datetime
    entry_price: Decimal
    exit_price: Decimal
    entry_commission: Decimal
    exit_commission: Decimal
    realized_pnl: Decimal
    reliable: bool = True


@dataclass(frozen=True)
class RejectedOrder:
    timestamp: datetime
    side: str
    quantity: int
    reason: str


@dataclass(frozen=True)
class UnresolvedPosition:
    symbol: str
    quantity: int
    entry_timestamp: datetime
    entry_price: Decimal
    reason: str


@dataclass
class SessionResult:
    session_date: str
    starting_cash: Decimal
    trades: list[Trade] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)
    rejected_orders: list[RejectedOrder] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unresolved_position: UnresolvedPosition | None = None

    @property
    def reliable_realized_pnl(self) -> Decimal:
        return sum(
            (trade.realized_pnl for trade in self.trades if trade.reliable),
            Decimal("0"),
        )

    @property
    def uncertain_trade_count(self) -> int:
        return sum(not trade.reliable for trade in self.trades)


@dataclass(frozen=True)
class DataIssue:
    severity: str
    message: str


@dataclass(frozen=True)
class MarketData:
    sessions: tuple[SessionData, ...]
    issues: tuple[DataIssue, ...]
    invalid_rows: int = 0


@dataclass(frozen=True)
class BacktestResult:
    sessions: tuple[SessionResult, ...]
    data_issues: tuple[DataIssue, ...] = ()

    @property
    def realized_pnl(self) -> Decimal:
        return sum(
            (session.reliable_realized_pnl for session in self.sessions),
            Decimal("0"),
        )
