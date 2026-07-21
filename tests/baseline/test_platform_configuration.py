from __future__ import annotations

from pathlib import Path

import yaml


SETTINGS_PATH = Path("config/settings.yaml")


def test_settings_file_exists() -> None:
    assert SETTINGS_PATH.is_file()


def test_platform_version_is_v13() -> None:
    with SETTINGS_PATH.open("r", encoding="utf-8") as handle:
        settings = yaml.safe_load(handle)

    assert isinstance(settings, dict)

    platform = settings.get("platform", {})
    assert str(platform.get("version")) == "13.0.0"
