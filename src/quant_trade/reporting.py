from decimal import Decimal

from quant_trade.models import BacktestResult


def format_report(result: BacktestResult) -> str:
    lines: list[str] = []
    lines.append("BACKTEST SUMMARY")
    lines.append(f"Sessions simulated: {len(result.sessions)}")
    lines.append(f"Completed trades: {sum(len(s.trades) for s in result.sessions)}")
    lines.append(f"Reliable realized P&L: {_money(result.realized_pnl)}")
    lines.append("")

    for session in result.sessions:
        lines.append(
            f"{session.session_date} | balance reset {_money(session.starting_cash)}"
            f" | realized P&L {_money(session.reliable_realized_pnl)}"
            f" | trades {len(session.trades)}"
            f" | uncertain {session.uncertain_trade_count}"
        )
        for trade in session.trades:
            reliability = "reliable" if trade.reliable else "UNCERTAIN (excluded from totals)"
            lines.append(
                f"  {trade.symbol} {trade.quantity} shares | "
                f"{trade.entry_order_type} BUY {trade.entry_price:.4f} "
                f"at {trade.entry_timestamp.isoformat()} -> "
                f"{trade.exit_order_type} SELL {trade.exit_price:.4f} "
                f"at {trade.exit_timestamp.isoformat()} | "
                f"commission {_money(trade.entry_commission + trade.exit_commission)} | "
                f"P&L {_money(trade.realized_pnl)} | {reliability}"
            )
        if session.unresolved_position is not None:
            position = session.unresolved_position
            lines.append(
                f"  UNRESOLVED: {position.symbol} {position.quantity} shares entered "
                f"at {position.entry_price:.4f} ({position.reason})"
            )
        for rejected in session.rejected_orders:
            lines.append(
                f"  REJECTED {rejected.side} {rejected.quantity} at "
                f"{rejected.timestamp.isoformat()}: {rejected.reason}"
            )
        for warning in session.warnings:
            lines.append(f"  DATA WARNING: {warning}")

    if result.data_issues:
        lines.append("")
        lines.append(f"DATA ISSUES: {len(result.data_issues)}")
        lines.extend(
            f"  {issue.severity.upper()}: {issue.message}"
            for issue in result.data_issues
        )
    return "\n".join(lines)


def _money(amount: Decimal) -> str:
    return f"${amount:,.2f}"
