from crypto_platform.module44 import run_module44


def main():
    print("Crypto Intelligence Platform — Module 44 v44.0")
    print("Economic Value & Strategy Validation Engine\n")
    r = run_module44()
    print("Module 44 summary")
    print("-----------------")
    print(f"Matured decisions:          {int(r['matured_decisions'])}")
    print(f"Pending decisions:          {int(r['pending_decisions'])}")
    print(f"Positive-value rate:        {r['economic_value_positive_rate_pct']}")
    print(f"Excess vs cash:             {r['mean_excess_vs_cash_pct']}")
    print(f"Excess vs buy-and-hold:     {r['mean_excess_vs_buy_hold_pct']}")
    print(f"Best action:                {r['best_action']}")
    print(f"Best horizon:               {int(r['best_horizon_days'])} days")
    print(f"Economic value score:       {r['economic_value_score']}")
    print(f"Evidence status:            {r['evidence_status']}")
    print(f"Economic value status:      {r['economic_value_status']}")
    print(f"Recommendation:             {r['advancement_recommendation']}")


if __name__ == "__main__":
    main()
