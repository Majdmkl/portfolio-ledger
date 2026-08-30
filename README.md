# portfolio-ledger

A command-line tool for recording investment trades and computing realized and
unrealized P&L using the weighted average cost basis method
(genomsnittsmetoden).

---

## What this project does

`portfolio-ledger` lets you:

- Create named **portfolios** with a base currency.
- Register **instruments** (stocks, ETFs, etc.) within a portfolio by ticker
  symbol and full name.
- **Record buy and sell trades** with an exact timestamp, quantity, and price.
- View **realized and unrealized P&L** per instrument, including a portfolio
  total row.

Everything is persisted to a single JSON file. The data file is written
atomically (temp file + rename) so a crash mid-write never corrupts it.

**Out of scope by design:** FX conversion, fees/commissions, dividends,
corporate actions, short selling, and any network or web-API layer.

---

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/MajdMkl/portfolio-ledger.git
cd portfolio-ledger
pip install -e ".[dev]"
```

This installs the `pledger` entry point and all development tools (pytest,
mypy, ruff).

---

## Usage

All commands accept `--data-file PATH` (or the `PORTFOLIO_LEDGER_DATA`
environment variable) to specify where data is stored. Default:
`portfolio_ledger_data.json` in the working directory.

### Portfolios

```
$ pledger portfolio create "Demo" --currency SEK
Created portfolio 'Demo' (SEK) [dad3a0ca-f983-4b23-a500-fe6351d1e873]

$ pledger portfolio list
┏━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name ┃ Currency ┃ ID                                   ┃
┡━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Demo │ SEK      │ dad3a0ca-f983-4b23-a500-fe6351d1e873 │
└──────┴──────────┴──────────────────────────────────────┘
```

### Instruments

```
$ pledger instrument create SINCH "Sinch AB" --portfolio "Demo"
Created instrument 'SINCH' (Sinch AB) [65372ba4-4aa7-481c-8ff0-5a9562fb7be3]

$ pledger instrument list --portfolio "Demo"
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Symbol ┃ Name     ┃ ID                                   ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ SINCH  │ Sinch AB │ 65372ba4-4aa7-481c-8ff0-5a9562fb7be3 │
└────────┴──────────┴──────────────────────────────────────┘
```

### Trades

```
$ pledger trade record SINCH BUY 100 10.00 --portfolio "Demo" --at 2024-01-10T09:00:00Z
Recorded BUY 100 SINCH @ 10.00 on 2024-01-10 09:00 UTC

$ pledger trade record SINCH BUY 50 16.00 --portfolio "Demo" --at 2024-01-20T09:00:00Z
Recorded BUY 50 SINCH @ 16.00 on 2024-01-20 09:00 UTC

$ pledger trade record SINCH SELL 120 20.00 --portfolio "Demo" --at 2024-02-01T09:00:00Z
Recorded SELL 120 SINCH @ 20.00 on 2024-02-01 09:00 UTC

$ pledger trade list --portfolio "Demo"
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┓
┃ Date (UTC)       ┃ Symbol ┃ Direction ┃ Quantity ┃ Price ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━┩
│ 2024-01-10 09:00 │ SINCH  │ BUY       │      100 │ 10.00 │
│ 2024-01-20 09:00 │ SINCH  │ BUY       │       50 │ 16.00 │
│ 2024-02-01 09:00 │ SINCH  │ SELL      │      120 │ 20.00 │
└──────────────────┴────────┴───────────┴──────────┴───────┘
```

### P&L

```
$ pledger pnl --portfolio "Demo"
┏━━━━━━━━┳━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃        ┃     ┃          ┃            ┃    Realized ┃  Unrealized ┃           ┃
┃ Symbol ┃ Qty ┃ Avg Cost ┃ Cost Basis ┃         P&L ┃         P&L ┃ Total P&L ┃
┡━━━━━━━━╇━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ SINCH  │  30 │    12.00 │     360.00 │      960.00 │         n/a │       n/a │
├────────┼─────┼──────────┼────────────┼─────────────┼─────────────┼───────────┤
│ TOTAL  │     │          │            │      960.00 │         n/a │       n/a │
└────────┴─────┴──────────┴────────────┴─────────────┴─────────────┴───────────┘

