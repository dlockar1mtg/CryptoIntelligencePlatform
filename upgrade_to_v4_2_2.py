import shutil
from crypto_platform.platform import (
    load_all, connect, path_for
)
from crypto_platform.module19 import MODULE19_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(
        settings, "database_path"
    )
    backup = database.with_name(
        database.stem
        + "_before_v4_2_2"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE19_SCHEMA)
    conn.close()

    print(
        "Crypto Intelligence Platform "
        "v4.2.2 installed."
    )
    print(
        "Feature registry and rolling "
        "promotion validation are ready."
    )
    print(
        "Live Module 13 scoring remains unchanged."
    )

if __name__ == "__main__":
    main()
