import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    if database.exists():
        backup = database.with_name(
            database.stem + "_before_v3_0" + database.suffix
        )
        if not backup.exists():
            shutil.copy2(database, backup)
            print(f"Database backup: {backup}")
        else:
            print(f"Backup already exists: {backup}")

    conn = connect(settings)
    for schema in [
        MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
        MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
        MODULE9_SCHEMA, MODULE10_SCHEMA,
    ]:
        conn.execute(schema)
    conn.close()

    print("Crypto Intelligence Platform v3.0 installed.")
    print("Modules 1-9 and all existing data were preserved.")
    print("A separate 50-asset research universe was added without altering the six-asset core portfolio.")
    print("Derivatives, sentiment, DeFi, market-breadth, and isotonic calibration tables were created.")
    print("Predictive influence is capped at 20% until the expanded universe has sufficient validated history.")

if __name__ == "__main__":
    main()
