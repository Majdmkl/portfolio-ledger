"""Typer CLI application."""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated

import typer

from portfolio_ledger import service
from portfolio_ledger.cli import render
from portfolio_ledger.domain.errors import PortfolioLedgerError
from portfolio_ledger.domain.models import TradeDirection
from portfolio_ledger.storage.json_store import JsonStore, SchemaVersionError
from portfolio_ledger.storage.repository import Repository

app = typer.Typer(help="portfolio-ledger: track trades and compute P&L.")
portfolio_app = typer.Typer(help="Manage portfolios.")
instrument_app = typer.Typer(help="Manage instruments.")
trade_app = typer.Typer(help="Record and list trades.")

app.add_typer(portfolio_app, name="portfolio")
app.add_typer(instrument_app, name="instrument")
app.add_typer(trade_app, name="trade")


class _State:
    def __init__(self) -> None:
        self.repo: Repository | None = None


_state = _State()


@app.callback()
def configure(
    data_file: Annotated[
        Path,
        typer.Option(
            "--data-file",
            envvar="PORTFOLIO_LEDGER_DATA",
            help="Path to the JSON data file.",
            show_default=True,
        ),
    ] = Path("portfolio_ledger_data.json"),
) -> None:
    try:
        _state.repo = JsonStore(data_file)
    except SchemaVersionError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def _repo() -> Repository:
    if _state.repo is None:
        raise RuntimeError("Repository not initialized - callback did not run.")
    return _state.repo


def _abort(message: str) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


def _parse_marks(raw: list[str]) -> dict[str, Decimal]:
    """Parse a list of 'SYMBOL=PRICE' strings into a symbol-to-Decimal map."""
    marks: dict[str, Decimal] = {}
    for entry in raw:
        if "=" not in entry:
            _abort(f"Invalid --mark {entry!r}. Expected SYMBOL=PRICE, e.g. AAPL=185.50")
        symbol, _, price_str = entry.partition("=")
        symbol = symbol.strip().upper()
        if not symbol:
            _abort(f"Missing symbol in --mark {entry!r}")
        try:
            price = Decimal(price_str.strip())
        except InvalidOperation:
            _abort(f"Invalid price in --mark {entry!r}: {price_str!r} is not a number")
            raise  # unreachable
        if price <= 0:
            _abort(f"Mark price must be positive in --mark {entry!r}")
        marks[symbol] = price
    return marks


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


# pnl command


@app.command("pnl")
def pnl(
    portfolio: Annotated[
        str, typer.Option("--portfolio", "-p", help="Portfolio name.")
    ],
    mark: Annotated[
        list[str],
        typer.Option(
            "--mark",
            "-m",
            help="Mark price for unrealized P&L, e.g. AAPL=185.50. Repeatable.",
        ),
    ] = [],  # noqa: B006
) -> None:
    """Show realized and unrealized P&L for all positions in a portfolio."""
    marks = _parse_marks(mark)
    try:
        rows = service.get_portfolio_pnl(_repo(), portfolio, marks)
    except PortfolioLedgerError as exc:
        _abort(str(exc))
        return
    render.render_pnl(rows)
