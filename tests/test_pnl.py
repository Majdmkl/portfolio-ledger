"""Tests for the P&L calculation engine (weighted average cost basis)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from portfolio_ledger.domain.errors import InsufficientPositionError
from portfolio_ledger.domain.models import Trade, TradeDirection
from portfolio_ledger.domain.pnl import Position, calculate_position

INSTRUMENT_ID = uuid4()
SYMBOL = "AAPL"


def make_trade(
    direction: TradeDirection,
    quantity: str,
    price: str,
    timestamp: datetime | None = None,
) -> Trade:
    return Trade(
        id=uuid4(),
        instrument_id=INSTRUMENT_ID,
        direction=direction,
        quantity=Decimal(quantity),
        price=Decimal(price),
        timestamp=timestamp or datetime(2024, 1, 1, tzinfo=UTC),
    )


def calc(*trades: Trade) -> Position:
    """Convenience wrapper so tests read like a list of trades."""
    return calculate_position(INSTRUMENT_ID, SYMBOL, list(trades))


# empty input


def test_empty_trade_list_returns_zero_position():
    pos = calc()
    assert pos.quantity == Decimal("0")
    assert pos.average_cost == Decimal("0")
    assert pos.realized_pnl == Decimal("0")


# single buy


def test_single_buy_sets_quantity_and_average_cost():
    pos = calc(make_trade(TradeDirection.BUY, "10", "100.00"))
    assert pos.quantity == Decimal("10")
    assert pos.average_cost == Decimal("100.00")
    assert pos.realized_pnl == Decimal("0")


# weighted average across two buys


def test_two_buys_at_different_prices_produce_correct_weighted_average():
    # buy 100 @ 10 -> cost_basis 1000
    # buy  50 @ 16 -> cost_basis 1800 total; avg = 1800/150 = 12
    t1 = make_trade(
        TradeDirection.BUY, "100", "10.00", datetime(2024, 1, 1, tzinfo=UTC)
    )
    t2 = make_trade(TradeDirection.BUY, "50", "16.00", datetime(2024, 1, 2, tzinfo=UTC))
    pos = calc(t1, t2)
    assert pos.quantity == Decimal("150")
    assert pos.average_cost == Decimal("12")
    assert pos.realized_pnl == Decimal("0")


# sell after buy


def test_sell_reduces_quantity_and_records_realized_pnl():
    # buy 100 @ 10, sell 50 @ 15 -> realized = (15-10)*50 = 250
    t1 = make_trade(
        TradeDirection.BUY, "100", "10.00", datetime(2024, 1, 1, tzinfo=UTC)
    )
    t2 = make_trade(
        TradeDirection.SELL, "50", "15.00", datetime(2024, 1, 2, tzinfo=UTC)
    )
    pos = calc(t1, t2)
    assert pos.quantity == Decimal("50")
    assert pos.average_cost == Decimal("10.00")
    assert pos.realized_pnl == Decimal("250")


def test_sell_does_not_change_average_cost():
    t1 = make_trade(
        TradeDirection.BUY, "100", "10.00", datetime(2024, 1, 1, tzinfo=UTC)
    )
    t2 = make_trade(
        TradeDirection.SELL, "40", "20.00", datetime(2024, 1, 2, tzinfo=UTC)
    )
    pos = calc(t1, t2)
    assert pos.average_cost == Decimal("10.00")


# worked example matching docs/PNL.md
# buy 100 @ 10.00, buy 50 @ 16.00, sell 120 @ 20.00


def test_pnl_md_worked_example():
    t1 = make_trade(
        TradeDirection.BUY, "100", "10.00", datetime(2024, 1, 1, tzinfo=UTC)
    )
    t2 = make_trade(TradeDirection.BUY, "50", "16.00", datetime(2024, 1, 2, tzinfo=UTC))
    t3 = make_trade(
        TradeDirection.SELL, "120", "20.00", datetime(2024, 1, 3, tzinfo=UTC)
    )
    pos = calc(t1, t2, t3)
    # avg after two buys = (1000 + 800) / 150 = 12.00
    # realized = (20.00 - 12.00) * 120 = 960.00
    # remaining qty = 30, avg unchanged at 12.00
    assert pos.quantity == Decimal("30")
    assert pos.average_cost == Decimal("12")
    assert pos.realized_pnl == Decimal("960")
    assert pos.cost_basis() == Decimal("360")


# backdated trade: insertion order must not affect the result (domain rule 2)


def test_backdated_trade_inserted_last_produces_correct_position():
    t_jan = make_trade(
        TradeDirection.BUY, "100", "10.00", datetime(2024, 1, 1, tzinfo=UTC)
    )
    t_mar = make_trade(
        TradeDirection.BUY, "50", "16.00", datetime(2024, 3, 1, tzinfo=UTC)
    )
    # Feb sell inserted after March buy but timestamps place it between them.
    t_feb = make_trade(
        TradeDirection.SELL, "50", "20.00", datetime(2024, 2, 1, tzinfo=UTC)
    )

    pos_ordered = calc(t_jan, t_feb, t_mar)
    pos_backdated = calc(t_mar, t_feb, t_jan)  # same trades, different insertion order
    assert pos_ordered == pos_backdated


# short-sell guard (domain rule 4)


def test_sell_exceeding_position_raises_insufficient_position_error():
    t1 = make_trade(
        TradeDirection.BUY, "10", "100.00", datetime(2024, 1, 1, tzinfo=UTC)
    )
    t2 = make_trade(
        TradeDirection.SELL, "11", "100.00", datetime(2024, 1, 2, tzinfo=UTC)
    )
    with pytest.raises(InsufficientPositionError) as exc_info:
        calc(t1, t2)
    err = exc_info.value
    assert err.symbol == SYMBOL
    assert err.quantity_requested == Decimal("11")
    assert err.quantity_held == Decimal("10")


def test_sell_on_empty_position_raises_insufficient_position_error():
    t = make_trade(TradeDirection.SELL, "1", "100.00")
    with pytest.raises(InsufficientPositionError):
        calc(t)


# unrealized P&L


def test_unrealized_pnl_is_mark_minus_average_cost_times_quantity():
    pos = Position(
        instrument_id=INSTRUMENT_ID,
        quantity=Decimal("30"),
        average_cost=Decimal("12"),
        realized_pnl=Decimal("960"),
    )
    # From the PNL.md example: mark 22.00 -> (22-12)*30 = 300
    assert pos.unrealized_pnl(Decimal("22.00")) == Decimal("300.00")
