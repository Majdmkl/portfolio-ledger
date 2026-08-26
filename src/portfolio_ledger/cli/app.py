"""Typer CLI application.

Each command instantiates a MemoryRepository for its lifetime. Persistence
across invocations is added in step 8 (json_store) with no changes required
to this file's command signatures.
"""

from typing import Annotated

import typer

from portfolio_ledger import service
from portfolio_ledger.cli import render
from portfolio_ledger.domain.errors import PortfolioLedgerError
from portfolio_ledger.storage.memory import MemoryRepository

app = typer.Typer(help="portfolio-ledger: track trades and compute P&L.")
portfolio_app = typer.Typer(help="Manage portfolios.")
instrument_app = typer.Typer(help="Manage instruments.")

app.add_typer(portfolio_app, name="portfolio")
app.add_typer(instrument_app, name="instrument")


def _repo() -> MemoryRepository:
    """Return a fresh repository. Replaced by JsonStore in step 8."""
    return MemoryRepository()


def _abort(message: str) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


# portfolio commands


@portfolio_app.command("create")
def portfolio_create(
    name: Annotated[str, typer.Argument(help="Portfolio name (must be unique).")],
    currency: Annotated[
        str, typer.Option("--currency", "-c", help="ISO 4217 currency code.")
    ] = "SEK",
) -> None:
    """Create a new portfolio."""
    try:
        portfolio = service.create_portfolio(_repo(), name, currency)
    except PortfolioLedgerError as exc:
        _abort(str(exc))
        return
    typer.echo(
        f"Created portfolio {portfolio.name!r} ({portfolio.currency}) [{portfolio.id}]"
    )


@portfolio_app.command("list")
def portfolio_list() -> None:
    """List all portfolios."""
    render.render_portfolios(service.list_portfolios(_repo()))


# instrument commands


@instrument_app.command("create")
def instrument_create(
    symbol: Annotated[str, typer.Argument(help="Ticker symbol, e.g. AAPL.")],
    name: Annotated[str, typer.Argument(help="Full instrument name.")],
    portfolio: Annotated[
        str, typer.Option("--portfolio", "-p", help="Portfolio name.")
    ],
) -> None:
    """Create a new instrument within a portfolio."""
    try:
        instrument = service.create_instrument(_repo(), portfolio, symbol, name)
    except PortfolioLedgerError as exc:
        _abort(str(exc))
        return
    typer.echo(
        f"Created instrument {instrument.symbol!r}"
        f" ({instrument.name}) [{instrument.id}]"
    )


@instrument_app.command("list")
def instrument_list(
    portfolio: Annotated[
        str, typer.Option("--portfolio", "-p", help="Portfolio name.")
    ],
) -> None:
    """List instruments in a portfolio."""
    try:
        instruments = service.list_instruments(_repo(), portfolio)
    except PortfolioLedgerError as exc:
        _abort(str(exc))
        return
    render.render_instruments(instruments)
