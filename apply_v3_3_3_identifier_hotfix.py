from __future__ import annotations

from pathlib import Path
import shutil
import yaml

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"

EXPECTED_CORE_IDS = [
    "bitcoin",
    "ethereum",
    "solana",
    "chainlink",
    "xrp",
    "avalanche",
]

def main() -> None:
    if not SETTINGS_PATH.exists():
        raise FileNotFoundError(
            f"Could not locate settings file: {SETTINGS_PATH}"
        )

    backup = SETTINGS_PATH.with_name(
        "settings_before_v3_3_3_identifier_hotfix.yaml"
    )
    if not backup.exists():
        shutil.copy2(SETTINGS_PATH, backup)
        print(f"Backup created: {backup}")
    else:
        print(f"Backup already exists: {backup}")

    settings = yaml.safe_load(
        SETTINGS_PATH.read_text(encoding="utf-8")
    )
    if not isinstance(settings, dict):
        raise RuntimeError("settings.yaml did not load as a mapping.")

    module13 = settings.setdefault("module13", {})
    recommendations = module13.setdefault("recommendations", {})

    previous = recommendations.get("core_asset_ids", [])
    recommendations["core_asset_ids"] = EXPECTED_CORE_IDS

    SETTINGS_PATH.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    print("Previous Module 13 core IDs:")
    for value in previous:
        print(f"  - {value}")

    print("Updated Module 13 core IDs:")
    for value in EXPECTED_CORE_IDS:
        print(f"  - {value}")

    reloaded = yaml.safe_load(
        SETTINGS_PATH.read_text(encoding="utf-8")
    )
    actual = (
        reloaded.get("module13", {})
        .get("recommendations", {})
        .get("core_asset_ids", [])
    )
    if actual != EXPECTED_CORE_IDS:
        raise RuntimeError(
            f"Identifier validation failed. Found: {actual}"
        )

    print("v3.3.3 identifier hotfix applied successfully.")
    print("Next command: python run_module13.py")

if __name__ == "__main__":
    main()
