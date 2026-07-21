import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module40 import MODULE40_SCHEMA
from crypto_platform.module41 import MODULE41_SCHEMA

def main():
    s,_=load_all();db=path_for(s,"database_path")
    b=db.with_name(db.stem+"_before_v11_0_0"+db.suffix)
    if db.exists() and not b.exists():shutil.copy2(db,b);print(f"Database backup: {b}")
    c=connect(s);c.execute(MODULE40_SCHEMA);c.execute(MODULE41_SCHEMA)

    # Identify duplicate forecast memories, preserving the latest row in each
    # canonical forecast date/asset/horizon/model-version group.
    c.execute("""
        CREATE OR REPLACE TEMP TABLE m40_duplicate_ids AS
        SELECT forecast_memory_id
        FROM (
            SELECT forecast_memory_id,
                   row_number() OVER(
                       PARTITION BY forecast_date,asset_id,horizon_days,model_version
                       ORDER BY created_at_utc DESC,forecast_memory_id DESC
                   ) AS duplicate_rank
            FROM m40_forecast_memory
        )
        WHERE duplicate_rank>1
    """)
    duplicate_count=c.execute(
        "SELECT COUNT(*) FROM m40_duplicate_ids"
    ).fetchone()[0]
    c.execute("""
        DELETE FROM m40_model_memory
        WHERE forecast_memory_id IN(
            SELECT forecast_memory_id FROM m40_duplicate_ids
        )
    """)
    c.execute("""
        DELETE FROM m40_attribution_memory
        WHERE forecast_memory_id IN(
            SELECT forecast_memory_id FROM m40_duplicate_ids
        )
    """)
    c.execute("""
        DELETE FROM m40_forecast_memory
        WHERE forecast_memory_id IN(
            SELECT forecast_memory_id FROM m40_duplicate_ids
        )
    """)
    c.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_m40_canonical_forecast
        ON m40_forecast_memory(
            forecast_date,asset_id,horizon_days,model_version
        )
    """)
    c.close()
    print("Crypto Intelligence Platform v11.0.0 installed.")
    print(f"v10.2.1 duplicate forecast memories removed: {duplicate_count}")
    print("Canonical forecast uniqueness is now enforced.")
    print("Module 41 Adaptive Meta-Learning Engine is ready.")

if __name__=="__main__":main()
