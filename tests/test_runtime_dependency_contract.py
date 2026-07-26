from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pytz_is_declared_as_production_dependency() -> None:
    requirements = (
        ROOT / "requirements.txt"
    ).read_text(encoding="utf-8").splitlines()

    declared = {
        line.strip().split(";", 1)[0].strip().lower()
        for line in requirements
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert any(
        requirement == "pytz"
        or requirement.startswith(
            (
                "pytz>",
                "pytz<",
                "pytz=",
                "pytz!",
                "pytz~",
            )
        )
        for requirement in declared
    )


def test_pytz_is_importable_in_runtime_environment() -> None:
    assert importlib.util.find_spec("pytz") is not None
