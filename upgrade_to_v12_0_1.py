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
        + "_before_v12_0_1"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE42_SCHEMA)
    conn.close()

    print("Crypto Intelligence Platform v12.0.1 installed.")
    print("Decision consistency guardrails are enabled.")
    print("Crypto allocation is now a ceiling, not a forced target.")
    print("HOLD and WAIT actions cannot create new-buy instructions.")
    print("Defensive summaries are blocked from material purchase plans.")


if __name__ == "__main__":
    main()
