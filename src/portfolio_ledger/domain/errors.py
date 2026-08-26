"""Domain exception hierarchy.

All custom exceptions inherit from PortfolioLedgerError so callers can
catch the entire family with a single clause when needed.
"""

from decimal import Decimal
from uuid import UUID


class PortfolioLedgerError(Exception):
    """Base class for all portfolio-ledger domain errors."""


class InsufficientPositionError(PortfolioLedgerError):
    """Raised when a sell order exceeds the current holding for an instrument.

    Short selling is out of scope; this error is the explicit enforcement point
    for that boundary (domain rule 4).
    """

    def __init__(
        self,
        symbol: str,
        quantity_requested: Decimal,
        quantity_held: Decimal,
    ) -> None:
        self.symbol = symbol
        self.quantity_requested = quantity_requested
        self.quantity_held = quantity_held
        super().__init__(
            f"Cannot sell {quantity_requested} of {symbol}: only {quantity_held} held"
        )


class PortfolioNotFoundError(PortfolioLedgerError):
    """Raised when a portfolio ID does not match any stored portfolio."""

    def __init__(self, portfolio_id: UUID) -> None:
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio not found: {portfolio_id}")


class DuplicatePortfolioError(PortfolioLedgerError):
    """Raised when adding a portfolio whose name is already in use."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Portfolio already exists: {name!r}")


class InstrumentNotFoundError(PortfolioLedgerError):
    """Raised when an instrument ID does not match any stored instrument."""

    def __init__(self, instrument_id: UUID) -> None:
        self.instrument_id = instrument_id
        super().__init__(f"Instrument not found: {instrument_id}")


class DuplicateInstrumentError(PortfolioLedgerError):
    """Raised when adding an instrument whose symbol already exists in the portfolio."""

    def __init__(self, symbol: str, portfolio_id: UUID) -> None:
        self.symbol = symbol
        self.portfolio_id = portfolio_id
        super().__init__(
            f"Instrument {symbol!r} already exists in portfolio {portfolio_id}"
        )
