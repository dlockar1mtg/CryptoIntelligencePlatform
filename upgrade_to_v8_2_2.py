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
            completed_at_utc=COALESCE(
                completed_at_utc,
                CURRENT_TIMESTAMP
            ),
            notes=COALESCE(notes,'')
                || '; Closed during v8.2.2 schema-alignment hotfix.'
        WHERE status='RUNNING'
        """
    )
    conn.close()
    print("Crypto Intelligence Platform v8.2.2 hotfix installed.")
    print("Module 31 now uses the existing 14-column v8.2 schema.")
    print("No tables were dropped or recreated.")
    print("Modules 25-30 and all existing data remain unchanged.")

if __name__ == "__main__":
    main()
