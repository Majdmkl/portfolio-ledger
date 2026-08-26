"""Repository Protocol: the storage interface both backends must satisfy.

New backend implementations (e.g. json_store) gain type-safety for free
because mypy verifies structural compatibility with this Protocol.
"""

from typing import Protocol
from uuid import UUID

from portfolio_ledger.domain.models import Instrument, Portfolio, Trade


class Repository(Protocol):
    """Read/write interface for portfolios, instruments, and trades.

    Uniqueness constraints all implementations must enforce:
      - Portfolio names are unique across the store.
      - Instrument symbols are unique within a portfolio.
    """

    def add_portfolio(self, portfolio: Portfolio) -> None: ...

    def get_portfolio(self, portfolio_id: UUID) -> Portfolio: ...

    def list_portfolios(self) -> list[Portfolio]: ...

    def add_instrument(self, instrument: Instrument) -> None: ...

    def get_instrument(self, instrument_id: UUID) -> Instrument: ...

    def list_instruments(self, portfolio_id: UUID) -> list[Instrument]: ...

    def add_trade(self, trade: Trade) -> None: ...

    def list_trades(self, instrument_id: UUID) -> list[Trade]: ...
