import unittest
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from quant_trade.data import _parse_candle, load_market_data


class TimestampTests(unittest.TestCase):
    def test_local_session_timestamp_converts_with_daylight_saving(self) -> None:
        winter = _parse_candle(
            {
                "datetime": "2022-03-07 09:30:00",
                "Open": "100",
                "High": "101",
                "Low": "99",
                "Close": "100.5",
                "Volume": "100",
            }
        )
        summer = _parse_candle(
            {
                "datetime": "2022-07-07 09:30:00",
                "Open": "100",
                "High": "101",
                "Low": "99",
                "Close": "100.5",
                "Volume": "100",
            }
        )
        self.assertEqual(winter.timestamp.hour, 14)
        self.assertEqual(summer.timestamp.hour, 13)
        self.assertEqual(winter.timestamp.tzinfo, timezone.utc)

    def test_calendar_uses_early_close_for_final_scheduled_bar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "early-close.csv"
            path.write_text(
                "datetime,Open,High,Low,Close,Volume,source\n"
                "2022-11-25 09:30:00,100,101,99,100.5,100,iex\n"
                "2022-11-25 12:59:00,100,101,99,100.5,100,iex\n",
                encoding="utf-8",
            )
            market_data = load_market_data(path)

        self.assertEqual(len(market_data.sessions), 1)
        session = market_data.sessions[0]
        self.assertEqual(
            session.expected_last_timestamp,
            datetime(2022, 11, 25, 17, 59, tzinfo=timezone.utc),
        )
        self.assertEqual(len(session.missing_minutes), 208)

    def test_calendar_rejects_market_holiday_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "holiday.csv"
            path.write_text(
                "datetime,Open,High,Low,Close,Volume,source\n"
                "2022-11-24 09:30:00,100,101,99,100.5,100,iex\n",
                encoding="utf-8",
            )
            market_data = load_market_data(path)

        self.assertEqual(market_data.invalid_rows, 1)
        self.assertEqual(market_data.sessions, ())


if __name__ == "__main__":
    unittest.main()
