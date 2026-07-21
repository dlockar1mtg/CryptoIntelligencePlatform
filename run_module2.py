from crypto_platform.module2 import run_module2

def main():
    print("Crypto Intelligence Platform — Module 2 v2.3")
    print("Analytics, regime detection, risk, and asset scoring\n")
    result = run_module2()
    print("Module 2 summary")
    print("----------------")
    print(f"Status:          {result['status']}")
    print(f"Signal date:     {result['signal_date']}")
    print(f"Assets scored:   {result['assets_scored']}")
    print(f"Assets skipped:  {result['assets_skipped']}")
    print(f"Macro regime:    {result['macro_regime']}")
    print(f"Market regime:   {result['market_regime']}")
    print(f"Run ID:          {result['run_id']}")

if __name__ == "__main__":
    main()
