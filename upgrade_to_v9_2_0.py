import shutil

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module37 import MODULE37_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    backup = database.with_name(
        database.stem
        + "_before_v9_2_0"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE37_SCHEMA)
    conn.close()

    print("Crypto Intelligence Platform v9.2.0 installed.")
    print("Module 37 Institutional Portfolio Optimizer is ready.")
    print("Module 35 and 36 exporters are corrected.")
    print("Modules 25-36 and all existing data remain unchanged.")


if __name__ == "__main__":
    main()
