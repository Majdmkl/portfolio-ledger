"""Rich table renderers for CLI output."""

from rich.console import Console
from rich.table import Table

from portfolio_ledger.domain.models import Instrument, Portfolio

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
