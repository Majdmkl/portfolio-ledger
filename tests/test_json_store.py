"""Tests for the JSON-backed Repository implementation."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from portfolio_ledger.domain.errors import (
    DuplicateInstrumentError,
    DuplicatePortfolioError,
)
from portfolio_ledger.domain.models import Instrument, Portfolio, Trade, TradeDirection
from portfolio_ledger.storage.json_store import JsonStore, SchemaVersionError


def make_portfolio(name: str = "Test Portfolio") -> Portfolio:
    return Portfolio(id=uuid4(), name=name, currency="SEK")


def make_instrument(portfolio_id, symbol: str = "AAPL") -> Instrument:
    return Instrument(
        id=uuid4(), symbol=symbol, name="Apple Inc.", portfolio_id=portfolio_id
    )


def make_trade(instrument_id, price: str = "100.00") -> Trade:
    return Trade(
        id=uuid4(),
        instrument_id=instrument_id,
        direction=TradeDirection.BUY,
        quantity=Decimal("10"),
        price=Decimal(price),
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
    )


# persistence


def test_portfolio_persists_across_store_instances(tmp_path: Path):
    path = tmp_path / "ledger.json"
    portfolio = make_portfolio()

    JsonStore(path).add_portfolio(portfolio)

    assert JsonStore(path).get_portfolio(portfolio.id) == portfolio


def test_instrument_persists_across_store_instances(tmp_path: Path):
    path = tmp_path / "ledger.json"
    portfolio = make_portfolio()
    instrument = make_instrument(portfolio.id)

    store = JsonStore(path)
    store.add_portfolio(portfolio)
    store.add_instrument(instrument)

    assert JsonStore(path).get_instrument(instrument.id) == instrument


def test_trade_persists_across_store_instances(tmp_path: Path):
    path = tmp_path / "ledger.json"
    portfolio = make_portfolio()
    instrument = make_instrument(portfolio.id)
    trade = make_trade(instrument.id)

    store = JsonStore(path)
    store.add_portfolio(portfolio)
    store.add_instrument(instrument)
    store.add_trade(trade)

    result = JsonStore(path).list_trades(instrument.id)
    assert len(result) == 1
    assert result[0].id == trade.id


# Decimal round-trip


def test_decimal_quantity_survives_json_round_trip(tmp_path: Path):
    path = tmp_path / "ledger.json"
    portfolio = make_portfolio()
    instrument = make_instrument(portfolio.id)
    trade = Trade(
        id=uuid4(),
        instrument_id=instrument.id,
        direction=TradeDirection.BUY,
        quantity=Decimal("123.456789"),
        price=Decimal("9.99"),
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
    )
    store = JsonStore(path)
    store.add_portfolio(portfolio)
    store.add_instrument(instrument)
    store.add_trade(trade)

    loaded = JsonStore(path).list_trades(instrument.id)[0]
    assert loaded.quantity == Decimal("123.456789")
    assert loaded.price == Decimal("9.99")


def test_decimal_stored_as_string_not_float(tmp_path: Path):
    path = tmp_path / "ledger.json"
    portfolio = make_portfolio()
    instrument = make_instrument(portfolio.id)
    trade = make_trade(instrument.id, price="185.50")

    store = JsonStore(path)
    store.add_portfolio(portfolio)
    store.add_instrument(instrument)
    store.add_trade(trade)

    raw = json.loads(path.read_text())
    stored_price = raw["trades"][0]["price"]
    assert isinstance(stored_price, str), "Decimal must be stored as string, not float"


# missing file


def test_missing_file_returns_empty_store(tmp_path: Path):
    store = JsonStore(tmp_path / "nonexistent.json")
    assert store.list_portfolios() == []


# schema version


def test_unknown_schema_version_raises_schema_version_error(tmp_path: Path):
    path = tmp_path / "ledger.json"
    path.write_text(
        '{"schema_version": 99, "portfolios": [], "instruments": [], "trades": []}'
    )
    with pytest.raises(SchemaVersionError):
        JsonStore(path)


# uniqueness constraints preserved


def test_duplicate_portfolio_name_raises_error(tmp_path: Path):
    path = tmp_path / "ledger.json"
    store = JsonStore(path)
    store.add_portfolio(make_portfolio(name="My Portfolio"))
    with pytest.raises(DuplicatePortfolioError):
        store.add_portfolio(make_portfolio(name="My Portfolio"))


def test_duplicate_instrument_symbol_raises_error(tmp_path: Path):
    path = tmp_path / "ledger.json"
    portfolio = make_portfolio()
    store = JsonStore(path)
    store.add_portfolio(portfolio)
    store.add_instrument(make_instrument(portfolio.id, symbol="AAPL"))
    with pytest.raises(DuplicateInstrumentError):
        store.add_instrument(make_instrument(portfolio.id, symbol="AAPL"))


# atomic write: no temp files left behind


def test_no_temporary_files_left_after_write(tmp_path: Path):
    path = tmp_path / "ledger.json"
    JsonStore(path).add_portfolio(make_portfolio())
    leftover = [f for f in tmp_path.iterdir() if f.suffix == ".tmp"]
    assert leftover == [], "Temporary write files must be cleaned up"


def test_file_contains_valid_json_after_write(tmp_path: Path):
    path = tmp_path / "ledger.json"
    JsonStore(path).add_portfolio(make_portfolio(name="Alpha"))
    data = json.loads(path.read_text())
    assert data["schema_version"] == 1
    assert data["portfolios"][0]["name"] == "Alpha"
