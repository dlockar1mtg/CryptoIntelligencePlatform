from crypto_platform.module32 import run_module32

def main():
    print("Crypto Intelligence Platform — Module 32 v32.0")
    print("Validation Hardening & Benchmark Intelligence\n")
    r=run_module32()
    print("Module 32 summary")
    print("-----------------")
    print(f"Stable features evaluated:       {int(r['stable_features'])}")
    print(f"Mean feature stability:          {r['mean_feature_stability_score']:.2f}")
    print(f"Current probability drift:       {r['current_probability_drift_status']}")
    print(f"Best retraining policy:          {r['best_retraining_policy']}")
    print(f"Best retraining log loss:        {r['best_retraining_log_loss']:.4f}")
    print(f"Historical stress episodes:      {int(r['historical_stress_episodes'])}")
    print(f"Synthetic stress pass rate:      {r['synthetic_stress_pass_rate_pct']:.2f}%")
    print(f"Best validated strategy:         {r['best_strategy']}")
    print(f"Best strategy Sharpe:            {r['best_strategy_sharpe']:.4f}")
    print(f"BTC buy-and-hold Sharpe:         {r['btc_sharpe']:.4f}")
    print(f"Best strategy max drawdown:      {r['best_strategy_max_drawdown_pct']:.2f}%")
    print(f"BTC max drawdown:                {r['btc_max_drawdown_pct']:.2f}%")
    print(f"Validation status:               {r['validation_status']}")
    print(f"Recommendation:                  {r['advancement_recommendation']}")

if __name__=="__main__":
    main()
