from pathlib import Path
import shutil
import yaml


ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "config" / "settings.yaml"


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(
            f"Missing settings: {SETTINGS}"
        )

    backup = SETTINGS.with_name(
        "settings_before_v11_0_1.yaml"
    )
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(
        SETTINGS.read_text(encoding="utf-8")
    )
    if "platform" in settings:
        settings["platform"]["version"] = "11.0.1"

    module40 = settings.setdefault(
        "module40",
        {},
    )
    module40["transactional_persistence"] = True
    module40["validate_before_commit"] = True
    module40["recover_interrupted_runs"] = True

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print("v11.0.1 configuration applied.")


if __name__ == "__main__":
    main()
