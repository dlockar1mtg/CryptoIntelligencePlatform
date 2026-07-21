from pathlib import Path
import shutil
import yaml

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


def main() -> None:
    if not SETTINGS.exists():
        raise FileNotFoundError(f"Missing settings: {SETTINGS}")

    backup = SETTINGS.with_name("settings_before_v7_3_1.yaml")
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(SETTINGS.read_text(encoding="utf-8"))
    if "platform" in settings:
        settings["platform"]["version"] = "7.3.1"
    settings.setdefault("module28", {})["sklearn_compatibility_release"] = "7.3.1"

    SETTINGS.write_text(
        yaml.safe_dump(settings, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print("v7.3.1 version metadata applied.")


if __name__ == "__main__":
    main()
