"""JSON-backed Repository implementation with atomic writes.

Writes are atomic: data is serialised to a temporary file in the same
directory and then renamed into place with os.replace, which is atomic
on POSIX and best-effort on Windows.

Decimal values are stored as strings to avoid any floating-point loss.
All UUIDs and datetimes are stored as strings (ISO 8601 for datetimes).
"""

import json
import os
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from portfolio_ledger.domain.errors import (
    DuplicateInstrumentError,
    DuplicatePortfolioError,
    InstrumentNotFoundError,
    PortfolioNotFoundError,
)
from portfolio_ledger.domain.models import Instrument, Portfolio, Trade, TradeDirection

SCHEMA_VERSION = 1


class SchemaVersionError(Exception):
    """Raised when the data file was written by an incompatible schema version."""


class JsonStore:
    """Persistent Repository backed by a single JSON file.

    The entire dataset is loaded into memory at construction and written back
    atomically after every mutation. This is appropriate for the data volumes
    this assignment targets.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._portfolios: dict[UUID, Portfolio] = {}
        self._instruments: dict[UUID, Instrument] = {}
        self._trades: dict[UUID, Trade] = {}
        if path.exists():
            self._load()

    # internal I/O

    def _load(self) -> None:
        with self._path.open(encoding="utf-8") as f:
            # Any is the correct annotation for raw JSON: the structure is
            # validated manually below rather than through the type system.
            data: dict[str, Any] = json.load(f)

        version = data.get("schema_version")
        if version != SCHEMA_VERSION:
            raise SchemaVersionError(
                f"Unsupported schema version {version!r}. Expected {SCHEMA_VERSION}."
            )

        for raw in data.get("portfolios", []):
            p = Portfolio(
                id=UUID(raw["id"]),
                name=raw["name"],
                currency=raw["currency"],
            )
            self._portfolios[p.id] = p

        for raw in data.get("instruments", []):
            i = Instrument(
                id=UUID(raw["id"]),
                symbol=raw["symbol"],
                name=raw["name"],
                portfolio_id=UUID(raw["portfolio_id"]),
            )
            self._instruments[i.id] = i

        for raw in data.get("trades", []):
            t = Trade(
                id=UUID(raw["id"]),
                instrument_id=UUID(raw["instrument_id"]),
                direction=TradeDirection(raw["direction"]),
                quantity=Decimal(raw["quantity"]),
                price=Decimal(raw["price"]),
                timestamp=datetime.fromisoformat(raw["timestamp"]),
            )
            self._trades[t.id] = t

    def _save(self) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "portfolios": [
                {"id": str(p.id), "name": p.name, "currency": p.currency}
                for p in self._portfolios.values()
            ],
            "instruments": [
                {
                    "id": str(i.id),
                    "symbol": i.symbol,
                    "name": i.name,
                    "portfolio_id": str(i.portfolio_id),
                }
                for i in self._instruments.values()
            ],
            "trades": [
                {
                    "id": str(t.id),
                    "instrument_id": str(t.instrument_id),
                    "direction": t.direction.value,
                    "quantity": str(t.quantity),
                    "price": str(t.price),
                    "timestamp": t.timestamp.isoformat(),
                }
                for t in self._trades.values()
            ],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=self._path.parent,
            delete=False,
            suffix=".tmp",
            encoding="utf-8",
        ) as tmp:
            json.dump(payload, tmp, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, self._path)

    # portfolios

    def add_portfolio(self, portfolio: Portfolio) -> None:
        if any(p.name == portfolio.name for p in self._portfolios.values()):
            raise DuplicatePortfolioError(portfolio.name)
        self._portfolios[portfolio.id] = portfolio
        self._save()

    def get_portfolio(self, portfolio_id: UUID) -> Portfolio:
        try:
            return self._portfolios[portfolio_id]
        except KeyError:
            raise PortfolioNotFoundError(str(portfolio_id)) from None

    def get_portfolio_by_name(self, name: str) -> Portfolio | None:
        return next((p for p in self._portfolios.values() if p.name == name), None)

    def list_portfolios(self) -> list[Portfolio]:
        return sorted(self._portfolios.values(), key=lambda p: p.name)

    # instruments

    def add_instrument(self, instrument: Instrument) -> None:
        if any(
            i.portfolio_id == instrument.portfolio_id and i.symbol == instrument.symbol
            for i in self._instruments.values()
        ):
            raise DuplicateInstrumentError(instrument.symbol, instrument.portfolio_id)
        self._instruments[instrument.id] = instrument
        self._save()

    def get_instrument(self, instrument_id: UUID) -> Instrument:
        try:
            return self._instruments[instrument_id]
        except KeyError:
            raise InstrumentNotFoundError(str(instrument_id)) from None

    def get_instrument_by_symbol(
        self, portfolio_id: UUID, symbol: str
    ) -> Instrument | None:
        return next(
            (
                i
                for i in self._instruments.values()
                if i.portfolio_id == portfolio_id and i.symbol == symbol
            ),
            None,
        )

    def list_instruments(self, portfolio_id: UUID) -> list[Instrument]:
        return [i for i in self._instruments.values() if i.portfolio_id == portfolio_id]

    # trades

    def add_trade(self, trade: Trade) -> None:
        self._trades[trade.id] = trade
        self._save()

    def list_trades(self, instrument_id: UUID) -> list[Trade]:
        trades = [t for t in self._trades.values() if t.instrument_id == instrument_id]
        return sorted(trades, key=lambda t: t.timestamp)
