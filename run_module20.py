from crypto_platform.module20 import run_module20

def main():
    print("Crypto Intelligence Platform — Module 20 v20.0")
    print("Research maturity, model comparison, aging, and shadow testing\n")
    r=run_module20()
    print("Module 20 summary\n-----------------")
    print(f"Status:                    {r['status']}")
    print(f"Model comparison rows:     {r['model_rows']}")
    print(f"Explainability rows:       {r['explainability_rows']}")
    print(f"Redundancy rows:           {r['redundancy_rows']}")
    print(f"Evidence-aging rows:       {r['aging_rows']}")
    print(f"Shadow periods:            {r['shadow_periods']}")
    print(f"Shadow return:             {r['shadow_return_pct'] if r['shadow_return_pct'] is not None else 'N/A'}")
    print(f"Bitcoin return:            {r['btc_return_pct'] if r['btc_return_pct'] is not None else 'N/A'}")
    print(f"Shadow excess:             {r['shadow_excess_pct'] if r['shadow_excess_pct'] is not None else 'N/A'}")
    print(f"Shadow promoted:           {r['shadow_promoted']}")
    print(f"Run ID:                    {r['run_id']}")
if __name__=='__main__': main()
