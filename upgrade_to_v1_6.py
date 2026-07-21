import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    if database.exists():
        backup = database.with_name(
            database.stem + "_before_v1_6" + database.suffix
        )
        if not backup.exists():
            shutil.copy2(database, backup)
            print(f"Database backup: {backup}")
        else:
            print(f"Backup already exists: {backup}")

    conn = connect(settings)
    for schema in [MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA, MODULE6_SCHEMA]:
        conn.execute(schema)
    conn.close()

    print("Crypto Intelligence Platform v1.6 installed.")
    print("Modules 1-5 data were preserved.")
    print("Canonical history, daily snapshots, cycle transitions, and validation tables were created.")

if __name__ == "__main__":
    main()
