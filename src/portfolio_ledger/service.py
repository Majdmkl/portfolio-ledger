"""Application layer: use cases that orchestrate domain logic and storage.

Each function takes a Repository as its first argument so the CLI can swap
backends (memory vs. json_store) without any change here.
"""

from uuid import uuid4

from portfolio_ledger.domain.errors import PortfolioNotFoundError
from portfolio_ledger.domain.models import Instrument, Portfolio
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
