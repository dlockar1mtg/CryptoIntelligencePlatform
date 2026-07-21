import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    if database.exists():
        backup = database.with_name(
            database.stem + "_before_v1_2" + database.suffix
        )
        if not backup.exists():
            shutil.copy2(database, backup)
            print(f"Database backup: {backup}")
        else:
            print(f"Backup already exists: {backup}")

    conn = connect(settings)
    conn.execute(MODULE2_SCHEMA)
    conn.execute(
        "DELETE FROM provider_health "
        "WHERE provider_name IN ('shared_metals_database','dbnomics','fred_csv')"
    )
    conn.execute(
        "DELETE FROM collection_results "
        "WHERE provider_name IN ('shared_metals_database','dbnomics','fred_csv')"
    )
    conn.close()
    print("Crypto Intelligence Platform v1.2 installed.")
    print("Existing Module 1 observations were preserved.")
    print("Unused legacy macro-provider audit rows were removed.")
    print("Module 2 schema and analytical views were created.")

if __name__ == "__main__":
    main()
