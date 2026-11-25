import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import exchange_calendars as xcals

from quant_trade.models import Candle, DataIssue, MarketData, SessionData

NEW_YORK = ZoneInfo("America/New_York")
UTC = timezone.utc
REQUIRED_COLUMNS = ("datetime", "Open", "High", "Low", "Close", "Volume")


def load_market_data(
    path: str | Path,
    calendar_name: str = "XNYS",
) -> MarketData:
    source = Path(path)
    calendar = xcals.get_calendar(calendar_name)
    issues: list[DataIssue] = []
    rows_by_date: dict[str, list[Candle]] = {}
    seen_timestamps: set[datetime] = set()
    session_bounds: dict[str, tuple[datetime, datetime] | None] = {}
    invalid_rows = 0

    with source.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"{source} has no CSV header")
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing_columns:
            raise ValueError(f"{source} is missing required columns: {', '.join(missing_columns)}")

        for line_number, row in enumerate(reader, start=2):
            try:
                candle = _parse_candle(row)
                if candle.timestamp in seen_timestamps:
                    raise ValueError("duplicate datetime")
                if not _is_valid_ohlcv(candle):
                    raise ValueError("invalid OHLCV values")
                session_date = candle.timestamp.date().isoformat()
                if session_date not in session_bounds:
                    session = pd.Timestamp(session_date)
                    if calendar.is_session(session):
                        session_bounds[session_date] = (
                            calendar.session_open(session).to_pydatetime(),
                            calendar.session_close(session).to_pydatetime(),
                        )
                    else:
                        session_bounds[session_date] = None
                boundaries = session_bounds[session_date]
                if boundaries is None:
                    raise ValueError("timestamp is not on an XNYS session")
                session_open, session_close = boundaries
                if not session_open <= candle.timestamp < session_close:
                    raise ValueError("timestamp is outside regular trading hours")
                if candle.timestamp.second or candle.timestamp.microsecond:
                    raise ValueError("timestamp is not aligned to a minute")
                if (candle.timestamp - session_open) % timedelta(minutes=1):
                    raise ValueError("timestamp is not aligned to the session's minute grid")
                seen_timestamps.add(candle.timestamp)
                rows_by_date.setdefault(session_date, []).append(candle)
            except (ValueError, InvalidOperation, KeyError) as error:
                invalid_rows += 1
                issues.append(
                    DataIssue("error", f"CSV line {line_number}: {error}")
                )

    if not rows_by_date:
        return MarketData((), tuple(issues), invalid_rows)

    sessions = calendar.sessions_in_range(
        pd.Timestamp(min(rows_by_date)),
        pd.Timestamp(max(rows_by_date)),
    )
    loaded_sessions: list[SessionData] = []
    for session_label in sessions:
        session_date = session_label.date().isoformat()
        session_open = calendar.session_open(session_label).to_pydatetime()
        session_close = calendar.session_close(session_label).to_pydatetime()
        expected = []
        cursor = session_open
        while cursor < session_close:
            expected.append(cursor)
            cursor += timedelta(minutes=1)
        bars = sorted(rows_by_date.get(session_date, []), key=lambda bar: bar.timestamp)
        if not bars:
            issues.append(DataIssue("warning", f"{session_date}: no session data"))
            continue
        actual = {bar.timestamp for bar in bars}
        missing = tuple(timestamp for timestamp in expected if timestamp not in actual)
        if missing:
            sample = ", ".join(item.strftime("%H:%M") for item in missing[:3])
            issues.append(
                DataIssue(
                    "warning",
                    f"{session_date}: {len(missing)} missing minute(s), first: {sample}",
                )
            )
        loaded_sessions.append(
            SessionData(
                session_date=session_date,
                candles=tuple(bars),
                expected_last_timestamp=expected[-1],
                missing_minutes=missing,
            )
        )
    return MarketData(tuple(loaded_sessions), tuple(issues), invalid_rows)


def _parse_candle(row: dict[str, str]) -> Candle:
    if any(not row.get(column) for column in REQUIRED_COLUMNS):
        raise ValueError("empty required CSV value")
    naive_timestamp = datetime.strptime(row["datetime"].strip(), "%Y-%m-%d %H:%M:%S")
    timestamp = naive_timestamp.replace(tzinfo=NEW_YORK).astimezone(UTC)
    open_price = Decimal(row["Open"].strip())
    high = Decimal(row["High"].strip())
    low = Decimal(row["Low"].strip())
    close = Decimal(row["Close"].strip())
    volume_decimal = Decimal(row["Volume"].strip())
    if not volume_decimal.is_finite() or volume_decimal < 0:
        raise ValueError("volume must be finite and non-negative")
    if volume_decimal != volume_decimal.to_integral_value():
        raise ValueError("volume must be a whole number")
    return Candle(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=int(volume_decimal),
    )


def _is_valid_ohlcv(candle: Candle) -> bool:
    values = (candle.open, candle.high, candle.low, candle.close)
    if any(not value.is_finite() or value <= 0 for value in values):
        return False
    return (
        candle.high >= max(candle.open, candle.close, candle.low)
        and candle.low <= min(candle.open, candle.close, candle.high)
        and candle.volume >= 0
    )
