import shutil

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module33 import MODULE33_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(
        settings,
        "database_path",
    )
    backup = database.with_name(
        database.stem
        + "_before_v8_3_1"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(
            database,
            backup,
        )
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE33_SCHEMA)
    conn.close()

    print(
        "Crypto Intelligence Platform "
        "v8.3.1 installed."
    )
    print(
        "Module 33 Portfolio Decision Optimization "
        "and Drift Repair is ready."
    )
    print(
        "Modules 25-32 and all existing data remain unchanged."
    )


if __name__ == "__main__":
    main()
