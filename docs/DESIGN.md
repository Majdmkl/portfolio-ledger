# Design Notes

## Architecture

The codebase follows a strict four-layer dependency rule:

```
domain/   ←  storage/  ←  service.py  ←  cli/
```

Each layer may only import from layers to its left. A cross-layer import is
treated as a bug, not a style issue.

**`domain/`** — pure Python dataclasses and functions. No I/O, no framework
dependencies. Contains the data models (`Portfolio`, `Instrument`, `Trade`),
all custom exceptions, and the P&L calculation logic. This layer can be tested
and reasoned about in complete isolation.

**`storage/`** — persistence implementations behind a `Repository` Protocol.
Two implementations exist: `MemoryRepository` (in-memory dict, used in all
unit tests) and `JsonStore` (single JSON file, used in production). Adding a
third backend — SQLite, Postgres, etc. — requires no changes to any other
layer.

**`service.py`** — application use cases. Orchestrates domain objects and
storage calls. Accepts a `Repository` at the call site so tests can inject the
memory backend without touching the file system.

**`cli/`** — Typer application. Parses arguments, calls service functions,
renders output with Rich. Does not contain any business logic.

## Why `Decimal`, not `float`

IEEE 754 floating-point cannot represent many decimal fractions exactly.
`0.1 + 0.2 != 0.3` in Python (and every other language using binary floats).
For financial calculations, rounding errors accumulate across trades and
produce wrong P&L figures.

`decimal.Decimal` uses base-10 arithmetic with configurable precision.
`Decimal("0.1") + Decimal("0.2") == Decimal("0.3")` is `True`. All monetary
and quantity values in this project are `Decimal` from the moment they enter
the system. `float` is entirely absent.

In the JSON store, `Decimal` values are serialised as strings (`"185.50"` not
`185.5`) to survive the JSON round-trip without any floating-point conversion.

## Why weighted average cost basis (genomsnittsmetoden)

Swedish tax law (Skatteverket) requires the weighted average method for equity
holdings. FIFO would produce different realized P&L figures and is therefore
incorrect for this use case.

The method: each BUY blends the new trade value into the running average cost.
A SELL does not change the average cost — it reduces quantity and crystallises
realized P&L at the spread between the sell price and the current average cost.
See [`PNL.md`](PNL.md) for a worked numerical example.

## Repository Protocol

`storage/repository.py` defines a `typing.Protocol` that both
`MemoryRepository` and `JsonStore` satisfy structurally (no explicit
`implements` or base class needed). This means:

- Unit tests use `MemoryRepository` — fast, no I/O, no tmp files.
- The CLI uses `JsonStore` — durable, atomic writes.
- `service.py` is oblivious to which one it receives.

The Protocol has a single implementation pair today, but the abstraction is not
premature: the two backends already exist and are tested independently. A
future SQLite or HTTP backend would slot in without changing the service layer.

## Atomic JSON writes

`JsonStore._save()` never writes directly to the target file. It writes to a
temporary file in the same directory, then calls `os.replace(tmp, target)`.
`os.replace` is atomic on POSIX (rename syscall) and best-effort on Windows.

Consequence: a crash or power loss mid-write leaves the previous complete file
intact. There is never a partial or corrupt data file.

The file is always fully rewritten on every mutation. This is appropriate for
the data volumes this project targets (hundreds of trades). For larger datasets
an append-log or proper database would be preferable.

## `mypy --strict` as quality gate

All code passes `mypy --strict` with zero errors. This catches an entire class
of bugs at development time: wrong argument types, missing `None` checks,
unannotated return types. The CI pipeline blocks merges on mypy failures.

`py.typed` (PEP 561) is included so mypy resolves the package correctly when
it is installed as an editable package alongside the source tree.

## Typer + Rich

Typer handles argument parsing and generates `--help` text automatically from
type annotations and docstrings. Rich renders coloured tables: realized P&L is
green when positive, red when negative.

Trade-off: Rich tables are not machine-readable. A `--output json` flag would
make the CLI composable with other tools (e.g. `jq`). This was considered out
of scope for the assignment.
