"""Typer CLI application.

Each command instantiates a MemoryRepository for its lifetime. Persistence
across invocations is added in step 8 (json_store) with no changes required
to this file's command signatures.
"""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated

import typer

from portfolio_ledger import service
from portfolio_ledger.cli import render
from portfolio_ledger.domain.errors import PortfolioLedgerError
from portfolio_ledger.domain.models import TradeDirection
from portfolio_ledger.storage.memory import MemoryRepository

app = typer.Typer(help="portfolio-ledger: track trades and compute P&L.")
portfolio_app = typer.Typer(help="Manage portfolios.")
instrument_app = typer.Typer(help="Manage instruments.")
trade_app = typer.Typer(help="Record and list trades.")

app.add_typer(portfolio_app, name="portfolio")
app.add_typer(instrument_app, name="instrument")
app.add_typer(trade_app, name="trade")


def _repo() -> MemoryRepository:
    """Return a fresh repository. Replaced by JsonStore in step 8."""
    return MemoryRepository()


def _abort(message: str) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


def _parse_decimal(value: str, label: str) -> Decimal:
    """Parse a string to Decimal, aborting with a clear message on failure."""
    try:
        d = Decimal(value)
    except InvalidOperation:
        _abort(f"{label} must be a valid number, got {value!r}")
        raise  # unreachable; satisfies mypy that we always return Decimal
    if d <= 0:
        _abort(f"{label} must be positive, got {value!r}")
    return d


def _parse_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 string to a timezone-aware UTC datetime."""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        _abort(f"Invalid timestamp {value!r}. Use ISO 8601, e.g. 2024-01-15T10:30:00Z")
        raise  # unreachable
    if dt.tzinfo is None:
        _abort(
            f"Timestamp {value!r} must include a timezone, e.g. 2024-01-15T10:30:00Z"
        )
        raise  # unreachable
    return dt.astimezone(UTC)


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


# trade commands


@trade_app.command("record")
def trade_record(
    symbol: Annotated[str, typer.Argument(help="Instrument symbol, e.g. AAPL.")],
    direction: Annotated[TradeDirection, typer.Argument(help="BUY or SELL.")],
    quantity: Annotated[str, typer.Argument(help="Number of units (positive).")],
    price: Annotated[str, typer.Argument(help="Price per unit.")],
    portfolio: Annotated[
        str, typer.Option("--portfolio", "-p", help="Portfolio name.")
    ],
    at: Annotated[
        str | None,
        typer.Option("--at", help="Trade timestamp in ISO 8601 (default: now)."),
    ] = None,
) -> None:
    """Record a buy or sell trade."""
    qty = _parse_decimal(quantity, "quantity")
    prc = _parse_decimal(price, "price")
    ts = _parse_timestamp(at) if at is not None else datetime.now(UTC)
    try:
        trade = service.record_trade(
            _repo(), portfolio, symbol, direction, qty, prc, ts
        )
    except PortfolioLedgerError as exc:
        _abort(str(exc))
        return
    typer.echo(
        f"Recorded {trade.direction.value} {trade.quantity} {symbol.upper()}"
        f" @ {trade.price} on {trade.timestamp.strftime('%Y-%m-%d %H:%M UTC')}"
    )


@trade_app.command("list")
def trade_list(
    portfolio: Annotated[
        str, typer.Option("--portfolio", "-p", help="Portfolio name.")
    ],
    instrument: Annotated[
        str | None,
        typer.Option("--instrument", "-i", help="Filter by instrument symbol."),
    ] = None,
) -> None:
    """List trades, optionally filtered by instrument."""
    try:
        pairs = service.list_trades(_repo(), portfolio, instrument)
    except PortfolioLedgerError as exc:
        _abort(str(exc))
        return
    render.render_trades(pairs)
