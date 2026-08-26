"""P&L calculation using the weighted average cost basis method (genomsnittsmetoden).

All functions are pure: no I/O, no side effects. The service layer is
responsible for fetching trades and assembling portfolio-level summaries.
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from portfolio_ledger.domain.errors import InsufficientPositionError
from portfolio_ledger.domain.models import Trade, TradeDirection


@dataclass(frozen=True)
class Position:
    """The result of processing all trades for a single instrument.

    average_cost is the per-unit weighted average cost of the current holding.
    It is preserved after a full sell so that the invariant
    cost_basis == quantity * average_cost always holds; a subsequent buy
    naturally resets it via the weighted-average formula.
    """

    instrument_id: UUID
    quantity: Decimal  # current holding, always >= 0
    average_cost: Decimal  # per-unit cost (genomsnittsmetoden)
    realized_pnl: Decimal  # cumulative realized P&L from all sell trades

    def unrealized_pnl(self, mark_price: Decimal) -> Decimal:
        """Mark-to-market gain or loss at the given price."""
        return (mark_price - self.average_cost) * self.quantity

    def cost_basis(self) -> Decimal:
        """Total cost of the current holding: quantity * average_cost."""
        return self.quantity * self.average_cost


def calculate_position(
    instrument_id: UUID, symbol: str, trades: list[Trade]
) -> Position:
    """Process trades chronologically and return the resulting Position.

    Trades are sorted by timestamp before processing so insertion order
    never affects the result (domain rule 2). A backdated trade added later
    will correctly land in its chronological slot.

    Raises InsufficientPositionError if any sell exceeds the current holding.
    Short selling is out of scope (domain rule 4).
    """
    quantity = Decimal("0")
    average_cost = Decimal("0")
    realized_pnl = Decimal("0")

    for trade in sorted(trades, key=lambda t: t.timestamp):
        if trade.direction is TradeDirection.BUY:
            new_quantity = quantity + trade.quantity
            # Weighted average: blend existing cost basis with new trade value.
            average_cost = (quantity * average_cost + trade.trade_value) / new_quantity
            quantity = new_quantity
        else:
            if trade.quantity > quantity:
                raise InsufficientPositionError(
                    symbol=symbol,
                    quantity_requested=trade.quantity,
                    quantity_held=quantity,
                )
            realized_pnl += (trade.price - average_cost) * trade.quantity
            quantity -= trade.quantity

    return Position(
        instrument_id=instrument_id,
        quantity=quantity,
        average_cost=average_cost,
        realized_pnl=realized_pnl,
    )
