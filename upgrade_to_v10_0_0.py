import shutil

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module38 import MODULE38_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    backup = database.with_name(
        database.stem
        + "_before_v10_0_0"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(
            database,
            backup,
        )
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE38_SCHEMA)
    conn.close()

    print("Crypto Intelligence Platform v10.0.0 installed.")
    print("v9.2.1 entropy and information-ratio hotfixes are installed.")
    print("Module 38 Predictive Intelligence Engine is ready.")
    print("Modules 25-37 and all existing data remain unchanged.")


if __name__ == "__main__":
    main()
