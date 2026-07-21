import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    if database.exists():
        backup = database.with_name(
            database.stem + "_before_v1_4" + database.suffix
        )
        if not backup.exists():
            shutil.copy2(database, backup)
            print(f"Database backup: {backup}")
        else:
            print(f"Backup already exists: {backup}")

    conn = connect(settings)
    conn.execute(MODULE2_SCHEMA)
    conn.execute(MODULE3_SCHEMA)
    conn.execute("DELETE FROM asset_risk_metrics")
    conn.execute("DELETE FROM scenario_projections")
    conn.execute("DELETE FROM portfolio_recommendations")
    conn.execute("DELETE FROM portfolio_summary")
    conn.execute("DELETE FROM valuation_zones")
    conn.execute("DELETE FROM rebalance_recommendations")
    conn.execute("DELETE FROM position_risk_contributions")
    conn.close()

    print("Crypto Intelligence Platform v1.4 installed.")
    print("Module 1 and Module 2 warehouse data were preserved.")
    print("Module 3 analytics were cleared for clean CAGR-based recalculation.")
    print("Valuation zones, dynamic DCA, rebalancing, and risk budgets were installed.")

if __name__ == "__main__":
    main()
