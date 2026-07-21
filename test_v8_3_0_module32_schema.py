from crypto_platform.platform import load_all,connect
from crypto_platform.module32 import MODULE32_SCHEMA

EXPECTED=[
"run_id","source_module31_run_id","source_module30_run_id","started_at_utc",
"completed_at_utc","status","feature_stability_rows","probability_drift_rows",
"retraining_policy_rows","historical_stress_rows","synthetic_stress_rows",
"benchmark_rows","best_retraining_policy","best_strategy","validation_status",
"recommendation","notes","platform_version",
]

def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE32_SCHEMA)
    cols=c.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE lower(table_name)='module32_runs' ORDER BY ordinal_position"
    ).fetchdf()["column_name"].tolist()
    c.close()
    assert cols==EXPECTED,f"module32_runs mismatch: {cols}"
    print("v8.3.0 Module 32 schema preflight passed.")
    print(f"module32_runs columns: {len(cols)}")

if __name__=="__main__":
    main()
