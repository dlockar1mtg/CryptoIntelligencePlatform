import shutil

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module43 import MODULE43_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(
        settings,
        "database_path",
    )
    backup = database.with_name(
        database.stem
        + "_before_v12_1_0"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE43_SCHEMA)
    conn.close()

    print(
        "Crypto Intelligence Platform "
        "v12.1.0 installed."
    )
    print(
        "Module 43 Institutional Decision "
        "Intelligence is ready."
    )
    print(
        "Module 42 allocation guardrails "
        "remain unchanged."
    )


if __name__ == "__main__":
    main()