$ pledger pnl --portfolio "Demo" --mark SINCH=22.00
┏━━━━━━━━┳━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃        ┃     ┃          ┃            ┃    Realized ┃  Unrealized ┃           ┃
┃ Symbol ┃ Qty ┃ Avg Cost ┃ Cost Basis ┃         P&L ┃         P&L ┃ Total P&L ┃
┡━━━━━━━━╇━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ SINCH  │  30 │    12.00 │     360.00 │      960.00 │      300.00 │   1260.00 │
├────────┼─────┼──────────┼────────────┼─────────────┼─────────────┼───────────┤
│ TOTAL  │     │          │            │      960.00 │      300.00 │   1260.00 │
└────────┴─────┴──────────┴────────────┴─────────────┴─────────────┴───────────┘
```

Realized P&L is green when positive, red when negative. Unrealized P&L shows
`n/a` when no mark price is supplied, never zero, which would be misleading.

---

## Data model

```
Portfolio  (id, name, currency)
    └── Instrument  (id, symbol, name, portfolio_id)
            └── Trade  (id, instrument_id, direction, quantity, price, timestamp)
```

Data is stored in a single JSON file with `schema_version: 1` at the root.
All `Decimal` values are serialised as strings to preserve exact precision.
All UUIDs and datetimes are stored as strings (ISO 8601 for datetimes).

---

## P&L model and assumptions

Cost basis method: **weighted average** (genomsnittsmetoden), the standard
method required by Swedish tax law (Skatteverket) for equity holdings.

Rules encoded in the domain layer:

- **Quantities are always positive.** Direction (BUY / SELL) carries the sign.
- **Buys update the average cost.** Selling does not change it; only subsequent
  buys blend the cost basis.
- **Short selling is rejected.** A SELL exceeding the current holding raises
  `InsufficientPositionError`.
- **Timestamps are timezone-aware UTC.** Naive datetimes are rejected at the
  model level.
- **Trades are sorted chronologically before processing.** A back-dated trade
  always lands in the correct slot.
- **No FX.** All instruments trade in the portfolio's base currency.
- **No fees, dividends, or corporate actions.** Out of scope; documented.

For the worked numerical example see [`docs/PNL.md`](docs/PNL.md).

---

## Design decisions and trade-offs

See [`docs/DESIGN.md`](docs/DESIGN.md) for the full discussion.

Short version:

| Decision | Choice | Main trade-off |
|---|---|---|
| Persistence | Single JSON file, atomic write | Simple; not suitable for concurrent writers |
| Cost basis | Weighted average (genomsnittsmetoden) | Correct for Swedish tax law; FIFO not implemented |
| Type safety | `mypy --strict` + `Decimal` throughout | Verbose generic signatures; no float anywhere |
| CLI framework | Typer + Rich | Good DX; Rich tables not scriptable (no `--json` flag) |
| Architecture | Four-layer with Protocol interface | Testable; memory backend used in all unit tests |

---

## Known limitations

- **Negative numbers as positional arguments** require a `--` separator, e.g.
  `pledger trade record SINCH BUY -- -10 5.00`. Without it the shell
  interprets `-10` as a flag and produces a confusing error message.
- **Read-only commands against a non-writable path** appear to succeed silently.
  `pledger portfolio list --data-file /read-only/path.json` returns an empty
  list rather than a permission error, because no write is attempted until a
  mutation occurs.

---

## What was not built and why

| Feature | Reason |
|---|---|
| FX conversion | Out of scope; all instruments in one currency |
| Fees / commissions | Not required; would complicate cost-basis math |
| Dividends / corporate actions | Not required |
| Web / REST API | Explicitly out of scope |
| Database backend | JSON file is sufficient for stated data volumes |
| FIFO cost basis | Not required; Swedish law mandates weighted average |
| `--output json` flag | Not required; Rich tables are human-readable |

---

## Given more time, I would...

- Add a `--output json` flag so the CLI can be piped into other tools.
- Replace the full-file rewrite on every mutation with a proper append-log or
  SQLite backend once data volumes grow.
- Add import from CSV / brokerage export format (e.g. Avanza, Nordnet).
- Add a `portfolio delete` and `instrument delete` command with a confirmation
  prompt.
- Implement FIFO cost basis as an optional `--method fifo` flag alongside
  weighted average.
- Add FX support: store the exchange rate at time of trade, report P&L in a
  chosen reporting currency.

---

## Development

```bash
# Run the test suite
pytest

# Type-check
mypy src

# Lint and format
ruff check .
ruff format .
```

CI runs all four checks on every push via GitHub Actions
(`.github/workflows/ci.yml`).

This project was developed with AI assistance (Claude Code by Anthropic).
Data model design, P&L calculation method, architectural decisions, and
all explicit instructions to the AI agent are the author's own.
