"""CLI integration tests using Typer's CliRunner.

Every test passes --data-file pointing at a tmp_path file so no data
is written to the project root and tests are fully isolated.
"""

from pathlib import Path

from typer.testing import CliRunner

from portfolio_ledger.cli.app import app

runner = CliRunner()

_AT = "2024-01-10T09:00:00Z"
_AT2 = "2024-01-20T09:00:00Z"


def _df(tmp_path: Path) -> list[str]:
    return ["--data-file", str(tmp_path / "ledger.json")]


def _setup(tmp_path: Path) -> list[str]:
    """Create a portfolio and instrument; return --data-file args."""
    df = _df(tmp_path)
    runner.invoke(app, df + ["portfolio", "create", "Port"])
    runner.invoke(
        app,
        df + ["instrument", "create", "ACME", "Acme Corp", "--portfolio", "Port"],
    )
    return df


def test_happy_path_create_buy_pnl(tmp_path: Path) -> None:
    df = _setup(tmp_path)
    runner.invoke(
        app,
        df
        + [
            "trade",
            "record",
            "ACME",
            "BUY",
            "100",
            "10.00",
            "--portfolio",
            "Port",
            "--at",
            _AT,
        ],
    )
    result = runner.invoke(app, df + ["pnl", "--portfolio", "Port"])
    assert result.exit_code == 0
    assert "ACME" in result.output
    assert "1000.00" in result.output  # cost basis: 100 × 10.00


def test_sell_over_holding_rejected_message_names_instrument_and_quantities(
    tmp_path: Path,
) -> None:
    df = _setup(tmp_path)
    runner.invoke(
        app,
        df
        + [
            "trade",
            "record",
            "ACME",
            "BUY",
            "10",
            "10.00",
            "--portfolio",
            "Port",
            "--at",
            _AT,
        ],
    )
    result = runner.invoke(
        app,
        df
        + [
            "trade",
            "record",
            "ACME",
            "SELL",
            "11",
            "15.00",
            "--portfolio",
            "Port",
            "--at",
            _AT2,
        ],
    )
    assert result.exit_code != 0
    assert "ACME" in result.output  # instrument named
    assert "11" in result.output  # quantity requested
    assert "10" in result.output  # quantity held


def test_pnl_unknown_portfolio_clean_error_no_traceback(tmp_path: Path) -> None:
    df = _df(tmp_path)
    result = runner.invoke(app, df + ["pnl", "--portfolio", "Ghost"])
    assert result.exit_code != 0
    assert "Error:" in result.output
    assert "Traceback" not in result.output


def test_trade_record_unknown_instrument_clean_error(tmp_path: Path) -> None:
    df = _df(tmp_path)
    runner.invoke(app, df + ["portfolio", "create", "Port"])
    result = runner.invoke(
        app,
        df
        + [
            "trade",
            "record",
            "FAKE",
            "BUY",
            "10",
            "10.00",
            "--portfolio",
            "Port",
            "--at",
            _AT,
        ],
    )
    assert result.exit_code != 0
    assert "Error:" in result.output
    assert "Traceback" not in result.output


def test_duplicate_portfolio_clean_error(tmp_path: Path) -> None:
    df = _df(tmp_path)
    runner.invoke(app, df + ["portfolio", "create", "Port"])
    result = runner.invoke(app, df + ["portfolio", "create", "Port"])
    assert result.exit_code != 0
    assert "Error:" in result.output
    assert "Traceback" not in result.output


def test_pnl_without_mark_shows_na_with_mark_shows_unrealized(tmp_path: Path) -> None:
    df = _setup(tmp_path)
    runner.invoke(
        app,
        df
        + [
            "trade",
            "record",
            "ACME",
            "BUY",
            "100",
            "10.00",
            "--portfolio",
            "Port",
            "--at",
            _AT,
        ],
    )
    result_no_mark = runner.invoke(app, df + ["pnl", "--portfolio", "Port"])
    assert "n/a" in result_no_mark.output

    result_with_mark = runner.invoke(
        app, df + ["pnl", "--portfolio", "Port", "--mark", "ACME=15.00"]
    )
    assert "500.00" in result_with_mark.output  # unrealized: (15 - 10) × 100
    assert "n/a" not in result_with_mark.output
