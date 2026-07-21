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
        "settings_before_v11_0_3.yaml"
    )
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"Settings backup: {backup}")

    settings = yaml.safe_load(
        SETTINGS.read_text(encoding="utf-8")
    )

    if "platform" in settings:
        settings["platform"]["version"] = "11.0.3"

    module40 = settings.setdefault("module40", {})
    module40["canonical_identity"] = [
        "forecast_date",
        "asset_id",
        "horizon_days",
    ]
    module40["canonical_rebuild_engine"] = True
    module40["model_version_is_lineage"] = True

    SETTINGS.write_text(
        yaml.safe_dump(
            settings,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    print("v11.0.3 configuration applied.")
    print(
        "Canonical memory rebuild engine enabled."
    )


if __name__ == "__main__":
    main()
