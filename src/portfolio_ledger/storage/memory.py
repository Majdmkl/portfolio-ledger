"""In-memory Repository implementation.

Used in tests and as the active backend until json_store is wired up.
All operations are O(n) over trades/instruments; acceptable for the
data volumes this assignment targets.
"""

from uuid import UUID

from portfolio_ledger.domain.errors import (
    DuplicateInstrumentError,
    DuplicatePortfolioError,
    InstrumentNotFoundError,
    PortfolioNotFoundError,
)
from portfolio_ledger.domain.models import Instrument, Portfolio, Trade


class MemoryRepository:
    """Thread-unsafe in-memory store backed by plain dicts."""

    def __init__(self) -> None:
        self._portfolios: dict[UUID, Portfolio] = {}
        self._instruments: dict[UUID, Instrument] = {}
        self._trades: dict[UUID, Trade] = {}

    # portfolios

    def add_portfolio(self, portfolio: Portfolio) -> None:
        if any(p.name == portfolio.name for p in self._portfolios.values()):
            raise DuplicatePortfolioError(portfolio.name)
        self._portfolios[portfolio.id] = portfolio

    def get_portfolio(self, portfolio_id: UUID) -> Portfolio:
        try:
            return self._portfolios[portfolio_id]
        except KeyError:
            raise PortfolioNotFoundError(portfolio_id) from None

    def list_portfolios(self) -> list[Portfolio]:
        return sorted(self._portfolios.values(), key=lambda p: p.name)

    # instruments

    def add_instrument(self, instrument: Instrument) -> None:
        # Symbol must be unique within a portfolio; the same symbol in a
        # different portfolio is intentionally allowed.
        if any(
            i.portfolio_id == instrument.portfolio_id and i.symbol == instrument.symbol
            for i in self._instruments.values()
        ):
            raise DuplicateInstrumentError(instrument.symbol, instrument.portfolio_id)
        self._instruments[instrument.id] = instrument

    def get_instrument(self, instrument_id: UUID) -> Instrument:
        try:
            return self._instruments[instrument_id]
        except KeyError:
            raise InstrumentNotFoundError(instrument_id) from None

    def list_instruments(self, portfolio_id: UUID) -> list[Instrument]:
        return [i for i in self._instruments.values() if i.portfolio_id == portfolio_id]

    # trades

    def add_trade(self, trade: Trade) -> None:
        self._trades[trade.id] = trade

    def list_trades(self, instrument_id: UUID) -> list[Trade]:
        """Return trades for the given instrument sorted by timestamp (ascending)."""
        trades = [t for t in self._trades.values() if t.instrument_id == instrument_id]
        return sorted(trades, key=lambda t: t.timestamp)
