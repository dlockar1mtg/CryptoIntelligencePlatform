from crypto_platform.platform import load_all, connect
from crypto_platform.module44 import MODULE44_SCHEMA, HORIZONS


def main():
    s, _ = load_all()
    c = connect(s)
    c.execute(MODULE44_SCHEMA)
    run_cols = c.execute("SELECT COUNT(*) FROM information_schema.columns WHERE lower(table_name)='module44_runs'").fetchone()[0]
    outcome_cols = c.execute("SELECT COUNT(*) FROM information_schema.columns WHERE lower(table_name)='m44_decision_outcomes'").fetchone()[0]
    summary_cols = c.execute("SELECT COUNT(*) FROM information_schema.columns WHERE lower(table_name)='m44_economic_value_summary'").fetchone()[0]
    c.close()
    assert run_cols == 18, run_cols
    assert outcome_cols == 24, outcome_cols
    assert summary_cols == 15, summary_cols
    assert HORIZONS == [7, 30, 90, 180]
    print("v13.0.0 Module 44 schema preflight passed.")
    print(f"module44_runs columns: {run_cols}")
    print(f"decision outcome columns: {outcome_cols}")
    print(f"summary columns: {summary_cols}")
    print(f"evaluated horizons: {HORIZONS}")


if __name__ == "__main__":
    main()
