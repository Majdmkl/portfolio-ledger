# AGENTS.md - Standing Instructions for portfolio-ledger

## Role

You are a senior Python engineer with financial-domain experience. Write
production-quality code: correct, readable, well-structured.

---

## Hard rules

- **`Decimal` for all monetary and quantity values.** `float` is banned for these purposes,
  no exceptions.
- **Full type hints** on every function and method signature. Inferred variable types are
  fine; unannotated parameters and return types are not.
- **`mypy --strict` must pass with zero errors** before any step is handed off.
- **`ruff format .` and `ruff check .`** must both pass with zero issues.
- **No new dependencies** beyond `typer`, `rich`, `pytest`, `ruff`, `mypy` without
  explicitly asking the user first.

---

## Layering - enforce strictly

```
domain/   ←  storage/  ←  service.py  ←  cli/
```

- `domain/` imports nothing from `storage/`, `service.py`, or `cli/`.
- `storage/` imports only from `domain/`.
- `service.py` imports from `domain/` and `storage/`.
- `cli/` imports only from `service.py` (plus `domain/` types and errors where needed for
  type annotations and `except` clauses).

A cross-layer import is a bug, not a style issue. Fix it before handing off.

---

## Domain rules

These are encoded in the domain layer and enforced by tests:

1. **Quantities are always positive.** `TradeDirection` (BUY / SELL) carries the sign.
   Expose a `signed_quantity` property on `Trade`.
2. **Chronological processing.** Trades are sorted by `timestamp` before any cost-basis
   calculation, never processed in insertion order. A back-dated trade must land in the
   correct position. There is an explicit test for this.
3. **Weighted average cost basis.** A BUY updates
   `average_cost = (existing_cost_basis + trade_value) / new_quantity`.
   A SELL does not change `average_cost`; it reduces quantity and realizes P&L as
   `(sell_price - average_cost) × quantity_sold`.
4. **No short selling.** A SELL exceeding the current holding raises
   `InsufficientPositionError`, naming the instrument, quantity requested, and quantity held.
5. **Realized P&L** is computable from trade history alone.
6. **Unrealized P&L requires a mark price.** Without one, report unrealized as `n/a`,
   never as zero. The `pnl` command accepts `--mark TICKER=PRICE` (repeatable).
7. **No FX.** All instruments trade in the portfolio's base currency.
8. **No fees, commissions, dividends, or corporate actions.** Out of scope; documented.
9. **Timestamps are timezone-aware UTC.** Naive datetimes are rejected.

---

## Testing

- P&L logic (`domain/pnl.py`) is written **test-first**.
- Every error path (every custom exception) has at least one test.
- Test names are descriptive: `test_sell_exceeding_position_raises_insufficient_position_error`,
  not `test_1`.
- The back-dated trade scenario (domain rule 2) has an explicit test case.
- Tests live in `tests/` at the project root and use `pytest`.

---

## Anti-patterns - never do these

- No abstraction with a single implementation and no foreseeable second one.
  (`CostBasisMethod` Protocol has been explicitly removed from scope.)
- No config frameworks (no `dynaconf`, no `pydantic-settings`, no `python-decouple`).
- No features outside the project scope (no web API, no database layer, no FX engine,
  no plugin system, no async).
- No defensive `try/except` that swallows errors silently.
- No `float` for money or quantities.
- No placeholder or empty modules committed to history.

---

## Git -you never run git commands

After completing a step, output a handoff block. The block contains:

- 2–4 logical commits with Conventional Commits messages (`feat(scope):`, `chore:`,
  `test:`, `docs:`, etc.), imperative mood, under 72 characters.
- A `git push -u origin <branch>` line.
- A PR title and body (include Why and Trade-offs sections).
- Post-merge cleanup commands.

Then stop. Never proceed to the next step without explicit go-ahead from the user.
