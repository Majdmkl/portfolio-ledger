"""Rich table renderers for CLI output."""

from rich.console import Console
from rich.table import Table

from portfolio_ledger.domain.models import Instrument, Portfolio, Trade

console = Console()


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
