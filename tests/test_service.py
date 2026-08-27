"""Tests for record_trade validation in the service layer."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_ledger import service
from portfolio_ledger.domain.errors import InsufficientPositionError
from portfolio_ledger.domain.models import TradeDirection
from portfolio_ledger.storage.memory import MemoryRepository


def _make_repo() -> MemoryRepository:
    repo = MemoryRepository()
    service.create_portfolio(repo, "Test", "SEK")
    service.create_instrument(repo, "Test", "ACME", "Acme Corp")
    return repo


def _ts(day: int) -> datetime:
    return datetime(2024, 1, day, tzinfo=UTC)


def _buy(repo: MemoryRepository, qty: str, price: str, day: int) -> None:
    service.record_trade(
        repo,
        "Test",
        "ACME",
        TradeDirection.BUY,
        Decimal(qty),
        Decimal(price),
        _ts(day),
    )


def _sell(repo: MemoryRepository, qty: str, price: str, day: int) -> None:
    service.record_trade(
        repo,
        "Test",
        "ACME",
        TradeDirection.SELL,
        Decimal(qty),
        Decimal(price),
        _ts(day),
    )


def _trade_count(repo: MemoryRepository) -> int:
    portfolio = repo.get_portfolio_by_name("Test")
    assert portfolio is not None
    instrument = repo.get_instrument_by_symbol(portfolio.id, "ACME")
    assert instrument is not None
    return len(repo.list_trades(instrument.id))


def test_sell_over_holding_rejected_at_record_time():
    repo = _make_repo()
    _buy(repo, "10", "10", 10)
    with pytest.raises(InsufficientPositionError):
        _sell(repo, "11", "15", 20)


def test_rejected_trade_not_in_storage():
    repo = _make_repo()
    _buy(repo, "10", "10", 10)
    with pytest.raises(InsufficientPositionError):
        _sell(repo, "11", "15", 20)
    assert _trade_count(repo) == 1


def test_backdated_sell_that_invalidates_later_trade_is_rejected():
    repo = _make_repo()
    _buy(repo, "10", "10", 10)
    _sell(repo, "10", "15", 20)
    with pytest.raises(InsufficientPositionError):
        _sell(repo, "1", "12", 15)


def test_valid_backdated_trade_is_accepted():
    repo = _make_repo()
    _buy(repo, "10", "10", 10)
    _sell(repo, "5", "15", 20)
    _buy(repo, "5", "8", 15)
    assert _trade_count(repo) == 3
