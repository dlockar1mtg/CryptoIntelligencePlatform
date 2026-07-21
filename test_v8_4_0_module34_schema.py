from crypto_platform.platform import load_all,connect
from crypto_platform.module34 import MODULE34_SCHEMA

EXPECTED=[
"run_id","source_module33_run_id","source_module30_run_id","started_at_utc",
"completed_at_utc","status","execution_candidate_rows","execution_daily_rows",
"trade_rows","drift_rows","cost_rows","selected_candidate_id","selected_sharpe",
"selected_max_drawdown_pct","selected_turnover_pct","btc_sharpe",
"btc_max_drawdown_pct","execution_drift_status","validation_status",
"recommendation","notes","platform_version",
]

def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE34_SCHEMA)
    cols=c.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE lower(table_name)='module34_runs' ORDER BY ordinal_position"
    ).fetchdf()["column_name"].tolist()
    c.close()
    assert cols==EXPECTED,f"module34_runs mismatch: {cols}"
    print("v8.4.0 Module 34 schema preflight passed.")
    print(f"module34_runs columns: {len(cols)}")

if __name__=="__main__":
    main()
