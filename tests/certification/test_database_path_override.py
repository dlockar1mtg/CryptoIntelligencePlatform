from __future__ import annotations

from pathlib import Path

from crypto_platform.platform import ROOT, path_for


def settings(database_path: str) -> dict[str, object]:
    return {
        "platform": {
            "database_path": database_path,
            "log_directory": "logs",
        }
    }


def test_configured_relative_database_path_uses_repository_root(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "CRYPTO_DATABASE_PATH",
        raising=False,
    )

    result = path_for(
        settings("data/crypto_intelligence.duckdb"),
        "database_path",
    )

    assert result == ROOT / "data/crypto_intelligence.duckdb"


def test_absolute_configured_database_path_is_preserved(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(
        "CRYPTO_DATABASE_PATH",
        raising=False,
    )

    configured = tmp_path / "configured.duckdb"

    result = path_for(
        settings(str(configured)),
        "database_path",
    )

    assert result == configured


def test_database_environment_override_takes_precedence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configured = "data/crypto_intelligence.duckdb"
    override = tmp_path / "historical_replay.duckdb"

    monkeypatch.setenv(
        "CRYPTO_DATABASE_PATH",
        str(override),
    )

    result = path_for(
        settings(configured),
        "database_path",
    )

    assert result == override.resolve()


def test_database_override_does_not_change_other_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    override = tmp_path / "historical_replay.duckdb"

    monkeypatch.setenv(
        "CRYPTO_DATABASE_PATH",
        str(override),
    )

    result = path_for(
        settings("data/crypto_intelligence.duckdb"),
        "log_directory",
    )

    assert result == ROOT / "logs"


def test_blank_database_override_is_ignored(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "CRYPTO_DATABASE_PATH",
        "   ",
    )

    result = path_for(
        settings("data/crypto_intelligence.duckdb"),
        "database_path",
    )

    assert result == ROOT / "data/crypto_intelligence.duckdb"