from crypto_platform.module21 import run_module21

def main():
    print("Crypto Intelligence Platform — Module 21 v21.0")
    print("Investment Decision Engine: regimes, probabilities, risk, and sizing\n")
    result = run_module21()
    print("Module 21 summary")
    print("-----------------")
    print(f"Status:                    {result['status']}")
    print(f"Governed features:         {result['governed_features']}")
    print(f"Probability models:        {result['probability_models']}")
    print(f"Current stance:            {result['stance']}")
    print(f"Decision confidence:       {result['confidence']:.1f}%")
    print(f"Dominant regime:           {result['dominant_regime']}")
    print(f"Target BTC weight:         {result['btc_weight']*100:.2f}%")
    print(f"Target cash weight:        {result['cash_weight']*100:.2f}%")
    print(f"Risk score:                {result['risk_score']:.1f}")
    print(f"Shadow periods:            {result['shadow_periods']}")
    print(f"Shadow return:             {result['shadow_return_pct']}")
    print(f"Bitcoin return:            {result['btc_return_pct']}")
    print(f"Shadow excess:             {result['shadow_excess_pct']}")
    print(f"Promotion candidate:       {result['promoted']}")
    print(f"Run ID:                    {result['run_id']}")

if __name__ == "__main__":
    main()
