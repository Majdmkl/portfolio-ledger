"""Rich table renderers for CLI output."""

from decimal import Decimal

from rich.console import Console
from rich.table import Table

from portfolio_ledger.domain.models import Instrument, Portfolio, Trade
from portfolio_ledger.domain.pnl import Position

console = Console()

_NA = "[dim]n/a[/dim]"


def _fmt_pnl(value: Decimal) -> str:
    """Format a P&L value with colour: green for gains, red for losses."""
    if value > 0:
        return f"[green]{value:.2f}[/green]"
    if value < 0:
        return f"[red]{value:.2f}[/red]"
    return f"{value:.2f}"


def render_portfolios(portfolios: list[Portfolio]) -> None:
    if not portfolios:
        console.print("[dim]No portfolios found.[/dim]")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Currency")
    table.add_column("ID", style="dim")
    for p in portfolios:
        table.add_row(p.name, p.currency, str(p.id))
    console.print(table)


def render_instruments(instruments: list[Instrument]) -> None:
    if not instruments:
        console.print("[dim]No instruments found.[/dim]")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("Symbol")
    table.add_column("Name")
    table.add_column("ID", style="dim")
    for i in instruments:
        table.add_row(i.symbol, i.name, str(i.id))
    console.print(table)


def render_trades(pairs: list[tuple[Trade, Instrument]]) -> None:
    if not pairs:
        console.print("[dim]No trades found.[/dim]")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("Date (UTC)")
    table.add_column("Symbol")
    table.add_column("Direction")
    table.add_column("Quantity", justify="right")
    table.add_column("Price", justify="right")
    for trade, instrument in pairs:
        table.add_row(
            trade.timestamp.strftime("%Y-%m-%d %H:%M"),
            instrument.symbol,
            trade.direction.value,
            str(trade.quantity),
            str(trade.price),
        )
    console.print(table)


def render_pnl(
    rows: list[tuple[Instrument, Position, Decimal | None]],
) -> None:
    """Render a P&L summary table.

    Unrealized P&L and Total P&L show 'n/a' when no mark price is provided,
    never zero. A summary row totals realized P&L and, if every instrument has
    a mark price, unrealized and total P&L as well.
    """
    if not rows:
        console.print("[dim]No positions to display.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Symbol")
    table.add_column("Qty", justify="right")
    table.add_column("Avg Cost", justify="right")
    table.add_column("Cost Basis", justify="right")
    table.add_column("Realized P&L", justify="right")
    table.add_column("Unrealized P&L", justify="right")
    table.add_column("Total P&L", justify="right")

    total_realized = Decimal("0")
    total_unrealized: Decimal | None = Decimal("0")

    for instrument, position, mark in rows:
        realized = position.realized_pnl
        total_realized += realized

        if mark is not None:
            unrealized = position.unrealized_pnl(mark)
            unrealized_cell = _fmt_pnl(unrealized)
            total_cell = _fmt_pnl(realized + unrealized)
            if total_unrealized is not None:
                total_unrealized += unrealized
        else:
            unrealized_cell = _NA
            total_cell = _NA
            total_unrealized = None  # one missing mark collapses the total

        table.add_row(
            instrument.symbol,
            str(position.quantity),
            f"{position.average_cost:.2f}",
            f"{position.cost_basis():.2f}",
            _fmt_pnl(realized),
            unrealized_cell,
            total_cell,
        )

    # summary row
    unrealized_summary = (
        _fmt_pnl(total_unrealized) if total_unrealized is not None else _NA
    )
    total_summary = (
        _fmt_pnl(total_realized + total_unrealized)
        if total_unrealized is not None
        else _NA
    )
    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        "",
        "",
        "",
        f"[bold]{_fmt_pnl(total_realized)}[/bold]",
        f"[bold]{unrealized_summary}[/bold]",
        f"[bold]{total_summary}[/bold]",
    )

    console.print(table)
