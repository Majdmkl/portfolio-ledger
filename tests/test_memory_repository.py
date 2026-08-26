"""Tests for the in-memory Repository implementation."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from portfolio_ledger.domain.errors import (
    DuplicateInstrumentError,
    DuplicatePortfolioError,
    InstrumentNotFoundError,
    PortfolioNotFoundError,
)
from portfolio_ledger.domain.models import Instrument, Portfolio, Trade, TradeDirection
from portfolio_ledger.storage.memory import MemoryRepository

# helpers


def make_portfolio(name: str = "Test Portfolio") -> Portfolio:
    return Portfolio(id=uuid4(), name=name, currency="SEK")


def make_instrument(portfolio_id, symbol: str = "AAPL") -> Instrument:
    return Instrument(
        id=uuid4(), symbol=symbol, name="Apple Inc.", portfolio_id=portfolio_id
    )


def make_trade(instrument_id, timestamp: datetime | None = None) -> Trade:
    return Trade(
        id=uuid4(),
        instrument_id=instrument_id,
        direction=TradeDirection.BUY,
        quantity=Decimal("10"),
        price=Decimal("100.00"),
        timestamp=timestamp or datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def repo() -> MemoryRepository:
    return MemoryRepository()


# portfolios


def test_add_and_retrieve_portfolio(repo):
    portfolio = make_portfolio()
    repo.add_portfolio(portfolio)
    assert repo.get_portfolio(portfolio.id) == portfolio


def test_duplicate_portfolio_name_raises_error(repo):
    repo.add_portfolio(make_portfolio(name="My Portfolio"))
    with pytest.raises(DuplicatePortfolioError):
        repo.add_portfolio(make_portfolio(name="My Portfolio"))


def test_unknown_portfolio_id_raises_not_found_error(repo):
    with pytest.raises(PortfolioNotFoundError):
        repo.get_portfolio(uuid4())


def test_list_portfolios_is_sorted_by_name(repo):
    repo.add_portfolio(make_portfolio(name="Zebra Fund"))
    repo.add_portfolio(make_portfolio(name="Alpha Fund"))
    repo.add_portfolio(make_portfolio(name="Mid Fund"))
    names = [p.name for p in repo.list_portfolios()]
    assert names == ["Alpha Fund", "Mid Fund", "Zebra Fund"]


# instruments


def test_add_and_retrieve_instrument(repo):
    portfolio = make_portfolio()
    repo.add_portfolio(portfolio)
    instrument = make_instrument(portfolio.id)
    repo.add_instrument(instrument)
    assert repo.get_instrument(instrument.id) == instrument


def test_duplicate_symbol_in_same_portfolio_raises_error(repo):
    portfolio = make_portfolio()
    repo.add_portfolio(portfolio)
    repo.add_instrument(make_instrument(portfolio.id, symbol="AAPL"))
    with pytest.raises(DuplicateInstrumentError):
        repo.add_instrument(make_instrument(portfolio.id, symbol="AAPL"))


def test_same_symbol_in_different_portfolio_is_allowed(repo):
    p1 = make_portfolio(name="Portfolio A")
    p2 = make_portfolio(name="Portfolio B")
    repo.add_portfolio(p1)
    repo.add_portfolio(p2)
    repo.add_instrument(make_instrument(p1.id, symbol="AAPL"))
    repo.add_instrument(make_instrument(p2.id, symbol="AAPL"))  # must not raise


def test_unknown_instrument_id_raises_not_found_error(repo):
    with pytest.raises(InstrumentNotFoundError):
        repo.get_instrument(uuid4())


def test_list_instruments_returns_only_instruments_in_portfolio(repo):
    p1 = make_portfolio(name="Portfolio A")
    p2 = make_portfolio(name="Portfolio B")
    repo.add_portfolio(p1)
    repo.add_portfolio(p2)
    i1 = make_instrument(p1.id, symbol="AAPL")
    i2 = make_instrument(p2.id, symbol="MSFT")
    repo.add_instrument(i1)
    repo.add_instrument(i2)
    assert repo.list_instruments(p1.id) == [i1]


# trades


def test_list_trades_sorted_by_timestamp_regardless_of_insertion_order(repo):
    """Backdated trade inserted last must appear first in the result (domain rule 2)."""
    portfolio = make_portfolio()
    repo.add_portfolio(portfolio)
    instrument = make_instrument(portfolio.id)
    repo.add_instrument(instrument)

    t_march = make_trade(instrument.id, timestamp=datetime(2024, 3, 1, tzinfo=UTC))
    t_jan = make_trade(instrument.id, timestamp=datetime(2024, 1, 1, tzinfo=UTC))
    t_feb = make_trade(instrument.id, timestamp=datetime(2024, 2, 1, tzinfo=UTC))

    # Insert out of chronological order; t_jan is the backdated trade.
    repo.add_trade(t_march)
    repo.add_trade(t_jan)
    repo.add_trade(t_feb)

    assert repo.list_trades(instrument.id) == [t_jan, t_feb, t_march]
