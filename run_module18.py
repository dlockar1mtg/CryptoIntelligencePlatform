from crypto_platform.module18 import run_module18

def main():
    print('Crypto Intelligence Platform — Module 18 v18.0')
    print('Feature quality, interactions, importance, and regime stability\n')
    r=run_module18()
    print('Module 18 summary')
    print('-----------------')
    print(f"Status:                    {r['status']}")
    print(f"Stablecoin history rows:   {r['stablecoin_history_rows']}")
    print(f"Corrected readiness rows:  {r['readiness_rows']}")
    print(f"Interaction rows:          {r['interaction_rows']}")
    print(f"Permutation rows:          {r['permutation_rows']}")
    print(f"Regime rows:               {r['regime_rows']}")
    print(f"Run ID:                    {r['run_id']}")
if __name__=='__main__': main()
