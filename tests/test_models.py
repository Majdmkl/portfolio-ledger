"""Tests for domain models and the InsufficientPositionError exception."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from portfolio_ledger.domain.errors import InsufficientPositionError
from portfolio_ledger.domain.models import Trade, TradeDirection


def make_trade(**overrides):
    """Return a valid Trade, applying any field overrides."""
    defaults = dict(
        id=uuid4(),
        instrument_id=uuid4(),
        direction=TradeDirection.BUY,
        quantity=Decimal("10"),
        price=Decimal("100.00"),
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
    )
    return Trade(**{**defaults, **overrides})


# signed_quantity


def test_buy_signed_quantity_is_positive():
    trade = make_trade(direction=TradeDirection.BUY, quantity=Decimal("5"))
    assert trade.signed_quantity == Decimal("5")


def test_sell_signed_quantity_is_negative():
    trade = make_trade(direction=TradeDirection.SELL, quantity=Decimal("5"))
    assert trade.signed_quantity == Decimal("-5")


# trade_value


def test_trade_value_is_quantity_times_price():
    trade = make_trade(quantity=Decimal("10"), price=Decimal("25.50"))
    assert trade.trade_value == Decimal("255.00")


# quantity validation


def test_zero_quantity_raises_value_error():
    with pytest.raises(ValueError, match="quantity must be positive"):
        make_trade(quantity=Decimal("0"))


def test_negative_quantity_raises_value_error():
    with pytest.raises(ValueError, match="quantity must be positive"):
        make_trade(quantity=Decimal("-1"))


# price validation


def test_zero_price_raises_value_error():
    with pytest.raises(ValueError, match="price must be positive"):
        make_trade(price=Decimal("0"))


def test_negative_price_raises_value_error():
    with pytest.raises(ValueError, match="price must be positive"):
        make_trade(price=Decimal("-5"))


# timestamp validation


def test_naive_timestamp_raises_value_error():
    with pytest.raises(ValueError, match="timezone-aware"):
        make_trade(timestamp=datetime(2024, 1, 1))


# InsufficientPositionError


def test_insufficient_position_error_carries_correct_attributes():
    err = InsufficientPositionError(
        symbol="AAPL",
        quantity_requested=Decimal("50"),
        quantity_held=Decimal("30"),
    )
    assert err.symbol == "AAPL"
    assert err.quantity_requested == Decimal("50")
    assert err.quantity_held == Decimal("30")


def test_insufficient_position_error_message_names_instrument_and_quantities():
    err = InsufficientPositionError(
        symbol="AAPL",
        quantity_requested=Decimal("50"),
        quantity_held=Decimal("30"),
    )
    message = str(err)
    assert "AAPL" in message
    assert "50" in message
    assert "30" in message
