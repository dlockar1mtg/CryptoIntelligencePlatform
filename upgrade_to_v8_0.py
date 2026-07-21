import shutil

from crypto_platform.platform import (
    load_all,
    connect,
    path_for,
)
from crypto_platform.module29 import MODULE29_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(
        settings,
        "database_path",
    )
    backup = database.with_name(
        database.stem
        + "_before_v8_0"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(
            database,
            backup,
        )
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE29_SCHEMA)
    conn.close()

    print(
        "Crypto Intelligence Platform "
        "v8.0 installed."
    )
    print(
        "Module 29 Explainable AI Research "
        "Framework is ready."
    )
    print(
        "Modules 25-28 remain unchanged."
    )


if __name__ == "__main__":
    main()
