import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    if database.exists():
        backup = database.with_name(
            database.stem + "_before_v1_7" + database.suffix
        )
        if not backup.exists():
            shutil.copy2(database, backup)
            print(f"Database backup: {backup}")
        else:
            print(f"Backup already exists: {backup}")

    conn = connect(settings)
    for schema in [
        MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
        MODULE6_SCHEMA, MODULE7_SCHEMA,
    ]:
        conn.execute(schema)
    conn.close()

    print("Crypto Intelligence Platform v1.7 installed.")
    print("Modules 1-6 and all historical research data were preserved.")
    print("Calibration, feature-importance, walk-forward, and valuation-validation tables were created.")
    print("Learned thresholds are advisory by default and do not silently replace live thresholds.")

if __name__ == "__main__":
    main()
