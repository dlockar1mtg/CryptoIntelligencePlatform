import shutil

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module39 import MODULE39_SCHEMA
from crypto_platform.module40 import MODULE40_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(
        settings,
        "database_path",
    )
    backup = database.with_name(
        database.stem
        + "_before_v10_2_0"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(
            database,
            backup,
        )
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE39_SCHEMA)
    conn.execute(MODULE40_SCHEMA)
    conn.close()

    print("Crypto Intelligence Platform v10.2.0 installed.")
    print("v10.1.1 Module 39 corrections are installed.")
    print("Module 40 Forecast Memory & Continuous Learning is ready.")
    print("Modules 25-39 and all existing data remain unchanged.")


if __name__ == "__main__":
    main()
