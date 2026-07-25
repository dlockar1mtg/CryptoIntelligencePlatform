from __future__ import annotations

import importlib

import pytest


REQUIRED_MODULES = [
    "duckdb",
    "pandas",
    "yaml",
    "requests",
    "dotenv",
    "sklearn",
    "joblib",
    "numpy",
    "scipy",
]


@pytest.mark.parametrize("module_name", REQUIRED_MODULES)
def test_required_dependency_imports(module_name: str) -> None:
    module = importlib.import_module(module_name)
    assert module is not None
