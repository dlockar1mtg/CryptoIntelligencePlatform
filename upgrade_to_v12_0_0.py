import shutil

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module42 import MODULE42_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(
        settings,
        "database_path",
    )
    backup = database.with_name(
        database.stem
        + "_before_v12_0_0"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE42_SCHEMA)
    conn.close()

    print(
        "Crypto Intelligence Platform "
        "v12.0.0 installed."
    )
    print(
        "Module 42 Investment Decision & "
        "Long-Range Projection Engine is ready."
    )
    print(
        "Modules 25-41 and all existing "
        "forecast memory remain unchanged."
    )


if __name__ == "__main__":
    main()
