from crypto_platform.module17 import run_module17

def main():
    print("Crypto Intelligence Platform — Module 17 v17.0")
    print("Feature collection, feature warehouse, and predictive validation\n")
    r = run_module17()
    print("Module 17 summary")
    print("-----------------")
    print(f"Status:                 {r['status']}")
    print(f"Fear & Greed rows:      {r['fear_greed_rows']}")
    print(f"Manual ETF rows:        {r['manual_etf_rows']}")
    print(f"Feature rows:           {r['feature_rows']}")
    print(f"Validation rows:        {r['validation_rows']}")
    print(f"Research-ready features:{r['ready_features']}")
    print(f"Run ID:                 {r['run_id']}")

if __name__ == "__main__":
    main()
