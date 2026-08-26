"""Domain exception hierarchy.

All custom exceptions inherit from PortfolioLedgerError so callers can
catch the entire family with a single clause when needed.
"""

from decimal import Decimal


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
