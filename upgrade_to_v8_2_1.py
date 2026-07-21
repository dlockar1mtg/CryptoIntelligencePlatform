from crypto_platform.platform import load_all, connect
from crypto_platform.module31 import MODULE31_SCHEMA

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE31_SCHEMA)
    conn.execute(
        """
        UPDATE module31_runs
        SET status='FAILED',
            completed_at_utc=COALESCE(completed_at_utc, CURRENT_TIMESTAMP)
        WHERE status='RUNNING'
        """
    )
    conn.close()
    print("Crypto Intelligence Platform v8.2.1 hotfix installed.")
    print("Module 31 run-start insert now matches the 14-column schema.")
    print("No Module 30 or earlier data was changed.")

if __name__ == "__main__":
    main()
