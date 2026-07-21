import shutil

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module30 import MODULE30_SCHEMA
from crypto_platform.ml.registry import EXPERIMENT_REGISTRY_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    backup = database.with_name(
        database.stem
        + "_before_v8_1_0"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(EXPERIMENT_REGISTRY_SCHEMA)
    conn.execute(MODULE30_SCHEMA)
    conn.close()

    print("Crypto Intelligence Platform v8.1.0 installed.")
    print("Module 30 Clean Regime Engine is ready.")
    print("Shared crypto_platform/ml utilities are installed.")
    print("The clean model begins in OBSERVATION status.")
    print("Modules 25-29 remain unchanged.")


if __name__ == "__main__":
    main()
