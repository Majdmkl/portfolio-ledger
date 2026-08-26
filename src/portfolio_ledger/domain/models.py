"""Core domain models: Portfolio, Instrument, Trade.

These are plain frozen dataclasses with no I/O or persistence logic.
The domain layer imports nothing from storage, service, or cli.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class TradeDirection(StrEnum):
    """Whether a trade is a purchase or a sale.

    Inherits from str so members serialise transparently to/from JSON.
    """

    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Portfolio:
    """A named collection of instruments sharing a single base currency.

    All instruments in a portfolio trade in the same currency; there is no
    FX conversion (domain rule 7). currency is a label only, e.g. "SEK".
    """

    id: UUID
    name: str
    currency: str


@dataclass(frozen=True)
class Instrument:
    """A tradeable security that belongs to exactly one portfolio.

    symbol is the unique human-readable identifier used in the CLI and in
    mark-price lookups (e.g. "AAPL"). It must be unique within a portfolio.
    """

    id: UUID
    symbol: str
    name: str
    portfolio_id: UUID


@dataclass(frozen=True)
class Trade:
    """A single buy or sell event for one instrument.

    quantity is always a positive Decimal; direction carries the sign.
    Timestamps must be timezone-aware UTC; naive datetimes are rejected
    in __post_init__ to prevent silent ordering bugs (domain rule 2).
    """

    id: UUID
    instrument_id: UUID
    direction: TradeDirection
    quantity: Decimal
    price: Decimal
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")
        if self.price <= 0:
            raise ValueError(f"price must be positive, got {self.price}")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")

    @property
    def signed_quantity(self) -> Decimal:
        """Positive for BUY, negative for SELL. Use this in cost-basis arithmetic."""
        return self.quantity if self.direction is TradeDirection.BUY else -self.quantity

    @property
    def trade_value(self) -> Decimal:
        """Total consideration: quantity * price. Always positive."""
        return self.quantity * self.price
