from crypto_platform.platform import load_all, connect
from crypto_platform.module43 import MODULE43_SCHEMA


EXPECTED_RUN_COLUMNS = 19


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE43_SCHEMA)

    run_columns = conn.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE lower(table_name)='module43_runs'
        """
    ).fetchone()[0]

    ranking_columns = conn.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE lower(table_name)=
              'm43_opportunity_ranking'
        """
    ).fetchone()[0]

    committee_columns = conn.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE lower(table_name)=
              'm43_committee_brief'
        """
    ).fetchone()[0]

    conn.close()

    assert run_columns == EXPECTED_RUN_COLUMNS, (
        run_columns
    )
    assert ranking_columns == 20, (
        ranking_columns
    )
    assert committee_columns == 16, (
        committee_columns
    )

    print("v12.1.0 Module 43 schema preflight passed.")
    print(f"module43_runs columns: {run_columns}")
    print(
        f"ranking columns: {ranking_columns}"
    )
    print(
        f"committee columns: {committee_columns}"
    )


if __name__ == "__main__":
    main()
