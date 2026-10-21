"""DuckDB 2.0 refuses new work on a connection while a result is unfinished (even after
fetchone() on COUNT(*)), which this codebase does throughout. Stay on 1.x until migrated."""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]


def test_installed_duckdb_is_1x():
    assert int(duckdb.__version__.split(".")[0]) < 2


def test_requirements_cap_duckdb_below_2():
    line = next(l for l in (ROOT / "requirements.txt").read_text().splitlines() if l.strip().startswith("duckdb"))
    assert "<2" in line.replace(" ", "")
