from crypto_platform.platform import load_all,connect
from crypto_platform.module41 import MODULE41_SCHEMA

def main():
    s,_=load_all();c=connect(s);c.execute(MODULE41_SCHEMA)
    count=c.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE lower(table_name)='module41_runs'"
    ).fetchone()[0]
    duplicates=c.execute("""
        SELECT COUNT(*) FROM(
            SELECT forecast_date,asset_id,horizon_days,model_version,COUNT(*) n
            FROM m40_forecast_memory
            GROUP BY ALL HAVING COUNT(*)>1
        )
    """).fetchone()[0]
    c.close()
    assert count==16,count
    assert duplicates==0,duplicates
    print("v11.0.0 schema and forecast-memory idempotency preflight passed.")
    print(f"module41_runs columns: {count}")
    print(f"duplicate canonical forecasts: {duplicates}")

if __name__=="__main__":main()
