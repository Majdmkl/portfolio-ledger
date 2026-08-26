"""Application layer: use cases that orchestrate domain logic and storage.

Each function takes a Repository as its first argument so the CLI can swap
backends (memory vs. json_store) without any change here.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from portfolio_ledger.domain.errors import (
    InstrumentNotFoundError,
    PortfolioNotFoundError,
)
from portfolio_ledger.domain.models import Instrument, Portfolio, Trade, TradeDirection
from portfolio_ledger.domain.pnl import Position, calculate_position
from portfolio_ledger.storage.repository import Repository


def create_portfolio(repo: Repository, name: str, currency: str) -> Portfolio:
    portfolio = Portfolio(id=uuid4(), name=name, currency=currency.upper())
    repo.add_portfolio(portfolio)
    return portfolio


def list_portfolios(repo: Repository) -> list[Portfolio]:
    return repo.list_portfolios()


def _resolve_portfolio(repo: Repository, portfolio_name: str) -> Portfolio:
    """Look up a portfolio by name, raising PortfolioNotFoundError if absent."""
    portfolio = repo.get_portfolio_by_name(portfolio_name)
    if portfolio is None:
        raise PortfolioNotFoundError(portfolio_name)
    return portfolio


def _resolve_instrument(
    repo: Repository, portfolio_id: UUID, symbol: str
) -> Instrument:
    """Look up an instrument by symbol within a portfolio."""
    instrument = repo.get_instrument_by_symbol(portfolio_id, symbol.upper())
    if instrument is None:
        raise InstrumentNotFoundError(symbol.upper())
    return instrument


def create_instrument(
    repo: Repository, portfolio_name: str, symbol: str, name: str
) -> Instrument:
    portfolio = _resolve_portfolio(repo, portfolio_name)
    instrument = Instrument(
        id=uuid4(),
        symbol=symbol.upper(),
        name=name,
        portfolio_id=portfolio.id,
    )
    repo.add_instrument(instrument)
    return instrument


def list_instruments(repo: Repository, portfolio_name: str) -> list[Instrument]:
    portfolio = _resolve_portfolio(repo, portfolio_name)
    return repo.list_instruments(portfolio.id)


def record_trade(
    repo: Repository,
    portfolio_name: str,
    symbol: str,
    direction: TradeDirection,
    quantity: Decimal,
    price: Decimal,
    timestamp: datetime,
) -> Trade:
    portfolio = _resolve_portfolio(repo, portfolio_name)
    instrument = _resolve_instrument(repo, portfolio.id, symbol)
    trade = Trade(
        id=uuid4(),
        instrument_id=instrument.id,
        direction=direction,
        quantity=quantity,
        price=price,
        timestamp=timestamp,
    )
    repo.add_trade(trade)
    return trade


def list_trades(
    repo: Repository,
    portfolio_name: str,
    symbol: str | None = None,
) -> list[tuple[Trade, Instrument]]:
    """Return trades paired with their instrument, sorted by timestamp.

    If symbol is given, returns only trades for that instrument.
    Otherwise returns all trades across every instrument in the portfolio.
    """
    portfolio = _resolve_portfolio(repo, portfolio_name)

    if symbol is not None:
        instrument = _resolve_instrument(repo, portfolio.id, symbol)
        instruments = [instrument]
    else:
        instruments = repo.list_instruments(portfolio.id)

    pairs: list[tuple[Trade, Instrument]] = []
    for instrument in instruments:
        for trade in repo.list_trades(instrument.id):
            pairs.append((trade, instrument))

    return sorted(pairs, key=lambda p: p[0].timestamp)


def get_portfolio_pnl(
    repo: Repository,
    portfolio_name: str,
    marks: dict[str, Decimal],
) -> list[tuple[Instrument, Position, Decimal | None]]:
    """Return P&L for every instrument in a portfolio that has at least one trade.

    marks maps symbol -> mark price for unrealized P&L. Instruments without a
    mark entry get None, which the render layer shows as 'n/a' (never zero).
    """
    portfolio = _resolve_portfolio(repo, portfolio_name)
    result: list[tuple[Instrument, Position, Decimal | None]] = []
    for instrument in repo.list_instruments(portfolio.id):
        trades = repo.list_trades(instrument.id)
        if not trades:
            continue
        position = calculate_position(instrument.id, instrument.symbol, trades)
        mark = marks.get(instrument.symbol)
        result.append((instrument, position, mark))
    return result
